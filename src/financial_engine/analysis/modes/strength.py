def run_strength_mode(state):
    return {
        "mode": "strength",
        "metrics": {
            "debt_ratio": state.get_debt_ratio(),
            "current_ratio": state.get_current_ratio(),
            "piotroski": state.compute_piotroski(),
        },
        "signals": {
            "leverage_improvement": state.get_leverage_improvement_signal(),
            "stability": state.get_stability_signal(),
        },
        "diagnostics": {
            "balance_identity_valid": state.validate_balance_identity(),
        },
    }
