"""S7-D caption detection and derived snapshot integrity tests."""

import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import DocumentParseError
from app.models import Document, DocumentElement, Paper, Section, User
from app.parsers.base import ParsedDocument, ParsedPage, ParsedTextBlock, ParsedVisualBlock
from app.parsers.element_detector import DetectedElement, ElementDetector
from app.parsers.section_detector import DetectedSection
from app.services.document_derived_service import DerivedDocumentSnapshot, DocumentDerivedService


def parsed_page() -> ParsedDocument:
    figure_caption = ParsedTextBlock("Figure 1: Accuracy under different", 1, 80, 470, 310, 485, 9)
    continuation = ParsedTextBlock("heterogeneous settings.", 1, 80, 488, 240, 503, 9)
    heading = ParsedTextBlock("2.3", 1, 80, 506, 120, 521, 10)
    table_caption = ParsedTextBlock("Table 1: Main results.", 1, 80, 90, 220, 105, 9)
    return ParsedDocument(
        page_count=1,
        metadata={},
        pages=[ParsedPage(
            page_number=1, text="", width=600, height=800,
            blocks=[table_caption, figure_caption, continuation, heading],
            visual_blocks=[
                ParsedVisualBlock(1, 80, 120, 360, 300, "vector"),
                ParsedVisualBlock(1, 80, 260, 400, 450, "image"),
            ],
        )],
    )


def test_detector_merges_caption_and_resolves_normalized_bbox():
    section = DetectedSection(uuid.uuid4(), None, "Results", "experiment", 1, 0, 1, 1)
    elements = ElementDetector().detect(parsed_page(), [section])
    assert [(element.element_type, element.label) for element in elements] == [
        ("table", "Table 1"),
        ("figure", "Figure 1"),
    ]
    assert elements[1].caption == "Figure 1 Accuracy under different heterogeneous settings."
    assert elements[0].section_id == section.id
    assert elements[0].x is not None
    assert 0 <= elements[0].x <= 1
    assert elements[0].width is not None and elements[0].width > 0


def test_detector_allows_caption_without_visual_bbox():
    page = parsed_page()
    no_visual = ParsedDocument(page_count=1, metadata={}, pages=[ParsedPage(1, "", 600, 800, blocks=page.pages[0].blocks)])
    elements = ElementDetector().detect(no_visual, [])
    assert len(elements) == 2
    assert all((element.x, element.y, element.width, element.height) == (None, None, None, None) for element in elements)


@pytest.mark.parametrize(
    ("caption", "expected_type", "expected_label"),
    [
        ("图 4：多模态评测结果", "figure", "图 4"),
        ("表 5：主要实验结果", "table", "表 5"),
    ],
)
def test_detector_accepts_chinese_fullwidth_colon_captions(
    caption: str, expected_type: str, expected_label: str
):
    parsed = ParsedDocument(
        page_count=1,
        metadata={},
        pages=[ParsedPage(
            page_number=1,
            text=caption,
            width=600,
            height=800,
            blocks=[ParsedTextBlock(caption, 1, 80, 90, 260, 105, 9)],
        )],
    )

    elements = ElementDetector().detect(parsed, [])

    assert len(elements) == 1
    assert elements[0].element_type == expected_type
    assert elements[0].label == expected_label
    assert elements[0].caption == caption.replace("：", " ")


@pytest.mark.asyncio
async def test_element_validation_failure_keeps_prior_snapshot(session):
    user = User(id=uuid.uuid4(), username="element-snapshot", email="element-snapshot@test.local", password_hash="")
    session.add(user)
    await session.flush()
    paper = Paper(user_id=user.id, title="Elements", status="imported")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path="pdfs/elements.pdf", page_count=1)
    session.add(document)
    await session.flush()
    old_section = Section(document_id=document.id, title="Old", level=1, order_index=0, page_start=1, page_end=1, content="old")
    old_element = DocumentElement(document_id=document.id, order_index=0, element_type="figure", page_number=1, caption="Old Figure")
    session.add_all([old_section, old_element])
    await session.flush()

    invalid = DetectedElement(uuid.uuid4(), None, "figure", 0, 1, "Figure 1", "New", "New", 0.1, None, 0.4, 0.2, 0.9)
    snapshot = DerivedDocumentSnapshot([], [], [], [invalid])
    with pytest.raises(DocumentParseError):
        await DocumentDerivedService(session).replace(document, snapshot)

    persisted = (await session.execute(select(DocumentElement).where(DocumentElement.document_id == document.id))).scalars().all()
    assert [element.caption for element in persisted] == ["Old Figure"]
