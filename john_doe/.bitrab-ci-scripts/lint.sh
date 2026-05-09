#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run isort --check-only john_doe tests
uv run black --check john_doe tests
uv run ruff check --quiet john_doe tests
uv run pylint --score=n --reports=n --rcfile=.pylintrc john_doe
uv run pylint --score=n --reports=n --rcfile=.pylintrc_tests tests
