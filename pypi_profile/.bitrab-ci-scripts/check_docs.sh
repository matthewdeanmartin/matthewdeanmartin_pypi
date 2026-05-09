#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run interrogate pypi_profile --verbose --fail-under 70
uv run codespell --ignore-words=private_dictionary.txt pypi_profile tests README.md CHANGELOG.md docs || true
uv run pylint --score=n --reports=n --rcfile=.pylintrc_spell pypi_profile || true
