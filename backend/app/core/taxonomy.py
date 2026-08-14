"""Shared normalization for user-managed taxonomy names."""


def normalize_taxonomy_name(value: str) -> str:
    """Return the stable identity form for a visible taxonomy label."""
    normalized = value.strip().casefold()
    if not normalized:
        raise ValueError("分类名称不能为空")
    return normalized
