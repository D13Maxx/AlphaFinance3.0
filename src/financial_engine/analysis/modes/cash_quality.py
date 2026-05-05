def run_cash_quality_mode(state):
    return {
        "mode": "cash_quality",
        "metrics": {
            "cfo_to_net_income": state.get_cfo_to_net_income(),
            "free_cash_flow": state.get_free_cash_flow(),
            "ttm_net_income": state.compute_ttm_net_income(),
        },
        "signals": {
            "cash_conversion": state.get_cfo_to_net_income(),
        },
        "diagnostics": {},
    }
