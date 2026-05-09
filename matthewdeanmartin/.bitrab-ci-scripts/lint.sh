#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run isort --check-only matthewdeanmartin tests
uv run black --check matthewdeanmartin tests
uv run ruff check --quiet matthewdeanmartin tests
uv run pylint --score=n --reports=n --rcfile=.pylintrc matthewdeanmartin
uv run pylint --score=n --reports=n --rcfile=.pylintrc_tests tests
