from dataclasses import dataclass
from typing import Dict, Any
from decimal import Decimal


@dataclass(frozen=True)
class AnalysisResponse:
    mode: str
    metrics: Dict[str, Any]
    signals: Dict[str, Any]
    diagnostics: Dict[str, Any]
    overall_confidence: Decimal
    strict_diff: Dict[str, Any]
    analysis_time_ms: int
