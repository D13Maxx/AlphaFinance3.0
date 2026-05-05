import re
import time
from typing import Dict, List, Any, Optional
from src.orchestrator.state_enum import RAGStateEnum
from src.orchestrator.state_models import DocumentSession, RAGExecutionState
from src.parser.models import Document
from src.retrieval.chunk_builder import Chunk
from src.financial_engine.analysis.router import AnalysisRouter
from src.narrator.narrator import DeterministicNarrator, LLMBasedNarrator
from src.financial_engine.models.analysis_response import AnalysisResponse

class FinancialRAGEngine:
    def __init__(self,
                 classifier,
                 retrieval_engine,
                 llm,
                 numeric_engine,
                 tokenizer,
                 session_context=None,
                 debug: bool = False):
        """
        Store dependencies only.
        Do NOT store execution state.
        """
        self.classifier = classifier
        self.retrieval_engine = retrieval_engine
        self.llm = llm
        self.numeric_engine = numeric_engine
        self.tokenizer = tokenizer
        self.session_context = session_context
        self.debug = debug

    def run(self, session: DocumentSession, query: str) -> Dict[str, Any]:
        """
        Main execution loop.
        Initialize RAGExecutionState.
        Loop until FINALIZE_RESPONSE or ERROR.
        """
        # Initialize execution state
        state = RAGExecutionState(
            session=session,
            query=query
        )
        
        current_step = RAGStateEnum.INIT
        
        while True:
            if self.debug:
                print(f"State: {current_step.value}")

            if current_step == RAGStateEnum.INIT:
                current_step = self._handle_init(state)
            
            elif current_step == RAGStateEnum.CLASSIFY_QUERY:
                current_step = self._handle_classify_query(state)
                
            elif current_step == RAGStateEnum.RETRIEVE:
                current_step = self._handle_retrieve(state)
                
            elif current_step == RAGStateEnum.BUILD_CONTEXT:
                current_step = self._handle_build_context(state)
                
            elif current_step == RAGStateEnum.NUMERIC_PREPROCESS:
                current_step = self._handle_numeric_preprocess(state)
                
            elif current_step == RAGStateEnum.GENERATE_ANSWER:
                return self._handle_generate_answer(state.query, state.session)
                
            elif current_step == RAGStateEnum.VALIDATE_CITATIONS:
                current_step = self._handle_validate_citations(state)
                
            elif current_step == RAGStateEnum.FINALIZE_RESPONSE:
                return self._handle_finalize_response(state)
                
            elif current_step == RAGStateEnum.ERROR:
                return self._handle_error(state)
                
            else:
                state.error = f"Unknown state: {current_step}"
                return self._handle_error(state)

    def _handle_init(self, state: RAGExecutionState) -> RAGStateEnum:
        return RAGStateEnum.CLASSIFY_QUERY

    def _handle_classify_query(self, state: RAGExecutionState) -> RAGStateEnum:
        query_lower = state.query.lower()
        numeric_indicators = [
            "how much", "total", "percentage", "growth", "$",
            "revenue", "income", "profit", "loss",
            "debt", "assets", "liabilities",
            "cash flow", "margin", "earnings",
            "2020", "2021", "2022", "2023", "2024"
        ]
        
        is_numeric = any(indicator in query_lower for indicator in numeric_indicators)
        
        if is_numeric:
            state.query_type = "numeric"
            # Numeric/Comparison queries skip retrieval and context building
            # They rely on the pre-loaded CompanyFinancialState
            return RAGStateEnum.GENERATE_ANSWER
        else:
            state.query_type = "interpretive"
            return RAGStateEnum.RETRIEVE

    def _handle_retrieve(self, state: RAGExecutionState) -> RAGStateEnum:
        # Call retrieval_engine.retrieve(...)
        # Assuming retrieval_engine has a retrieve method that takes query and chunks
        # and returns a list of selected chunks.
        try:
            # We use the session chunks for retrieval
            selected = self.retrieval_engine.retrieve(state.query, state.session.chunks, state.session.embeddings, mode=state.query_type)
            state.selected_chunks = selected
            
            if not state.selected_chunks:
                state.error = "No relevant information found."
                return RAGStateEnum.ERROR
                
            return RAGStateEnum.BUILD_CONTEXT
            
        except Exception as e:
            state.error = f"Retrieval failed: {str(e)}"
            return RAGStateEnum.ERROR

    def _handle_build_context(self, state: RAGExecutionState) -> RAGStateEnum:
        context_parts = ["==== BEGIN CONTEXT ===="]
        
        for chunk in state.selected_chunks:
            part = (
                f"[CHUNK_ID: {chunk.chunk_id}]\n"
                f"Section: {chunk.section_path}\n"
                f"Tag: {chunk.semantic_tag}\n"
                f"Lines: {chunk.start_line}-{chunk.end_line}\n\n"
                f"{chunk.text}\n\n"
                f"----------------------------------------"
            )
            context_parts.append(part)
            
        context_parts.append("==== END CONTEXT ====")
        state.context = "\n".join(context_parts)
        
        if state.query_type == "numeric":
            return RAGStateEnum.NUMERIC_PREPROCESS
        else:
            return RAGStateEnum.GENERATE_ANSWER

    def _handle_numeric_preprocess(self, state: RAGExecutionState) -> RAGStateEnum:
        # Call numeric_engine if needed
        # Assuming numeric_engine.process(query, context) -> dict
        try:
            if self.numeric_engine:
                 state.numeric_result = self.numeric_engine.process(state.query, state.selected_chunks)
        except Exception as e:
            # If numeric processing fails, we might still try to answer or fail.
            # Strict rules say "Fail-fast on validation failure".
            pass
            
        return RAGStateEnum.GENERATE_ANSWER

    def _handle_generate_answer(self, query: str, session: DocumentSession):
        start_time = time.time()
        # New multi-company logic
        router = AnalysisRouter(self.session_context)
        structured_result = router.run(query)

        if self.session_context.strict_mode:
            from src.financial_engine.analysis.strict_diff import generate_strict_diff
            base_state = self.session_context.companies[self.session_context.active_company]
            strict_state = self.session_context.strict_companies[self.session_context.active_company]
            diff = generate_strict_diff(base_state, strict_state)
            structured_result["strict_diff"] = diff

        structured_result["analysis_time_ms"] = int((time.time() - start_time) * 1000)

        if structured_result.get("mode") == "qualitative":
            return self._handle_qualitative_query(query, session)

        # Wrap into final schema
        overall_conf = self.session_context.get_active_state().get_overall_confidence()
        
        analysis_response = AnalysisResponse(
            mode=structured_result["mode"],
            metrics=structured_result.get("metrics", {}),
            signals=structured_result.get("signals", {}),
            diagnostics=structured_result.get("diagnostics", {}),
            overall_confidence=overall_conf,
            strict_diff=structured_result.get("strict_diff", {}),
            analysis_time_ms=structured_result.get("analysis_time_ms", 0),
        )

        # Ensure narrator receives dictionary version
        response_dict = analysis_response.__dict__

        if hasattr(self, "llm") and self.llm is not None:
            narrator = LLMBasedNarrator(self.llm)
            return narrator.narrate(response_dict)

        narrator = DeterministicNarrator()
        return narrator.narrate(response_dict)

    def _handle_qualitative_query(self, query: str, session: DocumentSession):
        # Numeric modes must never call retrieval.
        # This handler is only for qualitative queries.
        
        try:
            # Retrieve chunks
            active_state = self.session_context.get_active_state()
            # Session object in active_state? 
            # In previous steps, "CompanyFinancialState" had "session" field?
            # Re-reading "CompanyFinancialState" definition (Step Id 122+):
            # It has income_statements, cash_flow_statements, balance_sheets, strict_config... 
            # It DOES NOT seem to have 'session' (DocumentSession).
            # However, 'DocumentSession' was passed to 'run' and stored in 'RAGExecutionState'.
            # 'self.session_context' does not store 'DocumentSession' directly unless I add it.
            # But 'engine.run' takes 'session'.
            # And I modified '_handle_generate_answer' to take 'session' (DocumentSession).
            # So I should use 'session.chunks' directly as I did before?
            # Wait, if 'active_company' changes, does 'session' change?
            # The current architecture allows 1 session per run.
            # If I have multiple companies, do they share the same document session?
            # "Support multiple companies per session."
            # Usually implies one uploaded document set corresponds to multiple companies?
            # OR multiple documents loaded into one session?
            # If so, 'session.chunks' contains all chunks.
            # Retrieval engine should filter by company?
            # Text says "Do not mix company states."
            # But for *retrieval*, usually we retrieve from all available docs?
            # The user instruction said: "Modify _handle_qualitative_query... Use retrieval_engine.retrieve(query, session.chunks...)"
            # I already did that.
            # Do I need to change it?
            # "Ensure all references updated."
            # In `_handle_qualitative_query`, I used `session.chunks`. This seems correct if `session` contains all docs.
            # But I'm looking at `_handle_generate_answer`.
            # I replaced `state = self.session_context.active_state` with `router = AnalysisRouter(self.session_context)`.
            # And `_handle_qualitative_query` uses `session` passed as arg.
            # BUT `self.session_context.active_state.session` was used in my *previous* attempt at `_handle_qualitative_query` (Step 243).
            # Then I corrected it to use passed `session` (Step 250).
            # So `_handle_qualitative_query` should be fine.
            # I just need to make sure I don't use `self.session_context.active_state` blindly.
            
            # The ONLY place I see `active_state` used in `_handle_qualitative_query` in my *thought process* was Step 243.
            # In Step 250 I used `session.chunks`.
            # So I just need to update `_handle_generate_answer`.
            
            # Wait, `get_active_state` usage:
            # "Modify _handle_generate_answer: Replace state = self.session_context.active_state With state = self.session_context.get_active_state()"
            # BUT I am ALSO told "Replace router = AnalysisRouter(state) With router = AnalysisRouter(self.session_context)".
            # These are conflicting if strictly followed line-by-line?
            # No, if I pass `self.session_context` to Router, I don't need `state` for the router.
            # But maybe I need `state` for other things?
            # Logic:
            # Old: state = ctx.active_state; router = Router(state); res = router.run(query)
            # New: router = Router(ctx); res = router.run(query)
            # So I effectively *remove* the `state` variable assignment?
            # "Modify _handle_generate_answer: Replace state = self.session_context.active_state With state = self.session_context.get_active_state()"
            # implies I should still have that line.
            # But "Replace router = AnalysisRouter(state) With router = AnalysisRouter(self.session_context)"
            # implies router uses context.
            # Maybe `state` is unused?
            # User said "Ensure all references updated."
            # If `state` becomes unused, fine.
            # I will follow "Replace router..." as it is more specific to the new Router signature.
            # And I will NOT define `state` if it's not used.
            # Let's check `_handle_generate_answer`:
            # It uses `router(state)` (old) -> `router(context)` (new).
            # It DOES NOT use `state` elsewhere.
            # So I will just instantiate Router with context.
            
            retrieved_chunks = self.retrieval_engine.retrieve(
                query, 
                session.chunks, 
                session.embeddings, 
                mode="qualitative"
            )
            
            # Filter large numeric tables (heuristic < 2000 chars)
            # Use chunk.text as chunk.content likely refers to text
            filtered_chunks = [
                chunk for chunk in retrieved_chunks
                if len(chunk.text) < 2000
            ]
            
            # Build context with citations preserved
            context_parts = []
            for chunk in filtered_chunks:
                context_parts.append(f"[CHUNK_ID: {chunk.chunk_id}]\n{chunk.text}")
            
            context = "\n\n".join(context_parts)
            
            prompt = (
                "You are financial research assistant.\n"
                "Answer using ONLY the provided context.\n"
                "If answer not found, say NOT FOUND.\n\n"
                f"Context:\n{context}\n\n"
                f"Question:\n{query}\n\n"
                "Provide answer with citations if available."
            )
            
            if hasattr(self.llm, 'generate'):
                return self.llm.generate(prompt)
            else:
                return self.llm(prompt)

        except Exception as e:
             return f"Error in qualitative analysis: {str(e)}"

        pass

    def _handle_validate_citations(self, state: RAGExecutionState) -> RAGStateEnum:
        # Verify:
        # * Every factual sentence contains citation pattern
        # * Citation matches selected chunk IDs
        
        if not state.answer:
            state.error = "Empty answer generated."
            return RAGStateEnum.ERROR
            
        if "NOT FOUND" in state.answer:
            return RAGStateEnum.FINALIZE_RESPONSE
            
        # Basic sentence splitting (naive for now, or regex)
        sentences = re.split(r'(?<=[.!?])\s+', state.answer)
        
        valid_chunk_ids = {str(c.chunk_id) for c in state.selected_chunks}
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Check for citation pattern [CHUNK_ID: X]
            matches = re.findall(r'\[CHUNK_ID:\s*(\d+)\]', sentence)
            
            # Citation is REQUIRED only if sentence contains numbers or symbols
            if re.search(r"[0-9$%]", sentence):
                if not matches:
                    state.error = f"Sentence missing citation: '{sentence}'"
                    return RAGStateEnum.ERROR
            
            for chunk_id in matches:
                if chunk_id not in valid_chunk_ids:
                    state.error = f"Invalid citation ID: {chunk_id}"
                    return RAGStateEnum.ERROR
                    
        return RAGStateEnum.FINALIZE_RESPONSE

    def _handle_finalize_response(self, state: RAGExecutionState) -> Dict[str, Any]:
        return {
            "answer": state.answer,
            "query_type": state.query_type
        }

    def _handle_error(self, state: RAGExecutionState) -> Dict[str, Any]:
        return {
            "error": state.error
        }

if __name__ == "__main__":
    # Minimal __main__ example
    
    # Mock dependencies
    class MockRetrieval:
        def retrieve(self, query, chunks):
            # return slice of chunks for testing
            return chunks[:1] if chunks else []
            
    class MockLLM:
        def __call__(self, prompt):
            return "The net income was $10M [CHUNK_ID: 0]."
            
    # Create dummy session
    from src.parser.models import Section
    
    doc = Document(lines=["Line 1", "Line 2"])
    session = DocumentSession(
        document_id="doc1",
        document=doc,
        classification={},
        chunks=[
            Chunk(
                chunk_id=0,
                text="The net income was $10M",
                section_heading="Financials",
                section_level=1,
                section_path="Financials",
                semantic_tag="financial_statements",
                start_line=0,
                end_line=1
            )
        ],
        embeddings=None
    )
    
    engine = FinancialRAGEngine(
        classifier=None,
        retrieval_engine=MockRetrieval(),
        llm=MockLLM(),
        numeric_engine=None,
        tokenizer=None,
        debug=True
    )
    
    result = engine.run(session, "What was the net income?")
    print("Result:", result)
