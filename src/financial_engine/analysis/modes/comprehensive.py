from .performance import run_performance_mode
from .cash_quality import run_cash_quality_mode
from .strength import run_strength_mode


def run_comprehensive_mode(state):
    perf = run_performance_mode(state)
    cash = run_cash_quality_mode(state)
    strength = run_strength_mode(state)

    return {
        "mode": "comprehensive",
        "metrics": {**perf["metrics"], **cash["metrics"], **strength["metrics"]},
        "signals": {**perf["signals"], **cash["signals"], **strength["signals"]},
        "diagnostics": {
            **perf["diagnostics"],
            **cash["diagnostics"],
            **strength["diagnostics"],
        },
    }
