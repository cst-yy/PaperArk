"""Seed script — idempotent: safe to run multiple times.

Each item is created only if it doesn't already exist (get_or_create pattern).
Colors are NOT hardcoded — the frontend generates stable default colors from
the tag/folder name when `color` is null.

Usage:
    cd backend
    python -m app.seed
"""

import asyncio

from sqlalchemy import select

from app.core.database import DEFAULT_USER_ID, async_session_factory, init_db
from app.models import (
    Author,
    Folder,
    Paper,
    PaperAuthor,
    PaperFolder,
    PaperTag,
    Tag,
)

# ──────────────────────── Sample Data ────────────────────────

FOLDERS = [
    {"name": "联邦学习", "icon": "folder"},
    {"name": "多模态", "icon": "folder"},
    {"name": "大模型", "icon": "folder"},
]

TAGS = [
    {"name": "Federated Learning"},
    {"name": "Heterogeneity"},
    {"name": "Label Distribution"},
    {"name": "Privacy"},
    {"name": "LoRA"},
    {"name": "Multimodal"},
    {"name": "ICML"},
    {"name": "NeurIPS"},
]

PAPERS = [
    {
        "title": "FedLDR: Federated Learning with Label Distribution Rectification",
        "abstract": "Federated learning suffers from performance degradation caused by non-IID label distributions across clients. We propose FedLDR, a novel approach that rectifies label distribution heterogeneity through a two-stage framework...",
        "doi": "10.1016/j.neucom.2025.001234",
        "journal": "Neurocomputing",
        "publication_year": 2025,
        "authors": ["Yu Yang", "Zhi Chen", "Wei Liu"],
        "tags": ["Federated Learning", "Heterogeneity", "Label Distribution"],
        "folders": ["联邦学习"],
    },
    {
        "title": "AHFL: Adaptive Heterogeneous Federated Learning for IoT Devices",
        "abstract": "The proliferation of IoT devices has created new challenges for federated learning due to extreme device heterogeneity. We present AHFL, an adaptive framework that dynamically adjusts aggregation strategies...",
        "doi": "10.1109/JIOT.2025.002345",
        "journal": "IEEE IoT Journal",
        "publication_year": 2025,
        "authors": ["Jingwen Li", "Xiaoming Zhang", "Haifeng Wang", "Yu Yang"],
        "tags": ["Federated Learning", "Heterogeneity", "Privacy"],
        "folders": ["联邦学习"],
    },
    {
        "title": "DP-HM2F: Differentially Private Heterogeneous Multimodal Federated Learning",
        "abstract": "We introduce DP-HM2F, the first framework to jointly address differential privacy and multimodal heterogeneity in federated learning. Our method achieves strong privacy guarantees while maintaining competitive accuracy...",
        "arxiv_id": "2501.00001",
        "conference": "ICML",
        "publication_year": 2025,
        "authors": ["Haifeng Wang", "Yu Yang", "Jingwen Li"],
        "tags": ["Federated Learning", "Multimodal", "Privacy", "ICML"],
        "folders": ["联邦学习", "多模态"],
    },
    {
        "title": "LoRA-FL: Efficient Federated Fine-tuning of Large Language Models via Low-Rank Adaptation",
        "abstract": "Fine-tuning large language models in a federated setting is challenging due to communication costs and data heterogeneity. We propose LoRA-FL, combining low-rank adaptation with federated optimization...",
        "arxiv_id": "2501.00002",
        "conference": "NeurIPS",
        "publication_year": 2024,
        "authors": ["Zhi Chen", "Xiaoming Zhang"],
        "tags": ["Federated Learning", "LoRA", "NeurIPS"],
        "folders": ["联邦学习", "大模型"],
    },
    {
        "title": "FedAvg: Communication-Efficient Learning of Deep Networks from Decentralized Data",
        "abstract": "We study a federated learning setting where a central server coordinates with many clients to train a shared model. We propose FedAvg, a simple and practical algorithm that averages local SGD updates...",
        "arxiv_id": "1602.05629",
        "conference": "AISTATS",
        "publication_year": 2017,
        "authors": ["Brendan McMahan", "Eider Moore", "Daniel Ramage", "Seth Hampson", "Blaise Aguera y Arcas"],
        "tags": ["Federated Learning"],
        "folders": ["联邦学习"],
    },
]


async def _get_or_create_folder(session, name: str, icon: str | None = None) -> Folder:
    result = await session.execute(
        select(Folder).where(
            Folder.user_id == DEFAULT_USER_ID,
            Folder.name == name,
        )
    )
    folder = result.scalars().first()
    if not folder:
        folder = Folder(
            user_id=DEFAULT_USER_ID,
            name=name,
            icon=icon,
        )
        session.add(folder)
        await session.flush()
        print(f"  + Folder: {name}")
    return folder


async def _get_or_create_tag(session, name: str) -> Tag:
    result = await session.execute(
        select(Tag).where(
            Tag.user_id == DEFAULT_USER_ID,
            Tag.name == name,
        )
    )
    tag = result.scalars().first()
    if not tag:
        tag = Tag(
            user_id=DEFAULT_USER_ID,
            name=name,
        )
        session.add(tag)
        await session.flush()
        print(f"  + Tag: {name}")
    return tag


async def _get_or_create_author(session, name: str) -> Author:
    """Get or create an author by name.

    Note: In production, this should use ORCID first. Seed data doesn't have
    ORCID, so we fall back to name matching. This is acceptable for seed data
    but not for real imports.
    """
    result = await session.execute(
        select(Author).where(Author.name == name)
    )
    author = result.scalars().first()
    if not author:
        author = Author(name=name)
        session.add(author)
        await session.flush()
    return author


async def _get_or_create_paper(session, paper_data: dict) -> Paper:
    """Get or create a paper by DOI, arXiv ID, or normalized title+year."""
    doi = paper_data.get("doi")
    arxiv_id = paper_data.get("arxiv_id")
    title = paper_data["title"]
    year = paper_data.get("publication_year")

    # Try DOI first
    if doi:
        result = await session.execute(
            select(Paper).where(
                Paper.user_id == DEFAULT_USER_ID,
                Paper.doi == doi.strip().lower(),
            )
        )
        if paper := result.scalars().first():
            return paper

    # Try arXiv ID
    if arxiv_id:
        result = await session.execute(
            select(Paper).where(
                Paper.user_id == DEFAULT_USER_ID,
                Paper.arxiv_id == arxiv_id.strip().lower(),
            )
        )
        if paper := result.scalars().first():
            return paper

    # Try title + year
    result = await session.execute(
        select(Paper).where(
            Paper.user_id == DEFAULT_USER_ID,
            Paper.title == title,
        )
    )
    if paper := result.scalars().first():
        return paper

    # Create new paper
    paper = Paper(
        user_id=DEFAULT_USER_ID,
        title=title,
        abstract=paper_data.get("abstract"),
        doi=doi.strip().lower() if doi else None,
        arxiv_id=arxiv_id.strip().lower() if arxiv_id else None,
        journal=paper_data.get("journal"),
        conference=paper_data.get("conference"),
        publication_year=year,
        status="imported",
        is_starred=False,
    )
    session.add(paper)
    await session.flush()
    print(f"  + Paper: {title[:60]}...")
    return paper


async def seed():
    """Insert sample data if not already present. Idempotent."""
    await init_db()

    async with async_session_factory() as session:
        # ── Folders (idempotent) ──
        folder_map: dict[str, Folder] = {}
        for f in FOLDERS:
            folder_map[f["name"]] = await _get_or_create_folder(
                session, f["name"], f.get("icon")
            )

        # ── Tags (idempotent) ──
        tag_map: dict[str, Tag] = {}
        for t in TAGS:
            tag_map[t["name"]] = await _get_or_create_tag(session, t["name"])

        # ── Authors (idempotent, cached) ──
        author_cache: dict[str, Author] = {}

        async def get_or_create_author(name: str) -> Author:
            if name in author_cache:
                return author_cache[name]
            author = await _get_or_create_author(session, name)
            author_cache[name] = author
            return author

        # ── Papers (idempotent) ──
        for p in PAPERS:
            paper = await _get_or_create_paper(session, p)

            # Link authors (idempotent — check if link exists)
            for idx, author_name in enumerate(p.get("authors", [])):
                author = await get_or_create_author(author_name)
                existing = await session.execute(
                    select(PaperAuthor).where(
                        PaperAuthor.paper_id == paper.id,
                        PaperAuthor.author_id == author.id,
                    )
                )
                if not existing.scalars().first():
                    session.add(PaperAuthor(
                        paper_id=paper.id,
                        author_id=author.id,
                        author_order=idx,
                    ))

            # Link tags (idempotent)
            for tag_name in p.get("tags", []):
                if tag_name in tag_map:
                    tag = tag_map[tag_name]
                    existing = await session.execute(
                        select(PaperTag).where(
                            PaperTag.paper_id == paper.id,
                            PaperTag.tag_id == tag.id,
                        )
                    )
                    if not existing.scalars().first():
                        session.add(PaperTag(
                            paper_id=paper.id,
                            tag_id=tag.id,
                        ))

            # Link folders (idempotent)
            for folder_name in p.get("folders", []):
                if folder_name in folder_map:
                    folder = folder_map[folder_name]
                    existing = await session.execute(
                        select(PaperFolder).where(
                            PaperFolder.paper_id == paper.id,
                            PaperFolder.folder_id == folder.id,
                        )
                    )
                    if not existing.scalars().first():
                        session.add(PaperFolder(
                            paper_id=paper.id,
                            folder_id=folder.id,
                        ))

            await session.flush()

        await session.commit()
        print("\nSeed complete (idempotent).")


if __name__ == "__main__":
    asyncio.run(seed())
