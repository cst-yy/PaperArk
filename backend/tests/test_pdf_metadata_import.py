from io import BytesIO

import fitz
import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.paper_service as paper_service_module
from app.models import User
from app.parsers.paper_metadata_extractor import PaperMetadataExtractor
from app.services.paper_service import PaperService


def _metadata_pdf(path, *, embedded: bool = True) -> bytes:
    with fitz.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        page.insert_text((72, 90), "Reliable Metadata Extraction for Research PDFs", fontsize=20)
        page.insert_text((72, 125), "Alice Smith, Bob Chen", fontsize=11)
        page.insert_text((72, 150), "Department of Research, Example University", fontsize=9)
        page.insert_text((72, 175), "Abstract", fontsize=12)
        page.insert_text((72, 195), "We present a reliable offline metadata extraction pipeline.", fontsize=10)
        page.insert_text((72, 220), "Keywords: metadata extraction; document parsing; research workflow", fontsize=10)
        page.insert_text((72, 245), "DOI: 10.1234/TEST.Meta.2024", fontsize=10)
        page.insert_text((72, 270), "arXiv: 2401.01234v2", fontsize=10)
        page.insert_text((72, 295), "Conference: TestConf 2024", fontsize=10)
        page.insert_text((72, 320), "Publisher: Example Press", fontsize=10)
        page.insert_text((72, 350), "1 Introduction", fontsize=12)
        if embedded:
            pdf.set_metadata({
                "title": "Reliable Metadata Extraction for Research PDFs",
                "author": "Alice Smith; Bob Chen",
                "keywords": "metadata extraction; document parsing; research workflow",
                "subject": "Journal: Journal of Reliable Systems",
                "creationDate": "D:20240203000000Z",
            })
        content = pdf.tobytes()
    path.write_bytes(content)
    return content


def test_extracts_embedded_and_visible_pdf_metadata(tmp_path):
    pdf_path = tmp_path / "source.pdf"
    _metadata_pdf(pdf_path)

    result = PaperMetadataExtractor().extract(pdf_path, "source")

    assert result.title == "Reliable Metadata Extraction for Research PDFs"
    assert [author.name for author in result.authors] == ["Alice Smith", "Bob Chen"]
    assert result.abstract == "We present a reliable offline metadata extraction pipeline."
    assert result.keywords == ["metadata extraction", "document parsing", "research workflow"]
    assert result.doi == "10.1234/test.meta.2024"
    assert result.arxiv_id == "2401.01234v2"
    assert result.publication_year == 2024
    assert result.journal == "Journal of Reliable Systems"
    assert result.conference == "TestConf 2024"
    assert result.publisher == "Example Press"


def test_layout_fallback_extracts_title_and_authors(tmp_path):
    pdf_path = tmp_path / "layout-only.pdf"
    _metadata_pdf(pdf_path, embedded=False)

    result = PaperMetadataExtractor().extract(pdf_path, "layout-only")

    assert result.title == "Reliable Metadata Extraction for Research PDFs"
    assert [author.name for author in result.authors] == ["Alice Smith", "Bob Chen"]


def test_layout_authors_join_wrapped_names_and_drop_roles_affiliations(tmp_path):
    pdf_path = tmp_path / "wrapped-authors.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        page.insert_text((72, 80), "A Reliable Author Parsing Study", fontsize=20)
        page.insert_text((72, 120), "Wayne Zhao, Beichen", fontsize=11)
        page.insert_text((72, 138), "Zhang, Alice Smith*, Senior Member, IEEE, and Bob Chen", fontsize=11)
        page.insert_text((72, 165), "Department of Computer Science, Example University", fontsize=9)
        page.insert_text((72, 200), "Abstract", fontsize=12)
        pdf.save(pdf_path)

    result = PaperMetadataExtractor().extract(pdf_path, "wrapped-authors")

    assert [author.name for author in result.authors] == ["Wayne Zhao", "Beichen Zhang", "Alice Smith", "Bob Chen"]
    assert {author.affiliation for author in result.authors} == {"Department of Computer Science, Example University"}


def test_numbered_author_affiliations_are_mapped_without_becoming_authors(tmp_path):
    pdf_path = tmp_path / "numbered-affiliations.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        page.insert_text((72, 80), "Structured Affiliation Mapping", fontsize=20)
        page.insert_text((72, 120), "Alice Smith1,2, Bob Chen2, Carol Wu3", fontsize=11)
        page.insert_text((72, 150), "1Example Research Laboratory", fontsize=9)
        page.insert_text((72, 166), "2School of Computing, Example University", fontsize=9)
        page.insert_text((72, 182), "3CASIA", fontsize=9)
        page.insert_text((72, 215), "Abstract", fontsize=12)
        pdf.save(pdf_path)

    result = PaperMetadataExtractor().extract(pdf_path, "numbered-affiliations")

    assert [(author.name, author.affiliation) for author in result.authors] == [
        ("Alice Smith", "Example Research Laboratory; School of Computing, Example University"),
        ("Bob Chen", "School of Computing, Example University"),
        ("Carol Wu", "CASIA"),
    ]


def test_multiline_keywords_after_abstract_are_joined_and_bounded(tmp_path):
    pdf_path = tmp_path / "multiline-keywords.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        page.insert_text((72, 80), "Multiline Keyword Extraction", fontsize=20)
        page.insert_text((72, 120), "Alice Smith, Bob Chen", fontsize=11)
        page.insert_text((72, 165), "Abstract—A concise research abstract.", fontsize=10)
        page.insert_text((72, 195), "Index Terms: Heterogeneous federated learning, knowl-", fontsize=10)
        page.insert_text((72, 212), "edge distillation, model compression, representation learning.", fontsize=10)
        page.insert_text((72, 245), "NOMENCLATURE", fontsize=12)
        page.insert_text((72, 270), "This must not become a keyword", fontsize=10)
        pdf.save(pdf_path)

    result = PaperMetadataExtractor().extract(pdf_path, "multiline-keywords")

    assert result.keywords == [
        "Heterogeneous federated learning",
        "knowledge distillation",
        "model compression",
        "representation learning",
    ]


@pytest.mark.asyncio
async def test_import_pdf_persists_metadata_authors_and_keyword_sources(
    session: AsyncSession, tmp_path, monkeypatch
):
    pdf_path = tmp_path / "import.pdf"
    content = _metadata_pdf(pdf_path)
    user = User(username="metadata-import", email="metadata-import@example.com", password_hash="test")
    session.add(user)
    await session.flush()

    async def fake_save_bytes(_content: bytes, _sub_dir: str, _ext: str):
        return pdf_path

    monkeypatch.setattr(paper_service_module, "save_bytes", fake_save_bytes)
    monkeypatch.setattr(paper_service_module, "get_relative_path", lambda _path: "pdfs/import.pdf")
    upload = UploadFile(filename="meaningless-filename.pdf", file=BytesIO(content), headers={"content-type": "application/pdf"})

    paper = await PaperService(session).import_pdf(user.id, upload)

    assert paper.title == "Reliable Metadata Extraction for Research PDFs"
    assert paper.abstract == "We present a reliable offline metadata extraction pipeline."
    assert paper.doi == "10.1234/test.meta.2024"
    assert paper.arxiv_id == "2401.01234v2"
    assert paper.publication_year == 2024
    assert paper.journal == "Journal of Reliable Systems"
    assert paper.conference == "TestConf 2024"
    assert paper.publisher == "Example Press"
    assert [link.author.name for link in sorted(paper.authors, key=lambda item: item.author_order)] == ["Alice Smith", "Bob Chen"]
    assert {link.author.affiliation for link in paper.authors} == {"Department of Research, Example University"}
    assert {link.keyword.display_name for link in paper.keywords} == {"metadata extraction", "document parsing", "research workflow"}
    assert {link.source for link in paper.keywords} == {"metadata"}
