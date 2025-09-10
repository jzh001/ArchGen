from transformers import pipeline
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.supabase import SupabaseVectorStore
import os

# Initialize Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def perform_rag(query):
    """Perform Retrieval-Augmented Generation (RAG) using CodeBERT."""
    # Connect to the vector database
    vector_store = SupabaseVectorStore(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_storage_context(storage_context)

    # Retrieve relevant documents
    retrieved_docs = index.query(query)

    # Initialize CodeBERT for generation
    generator = pipeline("text2text-generation", model="microsoft/codebert-base")

    # Generate responses based on retrieved documents
    context = "\n".join([doc.text for doc in retrieved_docs])
    response = generator(f"Context: {context}\nQuery: {query}", max_length=512, num_return_sequences=1)

    return response[0]['generated_text']