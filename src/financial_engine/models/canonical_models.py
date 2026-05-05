from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, List


@dataclass(frozen=True)
class CanonicalMatchMetadata:
    match_type: str
    match_weight: Decimal
    ambiguity_flag: bool


@dataclass(frozen=True)
class IncomeStatement:
    year: int
    revenue: Optional[Decimal]
    cogs: Optional[Decimal]
    gross_profit: Optional[Decimal]
    operating_income: Optional[Decimal]
    net_income: Optional[Decimal]


@dataclass(frozen=True)
class CashFlowStatement:
    year: int
    cfo: Optional[Decimal]
    cfi: Optional[Decimal]
    cff: Optional[Decimal]
    capex: Optional[Decimal]


@dataclass(frozen=True)
class BalanceSheet:
    year: int
    total_assets: Optional[Decimal]
    total_liabilities: Optional[Decimal]
    total_equity: Optional[Decimal]
    current_assets: Optional[Decimal]
    current_liabilities: Optional[Decimal]
    total_debt: Optional[Decimal]
    cash: Optional[Decimal]


@dataclass(frozen=True)
class StatementSeries:
    years: List[int]
    completeness_score: Decimal
    confidence_score: Decimal
    ambiguity_flags: List[str]
