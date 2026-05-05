from decimal import Decimal
from typing import List, Tuple


def normalize_label(label: str) -> str:
    return label.strip().lower().replace(",", "").replace("  ", " ")


def anchored_match(label: str, pattern: str) -> bool:
    return normalize_label(label).startswith(pattern)


def token_similarity(a: str, b: str) -> Decimal:
    tokens_a = set(normalize_label(a).split())
    tokens_b = set(normalize_label(b).split())
    if not tokens_a or not tokens_b:
        return Decimal("0")
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return Decimal(len(intersection)) / Decimal(len(union))
