.PHONY: help setup dev run test lint docker-build docker-up docker-down docker-test clean

PYTHON ?= python3
VENV ?= venv
VENV_BIN ?= $(VENV)/bin

help: ## Display available developer commands
	@echo "🌸 Cheeku AI Voice OS - Developer Workflow Commands"
	@echo "================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Create virtual environment and install all dependencies
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -r requirements.txt
	@echo "✅ Setup complete. Run 'source $(VENV)/bin/activate' to activate."

dev: ## Launch local development server with auto-reload and browser
	$(VENV_BIN)/python run.py

run: ## Launch server using launch script
	./run.sh

test: ## Run complete automated test suite
	$(VENV_BIN)/pytest -v

lint: ## Run flake8 syntax and static analysis checks
	$(VENV_BIN)/flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv,.venv,demo

docker-build: ## Build Docker container image
	docker build -t cheeku-voice-os .

docker-up: ## Start containerized Cheeku stack via Docker Compose
	docker compose up --build -d
	@echo "🚀 Cheeku is running at http://localhost:8000"

docker-down: ## Stop containerized Cheeku stack
	docker compose down

docker-test: ## Execute test suite inside Docker container
	docker compose run --rm cheeku-test

docker-logs: ## View real-time container logs
	docker compose logs -f cheeku

clean: ## Clean cached python files and test artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov

