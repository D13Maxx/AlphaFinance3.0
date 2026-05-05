import uuid
import logging
from typing import Dict, Any, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from pydantic import BaseModel
import uvicorn

# Project Imports
from src.parser.parser import parse_document
from src.parser.models import Document
from src.classifier.classifier import classify_document
from src.retrieval.retrieval_engine import RetrievalEngine
from src.retrieval.embedding_store import EmbeddingStore
from src.orchestrator.engine import FinancialRAGEngine
from src.orchestrator.state_models import DocumentSession
from src.orchestrator.state_enum import RAGStateEnum
from src.llm.ollama_llm import OllamaLLM

# Setup Interface Models
class QueryRequest(BaseModel):
    document_id: str
    query: str

class QueryResponse(BaseModel):
    status: str
    document_id: str
    query_type: str
    answer: str

class ErrorResponse(BaseModel):
    status: str
    message: str

# Mocks and Helpers (to replace with real implementations in production)
class MockTokenizer:
    def encode(self, text: str) -> List[int]:
        return [ord(c) for c in text[:50]] # Dummy
    def decode(self, tokens: List[int]) -> str:
        return "".join([chr(t) for t in tokens])

class MockEmbeddingModel:
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Return random vectors of dim 768
        return [[0.1] * 768 for _ in texts]
    def embed_query(self, text: str) -> List[float]:
        return [0.1] * 768



class MockNumericEngine:
    def process(self, query, chunks):
        return {"result": 50000000}

async def extract_text_from_file(file: UploadFile) -> str:
    # helper assumption - no longer decoding binary PDFs as utf-8
    content = await file.read()
    import fitz
    with fitz.open(stream=content, filetype="pdf") as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text

# Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("Starting up Financial RAG System...")
    
    # 1. Load Tokenizer
    app.state.tokenizer = MockTokenizer()
    
    # 2. Load Embedding Model
    # EmbeddingStore requires a model
    embed_model = MockEmbeddingModel()
    
    # 3. Initialize Retrieval
    embedding_store = EmbeddingStore(embed_model)
    app.state.retrieval_engine = RetrievalEngine(embedding_store)
    
    # 4. Load LLM
    app.state.llm = OllamaLLM(
        model_name="qwen2.5:7b-instruct"
    )

    try:
        app.state.llm.generate("Warm up.")
    except Exception:
        pass
    
    # 5. Initialize Numeric Engine
    app.state.numeric_engine = MockNumericEngine()
    
    # 6. Initialize Orchestrator
    # FinancialRAGEngine needs: classifier, retrieval_engine, llm, numeric_engine, tokenizer
    # Note: classifier is a module/function, not a class instance usually, 
    # but engine expects strict DI.
    # The engine uses `self.classifier`, but checking engine.py it didn't strictly call it 
    # except maybe implicitly? 
    # Wait, engine.py doesn't actually call classifier methods in the code I wrote?
    # Checking engine.py: `handle_init` -> `CLASSIFY_QUERY`.
    # `handle_classify_query` uses 'how much' keywords, does NOT use `self.classifier`.
    # `handle_retrieve` uses `self.retrieval_engine`.
    # So strictly, `self.classifier` might be unused in `engine.py` logic v1.
    # However, for `POST /upload`, we use `classify_document` directly.
    # I will pass `None` for classifier in engine init if unused, or the module.
    
    app.state.engine = FinancialRAGEngine(
        classifier=None, # Unused in current engine logic, handled in API
        retrieval_engine=app.state.retrieval_engine,
        llm=app.state.llm,
        numeric_engine=app.state.numeric_engine,
        tokenizer=app.state.tokenizer,
        debug=False
    )
    
    # 7. Document Store
    app.state.document_store = {}
    
    yield
    
    # Shutdown
    logging.info("Shutting down...")
    app.state.document_store.clear()

app = FastAPI(lifespan=lifespan)

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # 1. Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported in this demo version."
        )

    # 2. Extract text
    import fitz
    try:
        content = await file.read()
        with fitz.open(stream=content, filetype="pdf") as reader:
            page_count = len(reader)

            # 3. Enforce Caps
            if page_count > 500:
                raise HTTPException(
                    status_code=400,
                    detail="Document exceeds 500-page limit for this demo version."
                )

            if page_count > 200:
                print(f"Large document detected: {page_count} pages (processing may take longer).")

            text = ""
            for page in reader:
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"

    except Exception as e:
        # Catch errors or other extraction issues
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {str(e)}")
        
    # 2. Parse
    try:
        document = parse_document(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
        
    # 3. Classify
    classification = classify_document(document)
    
    # 4. Index
    try:
        # returns {"chunks": ..., "embeddings": ...}
        index_result = app.state.retrieval_engine.index_document(
            document_id="temp", # We'll assign real ID after
            document=document,
            tokenizer=app.state.tokenizer
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")
        
    # 5. Create Session
    doc_id = str(uuid.uuid4())
    session = DocumentSession(
        document_id=doc_id,
        document=document,
        classification=classification,
        chunks=index_result["chunks"],
        embeddings=index_result["embeddings"]
    )
    
    # 6. Store
    app.state.document_store[doc_id] = session
    
    return {
        "status": "success",
        "document_id": doc_id,
        "classification": classification["label"],
        "page_count": page_count
    }

@app.post("/query")
async def query_document(request: QueryRequest):
    doc_id = request.document_id
    query_text = request.query
    
    # 1. Retrieve Session
    session = app.state.document_store.get(doc_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # 2. Run Engine
    # Engine returns dict
    result = app.state.engine.run(session, query_text)
    
    if "error" in result and result["error"]:
        return {
            "status": "error",
            "message": result["error"]
        }
        
    return {
        "status": "success",
        "document_id": doc_id,
        "query_type": result.get("query_type", "unknown"),
        "answer": result.get("answer", "")
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
