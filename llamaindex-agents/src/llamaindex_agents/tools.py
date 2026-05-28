import os
from duckduckgo_search import DDGS
from llama_index.core.tools import FunctionTool
from llamaindex_agents.config import WORKSPACE_ROOT

def calculate(expression: str) -> str:
    """Evaluates a mathematical expression and returns the result.
    
    Args:
        expression: A string containing a mathematical expression to evaluate (e.g. "2 + 2 * 10").
    """
    try:
        # Basic eval just for demonstration of tool usage.
        # In a production app, use a safe math parser.
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"

def web_search(query: str) -> str:
    """Searches the web for the given query and returns a summary of results.
    
    Args:
        query: The search query string.
    """
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
    """Writes the given content to a file in the AI-Agents root workspace directory.
    
    Args:
        filename: The name of the file to write to.
        content: The text content to write into the file.
    """
    try:
        filepath = os.path.abspath(os.path.join(WORKSPACE_ROOT, filename))
        
        # Ensure we don't accidentally write outside the workspace
        if not filepath.startswith(os.path.abspath(WORKSPACE_ROOT)):
            return "Error: Cannot write outside the workspace directory."
            
        with open(filepath, "w") as f:
            f.write(content)
        return f"Successfully wrote content to {filename}"
    except Exception as e:
        return f"Error writing file: {e}"

def get_calculator_tool() -> FunctionTool:
    """Returns a LlamaIndex FunctionTool wrapping the calculate utility."""
    return FunctionTool.from_defaults(
        fn=calculate,
        name="calculator",
        description="Useful for evaluating mathematical expressions and arithmetic calculations."
    )

def get_web_search_tool() -> FunctionTool:
    """Returns a LlamaIndex FunctionTool wrapping the web_search utility."""
    return FunctionTool.from_defaults(
        fn=web_search,
        name="web_search",
        description="Useful for searching the web for real-time information or questions you don't know the answer to."
    )

def get_file_writer_tool() -> FunctionTool:
    """Returns a LlamaIndex FunctionTool wrapping the write_file utility."""
    return FunctionTool.from_defaults(
        fn=write_file,
        name="file_writer",
        description="Useful for writing text content or agent reports into a file in the root workspace."
    )

def get_all_tools(include_file_writer: bool = True) -> list:
    """Returns a list of all standard tools available to agents.
    
    Args:
        include_file_writer: If True, includes the file writer tool in the list.
    """
    tools = [
        get_calculator_tool(),
        get_web_search_tool()
    ]
    if include_file_writer:
        tools.append(get_file_writer_tool())
    return tools
