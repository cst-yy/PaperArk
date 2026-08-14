"""Paper repository - data access layer for papers.

All queries include user_id scoping. The API layer should never write SQL;
it calls methods here through the service layer.
"""

import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Author,
    Document,
    Paper,
    PaperAuthor,
    PaperFolder,
    PaperKeyword,
    PaperTag,
    Tag,
    Keyword,
    Folder,
)


# ── Helpers ──

# Match a standard ORCID ID: 0000-0002-1825-0097 (last char may be X)
_ORCID_RE = re.compile(
    r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", re.IGNORECASE
)


def normalize_orcid(raw: str | None) -> str | None:
    """Extract a bare ORCID ID from various input formats.

    Handles:
      0000-0002-1825-0097
      https://orcid.org/0000-0002-1825-0097
      ORCID: 0000-0002-1825-0097
      0000000218250097 (no dashes)

    Returns None if the input doesn't look like a valid ORCID.
    """
    if not raw:
        return None
    cleaned = raw.strip()

    # 1. Try standard dash-separated format
    match = _ORCID_RE.search(cleaned)
    if match:
        return match.group(1).upper()

    # 2. Try 16 consecutive digits/X (no dashes)
    digits = re.sub(r"[^\dX]", "", cleaned, flags=re.IGNORECASE).upper()
    if len(digits) == 16:
        return (
            f"{digits[0:4]}-"
            f"{digits[4:8]}-"
            f"{digits[8:12]}-"
            f"{digits[12:16]}"
        )

    # Not a valid ORCID — return None instead of garbage
    return None


@dataclass
class PaperListResult:
    """Result of a paginated paper list query."""
    items: list[Paper] = field(default_factory=list)
    total: int = 0


class PaperRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ────────────────── Single-item queries ──────────────────

    async def get_by_id(
        self, paper_id: uuid.UUID, user_id: uuid.UUID
    ) -> Paper | None:
        """Get a single paper, scoped to user_id, with relationships loaded."""
        stmt = (
            select(Paper)
            .where(Paper.id == paper_id, Paper.user_id == user_id)
            .options(
                selectinload(Paper.authors).selectinload(PaperAuthor.author),
                selectinload(Paper.tags).selectinload(PaperTag.tag),
                selectinload(Paper.folder_assignments).selectinload(PaperFolder.folder),
                selectinload(Paper.keywords).selectinload(PaperKeyword.keyword),
                selectinload(Paper.documents),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_raw(
        self, paper_id: uuid.UUID, user_id: uuid.UUID
    ) -> Paper | None:
        """Get a paper without eager-loaded relationships (for updates/deletes)."""
        stmt = select(Paper).where(
            Paper.id == paper_id, Paper.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ────────────────── List queries ──────────────────

    async def list_papers(
        self,
        user_id: uuid.UUID,
        q: str | None = None,
        folder_id: uuid.UUID | None = None,
        tag_id: uuid.UUID | None = None,
        year: int | None = None,
        starred: bool | None = None,
        status: str | None = None,
        reading_status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> PaperListResult:
        """List papers with filters, pagination, and eager loading."""
        stmt = (
            select(Paper)
            .where(Paper.user_id == user_id)
            .options(
                selectinload(Paper.authors).selectinload(PaperAuthor.author),
                selectinload(Paper.tags).selectinload(PaperTag.tag),
                selectinload(Paper.folder_assignments).selectinload(PaperFolder.folder),
                selectinload(Paper.keywords).selectinload(PaperKeyword.keyword),
                selectinload(Paper.documents),
            )
        )
        count_stmt = (
            select(func.count())
            .select_from(Paper)
            .where(Paper.user_id == user_id)
        )

        if q and q.strip():
            pattern = f"%{q.strip()}%"
            author_match = exists(
                select(PaperAuthor.id)
                .join(Author, PaperAuthor.author_id == Author.id)
                .where(PaperAuthor.paper_id == Paper.id, Author.name.ilike(pattern))
            )
            tag_match = exists(
                select(PaperTag.id)
                .join(Tag, PaperTag.tag_id == Tag.id)
                .where(
                    PaperTag.paper_id == Paper.id,
                    Tag.user_id == user_id,
                    Tag.name.ilike(pattern),
                )
            )
            keyword_match = exists(
                select(PaperKeyword.id)
                .join(Keyword, PaperKeyword.keyword_id == Keyword.id)
                .where(
                    PaperKeyword.paper_id == Paper.id,
                    Keyword.user_id == user_id,
                    Keyword.display_name.ilike(pattern),
                )
            )
            metadata_match = or_(
                Paper.title.ilike(pattern),
                Paper.abstract.ilike(pattern),
                Paper.doi.ilike(pattern),
                Paper.arxiv_id.ilike(pattern),
                Paper.journal.ilike(pattern),
                Paper.conference.ilike(pattern),
                Paper.publisher.ilike(pattern),
                author_match,
                tag_match,
                keyword_match,
            )
            stmt = stmt.where(metadata_match)
            count_stmt = count_stmt.where(metadata_match)

        if year:
            stmt = stmt.where(Paper.publication_year == year)
            count_stmt = count_stmt.where(Paper.publication_year == year)

        if starred is not None:
            stmt = stmt.where(Paper.is_starred == starred)
            count_stmt = count_stmt.where(Paper.is_starred == starred)

        if status:
            stmt = stmt.where(Paper.status == status)
            count_stmt = count_stmt.where(Paper.status == status)

        if reading_status:
            stmt = stmt.where(Paper.reading_status == reading_status)
            count_stmt = count_stmt.where(Paper.reading_status == reading_status)

        if tag_id:
            tag_filter = exists(
                select(PaperTag.id)
                .join(Tag, PaperTag.tag_id == Tag.id)
                .where(
                    PaperTag.paper_id == Paper.id,
                    PaperTag.tag_id == tag_id,
                    Tag.user_id == user_id,
                )
            )
            stmt = stmt.where(tag_filter)
            count_stmt = count_stmt.where(tag_filter)

        if folder_id:
            folder_filter = exists(
                select(PaperFolder.id)
                .join(Folder, PaperFolder.folder_id == Folder.id)
                .where(
                    PaperFolder.paper_id == Paper.id,
                    PaperFolder.folder_id == folder_id,
                    Folder.user_id == user_id,
                )
            )
            stmt = stmt.where(folder_filter)
            count_stmt = count_stmt.where(folder_filter)

        stmt = stmt.order_by(Paper.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        return PaperListResult(
            items=list(result.scalars().all()),
            total=count_result.scalar() or 0,
        )

    async def get_recent(
        self, user_id: uuid.UUID, limit: int = 5
    ) -> list[Paper]:
        stmt = (
            select(Paper)
            .where(Paper.user_id == user_id)
            .order_by(Paper.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_starred(self, user_id: uuid.UUID) -> list[Paper]:
        stmt = (
            select(Paper)
            .where(Paper.user_id == user_id, Paper.is_starred == True)
            .order_by(Paper.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ────────────────── Duplicate detection ──────────────────

    async def find_duplicate(
        self,
        user_id: uuid.UUID,
        doi: str | None = None,
        arxiv_id: str | None = None,
        title: str | None = None,
        publication_year: int | None = None,
        exclude_paper_id: uuid.UUID | None = None,
    ) -> Paper | None:
        """Find a duplicate paper by DOI > arXiv ID > normalized title+year.

        If ``exclude_paper_id`` is provided, that paper is excluded
        (used for update-time duplicate checks).
        """
        def _exclude(stmt):
            if exclude_paper_id:
                stmt = stmt.where(Paper.id != exclude_paper_id)
            return stmt

        if doi:
            doi = doi.strip().lower()
            stmt = _exclude(select(Paper).where(
                Paper.user_id == user_id,
                func.lower(Paper.doi) == doi,
            ))
            result = await self.db.execute(stmt)
            if paper := result.scalars().first():
                return paper

        if arxiv_id:
            arxiv_id = arxiv_id.strip().lower()
            stmt = _exclude(select(Paper).where(
                Paper.user_id == user_id,
                func.lower(Paper.arxiv_id) == arxiv_id,
            ))
            result = await self.db.execute(stmt)
            if paper := result.scalars().first():
                return paper

        if title and publication_year:
            title_normalized = title.strip().lower()
            stmt = _exclude(select(Paper).where(
                Paper.user_id == user_id,
                func.lower(Paper.title) == title_normalized,
                Paper.publication_year == publication_year,
            ))
            result = await self.db.execute(stmt)
            if paper := result.scalars().first():
                return paper

        return None

    # ────────────────── CRUD ──────────────────

    async def create(self, **kwargs) -> Paper:
        paper = Paper(**kwargs)
        self.db.add(paper)
        await self.db.flush()
        return paper

    async def update(self, paper: Paper, **kwargs) -> Paper:
        for key, value in kwargs.items():
            setattr(paper, key, value)
        await self.db.flush()
        return paper

    async def delete(self, paper: Paper) -> None:
        await self.db.delete(paper)

    async def set_starred(self, paper: Paper, is_starred: bool) -> Paper:
        paper.is_starred = is_starred
        await self.db.flush()
        return paper

    async def mark_reading_if_unread(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID,
    ) -> None:
        """Apply the only automatic reading-state transition without overwrites."""
        await self.db.execute(
            update(Paper)
            .where(
                Paper.id == paper_id,
                Paper.user_id == user_id,
                Paper.reading_status == "unread",
            )
            .values(reading_status="reading")
        )
        await self.db.flush()

    # ────────────────── Tag / Folder helpers ──────────────────

    async def replace_tags(self, paper_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> None:
        current_ids = set((await self.db.execute(
            select(PaperTag.tag_id).where(PaperTag.paper_id == paper_id)
        )).scalars().all())
        desired_ids = set(tag_ids)
        stale_ids = current_ids - desired_ids
        if stale_ids:
            await self.db.execute(
                delete(PaperTag).where(PaperTag.paper_id == paper_id, PaperTag.tag_id.in_(stale_ids))
            )
        for tag_id in desired_ids - current_ids:
            self.db.add(PaperTag(paper_id=paper_id, tag_id=tag_id))
        await self.db.flush()

    async def add_tag(self, paper_id: uuid.UUID, tag_id: uuid.UUID) -> None:
        existing = await self.db.execute(
            select(PaperTag).where(
                PaperTag.paper_id == paper_id,
                PaperTag.tag_id == tag_id,
            )
        )
        if not existing.scalars().first():
            self.db.add(PaperTag(paper_id=paper_id, tag_id=tag_id))
            await self.db.flush()

    async def remove_tag(self, paper_id: uuid.UUID, tag_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(PaperTag).where(
                PaperTag.paper_id == paper_id,
                PaperTag.tag_id == tag_id,
            )
        )
        pt = result.scalars().first()
        if pt:
            await self.db.delete(pt)
            return True
        return False

    async def replace_folders(self, paper_id: uuid.UUID, folder_ids: list[uuid.UUID]) -> None:
        current_ids = set((await self.db.execute(
            select(PaperFolder.folder_id).where(PaperFolder.paper_id == paper_id)
        )).scalars().all())
        desired_ids = set(folder_ids)
        stale_ids = current_ids - desired_ids
        if stale_ids:
            await self.db.execute(
                delete(PaperFolder).where(PaperFolder.paper_id == paper_id, PaperFolder.folder_id.in_(stale_ids))
            )
        for folder_id in desired_ids - current_ids:
            self.db.add(PaperFolder(paper_id=paper_id, folder_id=folder_id))
        await self.db.flush()

    async def add_folder(self, paper_id: uuid.UUID, folder_id: uuid.UUID) -> None:
        existing = await self.db.execute(
            select(PaperFolder).where(
                PaperFolder.paper_id == paper_id,
                PaperFolder.folder_id == folder_id,
            )
        )
        if not existing.scalars().first():
            self.db.add(PaperFolder(paper_id=paper_id, folder_id=folder_id))
            await self.db.flush()

    async def remove_folder(
        self, paper_id: uuid.UUID, folder_id: uuid.UUID
    ) -> bool:
        result = await self.db.execute(
            select(PaperFolder).where(
                PaperFolder.paper_id == paper_id,
                PaperFolder.folder_id == folder_id,
            )
        )
        pf = result.scalars().first()
        if pf:
            await self.db.delete(pf)
            return True
        return False

    # ────────────────── Author helpers ──────────────────

    async def find_authors_by_orcids(
        self, orcids: list[str]
    ) -> dict[str, Author]:
        """Batch fetch authors by ORCID. Returns {orcid: Author}."""
        if not orcids:
            return {}
        stmt = select(Author).where(Author.orcid.in_(orcids))
        result = await self.db.execute(stmt)
        return {a.orcid: a for a in result.scalars().all()}

    async def find_authors_by_names(
        self, names: list[str]
    ) -> dict[str, list[Author]]:
        """Batch fetch authors by exact name. Returns {name: [Author, ...]}.

        Multiple authors can share the same name (e.g. "Wei Wang" at PKU
        vs MIT). The caller is responsible for disambiguating by affiliation.
        """
        if not names:
            return {}
        stmt = select(Author).where(Author.name.in_(names))
        result = await self.db.execute(stmt)
        name_map: dict[str, list[Author]] = {}
        for a in result.scalars().all():
            name_map.setdefault(a.name, []).append(a)
        return name_map

    async def create_author(self, **kwargs) -> Author:
        author = Author(**kwargs)
        self.db.add(author)
        await self.db.flush()
        return author

    async def replace_authors(self, paper_id: uuid.UUID) -> None:
        await self.db.execute(delete(PaperAuthor).where(PaperAuthor.paper_id == paper_id))
        await self.db.flush()

    async def link_author(
        self, paper_id: uuid.UUID, author_id: uuid.UUID, author_order: int
    ) -> None:
        self.db.add(
            PaperAuthor(
                paper_id=paper_id,
                author_id=author_id,
                author_order=author_order,
            )
        )
        await self.db.flush()

    # ────────────────── Tag / Folder validation ──────────────────

    async def validate_tags_for_user(
        self, tag_ids: list[uuid.UUID], user_id: uuid.UUID
    ) -> list[Tag]:
        """Return only tags that exist and belong to the user."""
        if not tag_ids:
            return []
        stmt = select(Tag).where(
            Tag.id.in_(tag_ids),
            Tag.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def validate_folders_for_user(
        self, folder_ids: list[uuid.UUID], user_id: uuid.UUID
    ) -> list[Folder]:
        """Return only folders that exist and belong to the user."""
        if not folder_ids:
            return []
        stmt = select(Folder).where(
            Folder.id.in_(folder_ids),
            Folder.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
