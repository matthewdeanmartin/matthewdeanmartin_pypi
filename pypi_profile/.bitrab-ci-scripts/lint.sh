#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run isort --check-only pypi_profile tests
uv run black --check pypi_profile tests
uv run ruff check --quiet pypi_profile tests
uv run pylint --score=n --reports=n --rcfile=.pylintrc pypi_profile
uv run pylint --score=n --reports=n --rcfile=.pylintrc_tests tests
