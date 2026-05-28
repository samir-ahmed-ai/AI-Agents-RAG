import os
from dotenv import load_dotenv
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool, ToolMetadata, FunctionTool
from llama_index.llms.openai import OpenAI
from llamaindex_agents.ingestion import get_index
from duckduckgo_search import DDGS

load_dotenv()

def calculate(expression: str) -> str:
    """Evaluates a mathematical expression and returns the result."""
    try:
        # VERY basic and insecure eval just for demonstration of tool usage.
        # In a real app, use a safe math parser.
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

def write_file(filename: str, content: str) -> str:
    """Writes the given content to a file in the AI-Agents root workspace directory."""
    try:
        # Write to the AI-Agents root directory
        workspace_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..")
        filepath = os.path.abspath(os.path.join(workspace_dir, filename))
        
        # Ensure we don't accidentally write outside the workspace
        if not filepath.startswith(os.path.abspath(workspace_dir)):
            return "Error: Cannot write outside the workspace directory."
            
        with open(filepath, "w") as f:
            f.write(content)
        return f"Successfully wrote content to {filename}"
    except Exception as e:
        return f"Error writing file: {e}"

def main():
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your-openai-api-key-here":
        print("Please set your OPENAI_API_KEY in the .env file in the llamaindex-agents directory.")
        return

    print("Initializing LlamaIndex Agent...")
    index = get_index()
    query_engine = index.as_query_engine()

    # Tool 1: Document Search
    query_engine_tool = QueryEngineTool(
        query_engine=query_engine,
        metadata=ToolMetadata(
            name="knowledge_base",
            description="Useful for retrieving information about the documents indexed in the data folder.",
        ),
    )

    # Tool 2: Calculator
    calculator_tool = FunctionTool.from_defaults(fn=calculate)
    
    # Tool 3: Web Search
    web_search_tool = FunctionTool.from_defaults(fn=web_search)
    
    # Tool 4: File Writer
    file_writer_tool = FunctionTool.from_defaults(fn=write_file)

    llm = OpenAI(model="gpt-4o-mini")
    
    # The ReActAgent naturally maintains conversational memory using a chat history buffer
    tools = [query_engine_tool, calculator_tool, web_search_tool, file_writer_tool]
    agent = ReActAgent.from_tools(tools, llm=llm, verbose=True)

    print("\n--- Agent is ready! Type 'exit' or 'quit' to stop ---")
    
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
