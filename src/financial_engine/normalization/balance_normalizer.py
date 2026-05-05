from decimal import Decimal
from typing import Dict, Optional
from ..models.raw_models import RawStatement
from ..models.canonical_models import BalanceSheet
from ..models.strict_config import StrictConfig
from .matching import anchored_match


ASSET_PATTERNS = [("total assets", Decimal("1.0"))]
LIAB_PATTERNS = [("total liabilities", Decimal("1.0"))]
EQUITY_PATTERNS = [("total equity", Decimal("1.0"))]


def match_row(rows, patterns):
    for row in rows:
        for pattern, _ in patterns:
            if anchored_match(row.raw_label, pattern):
                return row
    return None


def normalize_balance(raw_statement: RawStatement, strict: StrictConfig) -> Optional[Dict[int, BalanceSheet]]:
    if not raw_statement.tables:
        return None

    table = raw_statement.tables[0]
    years = table.detected_years
    result = {}

    for year in years:
        asset_row = match_row(table.rows, ASSET_PATTERNS)
        liab_row = match_row(table.rows, LIAB_PATTERNS)
        equity_row = match_row(table.rows, EQUITY_PATTERNS)

        assets = asset_row.values[year].value * table.scaling_factor if asset_row and year in asset_row.values else None
        liabilities = liab_row.values[year].value * table.scaling_factor if liab_row and year in liab_row.values else None
        equity = equity_row.values[year].value * table.scaling_factor if equity_row and year in equity_row.values else None

        result[year] = BalanceSheet(
            year=year,
            total_assets=assets,
            total_liabilities=liabilities,
            total_equity=equity,
            current_assets=None,
            current_liabilities=None,
            total_debt=None,
            cash=None,
        )

    return result
