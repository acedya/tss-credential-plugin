PYTHON       ?= python3
PIP          ?= pip3
PYTEST       ?= pytest
REQUIREMENTS := requirements.txt
SRC_DIR      := credential_plugins
TEST_DIR     := tests

.PHONY: help install test test-verbose lint clean init

help: ## Show this help message
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

init: ## Create __init__.py files and requirements.txt if missing
	@mkdir -p $(SRC_DIR) $(TEST_DIR) credential_type examples
	@touch $(SRC_DIR)/__init__.py $(TEST_DIR)/__init__.py
	@if [ ! -f $(REQUIREMENTS) ]; then \
		echo "requests>=2.28.0" >  $(REQUIREMENTS); \
		echo "pytest>=7.0.0"    >> $(REQUIREMENTS); \
		echo "responses>=0.22"  >> $(REQUIREMENTS); \
		echo "$(REQUIREMENTS) created."; \
	fi
	@echo "Project structure initialized."

install: ## Install Python dependencies from requirements.txt
	$(PIP) install -r $(REQUIREMENTS)

test: install ## Run all unit tests
	$(PYTEST) $(TEST_DIR) -v --tb=short

test-verbose: install ## Run all unit tests with full output
	$(PYTEST) $(TEST_DIR) -v --tb=long -s

test-only: ## Run tests without installing dependencies (faster)
	$(PYTEST) $(TEST_DIR) -v --tb=short

lint: ## Run basic linting with py_compile on all plugin sources
	@echo "Checking syntax..."
	@find $(SRC_DIR) -name '*.py' -exec $(PYTHON) -m py_compile {} +
	@echo "All files OK."

clean: ## Remove caches, bytecode, and test artifacts
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	find . -type f -name '*.pyo' -delete 2>/dev/null || true
	@echo "Cleaned."
