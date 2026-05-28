from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Document
from llamaindex_agents.config import DATA_DIR, init_global_settings, get_pg_vector_store

def get_index() -> VectorStoreIndex | None:
    """Builds or updates the LlamaIndex PGVectorStore index from documents in the data folder.
    
    Initializes global embedding settings, reads documentation text files, and generates
    dense embeddings locally before saving the vectors into Postgres.
    """
    # Set up fully local HuggingFace embedding model
    init_global_settings()

    try:
        # Retrieve vector store setup from centralized config
        vector_store = get_pg_vector_store()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        print(f"Building/Updating local Postgres index from documents in '{DATA_DIR}' using BAAI/bge-small-en-v1.5...")
        try:
            documents = SimpleDirectoryReader(DATA_DIR).load_data()
        except ValueError:
            print("No documents found in data directory. Creating an empty document to initialize schema.")
            documents = [Document(text="This is an empty knowledge base. Add documents to the data folder.")]
        
        index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
        print("Index successfully stored in Postgres (Local Models Mode)!")
        return index
    except Exception as e:
        print(f"Failed to ingest data. Error: {e}")
        return None

if __name__ == "__main__":
    get_index()
