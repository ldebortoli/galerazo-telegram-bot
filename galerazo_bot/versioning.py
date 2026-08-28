from __future__ import annotations

from pathlib import Path
import re


CURRENT_VERSION = "0.45"
CHANGELOG_PATH = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
VERSION_HEADER_PATTERN = re.compile(r"^## \[([^]]+)\]")


def current_release_notes() -> str:
    entries = _release_entries()
    try:
        _version, release_lines = next(entry for entry in entries if entry[0] == CURRENT_VERSION)
    except StopIteration as exc:
        raise ValueError(f"CHANGELOG.md no contiene la version {CURRENT_VERSION}") from exc

    if not release_lines:
        raise ValueError(f"CHANGELOG.md no contiene cambios para la version {CURRENT_VERSION}")
    return _format_release_notes(CURRENT_VERSION, release_lines)


def pending_release_notes(announced_version: str | None) -> str:
    """Return the current entry plus any newer entries not yet announced."""
    entries = _release_entries()
    current_index = next(
        (index for index, entry in enumerate(entries) if entry[0] == CURRENT_VERSION),
        None,
    )
    if current_index is None:
        raise ValueError(f"CHANGELOG.md no contiene la version {CURRENT_VERSION}")

    current_version, current_lines = entries[current_index]
    if not current_lines:
        raise ValueError(f"CHANGELOG.md no contiene cambios para la version {CURRENT_VERSION}")
    if announced_version is None:
        return _format_release_notes(current_version, current_lines)

    announced_index = next(
        (index for index, entry in enumerate(entries) if entry[0] == announced_version),
        None,
    )
    if announced_index is None or announced_index <= current_index:
        return _format_release_notes(current_version, current_lines)

    pending_entries = entries[current_index : announced_index]
    sections = ["\n".join(_plain_lines(current_lines))]
    for version, lines in pending_entries[1:]:
        if lines:
            sections.append(f"Cambios acumulados de v{version}:\n" + "\n".join(_plain_lines(lines)))
    return f"Novedades de Galerazo Bot v{current_version}\n\n" + "\n\n".join(sections)


def _release_entries() -> list[tuple[str, list[str]]]:
    entries: list[tuple[str, list[str]]] = []
    version: str | None = None
    release_lines: list[str] = []
    for line in CHANGELOG_PATH.read_text(encoding="utf-8").splitlines():
        match = VERSION_HEADER_PATTERN.match(line)
        if match is not None:
            if version is not None:
                entries.append((version, release_lines))
            version = match.group(1)
            release_lines = []
        elif version is not None and line:
            release_lines.append(line)
    if version is not None:
        entries.append((version, release_lines))
    return entries


def _format_release_notes(version: str, lines: list[str]) -> str:
    return f"Novedades de Galerazo Bot v{version}\n\n" + "\n".join(_plain_lines(lines))


def _plain_lines(lines: list[str]) -> list[str]:
    return [INLINE_CODE_PATTERN.sub(r"\1", line) for line in lines]
