#!/usr/bin/env python3
"""
Sync dev bootstrap outputs into GitHub repository variables.

Usage:
    python scripts/sync_github_actions_vars.py --dry-run
    python scripts/sync_github_actions_vars.py

This helper is intentionally limited to the repository variables needed by the
GitHub Actions AWS OIDC smoke workflow. It does not manage secrets,
GitHub Environment variables, Terraform desired-state inputs, or deployment
configuration.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_OUTPUTS = {
    # These GitHub repository variables are consumed by the OIDC smoke workflow.
    # Terraform remains the source of truth, so the script reads bootstrap
    # outputs instead of asking operators to copy values by hand.
    "AWS_ROLE_TO_ASSUME": "github_actions_role_arn",
    "AWS_REGION": "aws_region",
    "TF_BACKEND_BUCKET": "state_bucket_name",
    "TF_BACKEND_KEY": "state_backend_key",
}


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def find_executable(*names: str) -> str:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    fail(f"Required executable not found: {', '.join(names)}")


def format_command_error(prefix: str, result: subprocess.CompletedProcess[str]) -> str:
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    details = stderr or stdout
    if details:
        return f"{prefix} {details}"
    return prefix


def run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        capture_output=capture_output,
    )


def normalize_repo_url(remote_url: str) -> str:
    remote_url = remote_url.strip()

    ssh_match = re.match(r"git@github\.com:(?P<repo>.+?)(?:\.git)?$", remote_url)
    if ssh_match:
        return ssh_match.group("repo")

    https_match = re.match(r"https://github\.com/(?P<repo>.+?)(?:\.git)?$", remote_url)
    if https_match:
        return https_match.group("repo")

    fail(f"Unsupported remote.origin.url format: {remote_url}")


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_running_from_repo_root(repo_root: Path) -> None:
    # Running from the repo root keeps relative paths and GitHub CLI repository
    # detection predictable across PowerShell, Git Bash, and CI shells.
    current_dir = Path.cwd().resolve()
    expected_dir = repo_root.resolve()
    if current_dir != expected_dir:
        fail(
            "Run this script from the repository root. "
            f"current={current_dir}, expected={expected_dir}"
        )


def ensure_repo_root(git_bin: str, repo_root: Path) -> None:
    result = run_command([git_bin, "rev-parse", "--show-toplevel"], cwd=repo_root)
    if result.returncode != 0:
        fail(format_command_error("Could not determine git repository root.", result))

    actual_root = Path(result.stdout.strip()).resolve()
    if actual_root != repo_root.resolve():
        fail(
            "Script-derived repo root does not match git top-level. "
            f"script={repo_root}, git={actual_root}"
        )


def get_local_remote_repo(git_bin: str, repo_root: Path) -> str:
    result = run_command(
        [git_bin, "config", "--get", "remote.origin.url"],
        cwd=repo_root,
    )
    if result.returncode != 0 or not result.stdout.strip():
        fail(format_command_error("Could not read git remote.origin.url.", result))

    return normalize_repo_url(result.stdout)


def ensure_gh_auth(gh_bin: str, repo_root: Path) -> None:
    result = run_command([gh_bin, "auth", "status"], cwd=repo_root)
    if result.returncode != 0:
        fail(
            format_command_error(
                "gh is installed, but authentication is missing. Run 'gh auth login' first.",
                result,
            )
        )


def resolve_github_repo(
    git_bin: str,
    gh_bin: str,
    repo_root: Path,
    repo_override: str | None,
) -> str:
    local_repo = get_local_remote_repo(git_bin, repo_root)
    repo_name = repo_override or local_repo

    # The override is intentionally an assertion, not a way to target a
    # different repository from this checkout.
    if repo_name != local_repo:
        fail(
            "The requested GitHub repository does not match git remote.origin.url. "
            f"requested={repo_name}, git={local_repo}"
        )

    result = run_command(
        [gh_bin, "repo", "view", repo_name, "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        cwd=repo_root,
    )
    if result.returncode != 0 or not result.stdout.strip():
        fail(
            format_command_error(
                f"Could not access GitHub repository {repo_name} via gh.",
                result,
            )
        )

    gh_repo = result.stdout.strip()
    if gh_repo != repo_name:
        fail(f"GitHub repository mismatch. requested={repo_name}, gh={gh_repo}")

    return gh_repo


def read_bootstrap_outputs(terraform_bin: str, bootstrap_dir: Path) -> dict[str, str]:
    result = run_command([terraform_bin, "output", "-json"], cwd=bootstrap_dir)
    if result.returncode != 0:
        fail(
            format_command_error(
                "Could not read Terraform outputs from bootstrap. "
                "Make sure infrastructure/bootstrap/dev has been applied successfully first.",
                result,
            )
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"Terraform outputs were not valid JSON: {exc}")

    values: dict[str, str] = {}
    for variable_name, output_name in REQUIRED_OUTPUTS.items():
        if output_name not in payload or "value" not in payload[output_name]:
            fail(f"Required bootstrap output is missing: {output_name}")

        value = payload[output_name]["value"]
        if value is None or str(value).strip() == "":
            fail(f"Bootstrap output is empty: {output_name}")

        values[variable_name] = str(value)

    return values


def set_repo_variable(
    gh_bin: str,
    repo_root: Path,
    repo_name: str,
    name: str,
    value: str,
) -> None:
    result = run_command(
        [gh_bin, "variable", "set", name, "--repo", repo_name, "--body", value],
        cwd=repo_root,
    )
    if result.returncode != 0:
        fail(format_command_error(f"Failed to set GitHub repository variable {name}.", result))


def display_value(name: str, value: str) -> str:
    # These values are not secrets, but masking account-specific identifiers
    # keeps normal terminal output and screenshots tidy.
    if name == "AWS_ROLE_TO_ASSUME":
        return "<role-arn>"
    if name == "TF_BACKEND_BUCKET":
        return "<state-bucket>"
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync dev bootstrap outputs into GitHub repository variables."
    )
    parser.add_argument(
        "--repo",
        help="Optional GitHub repository override in owner/name format. Must match remote.origin.url.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the variables that would be written without updating GitHub.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    repo_root = get_repo_root()
    bootstrap_dir = repo_root / "infrastructure" / "bootstrap" / "dev"

    if not bootstrap_dir.is_dir():
        fail(f"Bootstrap directory does not exist: {bootstrap_dir}")

    ensure_running_from_repo_root(repo_root)

    git_bin = find_executable("git.exe", "git")
    terraform_bin = find_executable("terraform.exe", "terraform")
    gh_bin = find_executable("gh.exe", "gh")

    ensure_repo_root(git_bin, repo_root)
    ensure_gh_auth(gh_bin, repo_root)
    repo_name = resolve_github_repo(git_bin, gh_bin, repo_root, args.repo)
    values = read_bootstrap_outputs(terraform_bin, bootstrap_dir)

    print("GitHub repository variable sync summary")
    print(f"Repository: {repo_name}")
    print("Variables:")
    for name, value in values.items():
        print(f"  - {name}={display_value(name, value)}")

    if args.dry_run:
        print("Dry run enabled. No GitHub variables were changed.")
        return

    for name, value in values.items():
        set_repo_variable(gh_bin, repo_root, repo_name, name, value)

    print("GitHub repository variables updated successfully.")


if __name__ == "__main__":
    main()
