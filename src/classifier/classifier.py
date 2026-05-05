from typing import Dict, Any, List
from src.parser.models import Document
from src.classifier.content_signals import extract_content_signals
from src.classifier.structural_signals import extract_structural_features
from src.classifier.scoring import compute_structural_scores, blend_scores

def classify_document(document: Document) -> Dict[str, Any]:
    """
    Classifies a document into one of: SEC_Filing, Investment_Memo, PFS, or Unknown.
    Uses strict deterministic rules and scoring thresholds.
    """
    # 1. Extract content signals
    content_scores = extract_content_signals(document)
    
    # 2. Extract structural features
    structural_features = extract_structural_features(document)
    
    # 3. Compute structural scores
    structural_scores = compute_structural_scores(structural_features)
    
    # 4. Blend scores
    final_scores = blend_scores(content_scores, structural_scores)
    
    # 5. Determine label
    max_label = "Unknown"
    max_score = 0.0
    total_score_sum = 0.0
    
    # Find max score and sum
    for label, score in final_scores.items():
        total_score_sum += score
        if score > max_score:
            max_score = score
            max_label = label
            
    # Calculate confidence
    confidence = 0.0
    if total_score_sum > 0:
        confidence = max_score / total_score_sum
        
    # 6. Apply threshold rules
    
    # Rule A: Zero score -> Unknown
    if max_score == 0:
        return {
            "label": "Unknown",
            "confidence": 0.0,
            "scores": final_scores
        }
        
    # Rule B: Low confidence -> Unknown
    if confidence < 0.6:
        return {
            "label": "Unknown",
            "confidence": confidence,
            "scores": final_scores
        }
        
    # Rule C: Low margin -> Unknown
    # "Else if difference between top two scores < 10% of max_score"
    sorted_scores = sorted(final_scores.values(), reverse=True)
    if len(sorted_scores) >= 2:
        top1 = sorted_scores[0]
        top2 = sorted_scores[1]
        diff = top1 - top2
        if diff < (0.10 * max_score):
             return {
                "label": "Unknown",
                "confidence": confidence,
                "scores": final_scores
            }

    return {
        "label": max_label,
        "confidence": confidence,
        "scores": final_scores
    }
