from src.parser.models import Document
from src.parser.preprocessing import preprocess_text
from src.parser.tree_builder import build_document_tree

def parse_document(text: str) -> Document:
    """
    Parses a raw text string into a structured Document object.
    1. Preprocesses text into lines.
    2. Builds a hierarchical tree of Sections.
    """
    lines = preprocess_text(text)
    doc = build_document_tree(lines)
    return doc
