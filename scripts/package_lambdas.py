#!/usr/bin/env python3
"""
Package every deployed Lambda workload expected by the dev Terraform root.

This helper orchestrates the existing single-workload packager. It does not
call AWS, read Terraform outputs, or deploy code. Its job is only to create the
ZIP artifacts that Terraform provisioning and Lambda code deployment
automation both need.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import build_rsvp_authorizer_vendor
from package_lambda import (
    package_lambda,
    validate_shared_dir,
    validate_source_dir,
    validate_vendor_dir,
)


@dataclass(frozen=True)
class WorkloadPackage:
    """Defines how one Terraform workload key maps to a Lambda ZIP artifact."""

    function_key: str
    source_dir_name: str
    include_shared: bool = True
    vendor_dir_name: str | None = None


WORKLOADS: tuple[WorkloadPackage, ...] = (
    WorkloadPackage(function_key="create-event", source_dir_name="create_event"),
    WorkloadPackage(function_key="get-event", source_dir_name="get_event"),
    WorkloadPackage(function_key="list-events", source_dir_name="list_events"),
    WorkloadPackage(function_key="list-my-events", source_dir_name="list_my_events"),
    WorkloadPackage(function_key="update-event", source_dir_name="update_event"),
    WorkloadPackage(function_key="cancel-event", source_dir_name="cancel_event"),
    WorkloadPackage(
        function_key="rsvp-authorizer",
        source_dir_name="rsvp_authorizer",
        vendor_dir_name="vendor",
    ),
    WorkloadPackage(function_key="rsvp", source_dir_name="rsvp"),
    WorkloadPackage(function_key="get-event-rsvps", source_dir_name="get_event_rsvps"),
    WorkloadPackage(
        function_key="notification-planner",
        source_dir_name="notification_planner",
        include_shared=False,
    ),
    WorkloadPackage(
        function_key="notification-sender",
        source_dir_name="notification_sender",
        include_shared=False,
    ),
)


def main() -> int:
    """Package all configured Lambda workloads and print a concise summary."""
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    artifacts_dir = repo_root / "artifacts" / "lambda"
    shared_dir = repo_root / "lambdas" / "shared"

    validate_shared_dir(shared_dir)
    validate_workload_sources(repo_root=repo_root, workloads=WORKLOADS)

    if args.skip_authorizer_vendor_build:
        validate_authorizer_vendor(repo_root=repo_root)
    else:
        rebuild_authorizer_vendor()

    packaged_artifacts = [
        package_workload(
            repo_root=repo_root,
            artifacts_dir=artifacts_dir,
            shared_dir=shared_dir,
            workload=workload,
        )
        for workload in WORKLOADS
    ]

    validate_artifacts(packaged_artifacts)
    print_summary(repo_root=repo_root, packaged_artifacts=packaged_artifacts)
    return 0


def parse_args() -> argparse.Namespace:
    """Parse CLI options for the orchestration helper."""
    parser = argparse.ArgumentParser(
        description="Package all Lambda workloads expected by infrastructure/envs/dev."
    )
    parser.add_argument(
        "--skip-authorizer-vendor-build",
        action="store_true",
        help=(
            "Do not rebuild lambdas/rsvp_authorizer/vendor before packaging. "
            "Use only when the Lambda-compatible vendor tree already exists."
        ),
    )
    return parser.parse_args()


def validate_workload_sources(
    *, repo_root: Path, workloads: tuple[WorkloadPackage, ...]
) -> None:
    """Fail fast when any configured workload source directory is missing."""
    for workload in workloads:
        validate_source_dir(source_dir_for(repo_root=repo_root, workload=workload))


def rebuild_authorizer_vendor() -> None:
    """Rebuild the RSVP authorizer vendor tree with the existing Docker helper."""
    result = build_rsvp_authorizer_vendor.main()
    if result != 0:
        raise SystemExit(f"RSVP authorizer vendor rebuild failed with exit code {result}")


def validate_authorizer_vendor(*, repo_root: Path) -> None:
    """Validate that the RSVP authorizer vendor tree already exists."""
    authorizer_vendor = repo_root / "lambdas" / "rsvp_authorizer" / "vendor"
    validate_vendor_dir(authorizer_vendor)
    if not any(authorizer_vendor.iterdir()):
        raise SystemExit(f"Vendor directory is empty: {authorizer_vendor}")


def package_workload(
    *,
    repo_root: Path,
    artifacts_dir: Path,
    shared_dir: Path,
    workload: WorkloadPackage,
) -> tuple[str, Path]:
    """Package one workload and return its function key and artifact path."""
    source_dir = source_dir_for(repo_root=repo_root, workload=workload)
    output_path = artifacts_dir / f"{workload.function_key}.zip"
    vendor_dir = vendor_dir_for(repo_root=repo_root, workload=workload)

    if vendor_dir is not None:
        validate_vendor_dir(vendor_dir)

    package_lambda(
        source_dir=source_dir,
        shared_dir=shared_dir if workload.include_shared else None,
        vendor_dir=vendor_dir,
        output_path=output_path,
    )

    return workload.function_key, output_path


def source_dir_for(*, repo_root: Path, workload: WorkloadPackage) -> Path:
    """Resolve the source directory for one workload."""
    return repo_root / "lambdas" / workload.source_dir_name


def vendor_dir_for(*, repo_root: Path, workload: WorkloadPackage) -> Path | None:
    """Resolve the optional vendor directory for one workload."""
    if workload.vendor_dir_name is None:
        return None
    return source_dir_for(repo_root=repo_root, workload=workload) / workload.vendor_dir_name


def validate_artifacts(packaged_artifacts: list[tuple[str, Path]]) -> None:
    """Fail if any expected ZIP artifact is missing after packaging."""
    missing_artifacts = [
        artifact_path
        for _, artifact_path in packaged_artifacts
        if not artifact_path.exists() or not artifact_path.is_file()
    ]
    if missing_artifacts:
        formatted_paths = "\n".join(str(path) for path in missing_artifacts)
        raise SystemExit(f"Missing expected Lambda ZIP artifacts:\n{formatted_paths}")


def print_summary(*, repo_root: Path, packaged_artifacts: list[tuple[str, Path]]) -> None:
    """Print the packaged workload keys and repo-relative artifact paths."""
    print("\nPackaged Lambda workloads:")
    for function_key, artifact_path in packaged_artifacts:
        print(f"- {function_key}: {relative_to_repo(repo_root=repo_root, path=artifact_path)}")


def relative_to_repo(*, repo_root: Path, path: Path) -> str:
    """Return a readable repo-relative path when possible."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())
