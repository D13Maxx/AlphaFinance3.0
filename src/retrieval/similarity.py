import numpy as np

def compute_cosine_similarity(query_vector: np.ndarray, chunk_matrix: np.ndarray) -> np.ndarray:
    """
    Computes cosine similarity between 1D query vector and 2D chunk matrix.
    Assumes all vectors are already L2 normalized.
    Returns 1D array of similarity scores.
    """
    if chunk_matrix.size == 0:
        return np.array([], dtype=np.float32)

    # Dot product for normalized vectors = cosine similarity
    # (N, D) dot (D,) -> (N,)
    scores = np.dot(chunk_matrix, query_vector)
    
    return scores
