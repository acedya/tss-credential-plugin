# ──────────────────────────────────────────────────────────────
# Delinea Secret Server — AAP/AWX Credential Plugin
# ──────────────────────────────────────────────────────────────

VENV_DIR      ?= .venv
PYTHON        ?= python3
VENV_PYTHON   := $(VENV_DIR)/bin/python
VENV_PIP      := $(VENV_DIR)/bin/pip
PYTEST        := $(VENV_DIR)/bin/pytest
BLACK         := $(VENV_DIR)/bin/black
ISORT         := $(VENV_DIR)/bin/isort
FLAKE8        := $(VENV_DIR)/bin/flake8
MYPY          := $(VENV_DIR)/bin/mypy
TWINE         := $(VENV_DIR)/bin/twine
RELEASE_SCRIPT := scripts/release.sh
SRC_DIR       := credential_plugins
TEST_DIR      := tests

.PHONY: help init venv install install-dev format lint test test-ci test-verbose test-only build release-check publish-testpypi-token publish-pypi-token release-tag ci clean

# ── Default target ────────────────────────────────────────────
help: ## Show this help message
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Project initialisation ───────────────────────────────────
init: ## Create __init__.py files and requirements.txt if missing
	@mkdir -p $(SRC_DIR) $(TEST_DIR) examples
	@touch $(SRC_DIR)/__init__.py $(TEST_DIR)/__init__.py
	@echo "Project structure initialised."

# ── Virtual environment ──────────────────────────────────────
venv: ## Create local virtual environment and upgrade pip
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip

# ── Dependency installation ──────────────────────────────────
install: venv ## Install runtime package in editable mode
	$(VENV_PIP) install -e .

install-dev: venv ## Install package with development dependencies
	$(VENV_PIP) install -e ".[dev]"
	$(VENV_PIP) install build twine

# ── Formatting / quality ─────────────────────────────────────
format: install-dev ## Auto-format source and tests (black + isort)
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	$(ISORT) $(SRC_DIR) $(TEST_DIR)

# ── Testing ──────────────────────────────────────────────────
test: install-dev ## Run all unit tests
	$(PYTEST) $(TEST_DIR) -v --tb=short

test-ci: install-dev ## Run CI-equivalent tests with coverage XML
	$(PYTEST) $(TEST_DIR) -v --tb=short --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=xml

test-verbose: install-dev ## Run all unit tests with full output
	$(PYTEST) $(TEST_DIR) -v --tb=long -s

test-only: ## Run tests without installing dependencies (faster)
	$(PYTEST) $(TEST_DIR) -v --tb=short

# ── Code quality ─────────────────────────────────────────────
lint: install-dev ## Run CI-equivalent lint checks
	$(BLACK) --check $(SRC_DIR) $(TEST_DIR)
	$(ISORT) --check-only $(SRC_DIR) $(TEST_DIR)
	$(FLAKE8) $(SRC_DIR) $(TEST_DIR) --max-line-length=100
	$(MYPY) $(SRC_DIR) --ignore-missing-imports
	@echo "Checking syntax..."
	@find $(SRC_DIR) -name '*.py' -exec $(VENV_PYTHON) -m py_compile {} +
	@echo "All files OK."

# ── Packaging ────────────────────────────────────────────────
build: install-dev ## Build source and wheel distributions
	$(VENV_PYTHON) -m build

release-check: build ## Verify built artifacts are valid for publishing
	$(TWINE) check dist/*

publish-testpypi-token: release-check ## Publish with token-based auth (local/manual fallback)
	@if [ -z "$(TEST_PYPI_API_TOKEN)" ]; then echo "TEST_PYPI_API_TOKEN is required"; exit 1; fi
	$(TWINE) upload --repository-url https://test.pypi.org/legacy/ -u __token__ -p $(TEST_PYPI_API_TOKEN) --skip-existing dist/*

publish-pypi-token: release-check ## Publish with token-based auth (local/manual fallback)
	@if [ -z "$(PYPI_API_TOKEN)" ]; then echo "PYPI_API_TOKEN is required"; exit 1; fi
	$(TWINE) upload -u __token__ -p $(PYPI_API_TOKEN) --skip-existing dist/*

release-tag: ## Create a validated release tag (usage: make release-tag TAG=v0.2.1 PUSH=1)
	@if [ -z "$(TAG)" ]; then echo "TAG is required (example: TAG=v0.2.1)"; exit 1; fi
	@bash $(RELEASE_SCRIPT) --tag $(TAG) $(if $(PUSH),--push,)

ci: lint test-ci build ## Reproduce CI workflow locally
	@echo "CI-equivalent checks completed successfully."

# ── Cleanup ──────────────────────────────────────────────────
clean: ## Remove caches, bytecode, and test artifacts
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	find . -type f -name '*.pyo' -delete 2>/dev/null || true
	rm -rf build dist *.egg-info
	@echo "Cleaned."