.PHONY: help dev ingest install ollama-install ollama-start ollama-pull ollama-check

LLAMAINDEX_DIR := llamaindex-agents
PYTHONPATH := src
APP := src/llamaindex_agents/app.py
INGEST := src/llamaindex_agents/ingestion.py
OLLAMA_MODEL ?= llama3.1

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

dev: ## Run Chainlit app with hot reload
	cd $(LLAMAINDEX_DIR) && PYTHONPATH=$(PYTHONPATH) uv run chainlit run $(APP) -w

ingest: ## Ingest documents into the Postgres vector store
	cd $(LLAMAINDEX_DIR) && PYTHONPATH=$(PYTHONPATH) uv run python $(INGEST)

install: ## Install workspace dependencies
	uv sync

ollama-install: ## Install Ollama via Homebrew
	brew install ollama

ollama-start: ## Start the Ollama background service
	brew services start ollama

ollama-pull: ## Download the default Ollama model
	ollama pull $(OLLAMA_MODEL)

ollama-check: ## Verify Ollama is running and the model is available
	@curl -sf http://127.0.0.1:11434/api/tags >/dev/null || (echo "Ollama is not running. Run: make ollama-start" && exit 1)
	@ollama show $(OLLAMA_MODEL) >/dev/null 2>&1 || (echo "Model $(OLLAMA_MODEL) is missing. Run: make ollama-pull" && exit 1)
	@echo "Ollama is ready with model $(OLLAMA_MODEL)"
