import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaperTag, Tag


class TagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: uuid.UUID) -> list[Tag]:
        result = await self.db.execute(select(Tag).where(Tag.user_id == user_id).order_by(Tag.name))
        return list(result.scalars().all())

    async def get_for_user(self, tag_id: uuid.UUID, user_id: uuid.UUID) -> Tag | None:
        return await self.db.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))

    async def get_by_normalized_name(self, user_id: uuid.UUID, normalized_name: str) -> Tag | None:
        return await self.db.scalar(
            select(Tag).where(Tag.user_id == user_id, Tag.normalized_name == normalized_name)
        )

    async def create(self, user_id: uuid.UUID, name: str, normalized_name: str, color: str | None) -> Tag:
        tag = Tag(user_id=user_id, name=name, normalized_name=normalized_name, color=color)
        self.db.add(tag)
        await self.db.flush()
        return tag

    async def update(self, tag: Tag, **values: object) -> Tag:
        for key, value in values.items():
            setattr(tag, key, value)
        await self.db.flush()
        return tag

    async def delete(self, tag: Tag) -> None:
        await self.db.delete(tag)

    async def paper_counts(self, tag_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not tag_ids:
            return {}
        result = await self.db.execute(
            select(PaperTag.tag_id, func.count(PaperTag.id))
            .where(PaperTag.tag_id.in_(tag_ids))
            .group_by(PaperTag.tag_id)
        )
        return dict(result.all())
