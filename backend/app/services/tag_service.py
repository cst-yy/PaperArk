import uuid

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DuplicateTagError, TagNotFoundError
from app.core.taxonomy import normalize_taxonomy_name
from app.repositories.tag_repository import TagRepository
from app.schemas.tag import TagCreate, TagResponse, TagUpdate


def normalize_tag_name(value: str) -> str:
    """Compatibility wrapper for the shared taxonomy identity rule."""
    return normalize_taxonomy_name(value)


class TagService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TagRepository(db)

    @staticmethod
    def _response(tag, paper_count: int = 0) -> TagResponse:
        return TagResponse(id=tag.id, name=tag.name, color=tag.color, paper_count=paper_count)

    async def list_tags(self, user_id: uuid.UUID) -> list[TagResponse]:
        tags = await self.repo.list_for_user(user_id)
        counts = await self.repo.paper_counts([tag.id for tag in tags])
        return [self._response(tag, counts.get(tag.id, 0)) for tag in tags]

    async def create_tag(self, user_id: uuid.UUID, data: TagCreate) -> TagResponse:
        normalized_name = normalize_tag_name(data.name)
        if await self.repo.get_by_normalized_name(user_id, normalized_name):
            raise DuplicateTagError(data.name)
        try:
            tag = await self.repo.create(user_id, data.name, normalized_name, data.color)
        except IntegrityError as exc:
            await self.db.rollback()
            raise DuplicateTagError(data.name) from exc
        return self._response(tag)

    async def update_tag(self, user_id: uuid.UUID, tag_id: uuid.UUID, data: TagUpdate) -> TagResponse:
        tag = await self.repo.get_for_user(tag_id, user_id)
        if not tag:
            raise TagNotFoundError(f"Tag {tag_id} not found")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            normalized_name = normalize_tag_name(update_data["name"])
            duplicate = await self.repo.get_by_normalized_name(user_id, normalized_name)
            if duplicate and duplicate.id != tag.id:
                raise DuplicateTagError(update_data["name"])
            update_data["normalized_name"] = normalized_name
        try:
            tag = await self.repo.update(tag, **update_data)
        except IntegrityError as exc:
            await self.db.rollback()
            raise DuplicateTagError(update_data.get("name", tag.name)) from exc
        return self._response(tag)

    async def delete_tag(self, user_id: uuid.UUID, tag_id: uuid.UUID) -> None:
        tag = await self.repo.get_for_user(tag_id, user_id)
        if not tag:
            raise TagNotFoundError(f"Tag {tag_id} not found")
        await self.repo.delete(tag)


def get_tag_service(db: AsyncSession = Depends(get_db)) -> TagService:
    return TagService(db)
