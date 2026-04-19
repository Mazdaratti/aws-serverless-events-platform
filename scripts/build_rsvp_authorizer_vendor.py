#!/usr/bin/env python3
"""
Rebuild the RSVP authorizer vendor tree in a Lambda-compatible Docker container.

This script keeps the Docker invocation portable and repo-relative so the same
workflow can be reused locally and later in CI without shell-specific path
quoting.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


IMAGE_NAME = "rsvp-authorizer-vendor"


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    workload_dir = repo_root / "lambdas" / "rsvp_authorizer"
    dockerfile_path = workload_dir / "Dockerfile.vendor"
    vendor_dir = workload_dir / "vendor"

    validate_workload_dir(workload_dir)
    validate_dockerfile(dockerfile_path)

    if vendor_dir.exists():
        shutil.rmtree(vendor_dir)

    print("Building RSVP authorizer vendor image...")
    run_command(
        [
            "docker",
            "build",
            "-f",
            str(dockerfile_path),
            "-t",
            IMAGE_NAME,
            str(workload_dir),
        ],
        repo_root=repo_root,
    )

    print("Rebuilding Lambda-compatible vendor directory...")
    run_command(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{workload_dir}:/output",
            IMAGE_NAME,
        ],
        repo_root=repo_root,
    )

    if not vendor_dir.exists() or not any(vendor_dir.iterdir()):
        raise SystemExit(f"Vendor directory was not created correctly: {vendor_dir}")

    print(f"Rebuilt Lambda-compatible vendor tree: {vendor_dir}")
    return 0


def validate_workload_dir(workload_dir: Path) -> None:
    if not workload_dir.exists():
        raise SystemExit(f"Authorizer workload directory does not exist: {workload_dir}")
    if not workload_dir.is_dir():
        raise SystemExit(f"Authorizer workload path is not a directory: {workload_dir}")


def validate_dockerfile(dockerfile_path: Path) -> None:
    if not dockerfile_path.exists():
        raise SystemExit(f"Docker vendor build file does not exist: {dockerfile_path}")
    if not dockerfile_path.is_file():
        raise SystemExit(f"Docker vendor build path is not a file: {dockerfile_path}")


def run_command(command: list[str], *, repo_root: Path) -> None:
    try:
        subprocess.run(command, cwd=repo_root, check=True)
    except FileNotFoundError as exc:
        raise SystemExit(
            "Docker is required to rebuild the RSVP authorizer vendor tree."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"Command failed with exit code {exc.returncode}: {' '.join(command)}"
        ) from exc


if __name__ == "__main__":
    sys.exit(main())
