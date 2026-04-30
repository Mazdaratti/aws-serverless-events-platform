#!/usr/bin/env python3
"""
Build and deploy the React/Vite frontend through the CloudFront/S3 path.

The script intentionally keeps the deployment path local and explicit:
- read public deployment values from Terraform outputs
- write only approved public VITE_* values for the Vite production build
- build the frontend
- dry-run the S3 sync by default
- require --apply before uploading assets or invalidating CloudFront
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_TERRAFORM_OUTPUTS = (
    "aws_region",
    "frontend_bucket_name",
    "cloudfront_distribution_id",
    "cloudfront_distribution_domain_name",
    "cognito_user_pool_id",
    "cognito_user_pool_client_id",
)
ALLOWED_VITE_KEYS = {
    "VITE_AWS_REGION",
    "VITE_COGNITO_USER_POOL_ID",
    "VITE_COGNITO_USER_POOL_CLIENT_ID",
}
VITE_ENV_FILE_NAME = ".env.production.local"
VITE_ENV_CANDIDATES = (
    ".env",
    ".env.local",
    ".env.production",
    ".env.production.local",
)


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    terraform_dir = repo_root / "infrastructure" / "envs" / "dev"
    frontend_dir = repo_root / "frontend"
    dist_dir = frontend_dir / "dist"
    vite_env_path = frontend_dir / VITE_ENV_FILE_NAME

    outputs = read_terraform_outputs(terraform_dir)
    validate_frontend_env_files(frontend_dir, managed_env_path=vite_env_path)

    vite_values = {
        "VITE_AWS_REGION": outputs["aws_region"],
        "VITE_COGNITO_USER_POOL_ID": outputs["cognito_user_pool_id"],
        "VITE_COGNITO_USER_POOL_CLIENT_ID": outputs["cognito_user_pool_client_id"],
    }
    build_env = create_sanitized_build_env(vite_values)

    previous_env_contents = read_existing_file(vite_env_path)
    try:
        write_vite_env_file(vite_env_path, vite_values)

        print_step("Installing frontend dependencies")
        run_command(["npm", "ci"], cwd=frontend_dir)

        print_step("Running frontend typecheck")
        run_command(["npm", "run", "typecheck"], cwd=frontend_dir, env=build_env)

        print_step("Building frontend")
        run_command(["npm", "run", "build"], cwd=frontend_dir, env=build_env)

        validate_dist_dir(dist_dir)

        s3_uri = f"s3://{outputs['frontend_bucket_name']}"
        print_step("Previewing S3 sync")
        run_aws_s3_sync(
            dist_dir=dist_dir,
            s3_uri=s3_uri,
            region=outputs["aws_region"],
            dry_run=True,
        )

        if args.apply:
            print_step("Syncing frontend assets to S3")
            run_aws_s3_sync(
                dist_dir=dist_dir,
                s3_uri=s3_uri,
                region=outputs["aws_region"],
                dry_run=False,
            )

            print_step("Invalidating CloudFront cache")
            run_cloudfront_invalidation(
                distribution_id=outputs["cloudfront_distribution_id"],
            )
        else:
            print()
            print("Dry-run complete. Re-run with --apply to upload and invalidate CloudFront.")

        print_final_urls(outputs["cloudfront_distribution_domain_name"])
        return 0
    finally:
        restore_env_file(vite_env_path, previous_env_contents)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and deploy the frontend to the dev CloudFront/S3 path."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="apply",
        action="store_false",
        help="Build and preview the S3 sync without uploading or invalidating. This is the default.",
    )
    mode.add_argument(
        "--apply",
        dest="apply",
        action="store_true",
        help="Build, sync frontend/dist to S3, and invalidate CloudFront.",
    )
    parser.set_defaults(apply=False)
    return parser.parse_args()


def read_terraform_outputs(terraform_dir: Path) -> dict[str, str]:
    if not terraform_dir.exists():
        raise SystemExit(f"Terraform env directory does not exist: {terraform_dir}")

    print_step("Reading Terraform outputs")
    completed = run_command(
        ["terraform", "output", "-json"],
        cwd=terraform_dir,
        capture_output=True,
    )

    try:
        raw_outputs = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("Terraform output was not valid JSON.") from exc

    outputs: dict[str, str] = {}
    missing_outputs: list[str] = []
    invalid_outputs: list[str] = []

    for output_name in REQUIRED_TERRAFORM_OUTPUTS:
        raw_output = raw_outputs.get(output_name)
        if raw_output is None:
            missing_outputs.append(output_name)
            continue

        value = raw_output.get("value")
        if not isinstance(value, str) or not value.strip():
            invalid_outputs.append(output_name)
            continue

        outputs[output_name] = value.strip()

    if missing_outputs:
        raise SystemExit(
            "Missing required Terraform outputs: " + ", ".join(sorted(missing_outputs))
        )

    if invalid_outputs:
        raise SystemExit(
            "Required Terraform outputs must be non-empty strings: "
            + ", ".join(sorted(invalid_outputs))
        )

    return outputs


def validate_frontend_env_files(frontend_dir: Path, *, managed_env_path: Path) -> None:
    # Vite loads multiple env files for production builds. Reject unexpected
    # VITE_* keys so local-only files cannot accidentally inject API URLs or
    # unrelated browser config into the production bundle.
    disallowed_keys: dict[Path, list[str]] = {}

    for file_name in VITE_ENV_CANDIDATES:
        env_path = frontend_dir / file_name
        if env_path == managed_env_path or not env_path.exists():
            continue

        keys = collect_vite_keys(env_path)
        unexpected_keys = sorted(keys - ALLOWED_VITE_KEYS)
        if unexpected_keys:
            disallowed_keys[env_path] = unexpected_keys

    if not disallowed_keys:
        return

    lines = ["Unexpected VITE_* keys found in frontend env files:"]
    for env_path, keys in sorted(disallowed_keys.items()):
        lines.append(f"- {env_path}: {', '.join(keys)}")
    lines.append("Only the approved public Cognito and region VITE_* values may be used.")
    raise SystemExit("\n".join(lines))


def collect_vite_keys(env_path: Path) -> set[str]:
    keys: set[str] = set()
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key = line.split("=", maxsplit=1)[0].strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        if key.startswith("VITE_"):
            keys.add(key)

    return keys


def create_sanitized_build_env(vite_values: dict[str, str]) -> dict[str, str]:
    build_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("VITE_")
    }
    build_env.update(vite_values)
    return build_env


def read_existing_file(path: Path) -> bytes | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise SystemExit(f"Expected frontend env path to be a file: {path}")
    return path.read_bytes()


def write_vite_env_file(path: Path, vite_values: dict[str, str]) -> None:
    lines = [
        "# Generated temporarily by scripts/deploy_frontend.py.",
        "# This file is restored or removed automatically after the build.",
    ]
    lines.extend(f"{key}={vite_values[key]}" for key in sorted(vite_values))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def restore_env_file(path: Path, previous_contents: bytes | None) -> None:
    if previous_contents is None:
        if path.exists():
            path.unlink()
        return

    path.write_bytes(previous_contents)


def validate_dist_dir(dist_dir: Path) -> None:
    if not dist_dir.exists() or not dist_dir.is_dir():
        raise SystemExit(f"Frontend build output directory does not exist: {dist_dir}")

    if not any(dist_dir.iterdir()):
        raise SystemExit(f"Frontend build output directory is empty: {dist_dir}")


def run_aws_s3_sync(*, dist_dir: Path, s3_uri: str, region: str, dry_run: bool) -> None:
    command = [
        "aws",
        "s3",
        "sync",
        str(dist_dir),
        s3_uri,
        "--delete",
        "--region",
        region,
    ]
    if dry_run:
        command.append("--dryrun")

    run_command(command, cwd=dist_dir.parent)


def run_cloudfront_invalidation(*, distribution_id: str) -> None:
    run_command(
        [
            "aws",
            "cloudfront",
            "create-invalidation",
            "--distribution-id",
            distribution_id,
            "--paths",
            "/*",
        ],
        cwd=Path.cwd(),
    )


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    resolved_command = [resolve_executable(command[0]), *command[1:]]

    try:
        return subprocess.run(
            resolved_command,
            cwd=cwd,
            env=env,
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
    resolved_path = shutil.which(command_name)
    if resolved_path is None:
        raise SystemExit(f"Required command was not found: {command_name}")
    return resolved_path


def print_step(message: str) -> None:
    print()
    print(f"==> {message}")


def print_final_urls(cloudfront_domain_name: str) -> None:
    base_url = f"https://{cloudfront_domain_name}"
    print()
    print("Frontend URLs:")
    print(f"- {base_url}/app")
    print(f"- {base_url}/app/events")


if __name__ == "__main__":
    sys.exit(main())
