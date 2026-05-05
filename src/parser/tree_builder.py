from typing import List, Optional
from src.parser.models import Document, Section
from src.parser.heading_detection import detect_heading

def build_document_tree(lines: List[str]) -> Document:
    """
    Builds a hierarchical document tree from lines of text.
    Enforces invariants:
    0 <= start_line <= end_line < len(lines)
    depth <= 3
    no None end_line
    """
    root_sections: List[Section] = []
    stack: List[Section] = [] # Stack of open sections
    
    for i, line in enumerate(lines):
        # Determine parent level based on stack
        parent_level = stack[-1].level if stack else 0
        
        is_heading, level = detect_heading(line, parent_level)
        
        if is_heading:
            # Close sections at same or deeper level (level >= new_level)
            # Example: If stack has [L1, L2], and new is L2 -> close L2.
            # If new is L1 -> close L2, then L1.
            while stack and stack[-1].level >= level:
                closed_section = stack.pop()
                # The section ends at the line BEFORE the new heading
                # But it must start at or before end_line.
                # If start_line == i, it means empty section? No, start_line implies inclusive.
                # end_line is inclusive.
                # So end logic: max(closed_section.start_line, i - 1)
                closed_section.end_line = max(closed_section.start_line, i - 1)
            
            # Create new section
            new_section = Section(
                heading=line.strip(),
                level=level,
                start_line=i,
                end_line=i, # Initialize end_line to current line (will be updated if not closed immediately)
                subsections=[]
            )
            
            # Add to hierarchy
            if not stack:
                root_sections.append(new_section)
            else:
                # Add as subsection to current parent (stack top)
                # Parent logic: if new level > parent level?
                # If stack is [L1], new is L2 -> L1.subsections.append(L2)
                # If stack is [L1], new is L3 -> L1.subsections.append(L3)?
                # Or require strict hierarchy? 
                # "depth capped at 3" in detection, but hierarchy construction just follows levels.
                # Just append to whatever is on stack top.
                stack[-1].subsections.append(new_section)
            
            stack.append(new_section)
            
    # Close any remaining open sections at end of document
    last_line_idx = max(0, len(lines) - 1)
    
    while stack:
        closed_section = stack.pop()
        closed_section.end_line = last_line_idx

    # Document-level fallback if no headings detected
    if not root_sections:
        # Create single covering section
        # Enforce invariant: 0 <= start <= end < len
        # If lines empty?
        if not lines:
            return Document(sections=[], lines=[])
            
        single_section = Section(
            heading="Document",
            level=1,
            start_line=0,
            end_line=last_line_idx,
            subsections=[]
        )
        root_sections.append(single_section)

    return Document(sections=root_sections, lines=lines)

if __name__ == "__main__":
    # Simple demo parse
    sample_text = [
        "1. Introduction",
        "This is the intro.",
        "1.1 Background",
        "Some background info.",
        "2. Conclusion",
        "End of doc."
    ]
    doc = build_document_tree(sample_text)
    print("Parsed Document Structure:")
    print(doc.to_dict())
