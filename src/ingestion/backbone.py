import fitz
import re
from typing import List, Dict, Optional, Tuple

def is_numeric_dense(text: str) -> bool:
    """
    STEP 3: NUMERIC PROTECTION MODE (CRITICAL)
    A line is numeric-dense if:
    - It contains 4 or more digits
    - It contains 2 or more 4-digit years
    - It contains common financial anchor words
    """
    # 4 or more digits
    if len(re.findall(r'\d', text)) >= 4:
        return True
    
    # 2 or more 4-digit years
    years = re.findall(r'\b(19|20)\d{2}\b', text)
    if len(years) >= 2:
        return True
    
    # Financial anchor words
    anchors = [
        "revenue", "net income", "assets", "liabilities", 
        "equity", "cash flow", "operating income"
    ]
    text_lower = text.lower()
    if any(anchor in text_lower for anchor in anchors):
        return True
    
    return False

def extract_backbone(file_path: Optional[str] = None, stream: Optional[bytes] = None) -> Dict[str, any]:
    """
    FORENSIC EXTRACTION ENGINE 2.0
    Uses block-aware extraction and coordinate sorting to preserve structural integrity.
    """
    if stream:
        doc = fitz.open(stream=stream, filetype="pdf")
    elif file_path:
        doc = fitz.open(file_path)
    else:
        raise ValueError("Must provide file_path or stream")

    all_lines = []
    protected_line_indices = []
    
    # Financial Statement Anchors for Step 5
    found_sections = {
        "income_statement": False,
        "balance_sheet": False,
        "cash_flow": False
    }

    is_anchors = ["consolidated statements of income", "statement of operations", "profit and loss"]
    bs_anchors = ["consolidated balance sheets", "statement of financial position"]
    cf_anchors = ["consolidated statements of cash flows", "statement of cash flows"]

    for page_num, page in enumerate(doc):
        height = page.rect.height
        hf_limit = height * 0.05
        
        # STEP 1: BLOCK-LEVEL EXTRACTION
        # blocks: (x0, y0, x1, y1, "text", block_no, block_type)
        blocks = page.get_text("blocks")
        
        # Sort blocks by y0 (vertical), then x0 (horizontal)
        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
        
        for b in sorted_blocks:
            x0, y0, x1, y1, text, block_no, block_type = b
            
            # STEP 2: SAFE HEADER / FOOTER REMOVAL
            if y1 < hf_limit or y0 > (height - hf_limit):
                continue
            
            # Split block into lines to apply numeric protection line-by-line
            block_lines = text.split('\n')
            for line in block_lines:
                clean_line = line.strip()
                if not clean_line:
                    continue
                
                line_lower = clean_line.lower()
                
                # Step 5 detection (Anchor scanning)
                if any(a in line_lower for a in is_anchors): found_sections["income_statement"] = True
                if any(a in line_lower for a in bs_anchors): found_sections["balance_sheet"] = True
                if any(a in line_lower for a in cf_anchors): found_sections["cash_flow"] = True
                
                # STEP 3 & 4: Numeric Protection & Whitespace
                is_numeric = is_numeric_dense(clean_line)
                
                if is_numeric:
                    # Preserve numeric-dense lines exactly (only trim)
                    all_lines.append(clean_line)
                    protected_line_indices.append(len(all_lines) - 1)
                else:
                    # Normalize whitespace for non-numeric lines
                    normalized = re.sub(r'\s+', ' ', clean_line)
                    all_lines.append(normalized)

    full_text = "\n".join(all_lines)
    
    # Step 6: Coverage Validation
    # Heuristic: Document density check (expected tokens per page)
    word_count = len(full_text.split())
    estimated_tokens = int(word_count * 1.3)
    
    page_count = len(doc)
    # 70% of expected density (assuming average page has 200 words min)
    min_tokens = page_count * 150 * 0.7 
    
    missing_sections = [k for k, v in found_sections.items() if not v]
    
    status = "success"
    message = "Full forensic extraction complete"
    
    if estimated_tokens < min_tokens:
        message = "FORENSIC ANALYSIS DISABLED — INCOMPLETE EXTRACTION (Low Density)"
        status = "error"
    elif missing_sections:
        message = "FINANCIAL STATEMENT SECTION NOT DETECTED"
        status = "error"

    return {
        "text": full_text,
        "tokens": estimated_tokens,
        "pages_processed": page_count,
        "protected_indices": protected_line_indices,
        "financial_sections_detected": found_sections,
        "status": status,
        "message": message
    }
