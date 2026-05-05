import numpy as np
from typing import List, Any
from src.retrieval.chunk_builder import Chunk

class EmbeddingStore:
    def __init__(self, embedding_model: Any):
        """
        embedding_model must implement:
        - embed_documents(texts: List[str]) -> List[List[float]] or np.ndarray
        - embed_query(text: str) -> List[float] or np.ndarray
        """
        self.model = embedding_model

    def embed_chunks(self, chunks: List[Chunk]) -> np.ndarray:
        """
        Batch embed chunk texts and return float32 numpy array.
        """
        if not chunks:
            return np.array([], dtype=np.float32)
            
        texts = [c.text for c in chunks]
        
        # Call model
        embeddings = self.model.embed_documents(texts)
        
        # Convert to numpy
        arr = np.array(embeddings, dtype=np.float32)
        
        # Normalize
        # L2 norm
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0] = 1.0
        normalized = arr / norms
        
        return normalized

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed query string and return 1D normalized float32 array.
        """
        vec = self.model.embed_query(query)
        arr = np.array(vec, dtype=np.float32)
        
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
            
        return arr
