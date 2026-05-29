import os
import psutil
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

def system_monitor() -> str:
    """Monitor local system resources such as CPU and Memory.
    
    Returns a string detailing the current host system's hardware utilization metrics.
    """
    try:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        mem_total_gb = mem.total / (1024 ** 3)
        mem_used_gb = mem.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)
        disk_used_gb = disk.used / (1024 ** 3)
        
        return (
            f"--- Host Machine System Resources ---\n"
            f"🧠 CPU Utilization: {cpu_usage:.1f}%\n"
            f"💾 Memory (RAM): {mem.percent:.1f}% ({mem_used_gb:.2f} GB / {mem_total_gb:.2f} GB)\n"
            f"💽 Disk Space: {disk.percent:.1f}% ({disk_used_gb:.1f} GB / {disk_total_gb:.1f} GB)\n"
            f"-------------------------------------"
        )
    except Exception as e:
        return f"Error monitoring system resources: {e}"

def list_directory(relative_path: str = ".") -> str:
    """Lists files and folders inside the workspace directory.
    
    Args:
        relative_path: The folder to list, relative to the workspace root.
    """
    try:
        target_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, relative_path))
        if not target_path.startswith(os.path.abspath(WORKSPACE_ROOT)):
            return "Error: Cannot explore directories outside the workspace."
            
        if not os.path.exists(target_path):
            return f"Error: Path '{relative_path}' does not exist."
            
        if not os.path.isdir(target_path):
            return f"Error: Path '{relative_path}' is a file, not a directory."
            
        entries = os.listdir(target_path)
        if not entries:
            return f"Directory '{relative_path}' is empty."
            
        results = []
        for entry in sorted(entries):
            full_entry = os.path.join(target_path, entry)
            is_dir = os.path.isdir(full_entry)
            marker = "📁" if is_dir else "📄"
            results.append(f"{marker} {entry}")
            
        return f"Contents of '{relative_path}':\n" + "\n".join(results)
    except Exception as e:
        return f"Error listing directory: {e}"

def read_file(filename: str) -> str:
    """Reads the contents of a text file inside the workspace directory.
    
    Args:
        filename: The path of the file to read, relative to the workspace root.
    """
    try:
        filepath = os.path.abspath(os.path.join(WORKSPACE_ROOT, filename))
        if not filepath.startswith(os.path.abspath(WORKSPACE_ROOT)):
            return "Error: Cannot read files outside the workspace."
            
        if not os.path.exists(filepath):
            return f"Error: File '{filename}' does not exist."
            
        if os.path.isdir(filepath):
            return f"Error: '{filename}' is a directory, not a file."
            
        # Avoid reading massive files at once
        file_size = os.path.getsize(filepath)
        if file_size > 1 * 1024 * 1024:  # 1MB limit for safety
            return "Error: File is too large to read (max 1MB)."
            
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return f"--- Content of {filename} ---\n{content}\n-----------------------------"
    except Exception as e:
        return f"Error reading file: {e}"

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

def get_system_monitor_tool() -> FunctionTool:
    """Returns a LlamaIndex FunctionTool wrapping the system_monitor utility."""
    return FunctionTool.from_defaults(
        fn=system_monitor,
        name="system_monitor",
        description="Useful for monitoring host system resources like CPU and RAM usage to verify machine load."
    )

def get_list_directory_tool() -> FunctionTool:
    """Returns a LlamaIndex FunctionTool wrapping the list_directory utility."""
    return FunctionTool.from_defaults(
        fn=list_directory,
        name="list_directory",
        description="Useful for exploring the files and folders inside the local workspace root."
    )

def get_read_file_tool() -> FunctionTool:
    """Returns a LlamaIndex FunctionTool wrapping the read_file utility."""
    return FunctionTool.from_defaults(
        fn=read_file,
        name="read_file",
        description="Useful for reading text file content inside the workspace root."
    )

def get_all_tools(include_file_writer: bool = True) -> list:
    """Returns a list of all standard tools available to agents.
    
    Args:
        include_file_writer: If True, includes the file writer tool in the list.
    """
    tools = [
        get_calculator_tool(),
        get_web_search_tool(),
        get_system_monitor_tool(),
        get_list_directory_tool(),
        get_read_file_tool()
    ]
    if include_file_writer:
        tools.append(get_file_writer_tool())
    return tools

