#!/usr/bin/env bash
# Smoke test: exercises the installed console entry point and verifies help/version render cleanly.

set -ou pipefail

PASS=0
FAIL=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${PACKAGE_DIR}/.." && pwd)"
CLI=(uv run pypi-profile)
SCRIPT=(uv run python "${REPO_ROOT}/scripts/delete_failed_github_actions.py")

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "  PASS: $desc"
        ((PASS++))
    else
        echo "  FAIL: $desc  (cmd: $*)"
        ((FAIL++))
    fi
}

check_fails() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "  FAIL: $desc  (expected non-zero exit, got 0)"
        ((FAIL++))
    else
        echo "  PASS: $desc"
        ((PASS++))
    fi
}

echo "=== pypi_profile basic_checks ==="
echo ""
printf 'using:'
printf ' %q' "${CLI[@]}"
echo
echo ""

echo "--- global flags ---"
check "pypi-profile --help" "${CLI[@]}" --help
check "pypi-profile --version" "${CLI[@]}" --version

echo "--- subcommand help ---"
for command in \
    serve validate init inspect doctor fetch-claims fetch dump keygen sign verify \
    update-proofs build find-profiles gui key-info key-list key-rotate key-recover \
    key-export key-import
do
    check "pypi-profile ${command} --help" "${CLI[@]}" "${command}" --help
done

echo "--- standalone script ---"
check "delete_failed_github_actions.py --help" "${SCRIPT[@]}" --help
check "delete_failed_github_actions.py --version" "${SCRIPT[@]}" --version

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
