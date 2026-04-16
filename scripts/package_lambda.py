#!/usr/bin/env python3
"""
Create a deterministic Lambda ZIP artifact for one Lambda workload.

What this script packages:
- the selected Lambda source directory
- the shared Lambda helpers under `lambdas/shared`
- optionally, one vendored dependency directory

Why this script exists:
- Lambda deployments in this repo use ZIP artifacts
- we want the packaging step to behave the same locally and later in CI/CD
- we want the ZIP contents to be deterministic so repeated packaging does not
  produce noisy differences when the inputs have not changed

This script intentionally stays small and uses only the Python standard library
so it does not introduce extra build tooling or platform-specific shell logic.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXCLUDED_DIRECTORY_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".venv",
    "venv",
    "env",
    "ENV",
    "tests",
}
EXCLUDED_FILE_SUFFIXES = {".pyc", ".pyo", ".zip"}
EXCLUDED_FILE_PREFIXES = ("test_",)
EXCLUDED_FILE_NAMES = {
    ".gitkeep",
    ".DS_Store",
}


def main() -> int:
    # Resolve the requested inputs once up front so the rest of the script can
    # work with absolute paths and validated directories only.
    args = parse_args()

    source_dir = args.source_dir.resolve()
    output_path = args.output_path.resolve()
    shared_dir = resolve_shared_dir()
    vendor_dir = args.vendor_dir.resolve() if args.vendor_dir is not None else None

    validate_source_dir(source_dir)
    validate_shared_dir(shared_dir)
    if vendor_dir is not None:
        validate_vendor_dir(vendor_dir)

    package_lambda(
        source_dir=source_dir,
        shared_dir=shared_dir,
        vendor_dir=vendor_dir,
        output_path=output_path,
    )

    print(f"Packaged {source_dir} -> {output_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package a Lambda source directory into a deterministic ZIP artifact."
    )
    parser.add_argument(
        "source_dir",
        type=Path,
        help="Path to the Lambda source directory to package.",
    )
    parser.add_argument(
        "output_path",
        type=Path,
        help="Path where the ZIP artifact should be written.",
    )
    parser.add_argument(
        "--vendor-dir",
        type=Path,
        default=None,
        help=(
            "Optional path to one vendored dependency directory whose contents "
            "should be packaged at the ZIP archive root so vendored modules "
            "can be imported directly."
        ),
    )
    return parser.parse_args()


def validate_source_dir(source_dir: Path) -> None:
    if not source_dir.exists():
        raise SystemExit(f"Source directory does not exist: {source_dir}")

    if not source_dir.is_dir():
        raise SystemExit(f"Source path is not a directory: {source_dir}")


def resolve_shared_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "lambdas" / "shared"


def validate_shared_dir(shared_dir: Path) -> None:
    if not shared_dir.exists():
        raise SystemExit(f"Shared Lambda directory does not exist: {shared_dir}")

    if not shared_dir.is_dir():
        raise SystemExit(f"Shared Lambda path is not a directory: {shared_dir}")


def validate_vendor_dir(vendor_dir: Path) -> None:
    if not vendor_dir.exists():
        raise SystemExit(f"Vendor directory does not exist: {vendor_dir}")

    if not vendor_dir.is_dir():
        raise SystemExit(f"Vendor path is not a directory: {vendor_dir}")


def package_lambda(
    *,
    source_dir: Path,
    shared_dir: Path,
    vendor_dir: Path | None,
    output_path: Path,
) -> None:
    # Build one deterministic ZIP file from the normalized input directories.
    # The output is replaced on each run so repeated packaging starts cleanly.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files_to_package = collect_files_to_package(
        source_dir=source_dir,
        shared_dir=shared_dir,
        vendor_dir=vendor_dir,
    )

    if not files_to_package:
        raise SystemExit(f"No packageable files found in: {source_dir}")

    if output_path.exists():
        output_path.unlink()

    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
        for file_path, archive_name in files_to_package:
            zip_info = ZipInfo(filename=archive_name, date_time=FIXED_ZIP_TIMESTAMP)
            zip_info.compress_type = ZIP_DEFLATED
            zip_info.external_attr = 0o100644 << 16

            zip_file.writestr(zip_info, file_path.read_bytes())


def collect_files_to_package(
    *,
    source_dir: Path,
    shared_dir: Path,
    vendor_dir: Path | None,
) -> list[tuple[Path, str]]:
    # Collect every file once and compute the exact archive path it will have
    # inside the ZIP. Tracking archive names here lets us fail early if two
    # different inputs would collide at the same ZIP path.
    packaged_files: list[tuple[Path, str]] = []
    seen_archive_names: set[str] = set()

    def add_directory(
        directory: Path,
        *,
        archive_base: Path,
        skipped_roots: tuple[Path, ...] = (),
    ) -> None:
        for file_path in sorted(directory.rglob("*")):
            if any(file_path.is_relative_to(skipped_root) for skipped_root in skipped_roots):
                continue
            if not file_path.is_file():
                continue
            if is_excluded(path=file_path, source_dir=directory):
                continue

            archive_name = file_path.relative_to(archive_base).as_posix()
            if archive_name in seen_archive_names:
                raise SystemExit(f"Duplicate archive path generated while packaging: {archive_name}")

            packaged_files.append((file_path, archive_name))
            seen_archive_names.add(archive_name)

    add_directory(
        source_dir,
        archive_base=source_dir,
        skipped_roots=(vendor_dir,) if vendor_dir is not None else (),
    )
    add_directory(shared_dir, archive_base=shared_dir.parent)
    if vendor_dir is not None:
        add_directory(vendor_dir, archive_base=vendor_dir)

    return packaged_files


def is_excluded(*, path: Path, source_dir: Path) -> bool:
    # Apply the same exclusion rules regardless of whether the file comes from
    # the Lambda source, shared helpers, or an optional vendor directory.
    relative_parts = path.relative_to(source_dir).parts

    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_parts[:-1]):
        return True

    if path.suffix in EXCLUDED_FILE_SUFFIXES:
        return True

    if path.name in EXCLUDED_FILE_NAMES:
        return True

    if path.name.startswith(EXCLUDED_FILE_PREFIXES):
        return True

    return False


if __name__ == "__main__":
    sys.exit(main())
