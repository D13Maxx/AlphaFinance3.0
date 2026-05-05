def compute_confidence(avg_semantic: float,
                       avg_lexical: float) -> str:

    score = 0.7 * avg_semantic + 0.3 * avg_lexical

    if score > 0.75:
        return "HIGH"
    elif score > 0.5:
        return "MEDIUM"
    return "LOW"
