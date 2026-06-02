#!/usr/bin/env python3
"""
Deploy Lambda ZIP artifacts through the direct Lambda code-update path.

The script intentionally mirrors the frontend deployment helper shape:
- package Lambda artifacts
- read deployment values from Terraform outputs
- dry-run by default
- require --apply before updating Lambda function code
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from package_lambdas import WORKLOADS


REQUIRED_TERRAFORM_OUTPUTS = (
    "aws_region",
    "lambda_function_names",
)


@dataclass(frozen=True)
class PlannedLambdaUpdate:
    """Describes one Lambda code update target."""

    function_key: str
    function_name: str
    artifact_path: Path
    zip_file_uri: str


def main() -> int:
    """Package Lambda artifacts and dry-run or apply Lambda code updates."""
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    terraform_dir = repo_root / "infrastructure" / "envs" / "dev"
    artifacts_dir = repo_root / "artifacts" / "lambda"

    package_lambdas(repo_root=repo_root, skip_vendor_build=args.skip_authorizer_vendor_build)
    outputs = read_terraform_outputs(terraform_dir)
    planned_updates = plan_lambda_updates(
        repo_root=repo_root,
        artifacts_dir=artifacts_dir,
        function_names=outputs["lambda_function_names"],
    )

    print_summary(
        repo_root=repo_root,
        aws_region=outputs["aws_region"],
        planned_updates=planned_updates,
        apply=args.apply,
    )

    if args.apply:
        apply_lambda_updates(
            repo_root=repo_root,
            aws_region=outputs["aws_region"],
            planned_updates=planned_updates,
        )
    else:
        print()
        print("Dry-run complete. Re-run with --apply to update Lambda function code.")

    return 0


def parse_args() -> argparse.Namespace:
    """Parse CLI options for Lambda code deployment."""
    parser = argparse.ArgumentParser(
        description="Deploy Lambda ZIP artifacts to existing dev Lambda functions."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="apply",
        action="store_false",
        help="Package artifacts and preview Lambda code updates without changing AWS. This is the default.",
    )
    mode.add_argument(
        "--apply",
        dest="apply",
        action="store_true",
        help="Package artifacts and update existing Lambda function code.",
    )
    parser.add_argument(
        "--skip-authorizer-vendor-build",
        action="store_true",
        help=(
            "Pass through to scripts/package_lambdas.py. Use only when the "
            "Lambda-compatible RSVP authorizer vendor tree already exists."
        ),
    )
    parser.set_defaults(apply=False)
    return parser.parse_args()


def package_lambdas(*, repo_root: Path, skip_vendor_build: bool) -> None:
    """Package all Lambda workloads through the existing orchestration helper."""
    command = [sys.executable, "scripts/package_lambdas.py"]
    if skip_vendor_build:
        command.append("--skip-authorizer-vendor-build")
    run_command(command, cwd=repo_root)


def read_terraform_outputs(terraform_dir: Path) -> dict[str, str | dict[str, str]]:
    """Read and validate Terraform outputs required for Lambda code deployment."""
    if not terraform_dir.exists():
        raise SystemExit(f"Terraform env directory does not exist: {terraform_dir}")

    completed = run_command(
        ["terraform", "output", "-json"],
        cwd=terraform_dir,
        capture_output=True,
    )

    try:
        raw_outputs = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("Terraform output was not valid JSON.") from exc

    missing_outputs = sorted(
        output_name
        for output_name in REQUIRED_TERRAFORM_OUTPUTS
        if output_name not in raw_outputs
    )
    if missing_outputs:
        raise SystemExit(
            "Missing required Terraform outputs: " + ", ".join(missing_outputs)
        )

    aws_region = raw_outputs["aws_region"].get("value")
    if not isinstance(aws_region, str) or not aws_region.strip():
        raise SystemExit("Terraform output aws_region must be a non-empty string.")

    function_names = raw_outputs["lambda_function_names"].get("value")
    if not isinstance(function_names, dict):
        raise SystemExit("Terraform output lambda_function_names must be a map.")

    validated_function_names: dict[str, str] = {}
    invalid_function_names: list[str] = []
    for function_key, function_name in function_names.items():
        if (
            not isinstance(function_key, str)
            or not isinstance(function_name, str)
            or not function_name.strip()
        ):
            invalid_function_names.append(str(function_key))
            continue
        validated_function_names[function_key] = function_name.strip()

    if invalid_function_names:
        raise SystemExit(
            "Terraform output lambda_function_names contains invalid values for: "
            + ", ".join(sorted(invalid_function_names))
        )

    return {
        "aws_region": aws_region.strip(),
        "lambda_function_names": validated_function_names,
    }


def plan_lambda_updates(
    *,
    repo_root: Path,
    artifacts_dir: Path,
    function_names: dict[str, str],
) -> list[PlannedLambdaUpdate]:
    """Build and validate Lambda update targets from workloads and Terraform outputs."""
    workload_keys = [workload.function_key for workload in WORKLOADS]
    missing_outputs = sorted(key for key in workload_keys if key not in function_names)
    if missing_outputs:
        raise SystemExit(
            "Missing lambda_function_names entries for workloads: "
            + ", ".join(missing_outputs)
        )

    planned_updates: list[PlannedLambdaUpdate] = []
    missing_artifacts: list[Path] = []

    for function_key in workload_keys:
        artifact_path = artifacts_dir / f"{function_key}.zip"
        if not artifact_path.exists() or not artifact_path.is_file():
            missing_artifacts.append(artifact_path)
            continue

        planned_updates.append(
            PlannedLambdaUpdate(
                function_key=function_key,
                function_name=function_names[function_key],
                artifact_path=artifact_path,
                zip_file_uri=f"fileb://{artifact_path}",
            )
        )

    if missing_artifacts:
        formatted_paths = "\n".join(
            f"- {relative_to_repo(repo_root=repo_root, path=path)}"
            for path in missing_artifacts
        )
        raise SystemExit(f"Missing expected Lambda ZIP artifacts:\n{formatted_paths}")

    return planned_updates


def apply_lambda_updates(
    *,
    repo_root: Path,
    aws_region: str,
    planned_updates: list[PlannedLambdaUpdate],
) -> None:
    """Update Lambda function code for every planned target."""
    for update in planned_updates:
        print()
        print(f"==> Updating Lambda function code: {update.function_key}")
        run_command(
            [
                "aws",
                "lambda",
                "update-function-code",
                "--function-name",
                update.function_name,
                "--zip-file",
                update.zip_file_uri,
                "--region",
                aws_region,
                "--no-publish",
            ],
            cwd=repo_root,
        )

    print()
    print("Lambda code deployment complete.")


def print_summary(
    *,
    repo_root: Path,
    aws_region: str,
    planned_updates: list[PlannedLambdaUpdate],
    apply: bool,
) -> None:
    """Print planned Lambda update-function-code targets."""
    print()
    print("Lambda code deployment plan:")
    print(f"AWS region: {aws_region}")
    print(f"Mode: {'apply' if apply else 'dry-run'}")

    for update in planned_updates:
        artifact = relative_to_repo(repo_root=repo_root, path=update.artifact_path)
        print(f"- {update.function_key}")
        print(f"  function: {update.function_name}")
        print(f"  artifact: {artifact}")
        print(
            "  command: aws lambda update-function-code "
            f"--function-name {update.function_name} "
            f"--zip-file {update.zip_file_uri} "
            f"--region {aws_region} --no-publish"
        )


def run_command(
    command: list[str],
    *,
    cwd: Path,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a local command and fail with a concise message."""
    resolved_command = [resolve_executable(command[0]), *command[1:]]
    try:
        return subprocess.run(
            resolved_command,
            cwd=cwd,
            check=True,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"Required command was not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"Command failed with exit code {exc.returncode}: {' '.join(command)}"
        ) from exc


def resolve_executable(command_name: str) -> str:
    """Resolve an executable from PATH or fail clearly."""
    resolved_path = shutil.which(command_name)
    if resolved_path is None:
        raise SystemExit(f"Required command was not found: {command_name}")
    return resolved_path


def relative_to_repo(*, repo_root: Path, path: Path) -> str:
    """Return a readable repo-relative path when possible."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())
