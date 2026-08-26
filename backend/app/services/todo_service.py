import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaperNotFoundError, RevisionConflictError, TodoNotFoundError
from app.models import Paper, Todo
from app.repositories.todo_repository import TodoRepository
from app.schemas.todo import TodoCreate, TodoResponse, TodoUpdate


class TodoService:
    def __init__(self, db: AsyncSession): self.db, self.repo = db, TodoRepository(db)

    async def list(self, user_id: uuid.UUID, completed: bool, limit: int):
        return [TodoResponse.model_validate(item).model_copy(update={"related_paper_title": title}) for item, title in await self.repo.list(user_id, completed, limit)]

    async def create(self, user_id: uuid.UUID, data: TodoCreate):
        await self._paper(user_id, data.related_paper_id)
        item = Todo(user_id=user_id, **data.model_dump())
        self.db.add(item); await self.db.flush(); await self.db.refresh(item)
        return TodoResponse.model_validate(item)

    async def update(self, user_id: uuid.UUID, item_id: uuid.UUID, data: TodoUpdate):
        existing = await self.repo.get(user_id, item_id)
        if not existing: raise TodoNotFoundError("Todo not found")
        values = data.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "related_paper_id" in values: await self._paper(user_id, values["related_paper_id"])
        if values.get("completed") is True: values["completed_at"] = datetime.now().astimezone()
        elif values.get("completed") is False: values["completed_at"] = None
        item = await self.repo.update(user_id, item_id, data.expected_revision, values)
        if not item: raise RevisionConflictError("Todo changed in another tab")
        return TodoResponse.model_validate(item)

    async def delete(self, user_id: uuid.UUID, item_id: uuid.UUID):
        item = await self.repo.get(user_id, item_id)
        if not item: raise TodoNotFoundError("Todo not found")
        await self.db.delete(item)

    async def _paper(self, user_id: uuid.UUID, paper_id: uuid.UUID | None):
        if paper_id is not None and not await self.db.scalar(select(Paper.id).where(Paper.id == paper_id, Paper.user_id == user_id)):
            raise PaperNotFoundError("Paper not found")
