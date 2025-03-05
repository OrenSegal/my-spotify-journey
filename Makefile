.PHONY: all install setup run-backend run-streamlit run stop format lint test clean deploy-prep venv help

# --- Variables ---
VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
UV := uv
DATA_DIR := data
DB_PATH := $(DATA_DIR)/spotify_streaming.duckdb
BACKEND_PID_FILE := backend.pid  # File to store backend PID
BACKEND_PORT := 8000

# --- Default target ---
all: install setup run

# --- Create and activate virtual environment ---
venv:
	$(UV) venv $(VENV_DIR)
	@echo "Virtual environment created. Activate with: source $(VENV_DIR)/bin/activate"

# --- Installation ---
install: venv
	$(UV) pip install -e .

# --- Database Setup ---
setup: install
	@if [ ! -d "$(DATA_DIR)" ]; then mkdir -p "$(DATA_DIR)"; fi
	@if [ ! -d "$(DATA_DIR)/Streaming_History" ]; then mkdir -p "$(DATA_DIR)/Streaming_History)"; fi
	@if [ ! -d "$(DATA_DIR)/extra_features" ]; then mkdir -p "$(DATA_DIR)/extra_features"; fi
	$(PYTHON) load_data.py --data-dir $(DATA_DIR) --force-reload
	@rm -f $(DB_PATH).lock

# --- Run Backend (FastAPI) ---
run-backend:
	@if lsof -i :$(BACKEND_PORT) > /dev/null; then \
		echo "Port $(BACKEND_PORT) is already in use. Attempting to free it..."; \
		lsof -ti :$(BACKEND_PORT) | xargs kill -9 2>/dev/null || true; \
		sleep 1; \
	fi
	@if [ -f "$(BACKEND_PID_FILE)" ]; then \
		if ps -p $$(cat $(BACKEND_PID_FILE)) > /dev/null; then \
			echo "Stopping existing backend process..."; \
			kill -9 $$(cat $(BACKEND_PID_FILE)) 2>/dev/null || true; \
		fi; \
		rm -f $(BACKEND_PID_FILE); \
	fi
	$(PYTHON) -m uvicorn backend.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) --root-path / &
	echo $$! > $(BACKEND_PID_FILE)
	@echo "Backend started with PID: $$(cat $(BACKEND_PID_FILE))"
	@sleep 2

# --- Stop Backend ---
stop-backend:
	@if [ -f "$(BACKEND_PID_FILE)" ]; then \
		if ps -p $$(cat $(BACKEND_PID_FILE)) > /dev/null; then \
			kill $$(cat $(BACKEND_PID_FILE)); \
			echo "Backend stopped (PID: $$(cat $(BACKEND_PID_FILE)))."; \
		else \
			echo "Backend not running."; \
		fi; \
		rm -f $(BACKEND_PID_FILE); \
	else \
		echo "Backend PID file not found. Backend may not be running."; \
	fi

# --- Run Streamlit ---
run-streamlit:
	streamlit run dashboard/streamlit_app.py

# --- Run Both (Backend and Streamlit) ---
run:
	@echo "Starting backend..."
	make run-backend
	@echo "Starting Streamlit..."
	streamlit run dashboard/streamlit_app.py &
	STREAMLIT_PID=$$!
	@echo "Streamlit started with PID: $$STREAMLIT_PID"

	trap "kill $$STREAMLIT_PID; exit" INT TERM

	wait

# --- Formatting (using Black) ---
format:
	$(PYTHON) -m black .

# --- Linting (using Ruff) ---
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format . --check

# --- Testing (using pytest) ---
test:
	$(PYTHON) -m pytest

# --- Cleaning ---
clean:
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -f $(DB_PATH).lock
	rm -f $(BACKEND_PID_FILE)  # Clean up the PID file

# --- Deployment Preparation ---
deploy-prep:
	@echo "Preparing for deployment..."
	$(UV) pip freeze > requirements.txt

# --- Help ---
help:
	@echo "Available targets:"
	@sed -n 's/^([a-zA-Z0-9_-]*):.*#\s*\(.*\)/\1\t\2/p' < $(MAKEFILE_LIST)