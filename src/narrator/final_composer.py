import re
import json
from typing import Dict, Any, Optional

class FinalAnswerComposer:
    """
    Final presentation layer for financial responses.
    Transforms internal structured results into clean, professional answers.
    Invisible to the user: internal JSON, metadata, and status flags.
    """

    def __init__(self, llm: Any):
        self.llm = llm

    def compose(self, query: str, internal_data: Any) -> str:
        """
        Main entry point for answer composition.
        """
        if isinstance(internal_data, str):
            # If it's already a string (maybe from a direct LLM call), clean it.
            return self._clean_text(internal_data)

        # Handling dictionary data (Structured Results)
        if isinstance(internal_data, dict):
            status = internal_data.get("status")
            if status == "not_found":
                return f"No supporting evidence was found in the document to answer the question: '{query}'."
            
            if "computed_metrics" in internal_data:
                return self._compose_computational_answer(query, internal_data)
            
            if "retrieval_method" in internal_data:
                return self._compose_retrieval_answer(query, internal_data)

        # Fallback for unexpected formats
        return self._clean_text(str(internal_data))

    def _clean_text(self, text: str) -> str:
        """
        Removes spacing artifacts, internal metadata, and duplicate fragments.
        """
        if not text:
            return ""

        # Remove common internal artifacts
        text = re.sub(r'\{.*\}', '', text) # Remove any JSON-like structures
        text = re.sub(r'\[Source:.*?\]', '', text) # Remove source tags
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common numeric duplication artifacts (e.g. "2024 2024")
        text = re.sub(r'(\b\d{4}\b)\s+\1', r'\1', text)
        
        return text

    def _compose_retrieval_answer(self, query: str, data: Dict[str, Any]) -> str:
        """
        Transforms raw retrieval content into a professional presentation.
        """
        raw_content = data.get("content", "")
        
        prompt = f"""You are a professional financial editor. 
Transform the following raw retrieval result into a clean, professional answer for the user's question.

STRICT RULES:
- Extract ONLY relevant information.
- Use a professional, reporting tone.
- HIDE all system metadata (retrieval methods, chunk counts, JSON).
- If the user asked for a quote, provide it verbatim.
- If the text feels fragmented, join it smoothly.

User Question: {query}
Raw Retrieval Content:
{raw_content}

Clean Professional Answer:"""

        return self.llm.generate(prompt)

    def _compose_computational_answer(self, query: str, data: Dict[str, Any]) -> str:
        """
        Presents computed metrics, handles partial success, and honors failed_metrics.
        """
        metrics = data.get("computed_metrics", {})
        failed_metrics = data.get("failed_metrics", {})
        piotroski = data.get("piotroski_score", "N/A")
        details = data.get("piotroski_details", {})
        rag_evidence = data.get("rag_evidence")
        status = data.get("status", "success")
        
        prompt = ""
        metadata_context = ""
        if status == "partial_success":
            metadata_context = f"NOTE: Some metrics could not be computed due to missing data: {json.dumps(failed_metrics)}"

        if rag_evidence:
            # Hybrid Mode
            prompt = f"""You are a senior financial analyst.
Present a hybrid analysis combining computed metrics with qualitative evidence.

STRICT RULES:
- Use bullet points for specific metrics.
- Interleave qualitative evidence (RAG) to explain the numbers.
- {metadata_context} (Explicitly mention if specific metrics are unavailable).
- HIDE all internal JSON status codes.
- Do NOT perform any arithmetic.

User Question: {query}
Computed Metrics: {json.dumps(metrics, indent=2)}
Piotroski Score: {piotroski}
Qualitative Evidence (RAG): {json.dumps(rag_evidence, indent=2)}
Failed Metrics (Do NOT guess these): {json.dumps(failed_metrics, indent=2)}

Hybrid Financial Analysis Presentation:"""
        else:
            # Pure Computation Mode
            prompt = f"""You are a senior financial analyst.
Present the following computed metrics in a professional, human-readable format.

STRICT RULES:
- Use bullet points for specific metrics.
- Provide a summary of what these numbers imply.
- {metadata_context} (Explain why certain metrics might be missing).
- HIDE all internal JSON status codes.
- Do NOT perform any arithmetic.

User Question: {query}
Computed Metrics: {json.dumps(metrics, indent=2)}
Piotroski Score: {piotroski}
Piotroski Details: {json.dumps(details, indent=2)}
Failed Metrics (Do NOT guess these): {json.dumps(failed_metrics, indent=2)}

Financial Analysis Presentation:"""

        return self.llm.generate(prompt)
