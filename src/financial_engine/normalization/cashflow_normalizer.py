from decimal import Decimal
from typing import Dict, Optional
from ..models.raw_models import RawStatement
from ..models.canonical_models import CashFlowStatement
from ..models.strict_config import StrictConfig
from .matching import anchored_match


CFO_PATTERNS = [("net cash provided by operating", Decimal("1.0"))]
CFI_PATTERNS = [("net cash used in investing", Decimal("1.0"))]
CFF_PATTERNS = [("net cash provided by financing", Decimal("1.0"))]


def match_row(rows, patterns):
    for row in rows:
        for pattern, _ in patterns:
            if anchored_match(row.raw_label, pattern):
                return row
    return None


def normalize_cashflow(raw_statement: RawStatement, strict: StrictConfig) -> Optional[Dict[int, CashFlowStatement]]:
    if not raw_statement.tables:
        return None

    table = raw_statement.tables[0]
    years = table.detected_years
    result = {}

    for year in years:
        cfo_row = match_row(table.rows, CFO_PATTERNS)
        cfi_row = match_row(table.rows, CFI_PATTERNS)
        cff_row = match_row(table.rows, CFF_PATTERNS)

        cfo = cfo_row.values[year].value * table.scaling_factor if cfo_row and year in cfo_row.values else None
        cfi = cfi_row.values[year].value * table.scaling_factor if cfi_row and year in cfi_row.values else None
        cff = cff_row.values[year].value * table.scaling_factor if cff_row and year in cff_row.values else None

        result[year] = CashFlowStatement(
            year=year,
            cfo=cfo,
            cfi=cfi,
            cff=cff,
            capex=None,
        )

    return result
