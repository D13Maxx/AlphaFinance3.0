FINANCIAL_SYNONYMS = {
    "revenue": ["net sales", "total net sales"],
    "sales": ["revenue", "net sales"],
    "profit": ["net income", "earnings"],
    "earnings": ["net income"],
    "net income": ["profit", "earnings"],
    "income": ["net income"],
    "cash flow": ["operating cash flow"],
}

def expand_query(query: str) -> str:
    query_lower = query.lower()
    expansion_terms = []

    for key, synonyms in FINANCIAL_SYNONYMS.items():
        if key in query_lower:
            expansion_terms.extend(synonyms)

    if expansion_terms:
        return query + " " + " ".join(expansion_terms)

    return query
