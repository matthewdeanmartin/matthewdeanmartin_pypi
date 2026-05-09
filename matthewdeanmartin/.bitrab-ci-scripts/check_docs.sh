#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run interrogate matthewdeanmartin --verbose --fail-under 70
uv run codespell --ignore-words=private_dictionary.txt matthewdeanmartin tests README.md CHANGELOG.md docs || true
uv run pylint --score=n --reports=n --rcfile=.pylintrc_spell matthewdeanmartin || true
