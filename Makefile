.PHONY: install lint format typecheck test check clean

## Setup
install:  ## Install dependencies
	uv sync

## Code Quality
lint:  ## Run linter
	uv run ruff check .

format:  ## Format code and fix auto-fixable lint issues
	uv run ruff format .
	uv run ruff check --fix .

typecheck:  ## Run type checker
	uv run ty

test:  ## Run test suite
	uv run pytest

check: lint typecheck test  ## Run all quality gates (lint + typecheck + test)

## Cleanup
clean:  ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

## Help
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
