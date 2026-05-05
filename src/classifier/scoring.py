from typing import Dict, Any

ALPHA = 0.65
BETA = 0.35

def compute_structural_scores(features: Dict[str, Any]) -> Dict[str, int]:
    """
    Computes structural scores for each document type based on extracted features.
    """
    scores = {
        "SEC_Filing": 0,
        "Investment_Memo": 0,
        "PFS": 0
    }
    
    # SEC_Filing Rules
    if features.get("item_section_count", 0) >= 3:
        scores["SEC_Filing"] += 4
    if features.get("has_mdna_section"):
        scores["SEC_Filing"] += 4
    if features.get("has_risk_factors_section"):
        scores["SEC_Filing"] += 4
    if features.get("has_financial_statements_section"):
        scores["SEC_Filing"] += 3
    if features.get("total_sections", 0) > 10:
        scores["SEC_Filing"] += 3
        
    # Investment_Memo Rules
    if features.get("has_executive_summary"):
        scores["Investment_Memo"] += 4
    if features.get("has_investment_highlights"):
        scores["Investment_Memo"] += 3
    if features.get("has_market_opportunity"):
        scores["Investment_Memo"] += 3
    if features.get("has_exit_strategy"):
        scores["Investment_Memo"] += 3
    
    total_sections = features.get("total_sections", 0)
    if 3 <= total_sections <= 10:
        scores["Investment_Memo"] += 2
        
    # PFS Rules
    if features.get("has_assets_section"):
        scores["PFS"] += 4
    if features.get("has_liabilities_section"):
        scores["PFS"] += 4
    if features.get("has_net_worth_section"):
        scores["PFS"] += 3
    if features.get("is_short_document"):
        scores["PFS"] += 3
        
    return scores

def blend_scores(content_scores: Dict[str, int], structural_scores: Dict[str, int]) -> Dict[str, float]:
    """
    Blends content and structural scores using weighted sum.
    Formula: total_score[type] = ALPHA * content_scores[type] + BETA * structural_scores[type]
    """
    final_scores = {}
    
    for category in content_scores:
        c_score = content_scores.get(category, 0)
        s_score = structural_scores.get(category, 0)
        
        final_scores[category] = (ALPHA * c_score) + (BETA * s_score)
        
    return final_scores
