from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
LAMBDAS_ROOT = REPO_ROOT / "lambdas"


def _prepend_sys_path(path: Path) -> None:
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


# Match the CI PYTHONPATH behavior locally so both import styles work:
# - from lambdas.<workload> import handler
# - from shared.auth import ...
_prepend_sys_path(REPO_ROOT)
_prepend_sys_path(LAMBDAS_ROOT)
