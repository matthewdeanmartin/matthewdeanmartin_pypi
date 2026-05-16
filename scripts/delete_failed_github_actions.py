r"""Delete failed GitHub Actions workflow runs or logs for a repository.

This script is intentionally standalone and only depends on the GitHub CLI
(`gh`) plus the Python standard library.

Examples:
    uv run python .\scripts\delete_failed_github_actions.py
    uv run python .\scripts\delete_failed_github_actions.py --execute
    uv run python .\scripts\delete_failed_github_actions.py --repo owner/repo --execute
    uv run python .\scripts\delete_failed_github_actions.py --mode logs --execute
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ENV_FILE = Path(r"C:\github\.env")
FAILED_CONCLUSIONS = {"failure"}
SCRIPT_VERSION = "0.1.0"
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_PARTIAL = 4


@dataclass(frozen=True)
class WorkflowRun:
    """A minimal view of a GitHub Actions workflow run."""

    id: int
    name: str
    display_title: str
    conclusion: str | None
    status: str | None
    html_url: str
    head_branch: str | None
    event: str | None
    created_at: str | None

    @classmethod
    def from_api(cls, payload: dict[str, object]) -> WorkflowRun:
        """Build a workflow run from the GitHub API payload."""
        return cls(
            id=int(payload["id"]),
            name=str(payload.get("name") or "<unknown>"),
            display_title=str(payload.get("display_title") or "<untitled>"),
            conclusion=_optional_str(payload.get("conclusion")),
            status=_optional_str(payload.get("status")),
            html_url=str(payload.get("html_url") or ""),
            head_branch=_optional_str(payload.get("head_branch")),
            event=_optional_str(payload.get("event")),
            created_at=_optional_str(payload.get("created_at")),
        )


def _optional_str(value: object) -> str | None:
    """Return a string value when present."""
    if value is None:
        return None
    return str(value)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="delete_failed_github_actions.py",
        description=(
            "Delete failed GitHub Actions workflow runs for the current repo. "
            "By default this is a dry run; add --execute to actually delete."
        )
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {SCRIPT_VERSION}")
    parser.add_argument(
        "--repo",
        help="Repository in owner/repo form. Defaults to the current git remote.",
    )
    parser.add_argument(
        "--mode",
        choices=("runs", "logs"),
        default="runs",
        help=(
            "Delete whole failed workflow runs (default) or only their logs. "
            "Deleting runs removes the failed entries from the Actions history."
        ),
    )
    parser.add_argument(
        "--branch",
        help="Only target workflow runs for this branch.",
    )
    parser.add_argument(
        "--event",
        help="Only target workflow runs for this event, for example push or pull_request.",
    )
    parser.add_argument(
        "--conclusion",
        action="append",
        dest="conclusions",
        help=("Workflow conclusion to target. Repeat to include more than one. " "Defaults to: failure"),
    )
    parser.add_argument(
        "--max-delete",
        type=int,
        default=None,
        help="Maximum number of matching runs to delete.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=rf"Optional .env file to load auth from. Default: {DEFAULT_ENV_FILE}",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform deletions. Without this flag the script only prints what it would delete.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON to stdout instead of human-oriented text.",
    )
    return parser.parse_args(argv)


def load_env_file(path: Path) -> dict[str, str]:
    """Load simple KEY=VALUE pairs from a .env file."""
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            loaded[key] = value
    return loaded


def has_gh_auth(env: dict[str, str]) -> bool:
    """Return True when gh already has usable authentication."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def build_gh_env(env_file: Path) -> dict[str, str]:
    """Create the environment used for gh commands."""
    env = os.environ.copy()
    if has_gh_auth(env):
        return env

    dotenv_values = load_env_file(env_file)
    if "GH_TOKEN" not in env:
        for key in (
            "GH_TOKEN",
            "GITHUB_TOKEN",
            "GH_KEY",
            "GITHUB_KEY",
            "GH",
            "GITHUB",
            "gh",
            "github",
        ):
            if key in dotenv_values:
                env["GH_TOKEN"] = dotenv_values[key]
                break
    if "GITHUB_TOKEN" not in env and "GH_TOKEN" in env:
        env["GITHUB_TOKEN"] = env["GH_TOKEN"]

    return env


def run_gh(args: Sequence[str], env: dict[str, str]) -> str:
    """Run a gh command and return stdout."""
    try:
        result = subprocess.run(
            ["gh", *args],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("The GitHub CLI ('gh') was not found on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()
        detail = stderr or stdout or str(exc)
        raise RuntimeError(f"gh {' '.join(args)} failed: {detail}") from exc
    return result.stdout


def resolve_repo(explicit_repo: str | None) -> str:
    """Resolve the repository from --repo or the current git remote."""
    if explicit_repo:
        return explicit_repo

    try:
        result = subprocess.run(
            ["git", "--no-pager", "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Could not read git remote 'origin'. Pass --repo owner/repo explicitly.") from exc
    remote = result.stdout.strip()

    patterns = [
        r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, remote)
        if match:
            owner = match.group("owner")
            repo = match.group("repo")
            return f"{owner}/{repo}"

    raise RuntimeError("Could not infer owner/repo from the current git remote. Pass --repo owner/repo explicitly.")


def iter_workflow_runs(
    repo: str,
    env: dict[str, str],
    branch: str | None,
    event: str | None,
) -> Iterable[WorkflowRun]:
    """Yield workflow runs for the repository."""
    owner, repo_name = repo.split("/", 1)
    page = 1

    while True:
        args = [
            "api",
            "-X",
            "GET",
            f"repos/{owner}/{repo_name}/actions/runs",
            "-f",
            "per_page=100",
            "-f",
            f"page={page}",
        ]
        if branch:
            args.extend(["-f", f"branch={branch}"])
        if event:
            args.extend(["-f", f"event={event}"])

        response = json.loads(run_gh(args, env))
        runs = response.get("workflow_runs", [])
        if not runs:
            return

        for run_payload in runs:
            if isinstance(run_payload, dict):
                yield WorkflowRun.from_api(run_payload)

        page += 1


def filter_runs(
    runs: Iterable[WorkflowRun],
    conclusions: set[str],
    max_delete: int | None,
) -> list[WorkflowRun]:
    """Filter workflow runs down to the requested conclusions."""
    matched = [run for run in runs if (run.conclusion or "").lower() in conclusions]
    if max_delete is not None:
        return matched[:max_delete]
    return matched


def delete_run(repo: str, run_id: int, env: dict[str, str], mode: str) -> None:
    """Delete a workflow run or just its logs."""
    owner, repo_name = repo.split("/", 1)
    if mode == "logs":
        endpoint = f"repos/{owner}/{repo_name}/actions/runs/{run_id}/logs"
    else:
        endpoint = f"repos/{owner}/{repo_name}/actions/runs/{run_id}"
    run_gh(["api", "-X", "DELETE", endpoint], env)


def render_run(run: WorkflowRun) -> str:
    """Render a single workflow run for terminal output."""
    created = run.created_at or "unknown-date"
    branch = run.head_branch or "unknown-branch"
    return f"- {run.id} | {created} | {run.name} | {run.display_title} | " f"{branch} | {run.conclusion or 'unknown'}"


def run_to_dict(run: WorkflowRun) -> dict[str, object]:
    """Convert a workflow run to a JSON-serializable dict."""
    return {
        "id": run.id,
        "name": run.name,
        "display_title": run.display_title,
        "conclusion": run.conclusion,
        "status": run.status,
        "html_url": run.html_url,
        "head_branch": run.head_branch,
        "event": run.event,
        "created_at": run.created_at,
    }


def main(argv: Sequence[str]) -> int:
    """Run the script."""
    try:
        args = parse_args(argv)
        env = build_gh_env(args.env_file)
        repo = resolve_repo(args.repo)
        conclusions = {value.lower() for value in (args.conclusions or FAILED_CONCLUSIONS)}

        runs = filter_runs(
            iter_workflow_runs(repo=repo, env=env, branch=args.branch, event=args.event),
            conclusions=conclusions,
            max_delete=args.max_delete,
        )
        run_payload = [run_to_dict(run) for run in runs]

        if not runs:
            if args.json:
                print(
                    json.dumps(
                        {
                            "repo": repo,
                            "mode": args.mode,
                            "execute": args.execute,
                            "matched_runs": [],
                            "deleted_count": 0,
                            "failures": [],
                        },
                        indent=2,
                    )
                )
                return EXIT_OK
            print(f"No matching workflow runs found in {repo}.")
            return EXIT_OK

        if not args.json:
            print(f"Found {len(runs)} matching workflow runs in {repo}.\n")
            for run in runs:
                print(render_run(run))

        if not args.execute:
            if args.json:
                print(
                    json.dumps(
                        {
                            "repo": repo,
                            "mode": args.mode,
                            "execute": False,
                            "matched_runs": run_payload,
                            "deleted_count": 0,
                            "failures": [],
                        },
                        indent=2,
                    )
                )
                return EXIT_OK
            action = "delete logs for" if args.mode == "logs" else "delete"
            print(f"\nDry run only. Re-run with --execute to {action} these workflow runs.")
            return EXIT_OK

        failures: list[tuple[int, str]] = []
        deleted = 0
        for run in runs:
            try:
                delete_run(repo=repo, run_id=run.id, env=env, mode=args.mode)
                deleted += 1
                if not args.json:
                    print(f"Deleted {run.id}")
            except RuntimeError as exc:
                failures.append((run.id, str(exc)))
                print(f"FAILED {run.id}: {exc}", file=sys.stderr)

        if args.json:
            print(
                json.dumps(
                    {
                        "repo": repo,
                        "mode": args.mode,
                        "execute": True,
                        "matched_runs": run_payload,
                        "deleted_count": deleted,
                        "failures": [{"run_id": run_id, "error": message} for run_id, message in failures],
                    },
                    indent=2,
                )
            )
        elif args.mode == "runs":
            print(f"\nDeleted {deleted} workflow runs.")
        else:
            print(f"\nDeleted logs for {deleted} workflow runs.")
        if failures:
            if not args.json:
                print(f"{len(failures)} deletions failed.", file=sys.stderr)
            return EXIT_PARTIAL
        return EXIT_OK
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
