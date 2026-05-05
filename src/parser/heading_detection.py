import re
from typing import Tuple

# Semantic keywords for fallback heuristic
SEMANTIC_KEYWORDS = {
    "introduction", "background", "abstract", "executive summary", 
    "conclusion", "references", "appendix", "table of contents",
    "definitions", "preamble", "summary"
}

def detect_heading(line: str, parent_level: int) -> Tuple[bool, int]:
    """
    Detects if a line is a heading and returns (is_heading, level).
    Follows strict priority:
    A) Numbering detection
    B) Semantic fallback keywords
    C) Formatting heuristic
    """
    stripped = line.strip()
    if not stripped:
        return False, 0
    
    # Priority A: Numbering detection
    
    # "Item X." -> level 1
    if re.match(r'^Item\s+\d+\.$', stripped, re.IGNORECASE):
        return True, 1
        
    # Numeric depth like 1., 1.1, 1.1.1 (depth capped at 3)
    # Regex matches "1.", "1.1", "1.1.1" followed by space or end of string
    # We must ensure it's at start of line
    match = re.match(r'^(\d+(?:\.\d+){0,2})\.?(\s|$)', stripped)
    if match:
        numbering = match.group(1)
        # Calculate depth based on dots
        parts = [p for p in numbering.split('.') if p]
        depth = len(parts)
        if depth > 3:
            depth = 3
        return True, depth

    # Priority B: Semantic fallback keywords
    # Check if the lowercased line matches a known keyword exactly
    if stripped.lower() in SEMANTIC_KEYWORDS:
        # Semantic headings are usually top-level
        return True, 1
        
    # Priority C: Formatting heuristic
    # Uppercase ratio > 0.6, length < 120, not ending with "."
    if len(stripped) < 120 and not stripped.endswith('.'):
        letters = [c for c in stripped if c.isalpha()]
        if letters:
            upper_count = sum(1 for c in letters if c.isupper())
            ratio = upper_count / len(letters)
            if ratio > 0.6:
                return True, 1 # Formatting heuristic implies main heading

    return False, 0
