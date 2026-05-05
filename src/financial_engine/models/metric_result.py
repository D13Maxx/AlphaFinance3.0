from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class MetricResult:
    value: Optional[Decimal]
    confidence: Decimal
    explanation: str
