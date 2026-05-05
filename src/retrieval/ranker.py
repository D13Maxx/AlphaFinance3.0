from typing import List, Tuple
from src.retrieval.chunk_builder import Chunk

# Weights configuration
PRIORITY_WEIGHTS = {
    "numeric": {
        "financial_statements": 1.0,
        "balance_sheet": 0.9,
        "income_statement": 0.9,
        "cash_flow": 0.9,
        "assets": 0.85,
        "liabilities": 0.85,
        "general": 0.2
    },
    "interpretive": {
        "mdna": 1.0,
        "risk_factors": 0.9,
        "executive_summary": 0.85,
        "market_opportunity": 0.8,
        "projections": 0.75,
        "general": 0.6
    }
}

SIMILARITY_WEIGHT = 0.75
PRIORITY_FACTOR = 0.25

def apply_hybrid_ranking(similarity_scores: list, 
                         chunks: List[Chunk], 
                         mode: str) -> List[Tuple[Chunk, float]]:
    """
    Combines similarity scores with heuristic priority weights.
    final_score = 0.75 * similarity + 0.25 * priority
    """
    if len(similarity_scores) != len(chunks):
        raise ValueError("Similarity scores and chunk list length mismatch")
    
    ranked = []
    
    # Select weight map based on mode (default to general if unknown mode)
    weight_map = PRIORITY_WEIGHTS.get(mode, PRIORITY_WEIGHTS["numeric"]) # Fallback to numeric or just empty? 

    # If mode is invalid, maybe fallback to general=0.0?
    if mode not in PRIORITY_WEIGHTS:
        weight_map = {"general": 0.5} # Safe fallback

    for i, chunk in enumerate(chunks):
        sim_score = float(similarity_scores[i])
        
        # Look up priority
        # Use semantic_tag driven by chunk_builder
        tag = chunk.semantic_tag
        priority = weight_map.get(tag, weight_map.get("general", 0.5))
        
        final_score = (SIMILARITY_WEIGHT * sim_score) + (PRIORITY_FACTOR * priority)
        
        ranked.append((chunk, final_score))
        
    # Sort descending
    ranked.sort(key=lambda x: x[1], reverse=True)
    
    return ranked
