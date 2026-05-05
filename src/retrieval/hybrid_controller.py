import re
import json
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from src.retrieval.chunk_builder import Chunk
from src.retrieval.similarity import compute_cosine_similarity

class HybridRetrievalController:
    """
    Forensic Hybrid Retrieval Controller.
    Implements a 5-step deterministic strategy for financial document retrieval.
    """
    
    FINANCIAL_ANCHORS = [
        "revenue", "net income", "income statement", "balance sheet", 
        "cash flow", "assets", "liabilities", "equity", 
        "operating income", "free cash flow"
    ]

    def __init__(self, embedding_store: Any, chunks: List[Chunk], embeddings: np.ndarray, structured_index: Dict[str, Any] = None):
        self.embedding_store = embedding_store
        self.chunks = chunks
        self.embeddings = embeddings
        self.structured_index = structured_index or {}

    def retrieve(self, query: str) -> Dict[str, Any]:
        """
        Main retrieval entry point. Executes 5 steps in priority order.
        """
        # STEP 1: EXACT PHRASE MATCH
        exact_res = self._step1_exact_match(query)
        if exact_res:
            return exact_res

        # STEP 2: FINANCIAL ANCHOR SEARCH
        anchor_res = self._step2_anchor_search(query)
        if anchor_res:
            return anchor_res

        # STEP 3: STRUCTURED INDEX LOOKUP
        # We check specific section requests.
        structured_res = self._step3_structured_lookup(query)
        if structured_res:
            return structured_res

        # STEP 4: VECTOR FALLBACK (Weighted Reranking)
        vector_res = self._step4_vector_fallback(query)
        if vector_res:
            return vector_res

        # STEP 5: NO SPECULATION RULE
        return {
            "status": "not_found",
            "reason": "No supporting evidence found in retrieved document context."
        }

    def _step1_exact_match(self, query: str) -> Optional[Dict[str, Any]]:
        quoted_phrases = re.findall(r'"([^"]*)"', query)
        is_explicit = any(cmd in query.lower() for cmd in ["search for", "quote the phrase", "find the exact header", "locate the line"])
        
        if not quoted_phrases and not is_explicit:
            return None

        # Determine target phrases to search for
        targets = quoted_phrases if quoted_phrases else [query]
        
        for chunk in self.chunks:
            for target in targets:
                if target.lower() in chunk.text.lower():
                    return self._format_response("success", "exact_match", [chunk.text])
        
        return {
            "status": "not_found",
            "reason": "Exact phrase not present in document."
        }

    def _step2_anchor_search(self, query: str) -> Optional[Dict[str, Any]]:
        query_lower = query.lower()
        has_anchor = any(anchor in query_lower for anchor in self.FINANCIAL_ANCHORS)
        
        if not has_anchor:
            return None

        scored_chunks = []
        for chunk in self.chunks:
            score = self._calculate_anchor_score(chunk.text, query_lower)
            if score > 0:
                scored_chunks.append((score, chunk))

        if scored_chunks:
            # Return top scoring chunks
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            top_chunks = [c.text for s, c in scored_chunks[:3]] # Return top 3 for richness
            return self._format_response("success", "financial_anchor", top_chunks)

        return None

    def _step3_structured_lookup(self, query: str) -> Optional[Dict[str, Any]]:
        query_lower = query.lower()
        sections = {
            "income statement": "income_statement",
            "balance sheet": "balance_sheet",
            "cash flow": "cash_flow"
        }
        
        for key, field in sections.items():
            if key in query_lower and field in self.structured_index:
                data = self.structured_index[field]
                return self._format_response("success", "structured_index", [f"STRUCTURED {field.upper()} DATA:\n{data}"])
        return None

    def _step4_vector_fallback(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Weighted reranking of vector results.
        Final Score = 0.4*Sim + 0.3*Anchor + 0.2*Density + 0.1*Overlap
        """
        # 1. Expand and Embed Query
        expanded_query = query # Keep it simple for forensic
        query_vec = self.embedding_store.embed_query(expanded_query)
        
        # 2. Get all semantic scores
        semantic_scores = compute_cosine_similarity(query_vec, self.embeddings)
        
        # 3. Rerank
        reranked = []
        query_terms = set(re.findall(r'\w+', query.lower()))
        
        for i, chunk in enumerate(self.chunks):
            # Semantic Similarity (0-1 typically)
            sim = float(semantic_scores[i])
            
            # Financial Anchor Score (0-1)
            found_anchors = sum(1 for a in self.FINANCIAL_ANCHORS if a in chunk.text.lower())
            anchor_score = min(found_anchors / 3.0, 1.0) 
            
            # Numeric Density Score (0-1)
            digit_count = len(re.findall(r'\d', chunk.text))
            density_score = min(digit_count / 20.0, 1.0)
            
            # Exact Term Overlap (0-1)
            chunk_terms = set(re.findall(r'\w+', chunk.text.lower()))
            overlap_score = len(query_terms & chunk_terms) / len(query_terms) if query_terms else 0
            
            final_score = (
                0.4 * sim + 
                0.3 * anchor_score + 
                0.2 * density_score + 
                0.1 * overlap_score
            )
            reranked.append((final_score, chunk))

        # Sort and return top results
        reranked.sort(key=lambda x: x[0], reverse=True)
        top_results = [r[1].text for r in reranked[:8]] # Return top 8 as requested by top-k (8-12)
        
        return self._format_response("success", "vector_fallback", top_results)

    def _calculate_anchor_score(self, text: str, query_lower: str) -> float:
        score = 0
        text_lower = text.lower()
        
        # Anchor match
        for anchor in self.FINANCIAL_ANCHORS:
            if anchor in text_lower:
                score += 10
        
        # High numeric density
        digit_count = len(re.findall(r'\d', text))
        if digit_count >= 10:
            score += 5
        
        # Year detection
        years = re.findall(r'\b(19|20)\d{2}\b', text)
        if len(years) >= 2:
            score += 5
            
        return score

    def _format_response(self, status: str, method: str, content_list: List[str]) -> Dict[str, Any]:
        return {
            "status": status,
            "retrieval_method": method,
            "chunks_returned": len(content_list),
            "content": "\n\n---\n\n".join(content_list)
        }
