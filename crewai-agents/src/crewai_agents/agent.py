import os
import urllib.request
import json
import psutil
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from shared.utils import hello_shared

# Monorepo Workspace configuration
PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(PACKAGE_ROOT, "..", "..", ".."))

# Ollama local parameters
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

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
# 🚀 Collaborative Execution Runner (Robust Hybrid Design)
# =========================================================================

def run_crew():
    """Starts the CrewAI multi-agent cooperative workflow using local Ollama."""
    print("========================================================================")
    print("👥 STARTING LOCAL CREWAI MULTI-AGENT COLLABORATION")
    print(f"🔗 Shared library check: {hello_shared()}")
    print("========================================================================")

    if not check_ollama_active():
        print(f"❌ Error: Ollama service is not running on {OLLAMA_BASE_URL}.")
        print("Run `make ollama-start` and try again.")
        return

    # 1. Gather Real Codebase & System Context in Python (100% Reliable!)
    print("📂 Gathering workspace files & diagnostics via Python...")
    
    # List Directory
    llamaindex_dir = os.path.join(WORKSPACE_ROOT, "llamaindex-agents/src/llamaindex_agents")
    try:
        if os.path.exists(llamaindex_dir):
            files = os.listdir(llamaindex_dir)
            files_list = "\n".join([f"📁 llamaindex_agents/{f}" if os.path.isdir(os.path.join(llamaindex_dir, f)) else f"📄 llamaindex_agents/{f}" for f in sorted(files)])
        else:
            files_list = "llamaindex-agents module folder not found."
    except Exception as e:
        files_list = f"Error listing directory: {e}"
        
    # Read config.py
    config_path = os.path.join(WORKSPACE_ROOT, "llamaindex-agents/src/llamaindex_agents/config.py")
    try:
        with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
            config_code = f.read()
    except Exception as e:
        config_code = f"Error reading config.py: {e}"
        
    # Read tools.py
    tools_path = os.path.join(WORKSPACE_ROOT, "llamaindex-agents/src/llamaindex_agents/tools.py")
    try:
        with open(tools_path, "r", encoding="utf-8", errors="ignore") as f:
            tools_code = f.read()
    except Exception as e:
        tools_code = f"Error reading tools.py: {e}"
        
    # Query Host System Resource Metrics
    try:
        cpu = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        mem_used = mem.used / (1024 ** 3)
        mem_total = mem.total / (1024 ** 3)
        hardware_info = (
            f"🧠 CPU Utilization: {cpu:.1f}%\n"
            f"💾 Memory (RAM): {mem.percent:.1f}% ({mem_used:.2f} GB / {mem_total:.2f} GB)"
        )
    except Exception as e:
        hardware_info = f"Error querying hardware metrics: {e}"

    print("✅ Context gathered successfully! Injecting parameters into agent prompts...")

    # 2. Initialize local LLM wrapper in CrewAI
    print(f"🤖 Configuring local LLM: ollama/{OLLAMA_MODEL}...")
    local_llm = LLM(
        model=f"ollama/{OLLAMA_MODEL}",
        base_url=OLLAMA_BASE_URL,
        temperature=0.2
    )

    # 3. Define CrewAI Collaborative Agents
    print("👥 Creating Agents...")
    
    developer_agent = Agent(
        role="Senior Software Explorer",
        goal="Structure the gathered codebase contents and host diagnostics into a comprehensive developer transcript.",
        backstory=(
            "You are a highly efficient software systems explorer. You organize code directories, "
            "file layouts, source code components, and hardware telemetry into a structured, highly clean markdown transcript."
        ),
        llm=local_llm,
        verbose=True
    )

    auditor_agent = Agent(
        role="Lead Technical Auditor & Code Reviewer",
        goal="Audit the code implementations, review safety parameters, and draft a finalized Code Review and Audit Report.",
        backstory=(
            "You are an elite codebase auditor and security reviewer. You analyze Python code structures, "
            "assess security boundary checks, verify clean separations of concerns, and write beautifully detailed technical review documents."
        ),
        llm=local_llm,
        verbose=True
    )

    # 4. Define Collaborative Tasks with Dynamic Context Injection
    print("📝 Mapping Tasks...")
    
    exploration_task = Task(
        description=(
            "You have been provided with the following real-time data gathered directly from the local workspace:\n\n"
            "=== WORKSPACE FILES ===\n"
            f"{files_list}\n\n"
            "=== CONFIG.PY IMPLEMENTATION ===\n"
            f"```python\n{config_code}\n```\n\n"
            "=== TOOLS.PY IMPLEMENTATION ===\n"
            f"```python\n{tools_code}\n```\n\n"
            "=== HOST SYSTEM TELEMETRY ===\n"
            f"{hardware_info}\n\n"
            "Your Task: Organize this information into a beautifully structured, highly readable Markdown Developer Transcript. "
            "Clearly list the files discovered, present the code implementations, and display the hardware loads."
        ),
        expected_output="A clean, structured markdown developer transcript containing files layout, source code sheets, and system resource loads.",
        agent=developer_agent
    )

    audit_task = Task(
        description=(
            "Analyze the structured Markdown Developer Transcript compiled by the Senior Software Explorer.\n"
            "Conduct a thorough code audit of the config.py and tools.py implementations, focusing on:\n"
            "1. **Architecture Quality**: Separation of configuration, tools, and UI layers.\n"
            "2. **Security Boundaries**: Safe file path validation checks (preventing directory traversal out of the workspace).\n"
            "3. **Local Tooling**: Checking system resource monitors, web searches, and calculators.\n"
            "4. **Recommendations**: Suggestions for optimization and premium expansions.\n\n"
            "Create a beautifully detailed, comprehensive **Code Review & Audit Report** markdown document based on these dimensions."
        ),
        expected_output="The full markdown content of the generated codebase review and audit report.",
        output_file="code_audit_report.md",
        agent=auditor_agent
    )

    # 5. Assemble the Crew
    print("🚀 Assembling Collaborative Crew...")
    crew = Crew(
        agents=[developer_agent, auditor_agent],
        tasks=[exploration_task, audit_task],
        process=Process.sequential,
        verbose=True
    )

    # 6. Kickoff local inference
    print("\n⚡ Kicking off local execution (Sequential Multi-Agent flow)...")
    result = crew.kickoff()
    
    print("\n========================================================================")
    print("🟢 CREWAI COLLABORATIVE WORKFLOW COMPLETED SUCCESSFULLY!")
    print("📝 Code Audit Report saved as 'code_audit_report.md' in the workspace root.")
    print("========================================================================")
    return result

if __name__ == "__main__":
    run_crew()
