#!/usr/bin/env bash
# Smoke test: exercise --dry-run across the CLI and fail if any command exits non-zero.

set -uo pipefail

PASS=0
FAIL=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${PACKAGE_DIR}/.." && pwd)"
WORK_DIR="$(mktemp -d)"
LOG_FILE="${WORK_DIR}/tests_dry_run.log"

cleanup() {
    rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

CLI=(uv run pypi-profile)
SCRIPT=(uv run python "${REPO_ROOT}/scripts/delete_failed_github_actions.py")
EXAMPLE_PROFILE="${REPO_ROOT}/john_doe/john_doe/pypi_profile.toml"
JSON_RESUME="${REPO_ROOT}/john_doe/resume.json"
INIT_DEST="${WORK_DIR}/generated-pypi_profile.toml"
BUILD_DEST="${WORK_DIR}/site"
KEY_DIR="${WORK_DIR}/keys"
EXPORT_DEST="${WORK_DIR}/exported-minisign.key"
IMPORT_SOURCE="${WORK_DIR}/imported-minisign.key"

run_case() {
    local desc="$1"
    shift
    local case_log="${WORK_DIR}/case_$((PASS + FAIL)).log"

    {
        echo "=== ${desc} ==="
        printf 'CMD:'
        printf ' %q' "$@"
        printf '\n'
    } >> "${LOG_FILE}"

    "$@" > "${case_log}" 2>&1
    local status=$?

    cat "${case_log}" >> "${LOG_FILE}"
    {
        echo
        echo "EXIT: ${status}"
        echo
    } >> "${LOG_FILE}"

    if [ "${status}" -eq 0 ]; then
        echo "  PASS: ${desc}"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: ${desc} (exit ${status})"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== pypi-profile dry-run smoke checks ==="
echo "repository: ${REPO_ROOT}"
echo

run_case "global help" "${CLI[@]}" --help
run_case "global version" "${CLI[@]}" --version
for command in \
    serve validate init inspect doctor fetch-claims fetch dump keygen sign verify \
    update-proofs build find-profiles gui key-info key-list key-rotate key-recover \
    key-export key-import
do
    run_case "${command} help" "${CLI[@]}" "${command}" --help
done
run_case "script help" "${SCRIPT[@]}" --help
run_case "script version" "${SCRIPT[@]}" --version
run_case "serve dry-run" "${CLI[@]}" serve --dry-run "${EXAMPLE_PROFILE}" --host 0.0.0.0 --port 8010
run_case "validate dry-run" "${CLI[@]}" validate --dry-run "${EXAMPLE_PROFILE}"
run_case \
    "init dry-run basic" \
    "${CLI[@]}" init --dry-run --no-interactive --username dryrun-user --kind individual --output "${INIT_DEST}"
run_case \
    "init dry-run with import and fetch" \
    "${CLI[@]}" init --dry-run --no-interactive --from-json-resume "${JSON_RESUME}" --fetch --output "${INIT_DEST}"
run_case "inspect dry-run" "${CLI[@]}" inspect --dry-run "${EXAMPLE_PROFILE}"
run_case "doctor dry-run" "${CLI[@]}" doctor --dry-run
run_case "fetch-claims dry-run json" "${CLI[@]}" fetch-claims --dry-run "${EXAMPLE_PROFILE}" --json
run_case "fetch dry-run json" "${CLI[@]}" fetch --dry-run "${EXAMPLE_PROFILE}" --json
run_case "dump dry-run" "${CLI[@]}" dump --dry-run "${EXAMPLE_PROFILE}"
run_case \
    "keygen dry-run" \
    "${CLI[@]}" keygen --dry-run --key-dir "${KEY_DIR}" --keyring-identity smoke-test --force
run_case "key-info dry-run" "${CLI[@]}" key-info --dry-run
run_case "key-list dry-run" "${CLI[@]}" key-list --dry-run
run_case \
    "sign dry-run compact" \
    "${CLI[@]}" sign --dry-run controls-url "${EXAMPLE_PROFILE}" --url "https://example.com/proof" --compact
run_case \
    "verify dry-run" \
    "${CLI[@]}" verify --dry-run "${EXAMPLE_PROFILE}" --profile-package pypi-profile-john-doe
run_case \
    "key-rotate dry-run force" \
    "${CLI[@]}" key-rotate --dry-run "${EXAMPLE_PROFILE}" --profile-package pypi-profile-john-doe --force
run_case \
    "key-recover dry-run" \
    "${CLI[@]}" key-recover --dry-run "${EXAMPLE_PROFILE}" --profile-package pypi-profile-john-doe
run_case \
    "key-export dry-run" \
    "${CLI[@]}" key-export --dry-run --output "${EXPORT_DEST}"
run_case \
    "key-import dry-run force" \
    "${CLI[@]}" key-import --dry-run "${IMPORT_SOURCE}" --key-dir "${KEY_DIR}" --force
run_case \
    "update-proofs dry-run force" \
    "${CLI[@]}" update-proofs --dry-run "${EXAMPLE_PROFILE}" --profile-package pypi-profile-john-doe --force
run_case \
    "build dry-run" \
    "${CLI[@]}" build --dry-run "${EXAMPLE_PROFILE}" --output "${BUILD_DEST}" --base-url /demo --resume-file "${JSON_RESUME}"
run_case "find-profiles dry-run" "${CLI[@]}" find-profiles --dry-run "${REPO_ROOT}"
run_case "gui dry-run" "${CLI[@]}" gui --dry-run

echo
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="

if [ "${FAIL}" -gt 0 ]; then
    echo
    echo "--- Aggregated command output ---"
    cat "${LOG_FILE}"
    exit 1
fi
