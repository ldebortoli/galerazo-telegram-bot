from __future__ import annotations

import platform
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON_VERSION_FILE = PROJECT_ROOT / ".python-version"


def required_python_version() -> str:
    return PYTHON_VERSION_FILE.read_text(encoding="ascii").strip()


def ensure_python_version() -> None:
    required = required_python_version()
    actual = platform.python_version()
    if actual != required:
        series = ".".join(required.split(".")[:2])
        raise RuntimeError(
            f"Este proyecto requiere Python {required}, pero esta ejecutando Python {actual}. "
            f"Recrea .venv con: py -{series} -m venv .venv"
        )
