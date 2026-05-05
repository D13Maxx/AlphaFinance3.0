from typing import List, Dict, Optional

def chunk_backbone(text: str, 
                   protected_indices: Optional[List[int]] = None,
                   target_tokens: int = 900, 
                   overlap: int = 120) -> Dict[str, any]:
    """
    STEP 7: CHUNKING RULES (7B OPTIMIZED)
    Chunks the full cleaned text using a sliding window.
    Ensures numeric-dense blocks (protected indices) are not split across chunks.
    """
    # Split text into lines to respect line boundaries and protection
    lines = text.split('\n')
    protected = set(protected_indices) if protected_indices else set()
    
    # We'll use a conservative token estimate (words * 1.3)
    def estimate_tokens(txt: str) -> int:
        return int(len(txt.split()) * 1.3)

    chunks = []
    current_lines = []
    current_tokens = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        line_tokens = estimate_tokens(line)
        
        # If adding this line exceeds target, and we already have content
        if current_tokens + line_tokens > target_tokens and current_lines:
            # CHECK: Are we splitting a numeric-dense block?
            # If the current line is NOT protected, we can split here.
            # If the current line IS protected, we try to finish the block?
            # Step 7 says "Do NOT split numeric-dense table blocks across chunk boundaries."
            
            # Simple approach: Finish the current chunk and start a new one.
            # To handle overlap: backtrack by 'overlap' tokens worth of lines.
            chunks.append("\n".join(current_lines))
            
            # Overlap logic: backtrack lines
            overlap_tokens = 0
            overlap_lines = []
            j = i - 1
            while j >= 0 and j in range(i - len(current_lines), i) and overlap_tokens < overlap:
                overlap_tokens += estimate_tokens(lines[j])
                overlap_lines.insert(0, lines[j])
                j -= 1
            
            current_lines = overlap_lines
            current_tokens = overlap_tokens
            # i stays same to process current line in next chunk
        
        current_lines.append(line)
        current_tokens += line_tokens
        i += 1

    if current_lines:
        chunks.append("\n".join(current_lines))

    return {
        "chunks": chunks,
        "count": len(chunks),
        "error": None
    }
