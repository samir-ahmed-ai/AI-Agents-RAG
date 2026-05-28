# LlamaIndex Agents

This project implements a highly modular **Reasoning and Acting (ReAct)** agent using LlamaIndex. It supports two runtimes:
1. A CLI agent running on cloud OpenAI models.
2. An interactive Chainlit web application running on local open-source models with two-stage RAG (retrieval + cross-encoder reranking) and observability tracing.

For detailed design details, component diagrams, and RAG pipelines, see the [Architecture Document](./ARCHITECTURE.md).

---

## Project Structure

The codebase is organized using a clean, separation-of-concerns module layout:
* **`src/llamaindex_agents/config.py`**: Centralized configuration, Postgres database connectivity parameters, and Ollama check utilities.
* **`src/llamaindex_agents/tools.py`**: Consolidation of all agent capabilities (Math Calculator, DuckDuckGo Web Search, File Writer) as standard `FunctionTool` wrappers.
* **`src/llamaindex_agents/ingestion.py`**: Script to process local text assets in `./data/`, build dense vector embeddings, and populate the Postgres database.
* **`src/llamaindex_agents/agent.py`**: Interactive CLI ReAct agent using the cloud OpenAI LLM.
* **`src/llamaindex_agents/app.py`**: Fully local interactive Chainlit Web UI with two-stage RAG, Ollama integrations, and Arize Phoenix tracing.

---

## Setup Instructions

### 1. Configure the Environment
Copy the example environment file and fill in your keys:
```bash
cp .env.example .env
```
Ensure your `.env` contains:
* `OPENAI_API_KEY`: Required for the cloud CLI agent.
* `POSTGRES_USER` / `POSTGRES_PASSWORD`: Postgres access credentials (if using vector store).
* `OLLAMA_MODEL` / `OLLAMA_BASE_URL`: Configuration for local LLM execution.

### 2. Start Services
Ensure Docker or Postgres is running on port `5432` with a database named `linearbits` (or the configured db name).
If using Ollama for local execution, verify it is running and download the model:
```bash
make ollama-start
make ollama-pull
```

---

## Ingesting Documents (RAG Setup)
Place files you want the agent to search into the `./data/` folder (created automatically).
Run the ingestion script to parse, embed, and store vectors into Postgres:
```bash
make ingest
```

---

## Running the Agents

### A. Run CLI Agent (OpenAI Mode)
Launch the lightweight terminal-based agent:
```bash
# From workspace root
PYTHONPATH=llamaindex-agents/src uv run python llamaindex-agents/src/llamaindex_agents/agent.py
```

### B. Run Web UI Agent (Local Mode)
Start the Chainlit app with hot reload:
```bash
make dev
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.

---

## Tracing and Observability
When starting the Chainlit Web UI agent, **Arize Phoenix** tracing launches automatically:
* Open [http://localhost:6006](http://localhost:6006) to view the live tracing dashboard.
* Track reasoning steps, tool calling execution times, token usages, and raw documents retriever scores!
