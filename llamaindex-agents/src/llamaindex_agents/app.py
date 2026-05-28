import os
import chainlit as cl
import phoenix as px
from llama_index.core import set_global_handler, VectorStoreIndex, Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.llms.ollama import Ollama
from llama_index.postprocessor.flag_embedding_reranker import FlagEmbeddingReranker

# Import refactored config and tools
from llamaindex_agents.config import (
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    check_ollama,
    init_global_settings,
    get_pg_vector_store,
)
from llamaindex_agents.tools import get_all_tools

# Launch Phoenix tracing in the background
px.launch_app()
set_global_handler("arize_phoenix")

# Set up local embedding model globally
init_global_settings()

# Set up local LLM globally
llm = Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
Settings.llm = llm

def get_postgres_index() -> VectorStoreIndex:
    """Connects to the Postgres vector store and retrieves the indexed documents."""
    vector_store = get_pg_vector_store()
    return VectorStoreIndex.from_vector_store(vector_store=vector_store)

@cl.on_chat_start
async def on_chat_start():
    """Triggers when the Chainlit web interface is opened.
    
    Checks local Ollama service, connects to Postgres, sets up the local
    two-stage RAG query engine (retrieval + reranking), builds the tools list,
    and initializes the conversational ReAct agent.
    """
    msg = cl.Message(content="Initializing Local Open-Source Agent (Loading models...)")
    await msg.send()

    # Verify Ollama service and model
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

    # Document Retrieval Tool
    query_engine_tool = QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name="knowledge_base",
            description="Searches local documents in Postgres. Use this when the user asks about indexed concepts.",
        ),
    )

    # Load standard refactored tools (Calculator, Web Search)
    tools = [query_engine_tool] + get_all_tools(include_file_writer=False)
    
    # Initialize ReAct Agent with local Ollama LLM
    agent = ReActAgent(
        tools=tools,
        llm=llm,
        verbose=True,
    )

    cl.user_session.set("agent", agent)
    
    msg.content = f"Local Agent is ready! (Phoenix Tracing available at http://localhost:6006). Using model {OLLAMA_MODEL}. How can I help you?"
    await msg.update()

@cl.on_message
async def on_message(message: cl.Message):
    """Triggers when a message is received in Chainlit chat.
    
    Sends the user's message to the ReAct agent and streams the generated response.
    """
    agent = cl.user_session.get("agent")
    if not agent:
        return
        
    response_msg = cl.Message(content="Thinking locally...")
    await response_msg.send()
    
    try:
        result = await agent.run(user_msg=message.content)
        response_msg.content = str(result.response.content)
    except Exception as e:
        response_msg.content = f"Error during generation: {e}\n\nDid you run `ollama run {OLLAMA_MODEL}` in your terminal?"
        
    await response_msg.update()
