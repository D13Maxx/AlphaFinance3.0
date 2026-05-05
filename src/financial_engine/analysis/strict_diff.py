def generate_strict_diff(base_state, strict_state):
    diff = {}

    base_growth = base_state.get_revenue_growth()
    strict_growth = strict_state.get_revenue_growth()

    if base_growth.value != strict_growth.value:
        diff["revenue_growth"] = {
            "base": base_growth,
            "strict": strict_growth,
        }

    base_piotroski = base_state.compute_piotroski()
    strict_piotroski = strict_state.compute_piotroski()

    if base_piotroski.value != strict_piotroski.value:
        diff["piotroski"] = {
            "base": base_piotroski,
            "strict": strict_piotroski,
        }

    return diff
