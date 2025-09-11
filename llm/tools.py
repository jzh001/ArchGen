from pydantic import BaseModel, Field
from langchain_core.tools import tool

@tool
def search_tikz_database(query: str, top_k: int = 5) -> str:
    """Simple RAG search over TikZ examples.

    Delegates to perform_rag and returns plain text (concatenated retrieved snippets).
    """
    from vector_db.rag import perform_rag

    result = perform_rag(query, top_k=top_k)
    # Ensure we always return a string
    return result if isinstance(result, str) else ""
