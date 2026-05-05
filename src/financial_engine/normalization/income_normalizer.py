from decimal import Decimal
from typing import Dict, Optional
from ..models.raw_models import RawStatement
from ..models.canonical_models import IncomeStatement
from ..models.strict_config import StrictConfig
from .matching import anchored_match, token_similarity


INCOME_PATTERNS = {
    "revenue": [
        ("total revenue", Decimal("1.0")),
        ("revenue", Decimal("0.95")),
        ("net sales", Decimal("0.9")),
    ],
    "net_income": [
        ("net income", Decimal("1.0")),
        ("net earnings", Decimal("0.95")),
    ],
}


FALLBACK_THRESHOLD = Decimal("0.75")


def match_row(rows, patterns, strict: StrictConfig):
    best_match = None
    best_weight = Decimal("0")

    for row in rows:
        for pattern, weight in patterns:
            if anchored_match(row.raw_label, pattern):
                if weight > best_weight:
                    best_match = row
                    best_weight = weight

    if best_match:
        return best_match

    if strict.disable_fallback_matching:
        return None

    # fallback
    for row in rows:
        similarity = token_similarity(row.raw_label, patterns[0][0])
        if similarity >= FALLBACK_THRESHOLD:
            return row

    return None


def normalize_income(raw_statement: RawStatement, strict: StrictConfig) -> Optional[Dict[int, IncomeStatement]]:
    if not raw_statement.tables:
        return None

    table = raw_statement.tables[0]

    years = table.detected_years
    result = {}

    for year in years:
        revenue_row = match_row(table.rows, INCOME_PATTERNS["revenue"], strict)
        net_income_row = match_row(table.rows, INCOME_PATTERNS["net_income"], strict)

        revenue = None
        net_income = None

        if revenue_row and year in revenue_row.values:
            revenue = revenue_row.values[year].value * table.scaling_factor

        if net_income_row and year in net_income_row.values:
            net_income = net_income_row.values[year].value * table.scaling_factor

        result[year] = IncomeStatement(
            year=year,
            revenue=revenue,
            cogs=None,
            gross_profit=None,
            operating_income=None,
            net_income=net_income,
        )

    return result
