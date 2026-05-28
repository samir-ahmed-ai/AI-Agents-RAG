from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.llms.openai import OpenAI
from llamaindex_agents.config import OPENAI_API_KEY, init_global_settings
from llamaindex_agents.tools import get_all_tools
from llamaindex_agents.ingestion import get_index

def main():
    """Starts the CLI-based LlamaIndex ReAct agent using OpenAI LLM and local Postgres vector store RAG."""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your-openai-api-key-here":
        print("Please set your OPENAI_API_KEY in the .env file in the llamaindex-agents directory.")
        return

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

    # Load refactored standard tools (Calculator, Web Search, File Writer)
    tools = [query_engine_tool] + get_all_tools(include_file_writer=True)

    # Initialize cloud LLM (GPT-4o-Mini)
    llm = OpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
    
    # Initialize ReAct Agent with the combined tools
    agent = ReActAgent.from_tools(tools, llm=llm, verbose=True)

    print("\n--- CLI Agent is ready! Type 'exit' or 'quit' to stop ---")
    
    while True:
        try:
            query = input("\nYou: ")
            if query.lower() in ['exit', 'quit']:
                break
            if not query.strip():
                continue
                
            response = agent.chat(query)
            print(f"\nAgent: {response}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
