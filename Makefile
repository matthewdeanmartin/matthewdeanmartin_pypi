.PHONY: help init install dev run run-json run-markdown run-version run-module run-entry run-entry-json build check-wheel lint test check clean publish

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

init: ## Create venv and install in editable mode
	uv venv
	uv pip install -e .

install: ## Install the package into venv
	uv pip install .

dev: ## Install in editable/dev mode
	uv pip install -e .

run: ## Run the CLI (formatted profile)
	uv run python -m matthewdeanmartin

run-json: ## Run the CLI (raw JSON output)
	uv run python -m matthewdeanmartin --json

run-markdown: ## Run the CLI (markdown output)
	uv run python -m matthewdeanmartin --markdown

run-version: ## Show package version
	uv run python -m matthewdeanmartin --version

run-module: ## Run via direct Python import
	uv run python -c "from matthewdeanmartin.__main__ import main; main()"

run-entry: dev ## Run via installed entry point script
	uv run matthewdeanmartin

run-entry-json: dev ## Run installed entry point with --json
	uv run matthewdeanmartin --json

build: ## Build sdist and wheel
	uv build

publish: build ## Build package distributions for publication

check-wheel: build ## Build and list wheel contents
	uv run python -c "import zipfile, glob; z=zipfile.ZipFile(glob.glob('dist/*.whl')[-1]); [print(n) for n in z.namelist()]"

lint: ## Run ruff check and format check
	uv run ruff check matthewdeanmartin/
	uv run ruff format --check matthewdeanmartin/

test: ## Run tests
	uv run pytest --cov=matthewdeanmartin

check: lint test ## Run all checks (lint + tests)

clean: ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info matthewdeanmartin/*.egg-info
