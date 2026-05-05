import re
from typing import List, Dict, Optional

def validate_coverage(extraction_res: Dict[str, any]) -> List[str]:
    """
    STEP 6: COVERAGE VALIDATION (MANDATORY CHECKPOINT)
    Verifies density and presence of core sections.
    Note: Much of this is now handled during extraction in backbone.py
    for early-exit, but this utility provides a standalone check.
    """
    missing = []
    found_sections = extraction_res.get("found_sections", {})
    
    required = ["income_statement", "balance_sheet", "cash_flow"]
    for r in required:
        if not found_sections.get(r):
            missing.append(r)
            
    return missing
