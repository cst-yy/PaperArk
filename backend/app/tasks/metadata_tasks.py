"""Async task: fetch and update paper metadata from external APIs."""

import uuid

from app.core.database import async_session_factory
from app.models import Paper
from app.services.metadata_service import metadata_service


async def fetch_metadata_by_doi(paper_id: uuid.UUID, doi: str) -> None:
    """Fetch metadata from Crossref and update the paper."""
    async with async_session_factory() as db:
        try:
            data = await metadata_service.fetch_by_doi(doi)

            paper = await db.get(Paper, paper_id)
            if not paper:
                return

            if data.get("title"):
                paper.title = data["title"]
            if data.get("abstract"):
                paper.abstract = data["abstract"]
            if data.get("journal"):
                paper.journal = data["journal"]
            if data.get("publisher"):
                paper.publisher = data["publisher"]
            if data.get("publication_year"):
                paper.publication_year = data["publication_year"]
            if data.get("citation_count"):
                paper.citation_count = data["citation_count"]

            await db.commit()
        except Exception as e:
            print(f"Failed to fetch metadata for DOI {doi}: {e}")


async def fetch_metadata_by_arxiv(paper_id: uuid.UUID, arxiv_id: str) -> None:
    """Fetch metadata from arXiv and update the paper."""
    async with async_session_factory() as db:
        try:
            data = await metadata_service.fetch_by_arxiv(arxiv_id)

            paper = await db.get(Paper, paper_id)
            if not paper:
                return

            # Update fields from arXiv data
            for key, value in data.items():
                if value and hasattr(paper, key):
                    setattr(paper, key, value)

            await db.commit()
        except Exception as e:
            print(f"Failed to fetch metadata for arXiv {arxiv_id}: {e}")
