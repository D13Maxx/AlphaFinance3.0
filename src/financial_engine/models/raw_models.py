from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RawCell:
    raw_text: str
    value: Optional[Decimal]
    is_negative: bool


@dataclass(frozen=True)
class RawRow:
    raw_label: str
    normalized_label: str
    values: Dict[int, RawCell]
    indent_level: int
    row_index: int


@dataclass(frozen=True)
class RawTable:
    table_id: str
    page_number: int
    detected_years: List[int]
    scaling_factor: Decimal
    rows: List[RawRow]
    confidence_score: Decimal


@dataclass(frozen=True)
class RawStatement:
    statement_type: str
    tables: List[RawTable]
