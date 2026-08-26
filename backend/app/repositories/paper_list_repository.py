import uuid
from dataclasses import dataclass

from sqlalchemy import String, asc, cast, desc, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Author, Document, Folder, Keyword, Note, Paper, PaperAuthor, PaperFolder, PaperKeyword, PaperTag, Tag


@dataclass
class PaperListQueryResult:
    items: list[tuple[Paper, int]]
    total: int


class PaperListRepository:
    SORT_COLUMNS = {
        "title": Paper.title,
        "title_zh": Paper.title_zh,
        "publication_year": Paper.publication_year,
        "journal": Paper.journal,
        "conference": Paper.conference,
        "citation_count": Paper.citation_count,
        "reading_status": Paper.reading_status,
        "created_at": Paper.created_at,
        "updated_at": Paper.updated_at,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_rows(self, user_id: uuid.UUID, *, q: str | None, year_from: int | None, year_to: int | None,
                        journal: str | None, author: str | None, tag_id: uuid.UUID | None, keyword: str | None,
                        reading_status: str | None, starred: bool | None, sort: str, order: str,
                        offset: int, limit: int) -> PaperListQueryResult:
        note_count = select(func.count(Note.id)).where(Note.paper_id == Paper.id, Note.user_id == user_id).correlate(Paper).scalar_subquery()
        filters = [Paper.user_id == user_id]

        def author_exists(pattern: str):
            return exists(select(PaperAuthor.id).join(Author, Author.id == PaperAuthor.author_id).where(PaperAuthor.paper_id == Paper.id, Author.name.ilike(pattern)))
        def tag_exists(pattern: str | None = None):
            conditions = [PaperTag.paper_id == Paper.id, Tag.user_id == user_id]
            if tag_id: conditions.append(PaperTag.tag_id == tag_id)
            if pattern: conditions.append(Tag.name.ilike(pattern))
            return exists(select(PaperTag.id).join(Tag, Tag.id == PaperTag.tag_id).where(*conditions))
        def keyword_exists(pattern: str):
            return exists(select(PaperKeyword.id).join(Keyword, Keyword.id == PaperKeyword.keyword_id).where(PaperKeyword.paper_id == Paper.id, Keyword.user_id == user_id, Keyword.display_name.ilike(pattern)))
        def folder_exists(pattern: str):
            return exists(select(PaperFolder.id).join(Folder, Folder.id == PaperFolder.folder_id).where(PaperFolder.paper_id == Paper.id, Folder.user_id == user_id, Folder.name.ilike(pattern)))

        if q and q.strip():
            pattern = f"%{q.strip()}%"
            filters.append(or_(Paper.title.ilike(pattern), Paper.title_zh.ilike(pattern), Paper.abstract.ilike(pattern),
                Paper.journal.ilike(pattern), Paper.conference.ilike(pattern), Paper.publisher.ilike(pattern),
                cast(Paper.publication_year, String).ilike(pattern), Paper.doi.ilike(pattern), Paper.arxiv_id.ilike(pattern),
                Paper.citation_text.ilike(pattern), author_exists(pattern), tag_exists(pattern), keyword_exists(pattern), folder_exists(pattern),
                exists(select(Note.id).where(Note.paper_id == Paper.id, Note.user_id == user_id, Note.title.ilike(pattern)))))
        if year_from is not None: filters.append(Paper.publication_year >= year_from)
        if year_to is not None: filters.append(Paper.publication_year <= year_to)
        if journal: filters.append(Paper.journal.ilike(f"%{journal.strip()}%"))
        if author: filters.append(author_exists(f"%{author.strip()}%"))
        if tag_id: filters.append(tag_exists())
        if keyword: filters.append(keyword_exists(f"%{keyword.strip()}%"))
        if reading_status: filters.append(Paper.reading_status == reading_status)
        if starred is not None: filters.append(Paper.is_starred == starred)

        total = int(await self.db.scalar(select(func.count(Paper.id)).where(*filters)) or 0)
        column = self.SORT_COLUMNS[sort]
        direction = asc if order == "asc" else desc
        stmt = (select(Paper, note_count.label("note_count")).where(*filters)
            .options(selectinload(Paper.authors).selectinload(PaperAuthor.author),
                     selectinload(Paper.tags).selectinload(PaperTag.tag),
                     selectinload(Paper.folder_assignments).selectinload(PaperFolder.folder),
                     selectinload(Paper.keywords).selectinload(PaperKeyword.keyword),
                     selectinload(Paper.documents).load_only(Document.id))
            .order_by(direction(column).nulls_last(), desc(Paper.id)).offset(offset).limit(limit))
        rows = (await self.db.execute(stmt)).all()
        return PaperListQueryResult(items=[(row[0], int(row[1] or 0)) for row in rows], total=total)
