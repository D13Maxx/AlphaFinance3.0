import numpy as np
from typing import List, Dict, Any, Optional

from src.parser.models import Document
from src.retrieval.chunk_builder import build_chunks, Chunk
from src.retrieval.embedding_store import EmbeddingStore
from src.retrieval.similarity import compute_cosine_similarity
from src.retrieval.ranker import apply_hybrid_ranking
from src.retrieval.diversity import enforce_section_diversity
from src.retrieval.query_expansion import expand_query
from src.retrieval.lexical_scorer import lexical_score
from src.retrieval.ranker import PRIORITY_WEIGHTS

class RetrievalEngine:
    def __init__(self,
                 embedding_store: EmbeddingStore,
                 semantic_weight: float = 0.65,
                 lexical_weight: float = 0.2,
                 priority_weight: float = 0.15):
        self.embedding_store = embedding_store
        self.semantic_weight = semantic_weight
        self.lexical_weight = lexical_weight
        self.priority_weight = priority_weight
        
    def index_document(self, 
                     document_id: str, 
                     document: Document, 
                     tokenizer: Any) -> Dict[str, Any]:
        """
        Orchestrates chunking and embedding.
        document_id is passed for context but not persisted here (stateless).
        """
        # Build chunks
        chunks = build_chunks(document, tokenizer)
        
        # Embed
        embeddings = self.embedding_store.embed_chunks(chunks)
        
        return {
            "chunks": chunks,
            "embeddings": embeddings
        }
        
    def retrieve(self, 
               query: str, 
               chunks: List[Chunk], 
               embeddings: np.ndarray, 
               mode: str = "numeric", 
               k: int = 5,
               diversity_cap: int = 2) -> List[Chunk]:
        """
        Retrieves top k relevant chunks for the query.
        """
        # 1. Expand Query
        expanded_query = expand_query(query)
        
        # 2. Embed Query
        query_vec = self.embedding_store.embed_query(expanded_query)
        
        # 3. Semantic Similarity
        semantic_scores = compute_cosine_similarity(query_vec, embeddings)
        
        # 4. Lexical Scorer & Hybrid Ranking
        ranked_chunks = []
        
        # Get priority weight map
        weight_map = PRIORITY_WEIGHTS.get(mode, PRIORITY_WEIGHTS.get("numeric", {}))
        if mode not in PRIORITY_WEIGHTS:
             weight_map = {"general": 0.5}

        for i, chunk in enumerate(chunks):
            # Semantic
            s_score = float(semantic_scores[i])
            
            # Lexical
            l_score = lexical_score(query, chunk.text)
            
            # Priority
            tag = chunk.semantic_tag
            p_score = weight_map.get(tag, weight_map.get("general", 0.5))
            
            # Combined
            combined_score = (
                self.semantic_weight * s_score +
                self.lexical_weight * l_score +
                self.priority_weight * p_score
            )
            
            ranked_chunks.append((chunk, combined_score))
            
        # 5. Rank
        ranked_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # 6. Diversity
        # If diversity_cap is negative or large, we effectively disable it?
        # enforce_section_diversity takes max_per_section
        final_chunks = enforce_section_diversity(ranked_chunks, k=k, max_per_section=diversity_cap)
        
        return final_chunks

if __name__ == "__main__":
    # Minimal usage example
    print("Initializing Retrieval Mock...")
    
    # Mock Tokenizer
    class MockTokenizer:
        def encode(self, text):
            # Simple space split for mock tokens
            return text.split()
        def decode(self, tokens):
            return " ".join(tokens)
            
    # Mock Embedding Model
    class MockModel:
        def embed_documents(self, texts):
            # Deterministic fake embeddings based on length
            return [[0.1 * len(t) % 1.0, 0.5, 0.2] for t in texts]
        def embed_query(self, text):
            return [0.5, 0.5, 0.5]

    # Mock Data
    from src.parser.models import Document, Section
    s1 = Section(heading="1. Financial Statements", level=1, start_line=0, end_line=0, subsections=[])
    doc = Document(sections=[s1], lines=["Financial statements data here."])
    
    # Setup
    model = MockModel()
    store = EmbeddingStore(model)
    engine = RetrievalEngine(store)
    tokenizer = MockTokenizer()
    
    # Index
    index_data = engine.index_document("doc1", doc, tokenizer)
    chunks = index_data["chunks"]
    emb = index_data["embeddings"]
    
    print(f"Indexed {len(chunks)} chunks.")
    
    # Retrieve
    results = engine.retrieve("query", chunks, emb, mode="numeric", k=1)
    
    if results:
        print(f"Retrieved chunk: {results[0].text[:20]}...")
        print(f"Tag: {results[0].semantic_tag}")
    else:
        print("No results.")
