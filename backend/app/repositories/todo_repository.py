import uuid
from datetime import datetime

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Paper, Todo


class TodoRepository:
    def __init__(self, db: AsyncSession): self.db = db

    async def list(self, user_id: uuid.UUID, completed: bool, limit: int):
        overdue = case((Todo.due_at < datetime.now().astimezone(), 0), else_=1)
        priority = case((Todo.priority == "high", 0), (Todo.priority == "normal", 1), else_=2)
        result = await self.db.execute(select(Todo, Paper.title).outerjoin(Paper, Paper.id == Todo.related_paper_id).where(Todo.user_id == user_id, Todo.completed == completed).order_by(overdue, Todo.due_at.asc().nullslast(), priority, Todo.position, Todo.created_at.desc(), Todo.id.desc()).limit(limit))
        return list(result.all())

    async def get(self, user_id: uuid.UUID, item_id: uuid.UUID):
        return await self.db.scalar(select(Todo).where(Todo.id == item_id, Todo.user_id == user_id))

    async def update(self, user_id: uuid.UUID, item_id: uuid.UUID, revision: int, values: dict):
        result = await self.db.execute(update(Todo).where(Todo.id == item_id, Todo.user_id == user_id, Todo.revision == revision).values(**values, revision=Todo.revision + 1, updated_at=datetime.now().astimezone()).returning(Todo))
        return result.scalar_one_or_none()
