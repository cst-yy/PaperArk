from decimal import Decimal

import pytest

from app.services.ai_cost import PriceSnapshot, calculate_cost, estimate_tokens
from app.services.ai_provider_service import AIProviderService
from app.services.translation_service import TranslationService
from app.parsers.base import ParsedDocument, ParsedPage, ParsedTextBlock
from app.parsers.page_block_detector import PageBlockDetector


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


def test_page_block_detector_merges_spans_without_crossing_columns():
    page = ParsedPage(page_number=1, text="", width=600, height=800, blocks=[
        ParsedTextBlock("Left", 1, 40, 100, 80, 112, 10),
        ParsedTextBlock("column", 1, 85, 100, 135, 112, 10),
        ParsedTextBlock("continues.", 1, 40, 116, 100, 128, 10),
        ParsedTextBlock("Right", 1, 330, 100, 375, 112, 10),
        ParsedTextBlock("column.", 1, 380, 100, 440, 112, 10),
    ])
    blocks = PageBlockDetector().detect(ParsedDocument(1, [page], {}, []))
    assert len(blocks) == 2
    assert blocks[0].source_text == "Left column continues."
    assert blocks[0].column_index == 0
    assert blocks[1].source_text == "Right column."
    assert blocks[1].column_index == 1
