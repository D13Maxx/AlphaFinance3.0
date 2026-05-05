from typing import Dict, List
from src.parser.models import Document, Section

# Scoring Rules (Category -> Weight -> Keywords)
SCORING_RULES = {
    "SEC_Filing": {
        5: [
            "form 10-k", "form 10-q", "securities and exchange commission",
            "commission file number", "cik"
        ],
        3: [
            "risk factors", "management’s discussion", "management's discussion", "financial statements"
        ],
        1: [] # Special handling for "item " prefix
    },
    "Investment_Memo": {
        5: [
            "confidential information memorandum", "investment memorandum"
        ],
        3: [
            "investment highlights", "market opportunity", "exit strategy"
        ],
        1: [
            "projections", "forecast"
        ]
    },
    "PFS": {
        5: [
            "personal financial statement"
        ],
        3: [
            "assets", "liabilities", "net worth"
        ],
        1: [
            "individual"
        ]
    }
}

def extract_content_signals(document: Document) -> Dict[str, int]:
    scores = {
        "SEC_Filing": 0,
        "Investment_Memo": 0,
        "PFS": 0
    }

    def _score_heading(heading: str):
        heading_lower = heading.lower()
        
        # SEC Special Weak Rule: Starts with "item "
        if heading_lower.lstrip().startswith("item "):
            scores["SEC_Filing"] += 1

        for category, weights in SCORING_RULES.items():
            for weight, keywords in weights.items():
                for keyword in keywords:
                    if keyword in heading_lower:
                        scores[category] += weight

    def traverse(sections: List[Section]):
        for section in sections:
            _score_heading(section.heading)
            traverse(section.subsections)

    traverse(document.sections)
    return scores
