override UV := uv
MAKEFLAGS += --no-print-directory
export PYTHONUTF8 := 1

PACKAGE := john_doe
TOML    := john_doe/pypi_profile.toml
ABOUT_FILE := john_doe/__about__.py

.PHONY: \
	sync pre-commit-install \
	fix \
	init update \
	serve inspect validate dump doctor \
	format format-python format-check format-check-python \
	lint lint-check typecheck security \
	test test-ci \
	metadata metadata-check \
	publish-check publish \
	check check-ci help

help:
	@echo "john-doe profile package — targets:"
	@echo ""
	@echo "  Profile management:"
	@echo "    init          Re-run the interactive wizard to create/update pypi_profile.toml"
	@echo "    update        Re-fetch live PyPI/GitHub data and merge into pypi_profile.toml"
	@echo "    serve         Serve the profile website locally (http://127.0.0.1:8000)"
	@echo "    inspect       Inspect the profile (no code executed)"
	@echo "    validate      Validate pypi_profile.toml against the schema"
	@echo "    dump          Dump profile as JSON (for debugging)"
	@echo "    doctor        Check that all runtime dependencies are installed"
	@echo ""
	@echo "  Development:"
	@echo "    sync          Install all dependencies"
	@echo "    format        Auto-format Python source"
	@echo "    format-check  Check Python formatting"
	@echo "    lint          Lint Python source"
	@echo "    typecheck     Type-check with mypy"
	@echo "    security      Run bandit security scan"
	@echo "    test          Run tests"
	@echo "    test-ci       Run tests (CI mode, parallel)"
	@echo "    check         Full local quality gate"
	@echo "    check-ci      CI quality gate"
	@echo ""
	@echo "  Publishing:"
	@echo "    metadata      Regenerate $(ABOUT_FILE) from pyproject.toml"
	@echo "    publish-check Build wheel/sdist and list artifacts"
	@echo "    publish       Publish to PyPI"

# ── Setup ─────────────────────────────────────────────────────────────────────

sync:
	@$(UV) sync

pre-commit-install:
	@$(UV) run pre-commit install

# ── Profile management ────────────────────────────────────────────────────────

init:
	@$(UV) run --package pypi-profile pypi-profile init \
		--username john_doe \
		--output $(TOML) \
		--force
	@"$(MAKE)" validate

update:
	@$(UV) run --package pypi-profile pypi-profile init \
		--username john_doe \
		--output $(TOML) \
		--force \
		--fetch
	@"$(MAKE)" validate

serve:
	@$(UV) run --package pypi-profile pypi-profile serve $(TOML)

inspect:
	@$(UV) run --package pypi-profile pypi-profile inspect $(TOML)

validate:
	@$(UV) run --package pypi-profile pypi-profile validate $(TOML)

dump:
	@$(UV) run --package pypi-profile pypi-profile dump $(TOML)

doctor:
	@$(UV) run --package pypi-profile pypi-profile doctor

# ── Code quality ──────────────────────────────────────────────────────────────

fix: format-python

format: format-python

format-python:
	@$(UV) run isort --settings-path pyproject.toml $(PACKAGE) tests
	@$(UV) run black --config pyproject.toml $(PACKAGE) tests
	@$(UV) run ruff check --fix --quiet --config pyproject.toml $(PACKAGE) tests
	@$(UV) run black --config pyproject.toml $(PACKAGE) tests

format-check: format-check-python

format-check-python:
	@$(UV) run isort --settings-path pyproject.toml --check-only $(PACKAGE) tests
	@$(UV) run black --config pyproject.toml --check $(PACKAGE) tests
	@$(UV) run ruff check --quiet --config pyproject.toml $(PACKAGE) tests

lint: lint-check

lint-check:
	@$(UV) run ruff check --quiet --config pyproject.toml $(PACKAGE) tests

typecheck:
	@$(UV) run mypy --hide-error-context $(PACKAGE) tests

security:
	@$(UV) run bandit -q -c pyproject.toml -r $(PACKAGE)

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	@$(UV) run pytest -q \
		--cov=$(PACKAGE) \
		--cov-report=html \
		--junitxml=junit.xml \
		--timeout=60

test-ci:
	@$(UV) run pytest -q \
		--cov=$(PACKAGE) \
		--cov-report=xml \
		--junitxml=junit.xml \
		--timeout=60

# ── Metadata & publishing ─────────────────────────────────────────────────────

metadata:
	@$(UV) run metametameta pep621 --name $(PACKAGE) --source pyproject.toml --output $(ABOUT_FILE)

metadata-check:
	@$(UV) run metametameta sync-check --output $(ABOUT_FILE)

publish-check:
	@$(UV) build
	@ls -lh dist/

publish:
	@$(UV) publish

# ── Gates ─────────────────────────────────────────────────────────────────────

check: format-check lint-check security test typecheck validate
	@echo "All checks passed."

check-ci: format-check lint-check security test-ci typecheck validate
	@echo "CI checks passed."
