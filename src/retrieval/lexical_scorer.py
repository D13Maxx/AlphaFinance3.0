import re

def lexical_score(query: str, chunk_text: str) -> float:
    query_terms = set(re.findall(r"\w+", query.lower()))
    chunk_terms = set(re.findall(r"\w+", chunk_text.lower()))

    if not query_terms:
        return 0.0

    overlap = query_terms.intersection(chunk_terms)
    return len(overlap) / len(query_terms)
