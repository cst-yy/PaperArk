import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MemoNotFoundError, PaperNotFoundError, RevisionConflictError
from app.models import Memo, Paper
from app.repositories.memo_repository import MemoRepository
from app.schemas.memo import MemoCreate, MemoResponse, MemoUpdate


class MemoService:
    def __init__(self, db: AsyncSession): self.db, self.repo = db, MemoRepository(db)

    async def list(self, user_id: uuid.UUID, limit: int):
        return [MemoResponse.model_validate(item).model_copy(update={"related_paper_title": title}) for item, title in await self.repo.list(user_id, limit)]

    async def create(self, user_id: uuid.UUID, data: MemoCreate):
        await self._paper(user_id, data.related_paper_id)
        item = Memo(user_id=user_id, **data.model_dump())
        self.db.add(item); await self.db.flush(); await self.db.refresh(item)
        return MemoResponse.model_validate(item)

    async def update(self, user_id: uuid.UUID, item_id: uuid.UUID, data: MemoUpdate):
        existing = await self.repo.get(user_id, item_id)
        if not existing: raise MemoNotFoundError("Memo not found")
        values = data.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "related_paper_id" in values: await self._paper(user_id, values["related_paper_id"])
        item = await self.repo.update(user_id, item_id, data.expected_revision, values)
        if not item: raise RevisionConflictError("Memo changed in another tab")
        return MemoResponse.model_validate(item)

    async def delete(self, user_id: uuid.UUID, item_id: uuid.UUID):
        item = await self.repo.get(user_id, item_id)
        if not item: raise MemoNotFoundError("Memo not found")
        await self.db.delete(item)

    async def _paper(self, user_id: uuid.UUID, paper_id: uuid.UUID | None):
        if paper_id is not None and not await self.db.scalar(select(Paper.id).where(Paper.id == paper_id, Paper.user_id == user_id)):
            raise PaperNotFoundError("Paper not found")
