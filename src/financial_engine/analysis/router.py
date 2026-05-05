from .modes.performance import run_performance_mode
from .modes.cash_quality import run_cash_quality_mode
from .modes.strength import run_strength_mode
from .modes.comprehensive import run_comprehensive_mode
from .modes.comparison import run_comparison_mode


class AnalysisRouter:

    def __init__(self, session_context):
        self.session_context = session_context

    def run(self, query: str):
        q = query.lower()

        if "compare" in q or "comparison" in q:
            return run_comparison_mode(self.session_context)

        state = self.session_context.get_active_state()

        if any(word in q for word in ["growth", "revenue", "trend"]):
            return run_performance_mode(state)

        if any(word in q for word in ["cash", "cfo", "quality"]):
            return run_cash_quality_mode(state)

        if any(word in q for word in ["leverage", "debt", "solvency"]):
            return run_strength_mode(state)

        if any(word in q for word in ["overall", "summary", "analysis"]):
            return run_comprehensive_mode(state)

        return {"mode": "qualitative"}
