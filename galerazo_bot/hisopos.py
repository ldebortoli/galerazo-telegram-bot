from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .database import HisopoCollectionEntry, HisopoScore
from .i18n import DEFAULT_LANGUAGE, t
from .pagination import MESSAGE_LIMIT, PaginatedPage, build_page_line_groups, render_prebuilt_pages


ARGENTINA_TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
HISOPO_EXPIRATION = timedelta(minutes=20)
HISOPO_FLEETING_EXPIRATION = timedelta(minutes=1)
HISOPO_CALLBACK_PREFIX = "hisopo"
HISOPO_CAPTURE_CALLBACK = f"{HISOPO_CALLBACK_PREFIX}:capture"
HISOPO_BOMB_CALLBACK_PREFIX = f"{HISOPO_CALLBACK_PREFIX}:bomb"
HISOPO_RACE_CALLBACK = f"{HISOPO_CALLBACK_PREFIX}:race"
HISOPO_BOMB_SLOT_COUNT = 16
HISOPO_BOMB_DEFUSE_POINTS = 10
HISOPO_BOMB_EXPLOSION_POINTS = -10
HISOPO_RACE_REQUIRED_PRESSES = 20
HISOPO_RACE_MIN_PRESS_INTERVAL = timedelta(milliseconds=100)
HISOPO_TYPE_ROLL_MAX = 10_000
HISOPO_GIANT_MAX_HELPERS = 15
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
    immediate_spawns: int = 0
    hides_points: bool = False


@dataclass(frozen=True)
class HisopoSelection:
    actual: HisopoKind
    appearance: HisopoKind


COMMON_HISOPO = HisopoKind("common", 1)
SILVER_HISOPO = HisopoKind("silver", 2)
GOLD_HISOPO = HisopoKind("gold", 3)
FLEETING_HISOPO = HisopoKind("fleeting", 5, expiration=HISOPO_FLEETING_EXPIRATION)
MYSTERY_HISOPO = HisopoKind("mystery", 0, hides_points=True)
PUTRID_HISOPO = HisopoKind("putrid", -2)
RADIOACTIVE_HISOPO = HisopoKind("radioactive", 0, hides_points=True)
BOMB_HISOPO = HisopoKind("bomb", HISOPO_BOMB_DEFUSE_POINTS, hides_points=True)
FRENETIC_HISOPO = HisopoKind("frenetic", 3)
BLACK_HOLE_HISOPO = HisopoKind("black_hole", 10, hides_points=True)
FAKE_HISOPO = HisopoKind("fake", 0, next_day_spawns=0)
TWIN_HISOPO = HisopoKind("twin", 4, immediate_spawns=1)
DIAMOND_HISOPO = HisopoKind("diamond", 10)
GIANT_HISOPO = HisopoKind("giant", 4)
MIRACLE_HISOPO = HisopoKind("miracle", 15, hides_points=True)
EXPIRED_HISOPO = HisopoKind("expired", 0, next_day_spawns=0)

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
        BOMB_HISOPO,
        FRENETIC_HISOPO,
        BLACK_HOLE_HISOPO,
        FAKE_HISOPO,
        TWIN_HISOPO,
        DIAMOND_HISOPO,
        GIANT_HISOPO,
        MIRACLE_HISOPO,
        EXPIRED_HISOPO,
    )
}
COLLECTIBLE_HISOPO_KEYS = tuple(HISOPO_KINDS)
HISOPO_PROBABILITY_RANGES = {
    "common": (1, 3465),
    "silver": (3466, 4865),
    "gold": (4866, 5865),
    "fleeting": (5866, 6565),
    "mystery": (6566, 7265),
    "putrid": (7266, 7765),
    "radioactive": (7766, 8165),
    "bomb": (8166, 8565),
    "frenetic": (8566, 8965),
    "black_hole": (8966, 9365),
    "fake": (9366, 9665),
    "twin": (9666, 9865),
    "diamond": (9866, 9965),
    "giant": (9966, 9990),
    "miracle": (9991, 10_000),
}
RADIOACTIVE_POINT_VALUES = (-3, -1, 2, 4, 6)
HISOPO_DISGUISE_PROBABILITY_RANGES = {
    "common": (1, 75),
    "silver": (76, 89),
    "gold": (90, 99),
    "diamond": (100, 100),
}


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
    if not 1 <= roll <= HISOPO_TYPE_ROLL_MAX:
        raise ValueError("La tirada de tipo de Hisopo debe estar entre 1 y 10000.")
    kind = next(
        HISOPO_KINDS[key]
        for key, (lower, upper) in HISOPO_PROBABILITY_RANGES.items()
        if lower <= roll <= upper
    )
    return kind


def select_hisopo_spawn(
    roll: int,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> HisopoSelection:
    outer_kind = select_hisopo_kind(roll, randbelow=randbelow)
    if outer_kind.key == "mystery":
        actual_kind = _select_weighted_non_mystery_kind(randbelow)
        return HisopoSelection(actual=actual_kind, appearance=MYSTERY_HISOPO)
    if outer_kind.key in {"fake", "putrid"}:
        return HisopoSelection(
            actual=outer_kind,
            appearance=select_hisopo_disguise(randbelow),
        )
    return HisopoSelection(actual=outer_kind, appearance=outer_kind)


def select_hisopo_disguise(
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> HisopoKind:
    roll = randbelow(100) + 1
    return next(
        HISOPO_KINDS[key]
        for key, (lower, upper) in HISOPO_DISGUISE_PROBABILITY_RANGES.items()
        if lower <= roll <= upper
    )


def select_bomb_slots(
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> tuple[int, int]:
    success_slot = randbelow(HISOPO_BOMB_SLOT_COUNT)
    explosion_slot = randbelow(HISOPO_BOMB_SLOT_COUNT - 1)
    if explosion_slot >= success_slot:
        explosion_slot += 1
    return success_slot, explosion_slot


def _select_weighted_non_mystery_kind(
    randbelow: Callable[[int], int],
) -> HisopoKind:
    weighted_kinds = [
        (HISOPO_KINDS[key], upper - lower + 1)
        for key, (lower, upper) in HISOPO_PROBABILITY_RANGES.items()
        if key != MYSTERY_HISOPO.key
    ]
    roll = randbelow(sum(weight for _kind, weight in weighted_kinds)) + 1
    cumulative = 0
    for kind, weight in weighted_kinds:
        cumulative += weight
        if roll <= cumulative:
            return kind
    raise RuntimeError("No se pudo seleccionar el contenido del Hisopo misterioso.")


def radioactive_points_at(spawned_at: datetime, captured_at: datetime) -> int:
    if spawned_at.tzinfo is None:
        spawned_at = spawned_at.replace(tzinfo=timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    elapsed_minutes = max((captured_at - spawned_at).total_seconds(), 0.0) / 60
    if elapsed_minutes < 5:
        return RADIOACTIVE_POINT_VALUES[0]
    if elapsed_minutes < 10:
        return RADIOACTIVE_POINT_VALUES[1]
    if elapsed_minutes < 15:
        return RADIOACTIVE_POINT_VALUES[2]
    if elapsed_minutes < 18:
        return RADIOACTIVE_POINT_VALUES[3]
    return RADIOACTIVE_POINT_VALUES[4]


def is_fleeting_window_expired(spawned_at: datetime, captured_at: datetime) -> bool:
    if spawned_at.tzinfo is None:
        spawned_at = spawned_at.replace(tzinfo=timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    return captured_at >= spawned_at + HISOPO_FLEETING_EXPIRATION


def hisopo_kind_for_spawn(key: str, points: int) -> HisopoKind:
    try:
        return replace(HISOPO_KINDS[key], points=points)
    except KeyError as exc:
        raise ValueError(f"Tipo de Hisopo desconocido: {key}") from exc


def giant_required_helpers(chat_member_count: int) -> int:
    if chat_member_count < 1:
        raise ValueError("La cantidad de miembros del chat debe ser positiva.")
    human_member_count = max(chat_member_count - 1, 1)
    return min(human_member_count, HISOPO_GIANT_MAX_HELPERS)


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


def render_hisopo_collection(
    entries: list[HisopoCollectionEntry],
    user_name: str,
    user_id: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    counts = {entry.hisopo_type: entry.capture_count for entry in entries}
    discovered = sum(counts.get(key, 0) > 0 for key in COLLECTIBLE_HISOPO_KEYS)
    captures = sum(counts.get(key, 0) for key in COLLECTIBLE_HISOPO_KEYS)
    lines = [
        t(
            language,
            "hisopos.collection.header",
            user=user_name,
            user_id=user_id,
        ),
        t(
            language,
            "hisopos.collection.progress",
            discovered=discovered,
            total=len(COLLECTIBLE_HISOPO_KEYS),
            captures=captures,
        ),
        "",
    ]
    for key in COLLECTIBLE_HISOPO_KEYS:
        count = counts.get(key, 0)
        marker = "✅" if count else "❓"
        type_key = (
            "hisopos.collection.type.giant"
            if key == "giant"
            else f"hisopos.type.{key}"
        )
        lines.append(f"{marker} {t(language, type_key)}: {count}")
    return "\n".join(lines)


def _position_at(scores: list[HisopoScore], index: int) -> int:
    points = scores[index].points
    return next(position for position, score in enumerate(scores, start=1) if score.points == points)
