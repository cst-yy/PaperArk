"""Paper service - orchestrates business logic for paper management.

Responsibilities:
  - Author deduplication (ORCID > name+affiliation > create new)
  - Tag/Folder ownership validation
  - Duplicate paper detection (create + update)
  - Delete consistency (DB commit first, then file)
  - PDF import (validate -> save -> create Paper+Document -> compensate on failure)
  - ORM -> Schema conversion

Raises domain exceptions (app.core.exceptions), NOT HTTPException.
The API layer is responsible for converting them to HTTP responses.
"""

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    DuplicatePaperError,
    FolderNotFoundError,
    InvalidFolderError,
    InvalidTagError,
    PaperNotFoundError,
    StorageError,
    TagNotFoundError,
)
from app.core.storage import (
    get_full_path,
    get_relative_path,
    save_bytes,
    sha256_bytes,
    validate_pdf,
)
from app.models import Paper
from app.repositories.document_repository import DocumentRepository
from app.repositories.paper_repository import PaperRepository, normalize_orcid
from app.schemas.keyword import KeywordReplacement, PaperKeywordBrief
from app.services.keyword_service import KeywordService
from app.schemas.document import DocumentBrief
from app.schemas.paper import (
    AuthorBrief,
    PaperCreate,
    PaperListResponse,
    PaperMetadataReplaceRequest,
    PaperPageResponse,
    PaperResponse,
    PaperUpdate,
    ReadingStatus,
    FolderBrief,
    TagBrief,
)

logger = logging.getLogger(__name__)


def _normalize_text(value: str | None) -> str | None:
    """Normalize a text field for comparison (strip + lower)."""
    if value is None:
        return None
    return value.strip().lower() if value.strip() else None


class PaperMapper:
    """Convert ORM Paper objects to Pydantic response models."""

    @staticmethod
    def _document_briefs(paper: Paper) -> list[DocumentBrief]:
        """Return a stable document ordering for the Reader's document scope."""
        documents = sorted(
            paper.documents,
            key=lambda document: (document.created_at, str(document.id)),
            reverse=True,
        )
        return [
            DocumentBrief(
                id=document.id,
                original_filename=document.original_filename,
                file_size=document.file_size,
                mime_type=document.mime_type,
                parse_status=document.parse_status,
            )
            for document in documents
        ]

    @staticmethod
    def _extract_document(paper: Paper) -> DocumentBrief | None:
        """Return the deterministic default document for backward compatibility."""
        documents = PaperMapper._document_briefs(paper)
        return documents[0] if documents else None

    @staticmethod
    def _keyword_briefs(paper: Paper) -> list[PaperKeywordBrief]:
        grouped: dict[uuid.UUID, PaperKeywordBrief] = {}
        for link in paper.keywords:
            existing = grouped.get(link.keyword.id)
            if existing:
                existing.sources.append(link.source)
            else:
                grouped[link.keyword.id] = PaperKeywordBrief(
                    id=link.keyword.id,
                    display_name=link.keyword.display_name,
                    sources=[link.source],
                )
        return sorted(grouped.values(), key=lambda keyword: keyword.display_name.casefold())

    @staticmethod
    def to_detail_response(paper: Paper) -> PaperResponse:
        authors = sorted(paper.authors, key=lambda pa: pa.author_order)
        return PaperResponse(
            id=paper.id,
            title=paper.title,
            abstract=paper.abstract,
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            url=paper.url,
            journal=paper.journal,
            conference=paper.conference,
            publisher=paper.publisher,
            publication_year=paper.publication_year,
            citation_count=paper.citation_count,
            pdf_path=paper.pdf_path,
            cover_path=paper.cover_path,
            status=paper.status,
            reading_status=paper.reading_status,
            is_starred=paper.is_starred,
            created_at=paper.created_at,
            updated_at=paper.updated_at,
            authors=[
                AuthorBrief(
                    id=pa.author.id,
                    name=pa.author.name,
                    orcid=pa.author.orcid,
                    affiliation=pa.author.affiliation,
                    author_order=pa.author_order,
                )
                for pa in authors
            ],
            tags=[
                TagBrief(
                    id=pt.tag.id,
                    name=pt.tag.name,
                    color=pt.tag.color,
                )
                for pt in paper.tags
            ],
            folders=[
                FolderBrief(
                    id=pf.folder.id,
                    name=pf.folder.name,
                    color=pf.folder.color,
                    icon=pf.folder.icon,
                )
                for pf in paper.folder_assignments
            ],
            keywords=PaperMapper._keyword_briefs(paper),
            document=PaperMapper._extract_document(paper),
            documents=PaperMapper._document_briefs(paper),
        )

    @staticmethod
    def to_list_response(paper: Paper) -> PaperListResponse:
        authors = sorted(paper.authors, key=lambda pa: pa.author_order)
        first_author = authors[0].author.name if authors else None
        return PaperListResponse(
            id=paper.id,
            title=paper.title,
            publication_year=paper.publication_year,
            journal=paper.journal,
            conference=paper.conference,
            status=paper.status,
            reading_status=paper.reading_status,
            is_starred=paper.is_starred,
            created_at=paper.created_at,
            first_author=first_author,
            tags=[
                TagBrief(
                    id=pt.tag.id,
                    name=pt.tag.name,
                    color=pt.tag.color,
                )
                for pt in paper.tags
            ],
            has_document=bool(paper.documents),
        )


class PaperService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PaperRepository(db)
        self.doc_repo = DocumentRepository(db)

    # ────────────────── Create ──────────────────

    async def create_paper(
        self, user_id: uuid.UUID, data: PaperCreate
    ) -> Paper:
        """Create a paper with authors, tags, and folders.

        Steps:
          1. Check for duplicates (DOI > arXiv ID > title+year)
          2. Create Paper
          3. Deduplicate authors (ORCID > name+affiliation > create new)
          4. Validate & link tags
          5. Validate & link folders
        """
        # 1. Duplicate check
        dup = await self.repo.find_duplicate(
            user_id=user_id,
            doi=data.doi,
            arxiv_id=data.arxiv_id,
            title=data.title,
            publication_year=data.publication_year,
        )
        if dup:
            raise DuplicatePaperError(dup.title)

        # 2. Create paper
        paper = await self.repo.create(
            user_id=user_id,
            title=data.title,
            abstract=data.abstract,
            doi=_normalize_text(data.doi),
            arxiv_id=_normalize_text(data.arxiv_id),
            url=data.url,
            journal=data.journal,
            conference=data.conference,
            publisher=data.publisher,
            publication_year=data.publication_year,
            citation_count=data.citation_count,
            status="imported",
        )

        # 3. Deduplicate authors
        await self._link_authors(paper.id, data.authors)

        # 4. Validate & link tags (deduplicate IDs first)
        if data.tag_ids:
            tag_ids = list(dict.fromkeys(data.tag_ids))  # preserve order, remove dups
            valid_tags = await self.repo.validate_tags_for_user(tag_ids, user_id)
            valid_ids = {t.id for t in valid_tags}
            missing = [tid for tid in tag_ids if tid not in valid_ids]
            if missing:
                raise InvalidTagError(
                    "One or more tags do not exist or belong to another user",
                    detail=f"missing_tag_ids: {missing}",
                )
            for tag in valid_tags:
                await self.repo.add_tag(paper.id, tag.id)

        # 5. Validate & link folders (deduplicate IDs first)
        if data.folder_ids:
            folder_ids = list(dict.fromkeys(data.folder_ids))
            valid_folders = await self.repo.validate_folders_for_user(
                folder_ids, user_id
            )
            valid_ids = {f.id for f in valid_folders}
            missing = [fid for fid in folder_ids if fid not in valid_ids]
            if missing:
                raise InvalidFolderError(
                    "One or more folders do not exist or belong to another user",
                    detail=f"missing_folder_ids: {missing}",
                )
            for folder in valid_folders:
                await self.repo.add_folder(paper.id, folder.id)

        # Reload with relationships
        return await self.repo.get_by_id(paper.id, user_id)

    async def _link_authors(
        self, paper_id: uuid.UUID, authors: list[AuthorBrief]
    ) -> None:
        """Link authors to a paper with deduplication.

        Priority:
          1. ORCID match (exact, unique)
          2. Name + affiliation match (cautious -- same name at same org)
          3. Create a new Author record

        We NEVER blindly merge two people who happen to share a common name
        like "Wei Wang" from different institutions.
        """
        if not authors:
            return

        # Normalize ORCIDs in the input data
        normalized_orcids: dict[str, str] = {}  # original -> normalized
        for a in authors:
            norm = normalize_orcid(a.orcid)
            if norm:
                a.orcid = norm
                normalized_orcids[norm] = norm

        # Batch-fetch existing authors by ORCID
        orcids = list(normalized_orcids.keys())
        orcid_map = await self.repo.find_authors_by_orcids(orcids)

        # Batch-fetch existing authors by name (returns dict[str, list[Author]])
        names = [a.name for a in authors]
        name_map = await self.repo.find_authors_by_names(names)

        for idx, author_data in enumerate(authors):
            author = None

            # 1. ORCID match
            if author_data.orcid and author_data.orcid in orcid_map:
                author = orcid_map[author_data.orcid]

            # 2. Name + affiliation match
            #    name_map returns {name: [Author, Author, ...]}
            #    We look through ALL authors with the same name and try to
            #    match by affiliation.
            elif author_data.name in name_map:
                candidates = name_map[author_data.name]
                if author_data.affiliation:
                    target_affil = _normalize_text(author_data.affiliation)
                    author = next(
                        (
                            a for a in candidates
                            if _normalize_text(a.affiliation) == target_affil
                        ),
                        None,
                    )

            # 3. Create new
            if not author:
                author = await self.repo.create_author(
                    name=author_data.name,
                    orcid=author_data.orcid,
                    affiliation=author_data.affiliation,
                )
                # Update caches
                if author_data.orcid:
                    orcid_map[author_data.orcid] = author
                name_map.setdefault(author_data.name, []).append(author)

            await self.repo.link_author(paper_id, author.id, idx)

    # ────────────────── Read ──────────────────

    async def get_paper(
        self, user_id: uuid.UUID, paper_id: uuid.UUID
    ) -> Paper:
        paper = await self.repo.get_by_id(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        return paper

    async def list_papers(
        self,
        user_id: uuid.UUID,
        q: str | None = None,
        folder_id: uuid.UUID | None = None,
        tag_id: uuid.UUID | None = None,
        year: int | None = None,
        starred: bool | None = None,
        status: str | None = None,
        reading_status: ReadingStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaperPageResponse:
        result = await self.repo.list_papers(
            user_id=user_id,
            q=q,
            folder_id=folder_id,
            tag_id=tag_id,
            year=year,
            starred=starred,
            status=status,
            reading_status=reading_status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        total_pages = (result.total + page_size - 1) // page_size if result.total else 0
        return PaperPageResponse(
            items=[PaperMapper.to_list_response(p) for p in result.items],
            page=page,
            page_size=page_size,
            total=result.total,
            total_pages=total_pages,
        )

    # ────────────────── Update ──────────────────

    async def update_paper(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, data: PaperUpdate
    ) -> Paper:
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")

        update_data = data.model_dump(exclude_unset=True)

        # Normalize DOI/arXiv on update
        if "doi" in update_data and update_data["doi"]:
            update_data["doi"] = _normalize_text(update_data["doi"])
        if "arxiv_id" in update_data and update_data["arxiv_id"]:
            update_data["arxiv_id"] = _normalize_text(update_data["arxiv_id"])

        # Duplicate detection on update — only if identity fields changed
        identity_fields = {"doi", "arxiv_id", "title", "publication_year"}
        if identity_fields & update_data.keys():
            new_doi = update_data.get("doi", paper.doi)
            new_arxiv = update_data.get("arxiv_id", paper.arxiv_id)
            new_title = update_data.get("title", paper.title)
            new_year = update_data.get("publication_year", paper.publication_year)

            dup = await self.repo.find_duplicate(
                user_id=user_id,
                doi=new_doi,
                arxiv_id=new_arxiv,
                title=new_title,
                publication_year=new_year,
                exclude_paper_id=paper_id,
            )
            if dup:
                raise DuplicatePaperError(dup.title)

        await self.repo.update(paper, **update_data)

        # Reload with relationships
        return await self.repo.get_by_id(paper_id, user_id)

    # ────────────────── Delete ──────────────────

    async def delete_paper(
        self, user_id: uuid.UUID, paper_id: uuid.UUID
    ) -> None:
        """Delete paper: DB commit FIRST, then file.

        The transaction is explicitly committed here before any file
        operations. This guarantees:
          - If the commit fails, the file is untouched.
          - If the file deletion fails, the DB record is already gone
            and the orphan file is logged for later cleanup.

        File paths are read from every associated Document (authoritative
        source). Paper.pdf_path is also included for legacy records. Duplicate
        paths are removed before cleanup.
        """
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")

        # Collect all paths before the cascading DB delete removes Documents.
        documents = await self.doc_repo.list_by_paper(paper_id, user_id)
        pdf_paths = {doc.file_path for doc in documents if doc.file_path}
        if paper.pdf_path:
            # Legacy records may point at a file not represented by Document.
            pdf_paths.add(paper.pdf_path)

        # 1. Delete DB entity and commit immediately
        await self.repo.delete(paper)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        # 2. Attempt file cleanup AFTER successful commit
        for pdf_path in pdf_paths:
            full_path = get_full_path(pdf_path)
            if full_path.exists():
                try:
                    full_path.unlink()
                except Exception as e:
                    # DB is already committed — orphan file, not data loss
                    logger.warning(
                        "Failed to delete file %s: %s. "
                        "Orphan file can be cleaned up later.",
                        pdf_path,
                        e,
                    )

    # ────────────────── Reading status ──────────────────

    async def set_reading_status(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID,
        reading_status: ReadingStatus,
    ) -> Paper:
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        return await self.repo.update(paper, reading_status=reading_status)

    # ────────────────── Star ──────────────────

    async def set_starred(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, is_starred: bool
    ) -> Paper:
        """Explicit star state (not a toggle). Idempotent."""
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        await self.repo.set_starred(paper, is_starred)
        return paper

    # ────────────────── Tag management ──────────────────

    async def add_tag(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, tag_id: uuid.UUID
    ) -> None:
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")

        valid_tags = await self.repo.validate_tags_for_user([tag_id], user_id)
        if not valid_tags:
            raise TagNotFoundError(f"Tag {tag_id} not found")

        await self.repo.add_tag(paper_id, tag_id)

    async def remove_tag(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, tag_id: uuid.UUID
    ) -> None:
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        valid_tags = await self.repo.validate_tags_for_user([tag_id], user_id)
        if not valid_tags:
            raise TagNotFoundError(f"Tag {tag_id} not found")
        await self.repo.remove_tag(paper_id, tag_id)

    async def replace_tags(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, tag_ids: list[uuid.UUID]
    ) -> Paper:
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        valid_tags = await self.repo.validate_tags_for_user(tag_ids, user_id)
        if {tag.id for tag in valid_tags} != set(tag_ids):
            raise InvalidTagError("One or more tags do not exist or belong to another user")
        await self.repo.replace_tags(paper_id, tag_ids)
        return await self.get_paper(user_id, paper_id)

    # ────────────────── Folder management ──────────────────

    async def add_folder(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, folder_id: uuid.UUID
    ) -> None:
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")

        valid_folders = await self.repo.validate_folders_for_user(
            [folder_id], user_id
        )
        if not valid_folders:
            raise FolderNotFoundError(f"Folder {folder_id} not found")

        await self.repo.add_folder(paper_id, folder_id)

    async def remove_folder(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, folder_id: uuid.UUID
    ) -> None:
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        valid_folders = await self.repo.validate_folders_for_user([folder_id], user_id)
        if not valid_folders:
            raise FolderNotFoundError(f"Folder {folder_id} not found")
        await self.repo.remove_folder(paper_id, folder_id)

    async def replace_folders(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, folder_ids: list[uuid.UUID]
    ) -> Paper:
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        valid_folders = await self.repo.validate_folders_for_user(folder_ids, user_id)
        if {folder.id for folder in valid_folders} != set(folder_ids):
            raise InvalidFolderError("One or more folders do not exist or belong to another user")
        await self.repo.replace_folders(paper_id, folder_ids)
        return await self.get_paper(user_id, paper_id)

    async def replace_metadata_aggregate(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, data: PaperMetadataReplaceRequest
    ) -> Paper:
        """Atomically replace the full editor-owned Paper aggregate.

        The request dependency owns the final commit. A savepoint ensures every
        scalar and relationship edit is rolled back together on any failure.
        Non-manual keyword sources are intentionally retained.
        """
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")

        update_data = data.model_dump(
            exclude={"authors", "tag_ids", "folder_ids", "keywords"}
        )
        update_data["doi"] = _normalize_text(data.doi)
        update_data["arxiv_id"] = _normalize_text(data.arxiv_id)
        duplicate = await self.repo.find_duplicate(
            user_id=user_id,
            doi=update_data["doi"],
            arxiv_id=update_data["arxiv_id"],
            title=data.title,
            publication_year=data.publication_year,
            exclude_paper_id=paper_id,
        )
        if duplicate:
            raise DuplicatePaperError(duplicate.title)

        valid_tags = await self.repo.validate_tags_for_user(data.tag_ids, user_id)
        if {tag.id for tag in valid_tags} != set(data.tag_ids):
            raise InvalidTagError("One or more tags do not exist or belong to another user")
        valid_folders = await self.repo.validate_folders_for_user(data.folder_ids, user_id)
        if {folder.id for folder in valid_folders} != set(data.folder_ids):
            raise InvalidFolderError("One or more folders do not exist or belong to another user")

        keyword_service = KeywordService(self.db)
        async with self.db.begin_nested():
            await self.repo.update(paper, **update_data)
            await self.repo.replace_authors(paper_id)
            await self._link_authors(paper_id, data.authors)
            await self.repo.replace_tags(paper_id, data.tag_ids)
            keywords = [
                await keyword_service.get_or_create(user_id, item)
                for item in data.keywords
            ]
            await keyword_service.repo.replace_manual_for_paper(
                paper_id, [keyword.id for keyword in keywords]
            )
            await self.repo.replace_folders(paper_id, data.folder_ids)

        self.db.expire(paper, ["authors", "tags", "keywords", "folder_assignments"])
        return await self.get_paper(user_id, paper_id)

    async def replace_keywords(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, data: KeywordReplacement
    ) -> Paper:
        """Replace only manual keyword links; parser/AI sources are retained."""
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        keyword_service = KeywordService(self.db)
        try:
            async with self.db.begin_nested():
                keywords = [
                    await keyword_service.get_or_create(user_id, item)
                    for item in data.keywords
                ]
                await keyword_service.repo.replace_manual_for_paper(
                    paper_id, [keyword.id for keyword in keywords]
                )
        except Exception:
            raise
        self.db.expire(paper, ["keywords"])
        return await self.get_paper(user_id, paper_id)

    async def replace_authors(
        self, user_id: uuid.UUID, paper_id: uuid.UUID, authors: list[AuthorBrief]
    ) -> Paper:
        paper = await self.repo.get_raw(paper_id, user_id)
        if not paper:
            raise PaperNotFoundError(f"Paper {paper_id} not found")
        try:
            async with self.db.begin_nested():
                await self.repo.replace_authors(paper_id)
                await self._link_authors(paper_id, authors)
        except Exception:
            # The outer request transaction remains usable; no partial PaperAuthor links survive.
            raise
        self.db.expire(paper, ["authors"])
        return await self.get_paper(user_id, paper_id)

    # ────────────────── PDF import ──────────────────

    async def import_pdf(
        self, user_id: uuid.UUID, file: UploadFile
    ) -> Paper:
        """Import a PDF file as a new paper.

        Flow:
          1. validate_pdf (extension, content-type, magic bytes, size)
          2. Save file to storage with UUID filename
          3. Create Paper (title derived from filename)
          4. Create Document (authoritative file reference)
          5. flush
          6. On any DB failure: delete the saved file (compensation)

        Paper.pdf_path is deprecated — Document.file_path is the source of truth.
        """
        # 1. Validate PDF and get content
        content = await validate_pdf(file)

        # 2. Save to storage with UUID filename
        try:
            saved_path = await save_bytes(content, "pdfs", ".pdf")
        except Exception as e:
            logger.error("Failed to save PDF: %s", e)
            raise StorageError("文件保存失败")

        relative_path = get_relative_path(saved_path)
        file_size = len(content)
        file_hash = sha256_bytes(content)
        original_filename = file.filename or "Untitled.pdf"

        # Derive title from filename (strip extension)
        title = Path(original_filename).stem

        try:
            # 3. Create Paper
            paper = await self.repo.create(
                user_id=user_id,
                title=title,
                pdf_path=relative_path,  # deprecated, kept for backward compat
                status="imported",
            )

            # 4. Create Document — authoritative file reference
            await self.doc_repo.create(
                paper_id=paper.id,
                original_filename=original_filename,
                file_path=relative_path,
                file_size=file_size,
                file_hash=file_hash,
                mime_type="application/pdf",
                parse_status="pending",
            )

            # 5. Explicit commit: this extends compensation to the final
            # database commit, which normally happens after an endpoint returns.
            await self.db.commit()

        except Exception:
            # 6. Compensation: rollback every DB stage (including commit)
            # and remove the already-written file to prevent an orphan PDF.
            await self.db.rollback()
            try:
                if saved_path.exists():
                    await asyncio.to_thread(saved_path.unlink)
                    logger.info(
                        "Compensated: deleted orphan file %s after DB failure",
                        saved_path,
                    )
            except Exception as cleanup_err:
                logger.warning(
                    "Failed to clean up orphan file %s: %s",
                    saved_path,
                    cleanup_err,
                )
            raise

        # Reload with relationships after the transaction is durable.
        result = await self.repo.get_by_id(paper.id, user_id)
        if not result:
            # This should be unreachable after a successful commit, but avoids
            # returning None from a method whose contract is Paper.
            raise PaperNotFoundError(f"Paper {paper.id} not found after import")
        return result


def get_paper_service(
    db: AsyncSession = Depends(get_db),
) -> PaperService:
    """FastAPI dependency factory for PaperService."""
    return PaperService(db)
