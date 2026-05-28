import os
import getpass
from sqlalchemy import make_url
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Document, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

def get_index():
    # Setup fully local HuggingFace embedding model (no API key needed)
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    
    user = os.getenv("POSTGRES_USER", getpass.getuser())
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "linearbits")

    try:
        # Initialize PGVectorStore with the new local table and smaller embed dimension (384)
        vector_store = PGVectorStore.from_params(
            database=db_name,
            host=host,
            password=password,
            port=port,
            user=user,
            table_name="knowledge_base_local",
            embed_dim=384,  # BAAI/bge-small-en-v1.5 dimension
        )
        
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        print("Building/Updating local Postgres index from documents using BAAI/bge-small-en-v1.5...")
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
