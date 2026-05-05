def run_comparison_mode(session_context):
    results = {}

    for name, state in session_context.companies.items():
        results[name] = {
            "metrics": {
                "revenue_growth": state.get_revenue_growth(),
                "piotroski": state.compute_piotroski(),
            },
            "signals": {
                "growth_consistency": state.get_growth_consistency_signal(),
                "leverage_improvement": state.get_leverage_improvement_signal(),
            },
            "diagnostics": {
                "balance_identity_valid": state.validate_balance_identity(),
            },
            "overall_confidence": state.get_overall_confidence(),
        }

    return {
        "mode": "comparison",
        "companies": results,
    }
