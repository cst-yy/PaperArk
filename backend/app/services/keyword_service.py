import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.taxonomy import normalize_taxonomy_name
from app.repositories.keyword_repository import KeywordRepository
from app.schemas.keyword import KeywordInput, KeywordResponse


class KeywordService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = KeywordRepository(db)

    async def list_keywords(self, user_id: uuid.UUID) -> list[KeywordResponse]:
        return [
            KeywordResponse(id=item.id, display_name=item.display_name, created_at=item.created_at)
            for item in await self.repo.list_for_user(user_id)
        ]

    async def get_or_create(self, user_id: uuid.UUID, item: KeywordInput):
        return await self.repo.get_or_create(
            user_id=user_id,
            display_name=item.name.strip(),
            normalized_name=normalize_taxonomy_name(item.name),
        )


def get_keyword_service(db: AsyncSession = Depends(get_db)) -> KeywordService:
    return KeywordService(db)
