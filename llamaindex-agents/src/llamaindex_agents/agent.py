from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from llamaindex_agents.config import (
    OPENAI_API_KEY,
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    check_ollama,
    init_global_settings,
)
from llamaindex_agents.tools import get_all_tools
from llamaindex_agents.ingestion import get_index

def main():
    """Starts the CLI-based LlamaIndex ReAct agent using OpenAI or local Ollama LLM and Postgres vector store RAG."""
    print("Initializing LlamaIndex Agent (Settings & Local Index)...")
    init_global_settings()
    
    index = get_index()
    if not index:
        print("Error: Could not retrieve or build Postgres document index.")
        return

    query_engine = index.as_query_engine()

    # Tool 1: Document Search (RAG)
    query_engine_tool = QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name="knowledge_base",
            description="Useful for retrieving information about the documents indexed in the data folder.",
        ),
    )

    # Load refactored standard tools (Calculator, Web Search, File Writer, System Monitor, Directory Explorer)
    tools = [query_engine_tool] + get_all_tools(include_file_writer=True)

    # Hybrid Model Selection (OpenAI Cloud or Ollama Local)
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your-openai-api-key-here":
        print("⚠️ OPENAI_API_KEY not found in .env. Checking local Ollama service...")
        ollama_error = check_ollama()
        if ollama_error:
            print(f"❌ {ollama_error}")
            print("Please configure either a valid OPENAI_API_KEY or start the local Ollama service.")
            return
        print(f"✅ Local Ollama active! Loading model `{OLLAMA_MODEL}`...")
        llm = Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=120.0)
        model_name = f"Ollama Local ({OLLAMA_MODEL})"
    else:
        print("✅ OpenAI API Key loaded. Launching cloud-based execution...")
        llm = OpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
        model_name = "OpenAI Cloud (gpt-4o-mini)"
    
    # Initialize ReAct Agent with the combined tools
    system_prompt = (
        "You are a helpful, expert AI programming and DevOps assistant. You have access to professional local tools for calculations, filesystem exploration, web search, system monitoring, and a local Postgres knowledge base.\n\n"
        "IMPORTANT Formatting Rule:\n"
        "When using tools, you must strictly output:\n"
        "Thought: <your thought>\n"
        "Action: <tool_name>\n"
        "Action Input: <json_args>\n"
        "When giving a final response, you must strictly output:\n"
        "Thought: <your thought>\n"
        "Answer: <your final answer>\n"
        "Always include 'Thought:' first, followed by either 'Action:' and 'Action Input:', or 'Answer:'. Do not use any bolding or markdown code blocks for the Thought/Action/Answer structure."
    )
    agent = ReActAgent(
        tools=tools,
        llm=llm,
        verbose=True,
        system_prompt=system_prompt
    )

    print(f"\n--- CLI Agent is ready! using LLM: {model_name} ---")
    print("Type 'exit' or 'quit' to stop. Ask about system load, workspace files, or RAG concepts!\n")
    
    import asyncio
    
    while True:
        try:
            query = input("You: ")
            if query.lower() in ['exit', 'quit']:
                break
            if not query.strip():
                continue
                
            async def run_query(q):
                handler = agent.run(user_msg=q, max_iterations=10)
                res = await handler
                return res.response.content
                
            response = asyncio.run(run_query(query))
            print(f"\nAgent: {response}\n")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}\n")

if __name__ == "__main__":
    main()

