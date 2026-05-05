from typing import List, Tuple, Dict
from src.retrieval.chunk_builder import Chunk

def enforce_section_diversity(ranked_chunks: List[Tuple[Chunk, float]], 
                            k: int = 5, 
                            max_per_section: int = 2) -> List[Chunk]:
    """
    Selects top k chunks enforcing diversity on section_path.
    Limits max_per_section chunks from the same section path.
    """
    selected: List[Chunk] = []
    section_counts: Dict[str, int] = {}
    
    for chunk, score in ranked_chunks:
        if len(selected) >= k:
            break
            
        path = chunk.section_path
        current_count = section_counts.get(path, 0)
        
        if current_count < max_per_section:
            selected.append(chunk)
            section_counts[path] = current_count + 1
            
    return selected
