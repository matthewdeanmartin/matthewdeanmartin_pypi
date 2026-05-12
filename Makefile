override UV := uv
MAKEFLAGS += --no-print-directory
export PYTHONUTF8 := 1
export PYTHONPATH := $(CURDIR)

.PHONY: sync check check-ci test format lint typecheck help \
        serve-john-doe serve-matthewdeanmartin \
        validate-john-doe validate-matthewdeanmartin \
        inspect-john-doe inspect-matthewdeanmartin \
        init-example doctor dump-john-doe \
        gha-validate gha-pin gha-upgrade zizmor

GHA_WORKFLOWS := .github/workflows

help:
	@echo "Workspace targets (run from repo root):"
	@echo "  sync                    Install all workspace packages and dev deps"
	@echo "  test                    Run tests for all packages"
	@echo "  format                  Format all packages"
	@echo "  lint                    Lint all packages"
	@echo "  typecheck               Type-check all packages"
	@echo "  check                   Full quality gate for all packages"
	@echo "  check-ci                CI quality gate for all packages"
	@echo ""
	@echo "Try it out:"
	@echo "  serve-john-doe          Serve John Doe's example profile  (http://127.0.0.1:8000)"
	@echo "  serve-matthewdeanmartin Serve Matthew Martin's profile    (http://127.0.0.1:8000)"
	@echo "  validate-john-doe       Validate John Doe's profile TOML"
	@echo "  validate-matthewdeanmartin  Validate Matthew Martin's profile TOML"
	@echo "  inspect-john-doe        Inspect John Doe's profile (no code executed)"
	@echo "  inspect-matthewdeanmartin   Inspect Matthew Martin's profile"
	@echo "  dump-john-doe           Dump John Doe's profile as JSON"
	@echo "  init-example            Generate a starter pypi_profile.toml in /tmp"
	@echo "  doctor                  Check that all runtime dependencies are installed"
	@echo "  gha-validate            Validate repository GitHub Actions workflow YAML"
	@echo "  gha-pin                 Update pinned GitHub Actions SHAs in root workflows"
	@echo "  gha-upgrade             Refresh GitHub Actions pins and validate workflows"
	@echo "  zizmor                  Audit repository GitHub Actions workflows"
	@echo ""
	@echo "Per-package: cd <package> && make <target>"

sync:
	@$(UV) sync --all-packages

# ── Try it out ────────────────────────────────────────────────────────────────

serve-john-doe:
	$(UV) run --package pypi-profile pypi-profile serve john_doe/john_doe/pypi_profile.toml

serve-matthewdeanmartin:
	$(UV) run --package pypi-profile pypi-profile serve matthewdeanmartin/matthewdeanmartin/pypi_profile.toml

validate-john-doe:
	$(UV) run --package pypi-profile pypi-profile validate john_doe/john_doe/pypi_profile.toml

validate-matthewdeanmartin:
	$(UV) run --package pypi-profile pypi-profile validate matthewdeanmartin/matthewdeanmartin/pypi_profile.toml

inspect-john-doe:
	$(UV) run --package pypi-profile pypi-profile inspect john_doe/john_doe/pypi_profile.toml

inspect-matthewdeanmartin:
	$(UV) run --package pypi-profile pypi-profile inspect matthewdeanmartin/matthewdeanmartin/pypi_profile.toml

dump-john-doe:
	$(UV) run --package pypi-profile pypi-profile dump john_doe/john_doe/pypi_profile.toml

init-example:
	$(UV) run --package pypi-profile pypi-profile init --username your-username --output /tmp/pypi_profile.toml
	@echo ""
	$(UV) run --package pypi-profile pypi-profile validate /tmp/pypi_profile.toml

doctor:
	$(UV) run --package pypi-profile pypi-profile doctor

test:
	@"$(MAKE)" -C pypi_profile test
	@"$(MAKE)" -C matthewdeanmartin test
	@"$(MAKE)" -C john_doe test

format:
	@"$(MAKE)" -C pypi_profile format
	@"$(MAKE)" -C matthewdeanmartin format
	@"$(MAKE)" -C john_doe format

lint:
	@"$(MAKE)" -C pypi_profile lint
	@"$(MAKE)" -C matthewdeanmartin lint
	@"$(MAKE)" -C john_doe lint

typecheck:
	@"$(MAKE)" -C pypi_profile typecheck
	@"$(MAKE)" -C matthewdeanmartin typecheck
	@"$(MAKE)" -C john_doe typecheck

check:
	@"$(MAKE)" -C pypi_profile check
	@"$(MAKE)" -C matthewdeanmartin check
	@"$(MAKE)" -C john_doe check

check-ci:
	@"$(MAKE)" -C pypi_profile check-ci
	@"$(MAKE)" -C matthewdeanmartin check-ci
	@"$(MAKE)" -C john_doe check-ci

gha-validate:
	@$(UV) run python -c "import pathlib, yaml; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in pathlib.Path('$(GHA_WORKFLOWS)').glob('*.yml')]; print('YAML parse OK')"

gha-pin:
	@$(UV) run python -c "import os, subprocess; \
token=os.environ.get('GITHUB_TOKEN') or subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip(); \
assert token, 'Set GITHUB_TOKEN or run: gh auth login'; \
raise SystemExit(subprocess.run(['gha-update'], env=dict(os.environ, GITHUB_TOKEN=token)).returncode)"

gha-upgrade: gha-pin gha-validate

zizmor:
	@$(UV) run zizmor $(GHA_WORKFLOWS)
