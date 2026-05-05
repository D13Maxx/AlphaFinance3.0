from dataclasses import dataclass, field
from typing import List, Optional
from src.parser.models import Document, Section

@dataclass
class Chunk:
    chunk_id: int
    text: str
    section_heading: str
    section_level: int
    section_path: str
    semantic_tag: str
    start_line: int
    end_line: int

SEMANTIC_TAG_RULES = {
    # Financial Statements (Numeric Mode)
    "financial_statements": ["financial statements", "financials"],
    "balance_sheet": ["balance sheet", "consolidated balance sheets"],
    "income_statement": ["income statement", "statement of operations", "profit and loss"],
    "cash_flow": ["cash flow", "statement of cash flows"],
    "assets": ["assets"],
    "liabilities": ["liabilities"],
    
    # Interpretive Mode
    "mdna": ["management's discussion", "md&a"],
    "risk_factors": ["risk factors"],
    "executive_summary": ["executive summary"],
    "market_opportunity": ["market opportunity", "market analysis"],
    "projections": ["projections", "forecasts"],
    "general": [] # Fallback
}

def _derive_tag(heading: str) -> str:
    heading_lower = heading.lower()
    
    # Priority check based on specific keywords
    # Check strict matches or containment
    
    for tag, keywords in SEMANTIC_TAG_RULES.items():
        if tag == "general": continue
        for kw in keywords:
            if kw in heading_lower:
                return tag
                
    return "general"

def build_chunks(document: Document,
                 tokenizer, 
                 target_tokens: int = 500,
                 overlap_tokens: int = 75) -> List[Chunk]:
    """
    Splits document sections into overlapping chunks.
    """
    chunks = []
    chunk_counter = 0

    def traverse(section: Section, parent_path: str = ""):
        nonlocal chunk_counter
        
        # Build current path
        current_path = f"{parent_path} > {section.heading}" if parent_path else section.heading
        
        # Get text for this section (excluding subsections? No, usually inclusive or exclusive?
        # The prompt says: "Chunk only within section boundaries."
        # And "Decode token slices back to text."
        # If I include subsections, I might double count if I also traverse subsections?
        # Usually RAG chunks leaf nodes or specific levels.
        # But Sections in `parser.models` cover a range of lines.
        # If I chunk formatting: section text is lines[start:end+1].
        # But this range includes subsections lines.
        # Should I chunk the *entire* range, or just the text *exclusive* of subsections?
        # Prompt: "Chunk only within section boundaries."
        # It doesn't explicitly say "exclusive".
        # However, typically you want the full context of a section. The issue is redundancy.
        # If Section 1 has lines 0-100, and Subsection 1.1 has 10-50.
        # If I chunk Section 1, I get 0-100.
        # If I chunk Subsection 1.1, I get 10-50.
        # This is duplication.
        # "Do NOT store duplicated content" was in parser req.
        # But `parser.models` implemented `lines` list separate from sections.
        # The `Section` object has `start_line` and `end_line`.
        # If the parser implementation followed standard hierarchy, the parent covers children.
        # For RAG, we usually want specificity.
        # If I only chunk leaf nodes, I miss top-level intro text that isn't in a subsection.
        # If I chunk all nodes, I duplicate.
        # Strategy:
        # A simple approach for this assignment without complex text subtraction:
        # 1. Chunk every section independently.
        # OR
        # 2. Only chunk leaf sections? No, might miss text.
        # 3. Use the lines directly?
        # Given "recursive traversal" in other parts, maybe just chunking every section is expected, despite overlap.
        # Or, maybe the prompt implies "Section" lines are inclusive.
        # Let's look at `Section` definition in `parser/models.py`:
        # "subsections: List['Section']".
        # "start_line", "end_line".
        # If I assume the parser assigns lines correctly.
        # I will chunk the *range* of lines for each section.
        # Yes, this introduces duplication for parents vs children, but ensures context.
        # Given the "Structural" focus, maybe redundancy is acceptable or intended to capture "level" context.
        # I will proceed with chunking the full line range of each section.
        
        # Get lines for this section
        # Ensure indices are valid
        start = max(0, section.start_line)
        end = min(len(document.lines) - 1, section.end_line)
        
        if start <= end:
            section_lines = document.lines[start : end + 1]
            section_text = "\n".join(section_lines)
            
            if section_text.strip():
                # Encode
                # Assuming tokenizer has .encode(text) -> List[int] or sim.
                # And .decode(tokens) -> str
                tokens = tokenizer.encode(section_text)
                
                # Sliding window
                num_tokens = len(tokens)
                start_idx = 0
                
                while start_idx < num_tokens:
                    end_idx = min(start_idx + target_tokens, num_tokens)
                    chunk_tokens = tokens[start_idx : end_idx]
                    
                    # Decode
                    chunk_text = tokenizer.decode(chunk_tokens)
                    
                    # Metadata
                    tag = _derive_tag(section.heading)
                    
                    new_chunk = Chunk(
                        chunk_id=chunk_counter,
                        text=chunk_text,
                        section_heading=section.heading,
                        section_level=section.level,
                        section_path=current_path,
                        semantic_tag=tag,
                        start_line=start, # Rough approximation, hard to map back exactly line-by-line without map
                        end_line=end
                    )
                    chunks.append(new_chunk)
                    chunk_counter += 1
                    
                    # Stop if we reached end
                    if end_idx == num_tokens:
                        break
                        
                    # Slide
                    # If target < num_tokens, stride = target - overlap
                    stride = target_tokens - overlap_tokens
                    if stride < 1: stride = 1 # Prevent infinite loop
                    
                    start_idx += stride
        
        # Recurse
        for sub in section.subsections:
            traverse(sub, current_path)

    # Start traversal
    for section in document.sections:
        traverse(section, "")
        
    return chunks
