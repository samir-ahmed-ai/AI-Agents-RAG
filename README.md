# AI Agents

A monorepo for exploring different AI agent frameworks with a shared Python workspace.

## Projects

| Directory | Framework |
|-----------|-----------|
| `llamaindex-agents` | LlamaIndex + Chainlit RAG agent |
| `langgraph-agents` | LangGraph |
| `crewai-agents` | CrewAI |
| `shared` | Shared utilities |

## Setup

```bash
uv sync
cp llamaindex-agents/.env.example llamaindex-agents/.env  # add your keys locally
make dev
```

See `make help` for Ollama, ingestion, and other commands.
