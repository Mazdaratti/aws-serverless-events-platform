#!/usr/bin/env python3
"""
Sync dev GitHub Actions variables and secrets.

Usage:
    python scripts/sync_github_actions_vars.py --dry-run
    python scripts/sync_github_actions_vars.py

This helper syncs bootstrap-derived GitHub Actions values and dev Terraform
inputs into GitHub repository variables and secrets.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


BOOTSTRAP_REPO_VARIABLES = {
    # These GitHub repository variables are consumed by the OIDC smoke workflow.
    # Terraform remains the source of truth, so the script reads bootstrap
    # outputs instead of asking operators to copy values by hand.
    "AWS_ROLE_TO_ASSUME": "github_actions_role_arn",
    "AWS_REGION": "aws_region",
    "TF_BACKEND_BUCKET": "state_bucket_name",
    "TF_BACKEND_KEY": "state_backend_key",
}

DEV_REPO_VARIABLES = {
    "DEV_PROJECT_NAME": "project_name",
    "DEV_ENVIRONMENT": "environment",
    "DEV_DYNAMODB_POINT_IN_TIME_RECOVERY_ENABLED": "dynamodb_point_in_time_recovery_enabled",
    "DEV_ENABLE_WAF": "enable_waf",
}

DEV_DEFAULT_TFVARS = {
    "dynamodb_point_in_time_recovery_enabled": False,
    "enable_waf": False,
    "sns_admin_email_subscriptions": [],
}

DEV_REQUIRED_TFVARS = {
    "project_name",
    "environment",
    "ses_sender_email",
}

DEV_SUPPORTED_TFVARS = {
    "project_name",
    "environment",
    "aws_region",
    "dynamodb_point_in_time_recovery_enabled",
    "enable_waf",
    "sns_admin_email_subscriptions",
    "ses_sender_email",
}


def fail(message: str) -> None:
    """Print one clear error message and stop."""
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def find_executable(*names: str) -> str:
    """Return the first executable found on PATH."""
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    fail(f"Required executable not found: {', '.join(names)}")


def format_command_error(prefix: str, result: subprocess.CompletedProcess[str]) -> str:
    """Format a subprocess failure without losing stderr/stdout details."""
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
    input_text: str | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a command and capture text output for validation and errors."""
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        check=False,
        text=True,
        capture_output=capture_output,
    )


def normalize_repo_url(remote_url: str) -> str:
    """Normalize a Git remote URL into a GitHub owner/name repository string."""
    remote_url = remote_url.strip()

    ssh_match = re.match(r"git@github\.com:(?P<repo>.+?)(?:\.git)?$", remote_url)
    if ssh_match:
        return ssh_match.group("repo")

    https_match = re.match(r"https://github\.com/(?P<repo>.+?)(?:\.git)?$", remote_url)
    if https_match:
        return https_match.group("repo")

    fail(f"Unsupported remote.origin.url format: {remote_url}")


def get_repo_root() -> Path:
    """Resolve the repository root from this script path."""
    return Path(__file__).resolve().parents[1]


def ensure_running_from_repo_root(repo_root: Path) -> None:
    """Require repo-root execution so relative paths stay predictable."""
    current_dir = Path.cwd().resolve()
    expected_dir = repo_root.resolve()
    if current_dir != expected_dir:
        fail(
            "Run this script from the repository root. "
            f"current={current_dir}, expected={expected_dir}"
        )


def ensure_repo_root(git_bin: str, repo_root: Path) -> None:
    """Check that the script-derived root matches Git's repository root."""
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
    """Read and normalize the local GitHub remote repository."""
    result = run_command(
        [git_bin, "config", "--get", "remote.origin.url"],
        cwd=repo_root,
    )
    if result.returncode != 0 or not result.stdout.strip():
        fail(format_command_error("Could not read git remote.origin.url.", result))

    return normalize_repo_url(result.stdout)


def ensure_gh_auth(gh_bin: str, repo_root: Path) -> None:
    """Fail early when GitHub CLI is not authenticated."""
    result = run_command([gh_bin, "auth", "status"], cwd=repo_root)
    if result.returncode != 0:
        fail(
            format_command_error(
                "gh is installed, but authentication is missing. Run 'gh auth login' first.",
                result,
            )
        )


def resolve_dry_run_repo(git_bin: str, repo_root: Path, repo_override: str | None) -> str:
    """Resolve the dry-run repository without requiring GitHub CLI auth."""
    local_repo = get_local_remote_repo(git_bin, repo_root)
    if repo_override and repo_override != local_repo:
        fail(
            "The requested GitHub repository does not match git remote.origin.url. "
            f"requested={repo_override}, git={local_repo}"
        )
    return repo_override or local_repo


def resolve_github_repo(
    git_bin: str,
    gh_bin: str,
    repo_root: Path,
    repo_override: str | None,
) -> str:
    """Resolve the target GitHub repository and assert it matches the checkout."""
    local_repo = get_local_remote_repo(git_bin, repo_root)
    repo_name = repo_override or local_repo

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
    """Read bootstrap outputs that become shared GitHub Actions variables."""
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
    for variable_name, output_name in BOOTSTRAP_REPO_VARIABLES.items():
        if output_name not in payload or "value" not in payload[output_name]:
            fail(f"Required bootstrap output is missing: {output_name}")

        value = payload[output_name]["value"]
        if value is None or str(value).strip() == "":
            fail(f"Bootstrap output is empty: {output_name}")

        values[variable_name] = str(value)

    return values


def strip_inline_comment(line: str) -> str:
    """Remove # comments outside quoted strings."""
    in_string = False
    escaped = False
    output: list[str] = []

    for character in line:
        if escaped:
            output.append(character)
            escaped = False
            continue
        if character == "\\" and in_string:
            output.append(character)
            escaped = True
            continue
        if character == '"':
            output.append(character)
            in_string = not in_string
            continue
        if character == "#" and not in_string:
            break
        output.append(character)

    return "".join(output).strip()


def read_dev_tfvars(tfvars_path: Path) -> dict[str, Any]:
    """Read the current simple dev terraform.tfvars format."""
    if not tfvars_path.exists():
        fail(
            "Missing infrastructure/envs/dev/terraform.tfvars. "
            "Create it from terraform.tfvars.example before syncing GitHub Actions variables."
        )
    if not tfvars_path.is_file():
        fail(f"Dev tfvars path is not a file: {tfvars_path}")

    values: dict[str, Any] = {}
    lines = tfvars_path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        raw_line = strip_inline_comment(lines[index])
        index += 1
        if not raw_line:
            continue
        if "=" not in raw_line:
            fail(f"Unsupported tfvars line: {raw_line}")

        name, raw_value = raw_line.split("=", 1)
        variable_name = name.strip()
        value_text = raw_value.strip()
        if variable_name not in DEV_SUPPORTED_TFVARS:
            fail(f"Unsupported dev tfvars variable: {variable_name}")

        if value_text.startswith("[") and not value_text.endswith("]"):
            collected = [value_text]
            while index < len(lines):
                next_line = strip_inline_comment(lines[index])
                index += 1
                if next_line:
                    collected.append(next_line)
                if next_line.endswith("]"):
                    break
            value_text = "\n".join(collected)

        values[variable_name] = parse_tfvars_value(variable_name, value_text)

    merged_values = {**DEV_DEFAULT_TFVARS, **values}
    validate_dev_tfvars(merged_values)
    return merged_values


def parse_tfvars_value(variable_name: str, value_text: str) -> Any:
    """Parse the supported JSON-compatible subset used by dev tfvars."""
    try:
        return json.loads(value_text)
    except json.JSONDecodeError as exc:
        if value_text.strip().startswith("[") and value_text.strip().endswith("]"):
            return parse_hcl_string_list(variable_name, value_text)
        fail(
            f"Unsupported value for {variable_name}. "
            "Use quoted strings, true/false booleans, or string lists. "
            f"Parser detail: {exc}"
        )


def parse_hcl_string_list(variable_name: str, value_text: str) -> list[str]:
    """Parse a narrow Terraform-style list of quoted strings with optional trailing commas."""
    stripped = value_text.strip()
    inner = stripped[1:-1]
    decoder = json.JSONDecoder()
    values: list[str] = []
    position = 0

    while position < len(inner):
        while position < len(inner) and inner[position] in " \t\r\n,":
            position += 1
        if position >= len(inner):
            break
        try:
            value, offset = decoder.raw_decode(inner[position:])
        except json.JSONDecodeError as exc:
            fail(
                f"Unsupported list item for {variable_name}. "
                "Use quoted string values separated by commas. "
                f"Parser detail: {exc}"
            )
        if not isinstance(value, str):
            fail(f"{variable_name} list values must be quoted strings.")
        values.append(value)
        position += offset
        while position < len(inner) and inner[position] in " \t\r\n":
            position += 1
        if position < len(inner) and inner[position] == ",":
            position += 1
        elif position < len(inner):
            fail(f"{variable_name} list values must be separated by commas.")

    return values


def validate_dev_tfvars(values: dict[str, Any]) -> None:
    """Validate the expected dev Terraform variable types and required values."""
    missing = sorted(name for name in DEV_REQUIRED_TFVARS if name not in values)
    if missing:
        fail(f"Missing required dev tfvars values: {', '.join(missing)}")

    for name in ("project_name", "environment", "ses_sender_email"):
        value = values.get(name)
        if not isinstance(value, str) or not value.strip():
            fail(f"{name} must be a non-empty string.")
        if value != value.strip():
            fail(f"{name} must not contain leading or trailing whitespace.")

    for name in ("dynamodb_point_in_time_recovery_enabled", "enable_waf"):
        if not isinstance(values.get(name), bool):
            fail(f"{name} must be true or false.")

    subscriptions = values.get("sns_admin_email_subscriptions")
    if not isinstance(subscriptions, list):
        fail("sns_admin_email_subscriptions must be a list of strings.")
    for email in subscriptions:
        if not isinstance(email, str) or not email.strip():
            fail("sns_admin_email_subscriptions must contain only non-empty strings.")
        if email != email.strip():
            fail("sns_admin_email_subscriptions values must not contain leading or trailing whitespace.")

    aws_region = values.get("aws_region")
    if aws_region is not None and (not isinstance(aws_region, str) or not aws_region.strip()):
        fail("aws_region must be a non-empty string when present.")


def verify_dev_region(values: dict[str, Any], bootstrap_variables: dict[str, str]) -> None:
    """Check local aws_region against the bootstrap-derived AWS_REGION value."""
    local_region = values.get("aws_region")
    if local_region is None:
        return

    bootstrap_region = bootstrap_variables["AWS_REGION"]
    if str(local_region) != bootstrap_region:
        fail(
            "Local dev aws_region does not match bootstrap-derived AWS_REGION. "
            f"local={local_region}, bootstrap={bootstrap_region}"
        )


def stringify_variable(value: Any) -> str:
    """Convert supported non-secret values into GitHub variable strings."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    fail(f"Unsupported repository variable value type: {type(value).__name__}")


def build_dev_repo_variables(values: dict[str, Any]) -> dict[str, str]:
    """Build GitHub repository variable payloads from dev tfvars."""
    return {
        variable_name: stringify_variable(values[tfvars_name])
        for variable_name, tfvars_name in DEV_REPO_VARIABLES.items()
    }


def build_dev_repo_secrets(values: dict[str, Any]) -> dict[str, str]:
    """Build GitHub repository secret payloads from dev tfvars."""
    return {
        "DEV_SES_SENDER_EMAIL": values["ses_sender_email"],
        "DEV_SNS_ADMIN_EMAIL_SUBSCRIPTIONS_JSON": json.dumps(
            values["sns_admin_email_subscriptions"],
            separators=(",", ":"),
        ),
    }


def set_repo_variable(
    gh_bin: str,
    repo_root: Path,
    repo_name: str,
    name: str,
    value: str,
) -> None:
    """Write one GitHub repository variable."""
    result = run_command(
        [gh_bin, "variable", "set", name, "--repo", repo_name, "--body", value],
        cwd=repo_root,
    )
    if result.returncode != 0:
        fail(format_command_error(f"Failed to set GitHub repository variable {name}.", result))


def set_repo_secret(
    gh_bin: str,
    repo_root: Path,
    repo_name: str,
    name: str,
    value: str,
) -> None:
    """Write one GitHub repository secret through stdin."""
    result = run_command(
        [gh_bin, "secret", "set", name, "--repo", repo_name],
        cwd=repo_root,
        input_text=value,
    )
    if result.returncode != 0:
        fail(format_command_error(f"Failed to set GitHub repository secret {name}.", result))


def display_value(name: str, value: str) -> str:
    """Mask account-specific variable values in normal terminal output."""
    if name == "AWS_ROLE_TO_ASSUME":
        return "<role-arn>"
    if name == "TF_BACKEND_BUCKET":
        return "<state-bucket>"
    return value


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Sync dev GitHub Actions variables and secrets."
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


def print_summary(
    *,
    repo_name: str,
    bootstrap_variables: dict[str, str],
    dev_variables: dict[str, str],
    dev_secrets: dict[str, str],
    dry_run: bool,
) -> None:
    """Print a conservative sync summary without secret values."""
    print("GitHub Actions repository sync summary")
    print(f"Repository: {repo_name}")
    print("Bootstrap repository variables:")
    for name, value in bootstrap_variables.items():
        print(f"  - {name}={display_value(name, value)}")
    print("Dev Terraform repository variables:")
    for name, value in dev_variables.items():
        print(f"  - {name}={value}")
    print("Dev Terraform repository secrets:")
    for name in dev_secrets:
        print(f"  - {name}=<secret>")
    if dry_run:
        print("Dry run enabled. No GitHub variables or secrets were changed.")


def main() -> None:
    """Sync bootstrap outputs and dev Terraform inputs into GitHub."""
    args = parse_args()

    repo_root = get_repo_root()
    bootstrap_dir = repo_root / "infrastructure" / "bootstrap" / "dev"
    dev_tfvars_path = repo_root / "infrastructure" / "envs" / "dev" / "terraform.tfvars"

    if not bootstrap_dir.is_dir():
        fail(f"Bootstrap directory does not exist: {bootstrap_dir}")

    ensure_running_from_repo_root(repo_root)

    git_bin = find_executable("git.exe", "git")
    terraform_bin = find_executable("terraform.exe", "terraform")

    ensure_repo_root(git_bin, repo_root)

    if args.dry_run:
        repo_name = resolve_dry_run_repo(git_bin, repo_root, args.repo)
    else:
        gh_bin = find_executable("gh.exe", "gh")
        ensure_gh_auth(gh_bin, repo_root)
        repo_name = resolve_github_repo(git_bin, gh_bin, repo_root, args.repo)

    bootstrap_variables = read_bootstrap_outputs(terraform_bin, bootstrap_dir)
    dev_tfvars = read_dev_tfvars(dev_tfvars_path)
    verify_dev_region(dev_tfvars, bootstrap_variables)
    dev_variables = build_dev_repo_variables(dev_tfvars)
    dev_secrets = build_dev_repo_secrets(dev_tfvars)

    print_summary(
        repo_name=repo_name,
        bootstrap_variables=bootstrap_variables,
        dev_variables=dev_variables,
        dev_secrets=dev_secrets,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        return

    for name, value in bootstrap_variables.items():
        set_repo_variable(gh_bin, repo_root, repo_name, name, value)
    for name, value in dev_variables.items():
        set_repo_variable(gh_bin, repo_root, repo_name, name, value)
    for name, value in dev_secrets.items():
        set_repo_secret(gh_bin, repo_root, repo_name, name, value)

    print("GitHub repository variables and secrets updated successfully.")


if __name__ == "__main__":
    main()
