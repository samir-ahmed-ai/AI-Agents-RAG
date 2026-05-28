import os
import getpass
import urllib.error
import urllib.request
import chainlit as cl
from dotenv import load_dotenv

# Set up Arize Phoenix Tracer
import phoenix as px
from llama_index.core import set_global_handler

from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool, ToolMetadata, FunctionTool
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker
from duckduckgo_search import DDGS

load_dotenv()

# Launch Phoenix tracing in the background
px.launch_app()
set_global_handler("arize_phoenix")

# Set up local embedding model globally
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Set up local LLM globally
llm = Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
Settings.llm = llm


def check_ollama() -> str | None:
    """Return an error message if Ollama is unreachable or the model is missing."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as response:
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

def get_postgres_index():
    user = os.getenv("POSTGRES_USER", getpass.getuser())
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "linearbits")

    vector_store = PGVectorStore.from_params(
        database=db_name,
        host=host,
        password=password,
        port=port,
        user=user,
        table_name="knowledge_base_local",
        embed_dim=384,
    )
    return VectorStoreIndex.from_vector_store(vector_store=vector_store)

def calculate(expression: str) -> str:
    """Evaluates a mathematical expression and returns the result."""
    try:
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"

def web_search(query: str) -> str:
    """Searches the web for the given query and returns a summary of results."""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
            if not results:
                return "No results found."
            output = []
            for r in results:
                output.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nURL: {r.get('href')}\n")
            return "\n".join(output)
    except Exception as e:
        return f"Error performing web search: {e}"

@cl.on_chat_start
async def on_chat_start():
    msg = cl.Message(content="Initializing Local Open-Source Agent (Loading models...)")
    await msg.send()

    ollama_error = check_ollama()
    if ollama_error:
        await msg.update(content=ollama_error)
        return

    try:
        # Load Postgres Index
        index = get_postgres_index()
    except Exception as e:
        await msg.update(content=f"Failed to connect to Postgres. Error: {e}")
        return
        
    # Local Two-Stage RAG: Retrieves top 10, then uses FlagEmbeddingReranker (local cross-encoder)
    reranker = FlagEmbeddingReranker(model="BAAI/bge-reranker-base", top_n=3)
    
    query_engine = index.as_query_engine(
        similarity_top_k=10, 
        node_postprocessors=[reranker]
    )

    query_engine_tool = QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name="knowledge_base",
            description="Searches local documents in Postgres. Use this when the user asks about indexed concepts.",
        ),
    )

    calculator_tool = FunctionTool.from_defaults(fn=calculate)
    web_search_tool = FunctionTool.from_defaults(fn=web_search)
    
    # Initialize ReAct Agent with Ollama LLM
    agent = ReActAgent(
        tools=[query_engine_tool, calculator_tool, web_search_tool],
        llm=llm,
        verbose=True,
    )

    cl.user_session.set("agent", agent)
    
    msg.content = "Local Llama3.1 Agent is ready! (Phoenix Tracing available at http://localhost:6006). How can I help you?"
    await msg.update()

@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    if not agent:
        return
        
    response_msg = cl.Message(content="Thinking locally...")
    await response_msg.send()
    
    try:
        result = await agent.run(user_msg=message.content)
        response_msg.content = str(result.response.content)
    except Exception as e:
        response_msg.content = f"Error during generation: {e}\n\nDid you run `ollama run llama3.1` in your terminal?"
        
    await response_msg.update()
