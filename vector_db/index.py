from llama_index.core import SimpleDirectoryReader, Document, StorageContext
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.supabase import SupabaseVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings

import torch
import os
import threading
from dotenv import load_dotenv

load_dotenv()

# Global status and objects
VECTOR_DB_READY = False
VECTOR_DB_ERROR = None
vector_store = None
index = None


def _init_vector_db():
    global VECTOR_DB_READY, VECTOR_DB_ERROR, vector_store, index
    try:
        DB_CONNECTION = os.getenv("DB_CONNECTION")
        COLLECTION_NAME = "documents"
        missing_vars = []
        if not DB_CONNECTION:
            missing_vars.append("DB_CONNECTION")
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Set HuggingFace embedding model globally
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        print("Using device:", device)
        embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5",
            device=device
        )
        Settings.embed_model = embed_model
        # Explicitly disable default LLM usage to avoid OpenAI attempts
        Settings.llm = None

        vector_store = SupabaseVectorStore(
            postgres_connection_string=DB_CONNECTION,
            collection_name=COLLECTION_NAME
        )
        print("Connected to Supabase vector store.")
        index = VectorStoreIndex.from_vector_store(vector_store)
        VECTOR_DB_READY = True
    except Exception as e:
        VECTOR_DB_ERROR = str(e)
        print(f"Error initializing Supabase vector DB: {e}")

# Start connection in background
threading.Thread(target=_init_vector_db, daemon=True).start()

def is_vector_db_ready():
    return VECTOR_DB_READY

def get_vector_db_error():
    return VECTOR_DB_ERROR

def add_documents_to_vector_db(documents):
    """Add documents to the Supabase vector database."""
    if not VECTOR_DB_READY:
        raise RuntimeError("Vector DB is not ready yet.")
    if VECTOR_DB_ERROR:
        raise RuntimeError(f"Vector DB error: {VECTOR_DB_ERROR}")
    print("Adding documents to the vector database...")
    try:
        # Convert documents to the required format
        formatted_documents = [Document(text=doc) for doc in documents if doc.strip()]
        print(f"Prepared {len(formatted_documents)} documents for insertion.")
        for doc in formatted_documents:
            index.insert(doc)
        print("Documents added to the vector database.")
        return len(formatted_documents)
    except Exception as e:
        print(f"Error during Supabase connection or document insertion: {e}")
        raise