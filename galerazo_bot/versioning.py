from __future__ import annotations

from pathlib import Path
import re


CURRENT_VERSION = "0.6"
CHANGELOG_PATH = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")


def current_release_notes() -> str:
    lines = CHANGELOG_PATH.read_text(encoding="utf-8").splitlines()
    header = f"## [{CURRENT_VERSION}]"
    try:
        start = next(index for index, line in enumerate(lines) if line.startswith(header)) + 1
    except StopIteration as exc:
        raise ValueError(f"CHANGELOG.md no contiene la version {CURRENT_VERSION}") from exc

    release_lines: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line:
            release_lines.append(line)

    if not release_lines:
        raise ValueError(f"CHANGELOG.md no contiene cambios para la version {CURRENT_VERSION}")
    plain_release_lines = [INLINE_CODE_PATTERN.sub(r"\1", line) for line in release_lines]
    return f"Novedades de Galerazo Bot v{CURRENT_VERSION}\n\n" + "\n".join(plain_release_lines)
