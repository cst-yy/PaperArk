import math
import uuid
import json

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.paper_list_repository import PaperListRepository
from app.schemas.paper import AuthorBrief
from app.schemas.paper_list import PaperListNamedItem, PaperListPage, PaperListRow
from app.schemas.paper_list import BatchPaperUpdate, PaperListPreference, PaperListViewSettings, PaperListViewSettingsPatch
from app.models import Setting
from app.services.paper_service import PaperService
from sqlalchemy import select

_PREFERENCE_KEY = "paper_list.preference"
_VIEW_SETTINGS_KEY = "paper_list.view_settings.v2"


class PaperListService:
    def __init__(self, db: AsyncSession):
        self.repo = PaperListRepository(db)

    async def list_rows(self, user_id: uuid.UUID, **query) -> PaperListPage:
        page = query.pop("page")
        page_size = query.pop("page_size")
        result = await self.repo.list_rows(user_id, offset=(page - 1) * page_size, limit=page_size, **query)
        items = []
        for paper, note_count in result.items:
            authors = sorted(paper.authors, key=lambda link: (link.author_order, str(link.id)))
            items.append(PaperListRow(
                id=paper.id, title=paper.title, title_zh=paper.title_zh,
                authors=[AuthorBrief(id=link.author.id, name=link.author.name, orcid=link.author.orcid, affiliation=link.author.affiliation, author_order=link.author_order) for link in authors],
                journal=paper.journal, conference=paper.conference, publication_year=paper.publication_year,
                doi=paper.doi, arxiv_id=paper.arxiv_id, url=paper.url, publisher=paper.publisher,
                abstract=paper.abstract, citation_text=paper.citation_text, citation_count=paper.citation_count,
                keywords=[PaperListNamedItem(id=link.keyword.id, name=link.keyword.display_name) for link in paper.keywords],
                tags=[PaperListNamedItem(id=link.tag.id, name=link.tag.name) for link in paper.tags],
                folders=[PaperListNamedItem(id=link.folder.id, name=link.folder.name) for link in paper.folder_assignments],
                status=paper.status, reading_status=paper.reading_status, starred=paper.is_starred,
                note_count=note_count, has_document=bool(paper.documents), created_at=paper.created_at, updated_at=paper.updated_at,
                metadata_revision=paper.metadata_revision,
            ))
        return PaperListPage(items=items, total=result.total, page=page, page_size=page_size,
                             total_pages=math.ceil(result.total / page_size) if result.total else 0)

    async def get_preference(self, user_id: uuid.UUID) -> PaperListPreference:
        value = (await self.repo.db.execute(select(Setting.value).where(
            Setting.user_id == user_id, Setting.key == _PREFERENCE_KEY
        ))).scalar_one_or_none()
        if not value:
            return PaperListPreference()
        try:
            return PaperListPreference.model_validate_json(value)
        except Exception:
            return PaperListPreference()

    async def save_preference(self, user_id: uuid.UUID, preference: PaperListPreference) -> PaperListPreference:
        setting = (await self.repo.db.execute(select(Setting).where(
            Setting.user_id == user_id, Setting.key == _PREFERENCE_KEY
        ))).scalar_one_or_none()
        serialized = preference.model_dump_json()
        if setting:
            setting.value = serialized
        else:
            self.repo.db.add(Setting(user_id=user_id, key=_PREFERENCE_KEY, value=serialized))
        await self.repo.db.flush()
        return preference

    async def get_view_settings(self, user_id: uuid.UUID) -> PaperListViewSettings:
        value = (await self.repo.db.execute(select(Setting.value).where(
            Setting.user_id == user_id, Setting.key == _VIEW_SETTINGS_KEY
        ))).scalar_one_or_none()
        if not value:
            legacy = await self.get_preference(user_id)
            return PaperListViewSettings(
                columns={"visible": legacy.visible_columns, "order": legacy.column_order},
                appearance=legacy.appearance,
            )
        try:
            return PaperListViewSettings.model_validate_json(value)
        except Exception:
            return PaperListViewSettings()

    async def patch_view_settings(
        self, user_id: uuid.UUID, patch: PaperListViewSettingsPatch
    ) -> PaperListViewSettings:
        setting = (await self.repo.db.execute(
            select(Setting).where(
                Setting.user_id == user_id, Setting.key == _VIEW_SETTINGS_KEY
            ).with_for_update()
        )).scalar_one_or_none()
        current = PaperListViewSettings()
        if setting:
            try:
                current = PaperListViewSettings.model_validate_json(setting.value)
            except Exception:
                current = PaperListViewSettings()
        if current.revision != patch.expected_revision:
            from app.core.exceptions import RevisionConflictError
            raise RevisionConflictError("Paper List settings changed in another tab")
        next_value = current.model_copy(deep=True)
        for section in ("columns", "appearance", "query", "layout"):
            value = getattr(patch, section)
            if value is not None:
                setattr(next_value, section, value)
        next_value.revision = current.revision + 1
        serialized = next_value.model_dump_json()
        if setting:
            setting.value = serialized
        else:
            self.repo.db.add(Setting(user_id=user_id, key=_VIEW_SETTINGS_KEY, value=serialized))
        await self.repo.db.flush()
        return next_value

    async def batch_update(self, user_id: uuid.UUID, data: BatchPaperUpdate) -> int:
        service = PaperService(self.repo.db)
        papers = []
        for paper_id in data.paper_ids:
            paper = await service.repo.get_raw(paper_id, user_id)
            if paper is None:
                from app.core.exceptions import PaperNotFoundError
                raise PaperNotFoundError(f"Paper {paper_id} not found")
            papers.append(paper)
        valid_tags = await service.repo.validate_tags_for_user(data.add_tag_ids + data.remove_tag_ids, user_id)
        if {item.id for item in valid_tags} != set(data.add_tag_ids + data.remove_tag_ids):
            from app.core.exceptions import InvalidTagError
            raise InvalidTagError("One or more tags do not exist or belong to another user")
        valid_folders = await service.repo.validate_folders_for_user(data.add_folder_ids + data.remove_folder_ids, user_id)
        if {item.id for item in valid_folders} != set(data.add_folder_ids + data.remove_folder_ids):
            from app.core.exceptions import InvalidFolderError
            raise InvalidFolderError("One or more folders do not exist or belong to another user")
        async with self.repo.db.begin_nested():
            for paper in papers:
                if data.reading_status is not None:
                    paper.reading_status = data.reading_status
                if data.starred is not None:
                    paper.is_starred = data.starred
                for tag_id in data.add_tag_ids:
                    await service.repo.add_tag(paper.id, tag_id)
                for tag_id in data.remove_tag_ids:
                    await service.repo.remove_tag(paper.id, tag_id)
                for folder_id in data.add_folder_ids:
                    await service.repo.add_folder(paper.id, folder_id)
                for folder_id in data.remove_folder_ids:
                    await service.repo.remove_folder(paper.id, folder_id)
                paper.metadata_revision += 1
            await self.repo.db.flush()
        return len(papers)


def get_paper_list_service(db: AsyncSession = Depends(get_db)) -> PaperListService:
    return PaperListService(db)
