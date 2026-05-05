import streamlit as st
import time
import os
import fitz
import json
from decimal import Decimal
from typing import List, Dict

# Backend Imports
from src.financial_engine.analysis.router import AnalysisRouter
from src.financial_engine.session_context import SessionContext
from src.narrator.narrator import LLMBasedNarrator, DeterministicNarrator
from src.parser.parser import parse_document
from src.classifier.classifier import classify_document
from src.narrator.final_composer import FinalAnswerComposer
from src.financial_engine.company_state import CompanyFinancialState, build_financial_state
from src.financial_engine.models.strict_config import StrictConfig
from src.financial_engine.computation_controller import DeterministicComputationController
from src.financial_engine.models.raw_models import RawStatement
from src.financial_engine.analysis.charting import generate_revenue_chart

# RAG Infrastructure Imports
from src.retrieval.retrieval_engine import RetrievalEngine
from src.retrieval.embedding_store import EmbeddingStore
from src.retrieval.chunk_builder import build_chunks, Chunk
from src.llm.ollama_llm import OllamaLLM

# Orchestrator & Routing Imports
from src.orchestrator.query_router import QueryRoutingController, IntentType

# Forensic Ingestion Imports
from src.ingestion.backbone import extract_backbone
from src.ingestion.forensic_chunker import chunk_backbone
from src.ingestion.forensic_analyzer import validate_coverage
from src.retrieval.hybrid_controller import HybridRetrievalController

class MockTokenizer:
    def encode(self, text: str) -> List[int]:
        return [ord(c) for c in text[:50]]
    def decode(self, tokens: List[int]) -> str:
        return "".join([chr(t) for t in tokens])

class MockEmbeddingModel:
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * 768 for _ in texts]
    def embed_query(self, text: str) -> List[float]:
        return [0.1] * 768

st.set_page_config(layout="wide", page_title="Financial Intelligence Engine")

if "warning_shown" not in st.session_state:
    st.warning(
        "⚠️ This Financial RAG system supports PDF documents ONLY.\n\n"
        "Please upload 10K, 10Q, Investment Memo, or Personal Financial Statement PDFs.\n\n"
        "Uploading other file types will result in rejection."
    )
    st.session_state["warning_shown"] = True

st.title("Deterministic Financial Intelligence Engine")

if "session_context" not in st.session_state:
    st.session_state["session_context"] = None

if "tokenizer" not in st.session_state:
    st.session_state["tokenizer"] = MockTokenizer()

if "retrieval_engine" not in st.session_state:
    embed_model = MockEmbeddingModel()
    store = EmbeddingStore(embed_model)
    st.session_state["retrieval_engine"] = RetrievalEngine(store)

if "llm" not in st.session_state or st.session_state["llm"] is None:
    st.session_state["llm"] = OllamaLLM(model_name="qwen2.5:7b-instruct")

if "document_chunks" not in st.session_state:
    st.session_state["document_chunks"] = []

if "document_embeddings" not in st.session_state:
    st.session_state["document_embeddings"] = None

if "coverage_index" not in st.session_state:
    st.session_state["coverage_index"] = []

if "structured_index" not in st.session_state:
    st.session_state["structured_index"] = {}

if "forensic_status" not in st.session_state:
    st.session_state["forensic_status"] = "PENDING"

if "query_controller" not in st.session_state:
    st.session_state["query_controller"] = QueryRoutingController()

st.sidebar.header("Session Setup")
strict_mode = st.sidebar.toggle("Strict Mode")

if strict_mode:
    st.warning("Strict Mode Enabled")
else:
    st.success("Normal Mode")

def initialize_session(uploaded_files):
    """
    Ingestion + Build Base/Strict States.
    Orchestrates parser, classifier, and financial engine.
    Uses mock raw data as extraction pipeline is not explicitly exposed.
    """
    companies = {}
    strict_companies = {}
    
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext != ".pdf":
                st.error("Only PDF files are supported. Please upload a valid financial PDF.")
                st.stop()
                
        try:
            # forensic STEP 1: Backbone Extraction (Coordinate-Aware + Numeric Protection)
            uploaded_file.seek(0)
            backbone_res = extract_backbone(stream=uploaded_file.read())
            
            # DEBUG: Print keys to console
            print(f"DEBUG: backbone_res keys: {list(backbone_res.keys())}")
            
            # forensic STEP 7: Integrity-Preserving Chunking
            chunks_res = chunk_backbone(
                backbone_res["text"], 
                protected_indices=backbone_res.get("protected_indices", []),
                target_tokens=900,
                overlap=120
            )
            
            # ASSEMBLE FINAL FORENSIC JSON REPORT
            ingestion_report = {
                "status": backbone_res.get("status", "error"),
                "message": backbone_res.get("message", "Internal ingestion mapping error"),
                "pages_processed": backbone_res.get("pages_processed", 0),
                "financial_sections_detected": backbone_res.get("financial_sections_detected", {}),
                "chunk_count": chunks_res.get("count", 0)
            }
            
            # Emit JSON always
            report_json = json.dumps(ingestion_report, indent=2)
            st.code(report_json, language="json")
            print(f"INGESTION_REPORT for {uploaded_file.name}:\n{report_json}")

            if ingestion_report["status"] == "error":
                st.error(f"Ingestion failed for {uploaded_file.name}: {ingestion_report['message']}")
                st.session_state["forensic_status"] = "INCOMPLETE"
                continue
            
            st.session_state["forensic_status"] = "VERIFIED"
            text = backbone_res["text"]
            doc = parse_document(text) # For legacy compatibility
            
            # 2. Classify
            classification = classify_document(doc)
            company_name = uploaded_file.name.split(".")[0].upper()
            
            # 3. Build Mock Raw Statements (Integration Placeholder)
            mock_raw_income = RawStatement(statement_type="income", tables=[])
            mock_raw_cash = RawStatement(statement_type="cash_flow", tables=[])
            mock_raw_balance = RawStatement(statement_type="balance_sheet", tables=[])
            
            # 4. Build Financial States
            from src.financial_engine.normalization.income_normalizer import normalize_income
            from src.financial_engine.normalization.cashflow_normalizer import normalize_cashflow
            from src.financial_engine.normalization.balance_normalizer import normalize_balance

            def create_state(config):
                return CompanyFinancialState(
                    income_statements=normalize_income(mock_raw_income, config),
                    cash_flow_statements=normalize_cashflow(mock_raw_cash, config),
                    balance_sheets=normalize_balance(mock_raw_balance, config),
                    strict_config=config
                )

            base_config = StrictConfig(strict_mode=False, require_full_core_rows=False, disable_fallback_matching=False, disable_section_summation=False, require_identity_validation=False)
            strict_config = StrictConfig(strict_mode=True, require_full_core_rows=True, disable_fallback_matching=True, disable_section_summation=True, require_identity_validation=True)

            companies[company_name] = create_state(base_config)
            strict_companies[company_name] = create_state(strict_config)
            
            # Store forensic chunks
            for i, chunk_text in enumerate(chunks_res["chunks"]):
                chunk_obj = Chunk(
                    chunk_id=len(st.session_state["coverage_index"]),
                    text=chunk_text,
                    section_heading="Forensic Backbone",
                    section_level=1,
                    section_path=f"Segment {i+1}",
                    semantic_tag="general",
                    start_line=0,
                    end_line=0
                )
                st.session_state["coverage_index"].append(chunk_obj)

            # Keep legacy chunks for retrieval engine compatibility
            legacy_chunks = build_chunks(doc, st.session_state["tokenizer"])
            st.session_state["document_chunks"].extend(legacy_chunks)
            
        except Exception as e:
            st.error(f"Fatal error during ingestion: {str(e)}")
            continue

    if not companies:
        return None

    # Update embeddings for Coverage Index
    if st.session_state["coverage_index"]:
        all_chunks = st.session_state["coverage_index"]
        # Use existing embedding store
        embeddings = st.session_state["retrieval_engine"].embedding_store.embed_chunks(all_chunks)
        st.session_state["document_embeddings"] = embeddings
        # document_chunks needs to point to coverage index for retrieval_engine compatibility
        st.session_state["document_chunks"] = all_chunks

    first_company = list(companies.keys())[0]
    
    # Initialize Hybrid Retrieval Controller
    st.session_state["hybrid_retriever"] = HybridRetrievalController(
        embedding_store=st.session_state["retrieval_engine"].embedding_store,
        chunks=st.session_state["coverage_index"],
        embeddings=st.session_state["document_embeddings"],
        structured_index=st.session_state["structured_index"]
    )
    
    # Initialize Final Answer Composer
    st.session_state["final_composer"] = FinalAnswerComposer(st.session_state["llm"])
    
    return SessionContext(
        companies=companies,
        strict_companies=strict_companies,
        active_company=first_company,
        strict_mode=False
    )

def extract_text_from_pdf(uploaded_file):
    text = ""
    uploaded_file.seek(0)
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def run_rag_pipeline(query, raw_retrieval=False):
    if not st.session_state.get("coverage_index"):
        return "No documents uploaded. Please upload a PDF first."
    
    # Use Hybrid Retrieval Controller
    retriever = st.session_state.get("hybrid_retriever")
    if not retriever:
        return "Retriever not initialized."
    
    retrieval_res = retriever.retrieve(query)
    
    if raw_retrieval:
        return retrieval_res
    
    if retrieval_res["status"] == "not_found":
        return "NOT FOUND"
    
    # If not raw_retrieval, we proceed to LLM interpretation (for HYBRID intent)
    context = retrieval_res["content"]
    
    # Step 7: Model-Aware Optimization
    prompt = f"""You are a financial research assistant. 
Answer the following question using the provided context. 

If the answer is not in the context, say NOT FOUND.
Do NOT guess numbers. Do NOT perform arithmetic on raw text.

Context:
{context}

Question:
{query}

Answer with citations:"""

    return st.session_state["llm"].generate(prompt)

uploaded_files = st.sidebar.file_uploader(
    "Upload Financial Document (PDF only)",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_files and st.sidebar.button("Initialize Session"):
    with st.spinner("Initializing session..."):
        st.session_state["session_context"] = initialize_session(uploaded_files)
    if st.session_state.get("session_context"):
        st.success("Session initialized")

if st.session_state.get("session_context"):
    companies = list(st.session_state.get("session_context").companies.keys())

    selected_company = st.sidebar.selectbox("Select Company", companies)

    st.session_state["session_context"].active_company = selected_company
    st.session_state["session_context"].strict_mode = strict_mode

    state = st.session_state.get("session_context").get_active_state()
    user_query = st.chat_input("Ask a financial question...")

    if user_query:
        start_time = time.time()
        
        # STEP 1: Intent Classification
        controller = st.session_state["query_controller"]
        intent_info = controller.route_query(user_query)
        intent = intent_info["intent"]
        
        st.caption(f"Routing Intent: {intent}")

        # STEP 2: Routing Rules
        structured_result = None
        narrative = ""
        
        # Initialize Computation Controller for the active company
        comp_controller = None
        if state:
            comp_controller = DeterministicComputationController(state)

        if intent == IntentType.RETRIEVAL.value:
            # Route to Retrieval Engine ONLY (Always return JSON internally, then compose)
            with st.spinner("Executing forensic retrieval..."):
                retrieval_data = run_rag_pipeline(user_query, raw_retrieval=True)
                composer = st.session_state["final_composer"]
                narrative = composer.compose(user_query, retrieval_data)
        
        elif intent in [IntentType.COMPUTATION.value, IntentType.HYBRID.value]:
            # Step 2: Deterministic Computation (Python Only)
            with st.spinner("Executing deterministic computation..."):
                if not comp_controller:
                    narrative = "Computation Engine Error: No financial state available."
                else:
                    # Determine computation type (heuristic for now)
                    comp_type = "full_analysis"
                    if "piotroski" in user_query.lower():
                        comp_type = "piotroski"
                    elif "growth" in user_query.lower():
                        comp_type = "growth"
                    
                    comp_res = comp_controller.run_computation(comp_type)
                    
                    if comp_res["status"] == "error":
                        narrative = f"COMPUTATION ABORTED: {comp_res['reason']}\nMissing fields: {comp_res.get('missing_fields', 'N/A')}"
                    else:
                        # Step 3: LLM Interpretation Mode (Interpretation ONLY)
                        with st.spinner("Synthesizing analysis..."):
                            # If Hybrid, we also get RAG context
                            internal_data = comp_res
                            if intent == IntentType.HYBRID.value:
                                retrieval_data = run_rag_pipeline(user_query, raw_retrieval=True)
                                internal_data["rag_evidence"] = retrieval_data
                            
                            composer = st.session_state["final_composer"]
                            narrative = composer.compose(user_query, internal_data)

        with st.chat_message("assistant"):
            st.markdown(narrative)

        # UI Rendering for Metrics (only for COMPUTATION/HYBRID)
        if structured_result and structured_result.get("mode") != "qualitative":
            st.divider()

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Key Metrics")
                metrics = structured_result.get("metrics", {})
                if not metrics:
                    st.info("No metrics returned.")
                else:
                    for name, metric in metrics.items():
                        value = metric.value if metric.value is not None else "N/A"
                        st.metric(label=name.replace("_", " ").title(), value=value)

                confidence = state.get_overall_confidence()
                st.progress(float(confidence))
                st.caption(f"Overall Confidence: {confidence}")

            with col2:
                st.subheader("Signals")
                signals = structured_result.get("signals", {})
                if not signals:
                    st.info("No signals returned.")
                else:
                    for name, signal in signals.items():
                        if signal.value is None:
                            display = "N/A"
                        elif signal.value == 1:
                            display = "Positive"
                        else:
                            display = "Negative"
                        st.metric(label=name.replace("_", " ").title(), value=display)

            with st.expander("Diagnostics & Validation"):
                diagnostics = structured_result.get("diagnostics", {})
                for name, value in diagnostics.items():
                    st.write(f"{name}: {value}")

                if structured_result.get("strict_diff"):
                    st.write("Strict Mode Differences:")
                    st.json(structured_result["strict_diff"])

            st.subheader("Revenue Trend")
            fig = generate_revenue_chart(state)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            st.divider()
            analysis_time = structured_result.get('analysis_time_ms', int((time.time() - start_time) * 1000))
            st.caption(f"Analysis Time: {analysis_time} ms")

        if structured_result and structured_result.get("mode") == "comparison":
            st.subheader("Company Comparison")
            companies_res = structured_result["companies"]
            for name, data in companies_res.items():
                st.markdown(f"### {name}")
                comp_metrics = data["metrics"]
                for m_name, metric in comp_metrics.items():
                    st.metric(label=m_name.replace("_", " ").title(), value=metric.value)
