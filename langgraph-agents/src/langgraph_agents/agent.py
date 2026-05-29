import os
import getpass
import time
import urllib.request
import urllib.error
import json
import psutil
from typing import Annotated, TypedDict, Sequence, Literal
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from shared.utils import hello_shared

# Load environment variables
PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
for parent_lvl in [os.path.dirname(PACKAGE_ROOT), os.path.dirname(os.path.dirname(PACKAGE_ROOT)), os.path.dirname(os.path.dirname(os.path.dirname(PACKAGE_ROOT)))]:
    env_path = os.path.join(parent_lvl, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        break
else:
    load_dotenv()

# Monorepo workspace configuration
WORKSPACE_ROOT = os.path.abspath(os.path.join(PACKAGE_ROOT, "..", "..", ".."))

# Ollama local configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def check_ollama_active() -> bool:
    """Helper to check if Ollama background daemon is reachable."""
    try:
        url = f"{OLLAMA_BASE_URL}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False

# =========================================================================
# 🛠️ Safe & High-Quality Local Agent Tools
# =========================================================================

@tool
def calculate(expression: str) -> str:
    """Evaluates a mathematical expression and returns the result.
    
    Args:
        expression: A string containing a mathematical expression to evaluate (e.g. "2 + 2 * 10").
    """
    try:
        # Evaluates safely using isolated dict
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"

@tool
def web_search(query: str) -> str:
    """Searches the web for the given query and returns a summary of results.
    
    Args:
        query: The search query string.
    """
    try:
        from duckduckgo_search import DDGS
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

@tool
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

@tool
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

@tool
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
            
        file_size = os.path.getsize(filepath)
        if file_size > 1 * 1024 * 1024:  # 1MB limit for safety
            return "Error: File is too large to read (max 1MB)."
            
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return f"--- Content of {filename} ---\n{content}\n-----------------------------"
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(filename: str, content: str) -> str:
    """Writes the given content to a file in the AI-Agents root workspace directory.
    
    Args:
        filename: The name of the file to write to.
        content: The text content to write into the file.
    """
    try:
        filepath = os.path.abspath(os.path.join(WORKSPACE_ROOT, filename))
        
        # Ensure path boundaries
        if not filepath.startswith(os.path.abspath(WORKSPACE_ROOT)):
            return "Error: Cannot write outside the workspace directory."
            
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote content to {filename}"
    except Exception as e:
        return f"Error writing file: {e}"

# Map of available tools for execution
TOOLS = {
    "calculate": calculate,
    "web_search": web_search,
    "system_monitor": system_monitor,
    "list_directory": list_directory,
    "read_file": read_file,
    "write_file": write_file
}

# =========================================================================
# 🔄 Stateful Graph Definition
# =========================================================================

class AgentState(TypedDict):
    """The state representation of our graph agent."""
    messages: Annotated[list[BaseMessage], add_messages]
    steps_count: int
    current_tool: str
    active_model: str

# 1. Model Node
def call_model(state: AgentState):
    """Invokes the active model with current messages."""
    messages = state["messages"]
    active_model = state["active_model"]
    steps = state.get("steps_count", 0)
    
    # Prepend standard system prompt if not present
    has_system = any(isinstance(m, SystemMessage) for m in messages)
    if not has_system:
        system_prompt = (
            "You are a premium, stateful LangGraph local coding and DevOps partner. "
            "You have access to powerful local tools: calculate, web_search, system_monitor, "
            "list_directory, read_file, and write_file. "
            "Provide elegant, accurate responses. Always use tools to verify directories or file contents "
            "when asked about the workspace structure."
        )
        messages = [SystemMessage(content=system_prompt)] + messages

    # Set up LLM with bound tools
    if "OpenAI" in active_model:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    else:
        # Default local Ollama
        llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.2)
        
    llm_with_tools = llm.bind_tools(list(TOOLS.values()))
    
    print(f"  [Node: agent] Running active model: {active_model}...")
    response = llm_with_tools.invoke(messages)
    
    return {
        "messages": [response],
        "steps_count": steps + 1
    }

# 2. Tool Execution Node
def execute_tools(state: AgentState):
    """Executes tool calls generated by the LLM."""
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_outputs = []
    current_tool_name = "none"
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            call_id = tool_call["id"]
            
            print(f"  [Node: tools] Executing tool: '{name}' with arguments: {args}")
            current_tool_name = name
            
            if name in TOOLS:
                tool_func = TOOLS[name]
                try:
                    # Invoke tool function
                    result = tool_func.invoke(args)
                except Exception as e:
                    result = f"Error executing tool: {e}"
            else:
                result = f"Error: Tool '{name}' is not supported."
                
            # Create a ToolMessage to append to state
            tool_outputs.append(ToolMessage(content=str(result), tool_call_id=call_id, name=name))
            
    return {
        "messages": tool_outputs,
        "current_tool": current_tool_name
    }

# 3. Conditional Edge Routing
def should_continue(state: AgentState) -> Literal["continue", "end"]:
    """Checks whether the agent should execute a tool or stop."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the LLM made tool calls, we continue to the tools node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
        
    # Otherwise, we stop and present the final answer to the user
    return "end"

# Build and compile graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", execute_tools)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END
    }
)
workflow.add_edge("tools", "agent")
graph = workflow.compile()

# =========================================================================
# 🚀 Interactive Terminal Loop
# =========================================================================

def run_agent():
    """Starts the CLI-based LangGraph interactive stateful agent."""
    print("========================================================================")
    print("🕸️ STARTING LOCAL LANGGRAPH STATEFUL AGENT WORKSPACE")
    print(f"🔗 Shared library check: {hello_shared()}")
    print("========================================================================")
    
    active_model = f"Ollama Local ({OLLAMA_MODEL})"
    
    if not check_ollama_active():
        print(f"⚠️ Warning: Local Ollama service is not running on {OLLAMA_BASE_URL}.")
        if OPENAI_API_KEY:
            print("✅ OpenAI API Key found. Falling back to Cloud-based OpenAI (gpt-4o-mini).")
            active_model = "OpenAI Cloud (gpt-4o-mini)"
        else:
            print("❌ Error: No local Ollama service and no OPENAI_API_KEY detected.")
            print("Please run `make ollama-start` and `make ollama-pull` or set OPENAI_API_KEY.")
            return
    else:
        print(f"✅ Local Ollama active! Using model: `{OLLAMA_MODEL}`")
        
    print("\n🕸️ Stateful Graph Compiled successfully!")
    print(f"🤖 Active Model: {active_model}")
    print("Type 'exit' or 'quit' to stop. Ask about system load, list workspace files, or do math!\n")
    
    # Maintain user chat history in Python state
    chat_history = []
    
    while True:
        try:
            query = input("\nYou: ")
            if query.lower() in ["exit", "quit"]:
                break
            if not query.strip():
                continue
                
            # Construct start state
            user_message = HumanMessage(content=query)
            chat_history.append(user_message)
            
            initial_state = {
                "messages": chat_history,
                "steps_count": 0,
                "current_tool": "none",
                "active_model": active_model
            }
            
            print("\n🔄 [Graph State: Start Pipeline]")
            start_time = time.time()
            
            # Execute stateful graph invocation
            final_state = graph.invoke(initial_state)
            
            duration = time.time() - start_time
            print("🔄 [Graph State: End Pipeline]")
            
            # Extract final response
            final_messages = final_state["messages"]
            # Find the last AIMessage
            ai_responses = [m for m in final_messages if isinstance(m, AIMessage)]
            
            if ai_responses:
                response = ai_responses[-1].content
                # Update our overall chat history
                chat_history = final_messages
                
                print(f"\nAgent: {response}")
                print(f"\n⚡ Telemetry: Latency: {duration:.2f}s | Steps Taken: {final_state['steps_count']} | Last Tool: {final_state['current_tool']}")
            else:
                print("\nAgent: I encountered an issue generating a response.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    run_agent()
