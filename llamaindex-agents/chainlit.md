# 🧠 Local AI Workspace Agent

Welcome to the **World-Class Local AI Agent** workspace! This interface hooks directly into your locally running **Ollama** models and combines them with a high-fidelity local **Postgres Vector Store** + **BGE-Reranking** pipeline to deliver private, secure, and blazing-fast AI interactions.

---

### 🏠 Monorepo Central Control Dashboard

> [!IMPORTANT]
> A dedicated **Interactive Systems Landing Page & Central Dashboard Hub** is running in the background!
> 👉 **Open Dashboard Hub**: **[http://localhost:3000](http://localhost:3000)**
> Use this central visual workspace to interactively map out monorepo components (LlamaIndex, Ollama, CrewAI, LangGraph), view live query visualizers, test terminal diagnostics, and navigate all documentation.

---

### 🚀 Premium Core Capabilities

*   ⚡ **Full Streaming**: Responsive token-by-token generation with exact real-time latency and speed metrics.
*   🔍 **Two-Stage Postgres RAG**: Searches Postgres (`PGVectorStore`) and performs cross-encoder reranking (`FlagEmbeddingReranker`) locally.
*   📥 **Dynamic Ingestion**: Simply upload/drag `.pdf`, `.docx`, `.md`, or `.txt` documents into the chat input, and they are indexed instantly in the vector store!
*   👁️ **Multimodal Vision**: Upload images (PNG/JPEG) and they are routed dynamically to vision models like `llava` or `llama3.2-vision`.
*   🛠️ **Local Agent Tools**: The agent can inspect system resources (`system_monitor`), search the web (`web_search`), perform math (`calculator`), explore folders (`list_directory`), and read files (`read_file`).
*   📊 **Arize Phoenix Observability**: Live tracing, timing, and score tracking for all retrievals, LLM queries, and tool calls.

---

### ⚙️ Developer Quickstart & Tips

> [!TIP]
> **Open Chat Settings (bottom left)** to switch between Ollama models, adjust temperature, customize the system prompt, or fine-tune RAG variables in real-time!

#### 📥 Automatic Model Downloads
If you select a model in Chat Settings that you haven't downloaded yet (e.g. `gemma2` or `mistral`), the agent will **automatically stream the download** directly in the chat with a gorgeous live-updating progress bar!

#### 🔎 Live Observability
Every execution is tracked and visualized in **Arize Phoenix**.
*   **Phoenix Dashboard**: 👉 [http://localhost:6006](http://localhost:6006)

---

### 📚 Need Help?
For a comprehensive end-to-end setup guide, check out the [Local AI Agent Runbook](file:///Users/ahmedgmail/Documents/workspace-1/personal/AI-Agents/RUNBOOK.md) at the root of the workspace. It contains instructions for Docker, Ollama, model pulling, Postgres database setup, and advanced DevOps debugging.

Happy hacking! 💻🤖✨
