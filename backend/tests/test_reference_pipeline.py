"""S7-C reference segmentation, matching, and atomic snapshot tests."""

import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import DocumentParseError
from app.models import Document, Paper, Reference, Section, User
from app.parsers.chunker import DerivedChunk
from app.parsers.reference_matcher import ReferenceMatch, ReferenceMatcher
from app.parsers.reference_metadata_parser import ParsedReference, ReferenceMetadataParser, normalize_arxiv_id, normalize_doi
from app.parsers.reference_segmenter import ReferenceSegmenter
from app.parsers.section_detector import DetectedSection, TextFragment
from app.services.document_derived_service import DerivedDocumentSnapshot, DocumentDerivedService


def references_section() -> DetectedSection:
    section = DetectedSection(
        id=uuid.uuid4(), parent_id=None, title="References", section_type="references",
        level=1, order_index=0, page_start=18, page_end=19,
    )
    section.fragments.extend([
        TextFragment(18, "[1] A. Author and B. Writer."),
        TextFragment(18, "A Reliable Paper Title."),
        TextFragment(18, "NeurIPS, 2024. doi: https://doi.org/10.1234/Example.1."),
        TextFragment(18, "[2] C. Researcher. Cross page entry title"),
        TextFragment(19, "continued over a page. arXiv:2401.12345."),
        TextFragment(19, "[3] D. Scholar. Third entry. 2023."),
    ])
    return section


def test_segmenter_keeps_numbered_multiline_and_cross_page_entries():
    entries = ReferenceSegmenter().segment([references_section()])
    assert len(entries) == 3
    assert entries[0].raw_text.startswith("A. Author")
    assert "A Reliable Paper Title" in entries[0].raw_text
    assert entries[1].page_start == 18
    assert entries[1].page_end == 19
    assert entries[2].order_index == 2


def test_segmenter_supports_author_year_when_no_numbered_starters():
    section = DetectedSection(
        id=uuid.uuid4(), parent_id=None, title="References", section_type="references",
        level=1, order_index=0, page_start=1, page_end=1,
        fragments=[
            TextFragment(1, "Smith, J., 2022. A first article."),
            TextFragment(1, "Brown, A., 2021. A second article."),
        ],
    )
    entries = ReferenceSegmenter().segment([section])
    assert [entry.raw_text for entry in entries] == [
        "Smith, J., 2022. A first article.",
        "Brown, A., 2021. A second article.",
    ]


def test_metadata_parser_normalizes_stable_identifiers():
    entry = ReferenceSegmenter().segment([references_section()])[0]
    parsed = ReferenceMetadataParser().parse(entry)
    assert parsed.doi == "10.1234/example.1"
    assert normalize_arxiv_id("https://arxiv.org/abs/2401.12345") == "2401.12345"
    assert normalize_doi("DOI: 10.5555/ABC") == "10.5555/abc"
    assert parsed.year == 2024


@pytest.mark.asyncio
async def test_matcher_is_strictly_user_scoped(session):
    owner = User(id=uuid.uuid4(), username="reference-owner", email="reference-owner@test.local", password_hash="")
    other = User(id=uuid.uuid4(), username="reference-other", email="reference-other@test.local", password_hash="")
    session.add_all([owner, other])
    await session.flush()
    own_paper = Paper(user_id=owner.id, title="Owned", doi="10.1234/example.1", status="imported")
    foreign_paper = Paper(user_id=other.id, title="Foreign", doi="10.9999/foreign", status="imported")
    session.add_all([own_paper, foreign_paper])
    await session.flush()
    reference = ReferenceMetadataParser().parse(ReferenceSegmenter().segment([references_section()])[0])

    assert (await ReferenceMatcher(session).match(owner.id, reference)).paper_id == own_paper.id
    foreign_reference = ParsedReference(0, "x", 1, 1, None, None, None, None, "10.9999/foreign", None, None)
    assert (await ReferenceMatcher(session).match(owner.id, foreign_reference)).paper_id is None


@pytest.mark.asyncio
async def test_snapshot_validation_failure_preserves_old_references(session):
    user = User(id=uuid.uuid4(), username="reference-snapshot", email="reference-snapshot@test.local", password_hash="")
    session.add(user)
    await session.flush()
    paper = Paper(user_id=user.id, title="Snapshot", status="imported")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path="pdfs/snapshot.pdf", page_count=1)
    session.add(document)
    await session.flush()
    old_section = Section(document_id=document.id, title="References", section_type="references", level=1, order_index=0, page_start=1, page_end=1, content="old")
    old_reference = Reference(document_id=document.id, section_id=old_section.id, order_index=0, raw_text="Old reference", page_start=1, page_end=1)
    session.add_all([old_section, old_reference])
    await session.flush()

    invalid_reference = ParsedReference(0, "New", 0, 1, None, None, None, None, None, None, None)
    snapshot = DerivedDocumentSnapshot([], [], [(invalid_reference, ReferenceMatch())])
    with pytest.raises(DocumentParseError):
        await DocumentDerivedService(session).replace(document, snapshot)

    assert (await session.get(Reference, old_reference.id)) is not None


@pytest.mark.asyncio
async def test_paper_delete_keeps_reference_and_nulls_match(session):
    user = User(id=uuid.uuid4(), username="reference-delete", email="reference-delete@test.local", password_hash="")
    session.add(user)
    await session.flush()
    source = Paper(user_id=user.id, title="Source", status="imported")
    matched = Paper(user_id=user.id, title="Matched", status="imported")
    session.add_all([source, matched])
    await session.flush()
    document = Document(paper_id=source.id, file_path="pdfs/source.pdf", page_count=1)
    session.add(document)
    await session.flush()
    reference = Reference(document_id=document.id, order_index=0, raw_text="A reference", page_start=1, page_end=1, matched_paper_id=matched.id)
    session.add(reference)
    await session.commit()

    await session.delete(matched)
    await session.commit()
    retained = await session.get(Reference, reference.id)
    assert retained is not None
    assert retained.matched_paper_id is None
