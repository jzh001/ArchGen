from vector_db import index as vindex
from llama_index.core import Settings
from llama_index.embeddings.huggingface.base import HuggingFaceEmbedding

def perform_rag(query: str):
    """
    Perform Retrieval-Augmented Generation (RAG) using the vector index.
    Args:
        query (str): The input query string.
    Returns:
        list: Retrieved documents relevant to the query.
    """
    # IMPORTANT: reference attributes off the module to avoid stale imports
    if not vindex.is_vector_db_ready() or vindex.vector_store is None or vindex.index is None or type(Settings.embed_model) != HuggingFaceEmbedding:
        error = vindex.get_vector_db_error()
        print(f"Vector DB not ready. Error: {error}")
        return "Vector DB is not ready. Please try again later." if not error else f"Vector DB error: {error}"

    # Ensure a covering index for cosine_distance exists
    try:
        # This assumes vindex.vector_store is a vecs Collection object
        if hasattr(vindex.vector_store, "create_index"):
            vindex.vector_store.create_index(measure="cosine_distance")
    except Exception as e:
        print(f"Warning: Could not create covering index for cosine_distance: {e}")

    print(f"Performing RAG")
    try:
        query_engine = vindex.index.as_query_engine(llm=None, embed_model=Settings.embed_model)
        response = query_engine.query(query)
        docs = [node.node.get_content() for node in response.source_nodes]
        result_text = "\n\n".join(docs)

        # print("RAG response:", result_text)
        return result_text
    except Exception as e:
        print(f"Error during RAG query: {e}")
        return ""