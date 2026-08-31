from decimal import Decimal
import uuid

import pytest

from app.services.ai_cost import PriceSnapshot, calculate_cost, estimate_tokens
from app.services.ai_provider_service import AIProviderService
from app.services.translation_service import TranslationService
from app.services.page_block_service import PageBlockService
from app.parsers.base import ParsedDocument, ParsedPage, ParsedTextBlock
from app.parsers.page_block_detector import PageBlockDetector
from app.models import Document, PageBlock, Paper, TranslationBlock, User
from app.schemas.translation import CustomPageBlockCreate, CustomPageBlockUpdate, ManualTranslationBlockSave, PageBlockBBox, PageBlockTextStyle


def test_decimal_cost_separates_cached_input_without_double_charge():
    price = PriceSnapshot("USD", Decimal("2"), Decimal("0.5"), Decimal("8"))
    assert calculate_cost(1_000_000, 250_000, 100_000, price) == Decimal("2.4250000000")


def test_unknown_price_is_not_silently_zero():
    price = PriceSnapshot("USD", None, None, Decimal("8"))
    assert calculate_cost(100, 0, 50, price) is None
    assert estimate_tokens("research") > 0


def test_cloud_provider_rejects_http_and_private_networks():
    with pytest.raises(ValueError):
        AIProviderService._validate_url("http://api.example.com/v1", False)
    with pytest.raises(ValueError):
        AIProviderService._validate_url("https://127.0.0.1/v1", False)
    AIProviderService._validate_url("http://127.0.0.1:11434/v1", True)


def test_translation_structured_output_matches_ids_and_rejects_unknown():
    protected = {"a": ("Hello __PROTECTED_001__", ["[1]"])}
    parsed = TranslationService._parse('{"translations":[{"id":"a","translated_text":"你好 __PROTECTED_001__"}]}', protected)
    assert TranslationService._restore(parsed["a"], protected["a"][1]) == "你好 [1]"
    with pytest.raises(ValueError):
        TranslationService._parse('{"translations":[{"id":"b","translated_text":"bad"}]}', protected)


def test_translation_placeholder_loss_is_rejected():
    protected_text, values = TranslationService._protect("See https://example.com and [12].")
    assert len(values) == 2
    with pytest.raises(ValueError):
        TranslationService._restore("链接丢失", values)


def test_page_block_detector_creates_one_default_full_page_region():
    page = ParsedPage(page_number=1, text="", width=600, height=800, blocks=[
        ParsedTextBlock("Left", 1, 40, 100, 80, 112, 10),
        ParsedTextBlock("column", 1, 85, 100, 135, 112, 10),
        ParsedTextBlock("continues.", 1, 40, 116, 100, 128, 10),
        ParsedTextBlock("Right", 1, 330, 100, 375, 112, 10),
        ParsedTextBlock("column.", 1, 380, 100, 440, 112, 10),
    ])
    blocks = PageBlockDetector().detect(ParsedDocument(1, [page], {}, []))
    assert len(blocks) == 1
    assert blocks[0].name == "整页"
    assert blocks[0].is_default is True
    assert blocks[0].bounding_box == {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}


@pytest.mark.asyncio
async def test_manual_translation_can_create_first_translation_without_ai(session):
    user = User(id=uuid.uuid4(), username="manual-translator", email="manual-translator@test.local", password_hash="")
    session.add(user)
    await session.flush()
    paper = Paper(user_id=user.id, title="Manual translation", status="ready")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path="pdfs/manual.pdf", file_hash="abc", parse_status="ready", parser_version="pdf-parser-v2", page_count=1)
    session.add(document)
    await session.flush()
    page_block = PageBlock(document_id=document.id, paper_id=paper.id, page_number=1, block_order=0,
        reading_order=0, block_type="paragraph", column_index=0, bounding_box={"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.1},
        source_text="Original text", normalized_text="Original text", source_hash="source-hash", parser_version="page-block-v1")
    session.add(page_block)
    await session.flush()

    saved = await TranslationService(session).save_manual_block(user.id, paper.id, ManualTranslationBlockSave(
        document_id=document.id, page_block_id=page_block.id, user_translation="人工译文",
    ))

    assert saved.machine_translation is None
    assert saved.user_translation == "人工译文"
    assert saved.status == "completed"
    assert saved.page_block_id == page_block.id

    updated = await TranslationService(session).update_block(user.id, saved.id, "修改后译文", saved.revision)
    assert updated.user_translation == "修改后译文"

    # The endpoint must commit, otherwise leaving and reopening Reader rolls the edit back.
    translation_block_id = updated.id
    await session.rollback()
    session.expire_all()
    persisted = await session.get(TranslationBlock, translation_block_id)
    assert persisted is not None
    assert persisted.user_translation == "修改后译文"


@pytest.mark.asyncio
async def test_custom_page_block_crud_is_committed(session, monkeypatch):
    async def fake_extract(*_args, **_kwargs):
        return "Selected source text"

    monkeypatch.setattr(PageBlockService, "_extract", staticmethod(fake_extract))
    user = User(id=uuid.uuid4(), username="region-owner", email="region-owner@test.local", password_hash="")
    session.add(user)
    await session.flush()
    paper = Paper(user_id=user.id, title="Region persistence", status="ready")
    session.add(paper)
    await session.flush()
    document = Document(paper_id=paper.id, file_path="pdfs/region.pdf", file_hash="region-hash", parse_status="ready", page_count=1)
    session.add(document)
    await session.flush()
    user_id = user.id
    paper_id = paper.id
    document_id = document.id

    service = PageBlockService(session)
    created = await service.create(user_id, document_id, CustomPageBlockCreate(
        page_number=1, name="实验区域", bounding_box=PageBlockBBox(x=.1, y=.1, width=.4, height=.3),
    ))
    block_id = created.id
    await session.rollback()
    session.expire_all()
    persisted = await session.get(PageBlock, block_id)
    assert persisted is not None
    assert persisted.name == "实验区域"

    manual = await TranslationService(session).save_manual_block(user_id, paper_id, ManualTranslationBlockSave(
        document_id=document_id, page_block_id=block_id, user_translation="保留的人工译文",
    ))
    translation_id = manual.id

    updated = await service.update(user_id, block_id, CustomPageBlockUpdate(
        bounding_box=PageBlockBBox(x=.2, y=.2, width=.5, height=.4),
        text_style=PageBlockTextStyle(font_size=18, color="#2563eb"),
    ))
    assert updated.bounding_box["x"] == .2
    assert updated.text_style == {"font_size": 18, "color": "#2563eb"}
    await session.rollback()
    session.expire_all()
    persisted = await session.get(PageBlock, block_id)
    assert persisted is not None
    assert persisted.bounding_box["width"] == .5
    assert persisted.text_style["font_size"] == 18
    persisted_translation = await session.get(TranslationBlock, translation_id)
    assert persisted_translation is not None
    assert persisted_translation.user_translation == "保留的人工译文"

    await service.delete(user_id, block_id)
    await session.rollback()
    assert await session.get(PageBlock, block_id) is None
