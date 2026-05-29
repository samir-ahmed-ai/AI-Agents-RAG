.PHONY: start stop postgres-check ollama-check help dev ingest install ollama-install ollama-start ollama-pull crewai-run langgraph-run

.DEFAULT_GOAL := start

LLAMAINDEX_DIR := llamaindex-agents
PYTHONPATH := src
APP := src/llamaindex_agents/app.py
INGEST := src/llamaindex_agents/ingestion.py
OLLAMA_MODEL ?= llama3.1

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

start: postgres-check ollama-check ## [RECOMMENDED] Start all services (Postgres, Ollama, Landing Hub, LlamaIndex Web, CrewAI) in background
	@echo "========================================================================"
	@echo "   🔥 BOOTING ALL LOCAL MONOREPO AGENTS & COOPERATIVE SERVICES 🔥"
	@echo "========================================================================"
	@echo ""
	@echo "🏠 Checking Central Landing Page Server status..."
	@.venv/bin/python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1); s.connect(('127.0.0.1', 3000))" >/dev/null 2>&1 && ( \
		echo "  [Landing Hub] Central Landing Page is already running on port 3000." \
	) || ( \
		echo "  [Landing Hub] Starting Local Server in background (logging to 'landing.log')..." && \
		.venv/bin/python server.py 3000 > landing.log 2>&1 & \
		sleep 1 \
	)
	@echo "  👉 CENTRAL DASHBOARD HUB: http://localhost:3000"
	@echo ""
	@echo "🖥️  Checking LlamaIndex Web UI status..."
	@.venv/bin/python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1); s.connect(('127.0.0.1', 8000))" >/dev/null 2>&1 && ( \
		echo "  [LlamaIndex] Web UI is already running on port 8000." \
	) || ( \
		echo "  [LlamaIndex] Starting Web Server in the background (logging to 'chainlit.log')..." && \
		cd $(LLAMAINDEX_DIR) && PYTHONPATH=$(PYTHONPATH) ../.venv/bin/chainlit run $(APP) > ../chainlit.log 2>&1 & \
		sleep 1 \
	)
	@echo "  👉 LlamaIndex Web UI is available at: http://localhost:8000"
	@echo ""
	@echo "🔍 Checking Arize Phoenix Telemetry..."
	@.venv/bin/python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(1); s.connect(('127.0.0.1', 6006))" >/dev/null 2>&1 && ( \
		echo "  [Phoenix] Telemetry is already active on port 6006." \
	) || ( \
		echo "  [Phoenix] Telemetry starting up (integrated with Web UI)..." \
	)
	@echo "  👉 Arize Phoenix Dashboard is available at: http://localhost:6006"
	@echo ""
	@echo "👥 Checking CrewAI Codebase Auditor status..."
	@ps aux | grep -v grep | grep "crewai-agents/main.py" >/dev/null 2>&1 && ( \
		echo "  [CrewAI] Collaborative Codebase Auditor is already running." \
	) || ( \
		echo "  [CrewAI] Starting Multi-Agent Auditor in background (logging to 'crewai.log')..." && \
		PYTHONPATH=crewai-agents/src .venv/bin/python crewai-agents/main.py > crewai.log 2>&1 & \
		echo "  👉 CrewAI is auditing the codebase. Result will be in: 'code_audit_report.md'" \
	)
	@echo ""
	@echo "========================================================================"
	@echo "   ✅ All background services are up. Open the dashboard to begin."
	@echo "========================================================================"
	@echo "  🏠 Landing Hub:     http://localhost:3000"
	@echo "  🖥️  LlamaIndex UI:   http://localhost:8000"
	@echo "  🔍 Phoenix:         http://localhost:6006"
	@echo "  👥 CrewAI audit:    code_audit_report.md (see crewai.log)"
	@echo ""
	@echo "  🕸️  LangGraph CLI:  run \`make langgraph-run\` for interactive mode"
	@echo "  🛑 Stop everything: \`make stop\`"
	@echo "========================================================================"

stop: ## Stop all background running agents and servers (Landing Server, Chainlit, Phoenix, CrewAI)
	@echo "🛑 Stopping all local agent background services..."
	@(pkill -f "server.py 3000" || pkill -f "http.server 3000") && echo "  ✅ Stopped Central Landing Page / HTTP server." || echo "  ℹ️  Landing Page server is not running."
	@pkill -f "chainlit run" && echo "  ✅ Stopped LlamaIndex Web UI / Chainlit server." || echo "  ℹ️  LlamaIndex Web UI is not running."
	@pkill -f "crewai-agents/main.py" && echo "  ✅ Stopped CrewAI Auditor." || echo "  ℹ️  CrewAI Auditor is not running."
	@pkill -f "langgraph-agents/main.py" && echo "  ✅ Stopped LangGraph Agent." || echo "  ℹ️  LangGraph Agent is not running."
	@echo "✅ All background services stopped."

postgres-check: ## Verify local Postgres is accepting connections, otherwise auto-starts Docker container
	@echo "🔍 Checking PostgreSQL connection..."
	@pg_isready -h localhost -p 5432 >/dev/null 2>&1 || ( \
		echo "⚠️ Local Postgres is not running. Attempting Docker auto-start..." && \
		docker start local-postgres >/dev/null 2>&1 || true \
	)
	@pg_isready -h localhost -p 5432 >/dev/null 2>&1 || ( \
		echo "❌ Postgres is not running on localhost:5432. Please start Postgres before running." && exit 1 \
	)
	@echo "✅ PostgreSQL is active!"

ollama-check: ## Verify local Ollama is active, otherwise auto-starts service and pulls model
	@echo "🔍 Checking Ollama service..."
	@curl -sf http://127.0.0.1:11434/api/tags >/dev/null || ( \
		echo "⚠️ Ollama service is not running. Attempting brew auto-start..." && \
		brew services start ollama && \
		sleep 3 \
	)
	@curl -sf http://127.0.0.1:11434/api/tags >/dev/null || ( \
		echo "❌ Failed to start Ollama automatically. Please open the Ollama client application." && exit 1 \
	)
	@ollama list | grep -q "$(OLLAMA_MODEL)" || ( \
		echo "📥 Model $(OLLAMA_MODEL) is missing. Automatically downloading..." && \
		ollama pull $(OLLAMA_MODEL) \
	)
	@echo "✅ Ollama is active and loaded with model '$(OLLAMA_MODEL)'!"

dev: ## Run Chainlit app with hot reload directly
	cd $(LLAMAINDEX_DIR) && PYTHONPATH=$(PYTHONPATH) ../.venv/bin/chainlit run $(APP) -w

ingest: ## Ingest documents into the Postgres vector store
	cd $(LLAMAINDEX_DIR) && PYTHONPATH=$(PYTHONPATH) ../.venv/bin/python $(INGEST)

crewai-run: ## Run the local CrewAI collaborative multi-agent execution
	PYTHONPATH=crewai-agents/src .venv/bin/python crewai-agents/main.py

langgraph-run: ## Run the stateful local LangGraph agent execution
	PYTHONPATH=langgraph-agents/src .venv/bin/python langgraph-agents/main.py

install: ## Install workspace dependencies
	.venv/bin/uv sync --all-packages

ollama-install: ## Install Ollama via Homebrew
	brew install ollama

ollama-start: ## Start the Ollama background service
	brew services start ollama

ollama-pull: ## Download the default Ollama model
	ollama pull $(OLLAMA_MODEL)
