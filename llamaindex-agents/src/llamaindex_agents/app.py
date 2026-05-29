import os
import time
import urllib.request
import json
import chainlit as cl
from chainlit.input_widget import Select, TextInput, Slider, Switch
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
    get_ollama_models,
    pull_ollama_model_stream,
    init_global_settings,
    get_pg_vector_store,
)
from llamaindex_agents.tools import get_all_tools

# Launch Phoenix tracing safely in the background if ports are free
def is_port_in_use(port: int) -> bool:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False

try:
    if is_port_in_use(6006) or is_port_in_use(4317):
        print("⚠️ Phoenix ports (6006 or 4317) are already active. Connecting to the existing tracing session...")
        set_global_handler("arize_phoenix")
    else:
        if not px.active_session():
            px.launch_app()
        set_global_handler("arize_phoenix")
except Exception as e:
    print(f"⚠️ Phoenix Observability could not be launched: {e}. Continuing without dynamic tracing.")

# Set up local embedding model globally
init_global_settings()


def get_postgres_index() -> VectorStoreIndex:
    """Connects to the Postgres vector store and retrieves the indexed documents."""
    vector_store = get_pg_vector_store()
    return VectorStoreIndex.from_vector_store(vector_store=vector_store)

async def ensure_model_installed(model_name: str) -> bool:
    """Checks if the local model is installed, otherwise streams pull progress in UI."""
    installed_models = get_ollama_models()
    normalized_installed = {m.split(":")[0] for m in installed_models} | set(installed_models)
    
    if model_name not in normalized_installed:
        progress_msg = cl.Message(content=f"📥 **Model Not Found Locally**: Downloading `{model_name}` from Ollama registry. Please stand by...")
        await progress_msg.send()
        
        last_percent = -1
        last_update_time = 0
        try:
            for chunk in pull_ollama_model_stream(model_name):
                status = chunk.get("status", "")
                completed = chunk.get("completed", 0)
                total = chunk.get("total", 0)
                
                if "Error" in status or status.startswith("Error"):
                    await progress_msg.update(content=f"❌ **Ollama Pull Error**: {status}")
                    return False
                
                current_time = time.time()
                if total > 0:
                    percent = int((completed / total) * 100)
                    if percent != last_percent and (current_time - last_update_time >= 1.0 or percent == 100):
                        bar_length = 20
                        filled = int(round(bar_length * completed / float(total)))
                        bar = '█' * filled + '░' * (bar_length - filled)
                        completed_gb = completed / (1024 ** 3)
                        total_gb = total / (1024 ** 3)
                        
                        await progress_msg.update(
                            content=(
                                f"📥 **Downloading `{model_name}`**:\n"
                                f"`[{bar}] {percent}%` ({completed_gb:.2f} GB / {total_gb:.2f} GB)\n"
                                f"Status: *{status}*"
                            )
                        )
                        last_percent = percent
                        last_update_time = current_time
                else:
                    if current_time - last_update_time >= 1.0:
                        await progress_msg.update(content=f"📥 **Downloading `{model_name}`**:\nStatus: *{status}*")
                        last_update_time = current_time
                        
            await progress_msg.update(content=f"✅ **Model `{model_name}` successfully pulled!**")
            return True
        except Exception as e:
            await progress_msg.update(content=f"❌ **Failed to pull model**: {e}")
            return False
    return True

async def rebuild_agent(settings: dict):
    """Rebuilds the LlamaIndex ReAct agent using the updated user settings."""
    model_name = settings["ollama_model"]
    temperature = settings["temperature"]
    system_prompt = settings["system_prompt"]
    enable_rag = settings["enable_rag"]
    similarity_top_k = settings["similarity_top_k"]
    enable_reranker = settings["enable_reranker"]
    rerank_top_n = settings["rerank_top_n"]
    
    # Initialize the Ollama LLM
    llm = Ollama(model=model_name, base_url=OLLAMA_BASE_URL, request_timeout=300.0, temperature=temperature)
    Settings.llm = llm
    cl.user_session.set("llm", llm)
    
    # Retrieve index
    index = cl.user_session.get("index")
    if not index:
        try:
            index = get_postgres_index()
            cl.user_session.set("index", index)
        except Exception:
            index = None
            
    tools = []
    if enable_rag and index:
        node_postprocessors = []
        if enable_reranker:
            reranker = FlagEmbeddingReranker(model="BAAI/bge-reranker-base", top_n=rerank_top_n)
            node_postprocessors.append(reranker)
            
        query_engine = index.as_query_engine(
            similarity_top_k=similarity_top_k,
            node_postprocessors=node_postprocessors
        )
        
        query_engine_tool = QueryEngineTool(
            query_engine=query_engine,
            metadata=ToolMetadata(
                name="knowledge_base",
                description="Searches local documents in Postgres. Use this when the user asks about indexed concepts.",
            ),
        )
        tools.append(query_engine_tool)
        
    # Append core local tools
    tools = tools + get_all_tools(include_file_writer=False)
    
    agent = ReActAgent(
        tools=tools,
        llm=llm,
        verbose=True,
        system_prompt=system_prompt
    )
    cl.user_session.set("agent", agent)

@cl.on_chat_start
async def on_chat_start():
    """Triggers when the Chainlit web interface is opened."""
    msg = cl.Message(content="Initializing Local Open-Source Agent (Discovering models...)")
    await msg.send()

    # Verify Ollama service is running
    ollama_error = check_ollama()
    if ollama_error:
        await msg.update(content=ollama_error)
        return

    try:
        # Load Postgres Index and save to session
        index = get_postgres_index()
        cl.user_session.set("index", index)
    except Exception as e:
        await msg.update(content=f"Failed to connect to Postgres. Error: {e}")
        return
        
    # Get available models
    available_models = get_ollama_models()
    if not available_models:
        available_models = [OLLAMA_MODEL]
        
    # Standard popular models to support write-in / selection
    popular_models = ["llama3.1", "mistral", "gemma2", "phi3", "llava", "llama3.2-vision"]
    for pm in popular_models:
        if pm not in available_models and f"{pm}:latest" not in available_models:
            available_models.append(pm)
            
    # Setup premium Chat Settings
    settings = await cl.ChatSettings([
        Select(
            id="ollama_model",
            label="Local Ollama Model",
            values=available_models,
            initial_value=OLLAMA_MODEL if OLLAMA_MODEL in available_models else available_models[0]
        ),
        TextInput(
            id="system_prompt",
            label="System Instructions",
            initial_value="You are a helpful, expert AI programming and DevOps assistant. You have access to professional local tools for calculations, filesystem exploration, web search, system monitoring, and a local Postgres knowledge base.\n\n"
                          "IMPORTANT Formatting Rule:\n"
                          "When using tools, you must strictly output:\n"
                          "Thought: <your thought>\n"
                          "Action: <tool_name>\n"
                          "Action Input: <json_args>\n"
                          "When giving a final response, you must strictly output:\n"
                          "Thought: <your thought>\n"
                          "Answer: <your final answer>\n"
                          "Always include 'Thought:' first, followed by either 'Action:' and 'Action Input:', or 'Answer:'. Do not use any bolding or markdown code blocks for the Thought/Action/Answer structure."
        ),
        Slider(
            id="temperature",
            label="Temperature (Creativity)",
            initial=0.3,
            min=0.0,
            max=1.0,
            step=0.05
        ),
        Switch(
            id="enable_rag",
            label="Enable Knowledge Base (RAG)",
            initial=True
        ),
        Slider(
            id="similarity_top_k",
            label="RAG Similarity Top K",
            initial=5,
            min=1,
            max=20,
            step=1
        ),
        Switch(
            id="enable_reranker",
            label="Enable Local Reranking (BGE)",
            initial=True
        ),
        Slider(
            id="rerank_top_n",
            label="Rerank Top N (Context Count)",
            initial=3,
            min=1,
            max=10,
            step=1
        )
    ]).send()
    
    cl.user_session.set("settings", settings)
    
    # Ensure default model is available
    default_model = settings["ollama_model"]
    await ensure_model_installed(default_model)
    
    # Initialize the agent
    await rebuild_agent(settings)
    
    msg.content = f"🚀 **Local Agent Ready!**\n\n* **Model**: `{default_model}`\n* **RAG**: Postgres PGVector + BGE-Reranker\n* **Phoenix Observability**: Running live at [http://localhost:6006](http://localhost:6006)\n\nTry uploading documents to index them, or drag an image and ask a vision question!"
    await msg.update()

@cl.on_settings_update
async def on_settings_update(settings):
    """Fires when the user changes settings in the Chat Settings panel."""
    cl.user_session.set("settings", settings)
    
    msg = cl.Message(content=f"⚙️ **Re-configuring agent** to use `{settings['ollama_model']}`...")
    await msg.send()
    
    # Ensure selected model is installed
    success = await ensure_model_installed(settings["ollama_model"])
    if not success:
        await msg.update(content=f"❌ Failed to download model `{settings['ollama_model']}`. Keeping previous configuration.")
        return
        
    # Rebuild
    await rebuild_agent(settings)
    
    await msg.update(content=f"⚙️ **Configuration Updated**:\n* Model: `{settings['ollama_model']}`\n* RAG: {'Enabled' if settings['enable_rag'] else 'Disabled'}\n* Temperature: `{settings['temperature']}`")

@cl.on_message
async def on_message(message: cl.Message):
    """Triggers when a message is received in Chainlit chat."""
    settings = cl.user_session.get("settings")
    if not settings:
        return
        
    # Check for document or image uploads
    image_elements = [el for el in message.elements if el.mime and el.mime.startswith("image/")]
    doc_elements = [el for el in message.elements if el.mime and (el.mime.startswith("text/") or "pdf" in el.mime or "word" in el.mime or el.name.endswith((".txt", ".md", ".pdf", ".docx")))]
    
    # 1. Process uploaded documents (Index into Vector DB in real-time!)
    if doc_elements:
        for doc_el in doc_elements:
            filename = doc_el.name
            filepath = doc_el.path
            
            progress = cl.Message(content=f"📥 **File Upload**: Ingesting `{filename}` into the Postgres vector database...")
            await progress.send()
            
            try:
                from llama_index.core import SimpleDirectoryReader
                # Parse the single file
                reader = SimpleDirectoryReader(input_files=[filepath])
                documents = reader.load_data()
                
                index = cl.user_session.get("index")
                if not index:
                    index = get_postgres_index()
                    cl.user_session.set("index", index)
                    
                # Insert documents into local index (embeddings calculated automatically)
                for doc in documents:
                    doc.metadata["file_name"] = filename
                    index.insert(doc)
                    
                await progress.update(content=f"✅ **Ingestion Complete**: File `{filename}` ({len(documents)} blocks) has been parsed, embedded via BGE, and stored in Postgres. Ask the agent anything about it!")
            except Exception as e:
                await progress.update(content=f"❌ **Ingestion Failed** for `{filename}`: {e}")
        return
        
    # 2. Process image upload (Vision multimodal execution!)
    if image_elements:
        img_el = image_elements[0]
        model_name = settings["ollama_model"]
        
        # Verify vision model
        is_vision = any(x in model_name.lower() for x in ["vision", "llava", "bakllava", "minicpm"])
        if not is_vision:
            warn = cl.Message(content=f"⚠️ **Note**: Model `{model_name}` might not support image analysis. For best results, select a vision model like `llava` or `llama3.2-vision` in Chat Settings.")
            await warn.send()
            
        status_msg = cl.Message(content=f"👁️ **Analyzing Image** `{img_el.name}` using `{model_name}`...")
        await status_msg.send()
        
        try:
            from llama_index.core.llms import ChatMessage, ImageBlock, TextBlock
            
            prompt_text = message.content if message.content.strip() else "Describe this image."
            msg = ChatMessage(
                role="user",
                blocks=[
                    ImageBlock(path=img_el.path),
                    TextBlock(text=prompt_text)
                ]
            )
            
            response_msg = cl.Message(content="")
            await response_msg.send()
            
            llm = cl.user_session.get("llm")
            start_time = time.time()
            token_count = 0
            
            # Direct chat streaming with vision blocks
            stream = await llm.astream_chat([msg])
            async for chunk in stream:
                token_count += 1
                await response_msg.stream_token(chunk.delta)
                
            await response_msg.update()
            await status_msg.delete()
            
            duration = time.time() - start_time
            speed = token_count / duration if duration > 0 else 0
            
            metrics = (
                f"\n\n---\n"
                f"⚡ **Vision Performance Metrics**:\n"
                f"⏱️ **Total Latency**: {duration:.2f}s | 🚀 **Generation Speed**: {speed:.1f} tok/sec\n"
                f"👁️ **Model**: `{model_name}` | 📁 **Source Image**: `{img_el.name}`"
            )
            response_msg.content += metrics
            await response_msg.update()
            
        except Exception as e:
            await status_msg.update(content=f"❌ **Vision Error**: Failed to process image: {e}")
        return
        
    # 3. Standard Text Agent Reasoning Loop
    agent = cl.user_session.get("agent")
    if not agent:
        return
        
    response_msg = cl.Message(content="")
    await response_msg.send()
    
    start_time = time.time()
    token_count = 0
    try:
        # Stream response token-by-token using async workflow stream
        handler = agent.run(user_msg=message.content, max_iterations=10)
        async for event in handler.stream_events():
            if hasattr(event, "delta") and event.delta:
                token_count += len(event.delta.split())
                await response_msg.stream_token(event.delta)
                
        # Resolve final result response content
        result = await handler
        response_msg.content = result.response.content
        await response_msg.update()
        
        duration = time.time() - start_time
        speed = token_count / duration if duration > 0 else 0
        
        rag_enabled = settings.get("enable_rag", True)
        rerank_enabled = settings.get("enable_reranker", True)
        
        metrics = (
            f"\n\n---\n"
            f"⚡ **Performance Metrics (Local Execution)**:\n"
            f"⏱️ **Total Latency**: {duration:.2f}s | 🚀 **Generation Speed**: {speed:.1f} tok/sec (est.)\n"
            f"🔍 **Knowledge Base (RAG)**: {'Enabled (2-stage Postgres + BGE)' if (rag_enabled and rerank_enabled) else 'Enabled (Postgres standard)' if rag_enabled else 'Disabled'}\n"
            f"🤖 **Active Model**: `{settings.get('ollama_model')}`"
        )
        response_msg.content += metrics
        await response_msg.update()
        
    except Exception as e:
        response_msg.content = f"Error during generation: {e}\n\nDid you run `ollama run {settings.get('ollama_model', OLLAMA_MODEL)}` in your terminal?"
        await response_msg.update()
