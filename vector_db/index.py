from llama_index.core import SimpleDirectoryReader, Document, StorageContext
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.supabase import SupabaseVectorStore

import os

# Initialize Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_vector_db():
    """Connect to the Supabase vector database."""
    vector_store = SupabaseVectorStore(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_storage_context(storage_context)

def add_documents_to_vector_db(documents):
    """Add documents to the Supabase vector database."""
    vector_store = SupabaseVectorStore(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_storage_context(storage_context)

    # Convert documents to the required format
    formatted_documents = [Document(text=doc) for doc in documents]
    index.insert(formatted_documents)