#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run interrogate john_doe --verbose --fail-under 70
uv run codespell --ignore-words=private_dictionary.txt john_doe tests README.md CHANGELOG.md docs || true
uv run pylint --score=n --reports=n --rcfile=.pylintrc_spell john_doe || true
