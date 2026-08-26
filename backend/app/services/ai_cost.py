from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


MILLION = Decimal(1_000_000)
QUANTUM = Decimal("0.0000000001")


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    currency: str
    input_per_million: Decimal | None
    cached_input_per_million: Decimal | None
    output_per_million: Decimal | None

    def as_dict(self) -> dict[str, str | None]:
        return {"currency": self.currency, "input_per_million": self._s(self.input_per_million),
                "cached_input_per_million": self._s(self.cached_input_per_million),
                "output_per_million": self._s(self.output_per_million)}

    @staticmethod
    def _s(value: Decimal | None) -> str | None:
        return str(value) if value is not None else None


def calculate_cost(input_tokens: int, cached_input_tokens: int, output_tokens: int, price: PriceSnapshot) -> Decimal | None:
    if price.input_per_million is None or price.output_per_million is None:
        return None
    cached = min(max(cached_input_tokens, 0), max(input_tokens, 0))
    uncached = max(input_tokens - cached, 0)
    cached_rate = price.cached_input_per_million if price.cached_input_per_million is not None else price.input_per_million
    result = (Decimal(uncached) * price.input_per_million + Decimal(cached) * cached_rate + Decimal(max(output_tokens, 0)) * price.output_per_million) / MILLION
    return result.quantize(QUANTUM, rounding=ROUND_HALF_UP)


def estimate_tokens(text: str) -> int:
    # Conservative language-agnostic fallback. It is explicitly marked estimated.
    return max(1, (len(text.encode("utf-8")) + 3) // 4)
