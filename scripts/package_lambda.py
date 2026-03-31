#!/usr/bin/env python3
"""
Create a deterministic Lambda ZIP artifact from a source directory.

This script intentionally stays small and standard-library-only so the same
packaging command can be reused locally and later in CI/CD without introducing
platform-specific shell logic or extra build tooling.
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


def main() -> int:
    args = parse_args()

    source_dir = args.source_dir.resolve()
    output_path = args.output_path.resolve()

    validate_source_dir(source_dir)
    package_lambda(source_dir=source_dir, output_path=output_path)

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
    return parser.parse_args()


def validate_source_dir(source_dir: Path) -> None:
    if not source_dir.exists():
        raise SystemExit(f"Source directory does not exist: {source_dir}")

    if not source_dir.is_dir():
        raise SystemExit(f"Source path is not a directory: {source_dir}")


def package_lambda(*, source_dir: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files_to_package = [
        path for path in sorted(source_dir.rglob("*"))
        if path.is_file() and not is_excluded(path=path, source_dir=source_dir)
    ]

    if not files_to_package:
        raise SystemExit(f"No packageable files found in: {source_dir}")

    if output_path.exists():
        output_path.unlink()

    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in files_to_package:
            archive_name = file_path.relative_to(source_dir).as_posix()
            zip_info = ZipInfo(filename=archive_name, date_time=FIXED_ZIP_TIMESTAMP)
            zip_info.compress_type = ZIP_DEFLATED
            zip_info.external_attr = 0o100644 << 16

            zip_file.writestr(zip_info, file_path.read_bytes())


def is_excluded(*, path: Path, source_dir: Path) -> bool:
    relative_parts = path.relative_to(source_dir).parts

    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_parts[:-1]):
        return True

    if path.suffix in EXCLUDED_FILE_SUFFIXES:
        return True

    if path.name.startswith(EXCLUDED_FILE_PREFIXES):
        return True

    return False


if __name__ == "__main__":
    sys.exit(main())
