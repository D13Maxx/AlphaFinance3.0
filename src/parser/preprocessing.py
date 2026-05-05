from typing import List

def preprocess_text(text: str) -> List[str]:
    """
    Normalize line endings, strip trailing whitespace, and split into lines.
    """
    # Normalize line endings
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into lines
    lines = normalized.split('\n')
    
    # Strip trailing whitespace from each line
    processed_lines = [line.rstrip() for line in lines]
    
    return processed_lines
