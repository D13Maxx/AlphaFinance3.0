from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np

# Adjust imports to match project structure
from src.parser.models import Document
from src.retrieval.chunk_builder import Chunk

@dataclass
class DocumentSession:
    document_id: str
    document: Document
    classification: Dict
    chunks: List[Chunk]
    embeddings: np.ndarray

@dataclass
class RAGExecutionState:
    session: DocumentSession
    query: str
    query_type: Optional[str] = None
    selected_chunks: Optional[List[Chunk]] = None
    context: Optional[str] = None
    numeric_result: Optional[Dict] = None
    answer: Optional[str] = None
    error: Optional[str] = None
