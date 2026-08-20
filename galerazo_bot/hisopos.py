from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .database import HisopoScore
from .i18n import DEFAULT_LANGUAGE, t
from .pagination import MESSAGE_LIMIT, PaginatedPage, build_page_line_groups, render_prebuilt_pages


ARGENTINA_TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
HISOPO_EXPIRATION = timedelta(minutes=20)
HISOPO_FLEETING_EXPIRATION = timedelta(minutes=1)
HISOPO_CALLBACK_PREFIX = "hisopo"
HISOPO_CAPTURE_CALLBACK = f"{HISOPO_CALLBACK_PREFIX}:capture"
HISOPO_INTENSITIES = {
    "very_low": 1,
    "low": 5,
    "medium": 10,
    "high": 15,
    "very_high": 20,
}


@dataclass(frozen=True)
class HisopoKind:
    key: str
    points: int
    expiration: timedelta = HISOPO_EXPIRATION
    next_day_spawns: int = 1
    hides_points: bool = False


COMMON_HISOPO = HisopoKind("common", 1)
SILVER_HISOPO = HisopoKind("silver", 2)
GOLD_HISOPO = HisopoKind("gold", 3)
FLEETING_HISOPO = HisopoKind("fleeting", 5, expiration=HISOPO_FLEETING_EXPIRATION)
MYSTERY_HISOPO = HisopoKind("mystery", 0, hides_points=True)
PUTRID_HISOPO = HisopoKind("putrid", -2)
RADIOACTIVE_HISOPO = HisopoKind("radioactive", 0)
FAKE_HISOPO = HisopoKind("fake", 0, next_day_spawns=0)
TWIN_HISOPO = HisopoKind("twin", 4, next_day_spawns=2)
DIAMOND_HISOPO = HisopoKind("diamond", 10)

HISOPO_KINDS = {
    kind.key: kind
    for kind in (
        COMMON_HISOPO,
        SILVER_HISOPO,
        GOLD_HISOPO,
        FLEETING_HISOPO,
        MYSTERY_HISOPO,
        PUTRID_HISOPO,
        RADIOACTIVE_HISOPO,
        FAKE_HISOPO,
        TWIN_HISOPO,
        DIAMOND_HISOPO,
    )
}
HISOPO_PROBABILITY_RANGES = {
    "common": (1, 45),
    "silver": (46, 58),
    "gold": (59, 68),
    "fleeting": (69, 75),
    "mystery": (76, 82),
    "putrid": (83, 87),
    "radioactive": (88, 91),
    "fake": (92, 93),
    "twin": (94, 95),
    "diamond": (96, 100),
}
RADIOACTIVE_POINT_VALUES = (-3, -1, 2, 4, 6)
MYSTERY_POINT_VALUES = (-3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 10)


def should_spawn_hisopo(intensity_percent: int, roll: int) -> bool:
    if intensity_percent not in HISOPO_INTENSITIES.values():
        raise ValueError("Intensidad de Hisopos invalida.")
    if not 1 <= roll <= 100:
        raise ValueError("La tirada de Hisopos debe estar entre 1 y 100.")
    return roll <= intensity_percent


def select_hisopo_kind(
    roll: int,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> HisopoKind:
    if not 1 <= roll <= 100:
        raise ValueError("La tirada de tipo de Hisopo debe estar entre 1 y 100.")
    kind = next(
        HISOPO_KINDS[key]
        for key, (lower, upper) in HISOPO_PROBABILITY_RANGES.items()
        if lower <= roll <= upper
    )
    if kind.key == "radioactive":
        return replace(kind, points=RADIOACTIVE_POINT_VALUES[randbelow(len(RADIOACTIVE_POINT_VALUES))])
    if kind.key == "mystery":
        return replace(kind, points=MYSTERY_POINT_VALUES[randbelow(len(MYSTERY_POINT_VALUES))])
    return kind


def hisopo_kind_for_spawn(key: str, points: int) -> HisopoKind:
    try:
        return replace(HISOPO_KINDS[key], points=points)
    except KeyError as exc:
        raise ValueError(f"Tipo de Hisopo desconocido: {key}") from exc


def random_next_day_datetime(
    now: datetime,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> datetime:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    next_local_date = now.astimezone(ARGENTINA_TIMEZONE).date() + timedelta(days=1)
    next_local_midnight = datetime.combine(next_local_date, time.min, tzinfo=ARGENTINA_TIMEZONE)
    return (next_local_midnight + timedelta(seconds=randbelow(24 * 60 * 60))).astimezone(timezone.utc)


def intensity_translation_key(intensity_percent: int) -> str:
    for key, percent in HISOPO_INTENSITIES.items():
        if percent == intensity_percent:
            return f"hisopos.intensity.{key}"
    raise ValueError("Intensidad de Hisopos invalida.")


def render_hisopo_page(
    scores: list[HisopoScore],
    page: int,
    language: str = DEFAULT_LANGUAGE,
) -> PaginatedPage:
    return render_prebuilt_pages(build_hisopo_pages(scores, language), page)


def build_hisopo_pages(
    scores: list[HisopoScore],
    language: str = DEFAULT_LANGUAGE,
    max_chars: int = MESSAGE_LIMIT,
) -> list[str]:
    header = f"{t(language, 'hisopos.header')}\n"
    groups = build_page_line_groups(header, build_hisopo_lines(scores, language), max_chars)
    pages = []
    score_index = 0
    for group in groups:
        page_lines = list(group)
        if score_index and scores[score_index].points == scores[score_index - 1].points:
            position = _position_at(scores, score_index)
            prefix_length = len(f"{position}. ")
            page_lines[1] = f"{position}. {page_lines[1][prefix_length:]}"
        pages.append("\n".join(page_lines))
        score_index += len(page_lines) - 1
    return pages


def build_hisopo_lines(
    scores: list[HisopoScore],
    language: str = DEFAULT_LANGUAGE,
) -> list[str]:
    if not scores:
        return [t(language, "hisopos.empty")]

    lines = []
    previous_points = None
    position = 0
    for index, score in enumerate(scores, start=1):
        if score.points != previous_points:
            position = index
            prefix = f"{position}. "
            previous_points = score.points
        else:
            prefix = "-" + " " * (len(f"{position}. ") - 1)
        name = score.display_name or score.username or t(language, "user.unknown")
        lines.append(f"{prefix}{name} ({score.user_id}) => {score.points}")
    return lines


def _position_at(scores: list[HisopoScore], index: int) -> int:
    points = scores[index].points
    return next(position for position, score in enumerate(scores, start=1) if score.points == points)
