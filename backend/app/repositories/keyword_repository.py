import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Keyword, PaperKeyword


class KeywordRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: uuid.UUID) -> list[Keyword]:
        result = await self.db.execute(
            select(Keyword).where(Keyword.user_id == user_id).order_by(Keyword.display_name)
        )
        return list(result.scalars().all())

    async def get_by_normalized_name(
        self, user_id: uuid.UUID, normalized_name: str
    ) -> Keyword | None:
        return await self.db.scalar(
            select(Keyword).where(
                Keyword.user_id == user_id,
                Keyword.normalized_name == normalized_name,
            )
        )

    async def get_for_user(self, keyword_id: uuid.UUID, user_id: uuid.UUID) -> Keyword | None:
        return await self.db.scalar(
            select(Keyword).where(Keyword.id == keyword_id, Keyword.user_id == user_id)
        )

    async def delete(self, keyword: Keyword) -> None:
        await self.db.delete(keyword)
        await self.db.flush()

    async def get_or_create(
        self, user_id: uuid.UUID, display_name: str, normalized_name: str
    ) -> Keyword:
        keyword = await self.get_by_normalized_name(user_id, normalized_name)
        if keyword:
            return keyword
        keyword = Keyword(
            user_id=user_id,
            display_name=display_name,
            normalized_name=normalized_name,
        )
        self.db.add(keyword)
        await self.db.flush()
        return keyword

    async def replace_manual_for_paper(
        self, paper_id: uuid.UUID, keyword_ids: list[uuid.UUID]
    ) -> None:
        current_ids = set(
            (await self.db.execute(
                select(PaperKeyword.keyword_id).where(
                    PaperKeyword.paper_id == paper_id,
                    PaperKeyword.source == "manual",
                )
            )).scalars().all()
        )
        desired_ids = set(keyword_ids)
        stale_ids = current_ids - desired_ids
        if stale_ids:
            await self.db.execute(
                delete(PaperKeyword).where(
                    PaperKeyword.paper_id == paper_id,
                    PaperKeyword.source == "manual",
                    PaperKeyword.keyword_id.in_(stale_ids),
                )
            )
        for keyword_id in desired_ids - current_ids:
            self.db.add(
                PaperKeyword(paper_id=paper_id, keyword_id=keyword_id, source="manual")
            )
        await self.db.flush()

    async def replace_source_for_paper(
        self, paper_id: uuid.UUID, keyword_ids: list[uuid.UUID], source: str
    ) -> None:
        """Replace one derived keyword source without touching manual links."""
        current_ids = set(
            (await self.db.execute(
                select(PaperKeyword.keyword_id).where(
                    PaperKeyword.paper_id == paper_id,
                    PaperKeyword.source == source,
                )
            )).scalars().all()
        )
        desired_ids = set(keyword_ids)
        stale_ids = current_ids - desired_ids
        if stale_ids:
            await self.db.execute(
                delete(PaperKeyword).where(
                    PaperKeyword.paper_id == paper_id,
                    PaperKeyword.source == source,
                    PaperKeyword.keyword_id.in_(stale_ids),
                )
            )
        for keyword_id in desired_ids - current_ids:
            self.db.add(PaperKeyword(paper_id=paper_id, keyword_id=keyword_id, source=source))
        await self.db.flush()
