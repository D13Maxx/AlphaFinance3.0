def run_performance_mode(state):
    return {
        "mode": "performance",
        "metrics": {
            "revenue_growth": state.get_revenue_growth(),
            "roa": state.get_roa(),
            "roe": state.get_roe(),
            "asset_turnover": state.get_asset_turnover(),
        },
        "signals": {
            "growth_consistency": state.get_growth_consistency_signal(),
            "margin_expansion": state.get_margin_expansion_signal(),
        },
        "diagnostics": {
            "balance_identity_valid": state.validate_balance_identity(),
        },
    }
