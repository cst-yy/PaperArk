import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Memo, Paper


class MemoRepository:
    def __init__(self, db: AsyncSession): self.db = db

    async def list(self, user_id: uuid.UUID, limit: int):
        result = await self.db.execute(select(Memo, Paper.title).outerjoin(Paper, Paper.id == Memo.related_paper_id).where(Memo.user_id == user_id).order_by(Memo.pinned.desc(), Memo.updated_at.desc(), Memo.id.desc()).limit(limit))
        return list(result.all())

    async def get(self, user_id: uuid.UUID, item_id: uuid.UUID):
        return await self.db.scalar(select(Memo).where(Memo.id == item_id, Memo.user_id == user_id))

    async def update(self, user_id: uuid.UUID, item_id: uuid.UUID, revision: int, values: dict):
        result = await self.db.execute(update(Memo).where(Memo.id == item_id, Memo.user_id == user_id, Memo.revision == revision).values(**values, revision=Memo.revision + 1, updated_at=datetime.now().astimezone()).returning(Memo))
        return result.scalar_one_or_none()
