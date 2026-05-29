import os
import getpass
import urllib.request
import urllib.error
from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Load environment variables from the .env file in llamaindex-agents
# The app or scripts could be run from different relative directories, so we find the package root
PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
# Check for .env file up to two directories above the package root
for parent_lvl in [os.path.dirname(PACKAGE_ROOT), os.path.dirname(os.path.dirname(PACKAGE_ROOT))]:
    env_path = os.path.join(parent_lvl, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        break
else:
    load_dotenv()

# Workspace paths
WORKSPACE_ROOT = os.path.abspath(os.path.join(PACKAGE_ROOT, "..", "..", ".."))
DATA_DIR = os.path.abspath(os.path.join(PACKAGE_ROOT, "..", "..", "data"))

# Postgres configuration
POSTGRES_USER = os.getenv("POSTGRES_USER", getpass.getuser())
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "linearbits")
PG_TABLE_NAME = "knowledge_base_local"
EMBED_DIM = 384  # BAAI/bge-small-en-v1.5 dimension

# Ollama configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# OpenAI API Key (For cloud ReAct CLI agent)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def init_global_settings():
    """Initializes global embeddings model settings for LlamaIndex."""
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

def get_pg_vector_store() -> PGVectorStore:
    """Creates and returns a PGVectorStore instance using the configured database parameters."""
    return PGVectorStore.from_params(
        database=POSTGRES_DB,
        host=POSTGRES_HOST,
        password=POSTGRES_PASSWORD,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        table_name=PG_TABLE_NAME,
        embed_dim=EMBED_DIM,
    )

def check_ollama() -> str | None:
    """Verifies if the Ollama service is reachable and the required model is downloaded."""
    try:
        url = f"{OLLAMA_BASE_URL}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            import json
            data = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError):
        return (
            "Ollama is not running. Install it from https://ollama.com/download, "
            "then run `make ollama-start` and `make ollama-pull`."
        )

    models = {model["name"] for model in data.get("models", [])}
    model_names = {name.split(":")[0] for name in models}
    if OLLAMA_MODEL not in model_names and f"{OLLAMA_MODEL}:latest" not in models:
        return (
            f"Ollama model `{OLLAMA_MODEL}` is not installed. "
            f"Run `make ollama-pull` or `ollama pull {OLLAMA_MODEL}`."
        )

    return None

def get_ollama_models() -> list[str]:
    """Retrieves a list of all downloaded Ollama model names."""
    try:
        import json
        url = f"{OLLAMA_BASE_URL}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            # Return full tag names (e.g. 'llama3.1:latest', 'llava:latest')
            return [model["name"] for model in data.get("models", [])]
    except Exception:
        return []

def pull_ollama_model_stream(model_name: str):
    """Streams pull progress of an Ollama model.
    
    Yields dictionary chunks with progress info.
    """
    import json
    url = f"{OLLAMA_BASE_URL}/api/pull"
    payload = json.dumps({"name": model_name}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        # Long timeout for model downloading
        with urllib.request.urlopen(req, timeout=1200) as response:
            for line in response:
                if line:
                    yield json.loads(line.decode("utf-8").strip())
    except Exception as e:
        yield {"status": f"Error: {e}"}

