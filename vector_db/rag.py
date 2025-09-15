from vector_db import index as vindex
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from concurrent.futures import ThreadPoolExecutor, TimeoutError

def perform_rag(query: str, top_k: int = 5):
    """
    Perform Retrieval-Augmented Generation (RAG) using the vector index.
    """
    if (
        not vindex.is_vector_db_ready()
        or vindex.vector_store is None
        or vindex.index is None
        or type(Settings.embed_model) != HuggingFaceEmbedding
    ):
        error = vindex.get_vector_db_error()
        return "Vector DB is not ready. Please try again later." if not error else f"Vector DB error: {error}"

    print(f"===== Performing RAG =====\nQuery: {query}\nTop K: {top_k}")
    try:
        query_engine = vindex.index.as_query_engine(
            llm=None,
            embed_model=Settings.embed_model,
            similarity_top_k=top_k,
        )

        # Use a thread pool to enforce a timeout on the query
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(query_engine.query, query)
            try:
                response = future.result(timeout=20)  # Timeout after 10 seconds
            except TimeoutError:
                print("Error: RAG query timed out.")
                return "Error: RAG query timed out."

        docs = [node.node.get_content() for node in response.source_nodes]
        return "\n\n".join(docs)
    except Exception as e:
        print(f"Error during RAG query: {e}")
        return f"Error during RAG query: {e}"
