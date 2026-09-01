from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .announcements import maximum_formatted_announcement_length


BROADCAST_CHANGELOG_PATH = Path(__file__).resolve().parent.parent / "BROADCAST_CHANGELOG.md"
BROADCAST_HEADER_PATTERN = re.compile(
    r"^## \[([^]]+)\] desde=\[([^]]+)\] estado=(borrador|aprobado|omitido)$"
)
NO_PREVIOUS_VERSION = "ninguna"


@dataclass(frozen=True)
class ReleaseBroadcast:
    version: str
    previous_version: str | None
    status: str
    text: str


def release_broadcast_entries(
    path: Path = BROADCAST_CHANGELOG_PATH,
) -> tuple[ReleaseBroadcast, ...]:
    entries: list[ReleaseBroadcast] = []
    current: tuple[str, str | None, str] | None = None
    body: list[str] = []

    def finish_entry() -> None:
        if current is None:
            return
        version, previous_version, status = current
        entries.append(
            ReleaseBroadcast(
                version=version,
                previous_version=previous_version,
                status=status,
                text="\n".join(body).strip(),
            )
        )

    for line in path.read_text(encoding="utf-8").splitlines():
        match = BROADCAST_HEADER_PATTERN.match(line)
        if match is None:
            if current is not None:
                body.append(line)
            continue
        finish_entry()
        version, previous, status = match.groups()
        current = (
            version,
            None if previous == NO_PREVIOUS_VERSION else previous,
            status,
        )
        body = []
    finish_entry()

    versions = [entry.version for entry in entries]
    if len(versions) != len(set(versions)):
        raise ValueError("BROADCAST_CHANGELOG.md contiene versiones duplicadas")
    return tuple(entries)


def release_broadcast_entry(
    version: str,
    path: Path = BROADCAST_CHANGELOG_PATH,
) -> ReleaseBroadcast:
    try:
        return next(entry for entry in release_broadcast_entries(path) if entry.version == version)
    except StopIteration as exc:
        raise ValueError(
            f"BROADCAST_CHANGELOG.md no contiene un resumen para la version {version}"
        ) from exc


def validate_release_broadcast(
    version: str,
    max_chars: int,
    *,
    path: Path = BROADCAST_CHANGELOG_PATH,
    require_approved: bool = True,
) -> tuple[ReleaseBroadcast, int]:
    entry = release_broadcast_entry(version, path)
    if entry.status == "omitido":
        if entry.text:
            raise ValueError(
                f"el broadcast omitido de la version {version} no debe contener texto"
            )
        return entry, 0
    if require_approved and entry.status != "aprobado":
        raise ValueError(f"el broadcast de la version {version} sigue en borrador")
    if not entry.text:
        raise ValueError(f"el broadcast de la version {version} esta vacio")
    expected_title = f"Novedades de Galerazo Bot v{version}"
    if entry.text.splitlines()[0] != expected_title:
        raise ValueError(f"el broadcast debe comenzar con: {expected_title}")
    maximum_length = maximum_formatted_announcement_length(entry.text)
    if maximum_length > max_chars:
        raise ValueError(
            f"el broadcast formateado tiene {maximum_length} caracteres y supera "
            f"el limite de Telegram de {max_chars}"
        )
    return entry, maximum_length


def release_broadcast_notes(
    version: str,
    announced_version: str | None,
    max_chars: int,
    *,
    path: Path = BROADCAST_CHANGELOG_PATH,
) -> str | None:
    entry, _maximum_length = validate_release_broadcast(
        version,
        max_chars,
        path=path,
    )
    if entry.previous_version != announced_version:
        expected = entry.previous_version or NO_PREVIOUS_VERSION
        actual = announced_version or NO_PREVIOUS_VERSION
        raise ValueError(
            f"el resumen aprobado parte de {expected}, pero produccion tiene anunciado {actual}"
        )
    if entry.status == "omitido":
        return None
    return entry.text
