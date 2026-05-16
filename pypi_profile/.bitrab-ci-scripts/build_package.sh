#!/usr/bin/env bash
set -euo pipefail
source ./.bitrab-ci-scripts/setup.sh
uv run python -c "from pathlib import Path; import shutil; [shutil.rmtree(path) for path in (Path('build'), Path('dist')) if path.exists()]"
uv run python -m build
uv run twine check dist/*
uv run check-wheel-contents dist/*.whl
ls -lh dist/
