import re
from typing import Dict, Any, List
from src.parser.models import Document, Section

def extract_structural_features(document: Document) -> Dict[str, Any]:
    """
    Extracts structural features from a Document object.
    
    Includes:
    - Global features (counts, depths, spans)
    - SEC document indicators
    - Memo indicators
    - PFS indicators
    
    All section heading checks are case-insensitive.
    """
    
    features = {
        # Global
        "total_sections": 0,
        "max_depth": 0,
        "total_line_count": len(document.lines),
        "avg_section_span": 0.0,
        
        # SEC Indicators
        "item_section_count": 0,
        "has_mdna_section": False,
        "has_risk_factors_section": False,
        "has_financial_statements_section": False,
        
        # Memo Indicators
        "has_executive_summary": False,
        "has_investment_highlights": False,
        "has_market_opportunity": False,
        "has_exit_strategy": False,
        
        # PFS Indicators
        "has_assets_section": False,
        "has_liabilities_section": False,
        "has_net_worth_section": False,
        "is_short_document": False
    }

    # Short document check
    features["is_short_document"] = features["total_line_count"] < 500

    def _normalize_heading(text: str) -> str:
        """
        Strips numbering prefixes like 'Item 1A.', '1.', etc.
        Returns lowercased semantic title.
        """
        # Lowercase and strip whitespace
        normalized = text.lower().strip()
        # Remove "Item X." or "1.2." numbering at start
        # Regex matches:
        # ^(item\s+[a-z0-9\.]+\s*) -> "item 1a. "
        # |([\d\.]+\s*) -> "1. " or "1.2. "
        normalized = re.sub(r'^(item\s+[a-z0-9\.]+\s*|[\d\.]+\s*)', '', normalized)
        return normalized.strip()

    def traverse(sections: List[Section]):
        for section in sections:
            features["total_sections"] += 1
            if section.level > features["max_depth"]:
                features["max_depth"] = section.level
            
            heading_lower = section.heading.lower()
            normalized_heading = _normalize_heading(section.heading)
            
            # SEC Checks
            # "Item " check on raw lower heading
            if heading_lower.lstrip().startswith("item "):
                features["item_section_count"] += 1
            
            # MD&A
            if "management's discussion" in heading_lower or "md&a" in heading_lower:
                features["has_mdna_section"] = True
                
            # Risk Factors (Exact match on normalized heading, e.g. "Item 1A. Risk Factors" -> "risk factors")
            if normalized_heading == "risk factors":
                features["has_risk_factors_section"] = True
            
            # Financial Statements
            if "financial statements" in heading_lower:
                features["has_financial_statements_section"] = True
                
            # Memo Checks (Containment usually safe for these titles)
            if "executive summary" in heading_lower:
                features["has_executive_summary"] = True
            if "investment highlights" in heading_lower:
                features["has_investment_highlights"] = True
            if "market opportunity" in heading_lower:
                features["has_market_opportunity"] = True
            if "exit strategy" in heading_lower:
                features["has_exit_strategy"] = True
                
            # PFS Checks (Containment)
            if "assets" in heading_lower:
                features["has_assets_section"] = True
            if "liabilities" in heading_lower:
                features["has_liabilities_section"] = True
            if "net worth" in heading_lower:
                features["has_net_worth_section"] = True
            
            # Recurse
            traverse(section.subsections)

    traverse(document.sections)

    if features["total_sections"] > 0:
        features["avg_section_span"] = features["total_line_count"] / features["total_sections"]

    return features
