UV ?= uv
MAKEFLAGS += --no-print-directory
export PYTHONUTF8 := 1

PACKAGE := matthewdeanmartin
PYTHON_TARGETS := matthewdeanmartin tests
PYLINT_MAIN_TARGETS := matthewdeanmartin
PYLINT_TEST_TARGETS := tests
MARKDOWN_TARGETS := $(wildcard README.md CHANGELOG.md AGENTS.md docs)
YAML_TARGETS := $(wildcard mkdocs.yml .readthedocs.yaml .github/dependabot.yml)
GHA_WORKFLOWS := .github/workflows
ABOUT_FILE := matthewdeanmartin/__about__.py
AUDIT_IGNORE := PYSEC-2022-42969

.PHONY: \
	sync pre-commit-install \
	format format-python format-yaml format-markdown \
	format-check format-check-python format-check-yaml format-check-markdown \
	lint lint-check ruff-fix ruff-check pylint pylint-tests pylint-spelling \
	spell \
	docs-check docs-check-docstrings docs-check-links docs-check-pydoctest griffe \
	build-docs \
	dead-code vulture deadcode \
	explore refurb crosshair deptry import-linter \
	security bandit audit \
	smoke test test-ci tox \
	typecheck typecheck-mypy \
	metadata metadata-check version-check dev-status \
	gha-validate gha-pin gha-upgrade publish-gha \
	prerelease publish-check publish \
	check check-ci help

help:
	@echo "Package: $(PACKAGE)"
	@echo "Targets: sync format format-check lint lint-check spell test test-ci tox"
	@echo "         typecheck security docs-check build-docs dead-code explore"
	@echo "         metadata metadata-check version-check dev-status"
	@echo "         gha-validate gha-pin gha-upgrade publish-gha"
	@echo "         check check-ci prerelease publish-check publish"

sync:
	@$(UV) sync

pre-commit-install:
	@$(UV) run pre-commit install

format: format-python format-yaml format-markdown

format-python:
	@$(UV) run isort $(PYTHON_TARGETS)
	@$(UV) run black $(PYTHON_TARGETS)
	@$(UV) run ruff check --fix --quiet $(PYTHON_TARGETS)
	@$(UV) run black $(PYTHON_TARGETS)

format-yaml:
	@if [ -n "$(strip $(YAML_TARGETS))" ]; then "$(UV)" run yamlfix $(YAML_TARGETS); fi

format-markdown:
	@if [ -n "$(strip $(MARKDOWN_TARGETS))" ]; then "$(UV)" run mdformat $(MARKDOWN_TARGETS); fi

format-check: format-check-python format-check-yaml format-check-markdown

format-check-python:
	@$(UV) run isort --check-only $(PYTHON_TARGETS)
	@$(UV) run black --check $(PYTHON_TARGETS)
	@$(UV) run ruff check --quiet $(PYTHON_TARGETS)

format-check-yaml:
	@if [ -n "$(strip $(YAML_TARGETS))" ]; then "$(UV)" run yamlfix --check $(YAML_TARGETS); fi

format-check-markdown:
	@if [ -n "$(strip $(MARKDOWN_TARGETS))" ]; then "$(UV)" run mdformat --check $(MARKDOWN_TARGETS); fi

lint: ruff-fix pylint pylint-tests

lint-check: ruff-check pylint pylint-tests

ruff-fix:
	@$(UV) run ruff check --fix --quiet $(PYTHON_TARGETS)

ruff-check:
	@$(UV) run ruff check --quiet $(PYTHON_TARGETS)

pylint:
	@$(UV) run pylint --score=n --reports=n --rcfile=.pylintrc $(PYLINT_MAIN_TARGETS)

pylint-tests:
	@$(UV) run pylint --score=n --reports=n --rcfile=.pylintrc_tests $(PYLINT_TEST_TARGETS)

pylint-spelling:
	@$(UV) run pylint --score=n --reports=n --rcfile=.pylintrc_spell $(PYLINT_MAIN_TARGETS)

spell: pylint-spelling
	@$(UV) run codespell --ignore-words=private_dictionary.txt \
		$(PACKAGE) tests README.md CHANGELOG.md AGENTS.md docs

docs-check: docs-check-docstrings docs-check-pydoctest docs-check-links

docs-check-docstrings:
	@$(UV) run interrogate $(PACKAGE) --verbose --fail-under 70

docs-check-pydoctest:
	@$(UV) run pydoctest --config .pydoctest.json \
		| grep -v "__init__" | grep -v "__main__" | grep -v "Unable to parse" || true

docs-check-links:
	@$(UV) run linkcheckMarkdown README.md || true
	@$(UV) run mdformat --check README.md CHANGELOG.md docs/*.md || true

griffe:
	@echo "=== griffe API surface check (advisory) ==="
	@$(UV) run griffe check $(PACKAGE) || true

build-docs:
	@$(UV) run mkdocs build

dead-code: vulture deadcode

vulture:
	@echo "=== vulture (advisory) ==="
	@$(UV) run vulture $(PACKAGE) --min-confidence 80 || true

deadcode:
	@echo "=== deadcode (advisory) ==="
	@$(UV) run deadcode $(PACKAGE) || true

explore: refurb crosshair deptry import-linter

refurb:
	@echo "=== refurb (advisory) ==="
	@$(UV) run refurb $(PACKAGE) || true

crosshair:
	@echo "=== crosshair (advisory) ==="
	@$(UV) run crosshair check $(PACKAGE) || true

deptry:
	@echo "=== deptry (advisory) ==="
	@$(UV) run deptry . || true

import-linter:
	@echo "=== import-linter (advisory) ==="
	@$(UV) run lint-imports || true

security: bandit audit

bandit:
	@$(UV) run bandit -q -c pyproject.toml -r $(PACKAGE)

audit:
	@echo "=== uv audit ==="
	@$(UV) audit --ignore-until-fixed $(AUDIT_IGNORE)
	@echo "=== pip-audit ==="
	@$(UV) run pip-audit --ignore-vuln $(AUDIT_IGNORE)

smoke:
	@$(UV) run bash scripts/basic_checks.sh

test:
	@$(UV) run pytest -q \
		--cov=$(PACKAGE) \
		--cov-report=html \
		--junitxml=junit.xml \
		--timeout=60

test-ci:
	@$(UV) run pytest -q -n auto --dist=loadfile \
		--cov=$(PACKAGE) \
		--cov-report=xml \
		--junitxml=junit.xml \
		--timeout=60

tox:
	@$(UV) run tox

typecheck: typecheck-mypy

typecheck-mypy:
	@$(UV) run mypy --hide-error-context $(PACKAGE) tests

metadata:
	@$(UV) run metametameta pep621 --name $(PACKAGE) --source pyproject.toml --output $(ABOUT_FILE)

metadata-check:
	@$(UV) run metametameta sync-check --output $(ABOUT_FILE)

version-check:
	@$(UV) run jiggle_version check

dev-status:
	@$(UV) run troml-dev-status validate .

gha-validate:
	@$(UV) run python -c "import pathlib, yaml; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in pathlib.Path('$(GHA_WORKFLOWS)').glob('*.yml')]; print('YAML parse OK')"

gha-pin:
	@$(UV) run python -c "import os, subprocess; \
token=os.environ.get('GITHUB_TOKEN') or subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip(); \
assert token, 'Set GITHUB_TOKEN or run: gh auth login'; \
raise SystemExit(subprocess.run(['gha-update'], env=dict(os.environ, GITHUB_TOKEN=token)).returncode)"

gha-upgrade: gha-pin gha-validate

publish-gha:
	gh workflow run publish_matthewdeanmartin.yml --ref main

publish-check:
	@$(UV) build
	@ls -lh dist/

publish:
	@$(UV) publish

check: format-check lint-check security test typecheck metadata-check version-check
	@echo "All checks passed."

check-ci: format-check lint-check security test-ci typecheck metadata-check version-check
	@echo "CI checks passed."

prerelease: check dev-status docs-check smoke spell publish-check
	@echo "Pre-release checks complete — ready to publish."
