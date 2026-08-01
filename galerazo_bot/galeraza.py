from __future__ import annotations

from .database import GalerazaScore
from .i18n import DEFAULT_LANGUAGE, t
from .pagination import MESSAGE_LIMIT, PaginatedPage, build_page_line_groups, render_prebuilt_pages


def render_galeraza_page(scores: list[GalerazaScore], page: int, language: str = DEFAULT_LANGUAGE) -> PaginatedPage:
    return render_prebuilt_pages(build_galeraza_pages(scores, language), page)


def build_galeraza_header(language: str = DEFAULT_LANGUAGE) -> str:
    return f"{t(language, 'galeraza.header')}\n"


def build_galeraza_lines(scores: list[GalerazaScore], language: str = DEFAULT_LANGUAGE) -> list[str]:
    if not scores:
        return [t(language, "galeraza.empty")]

    lines = []
    previous_points = None
    position = 0
    for index, score in enumerate(scores, start=1):
        if score.points != previous_points:
            position = index
            prefix = f"{position}. "
            previous_points = score.points
        else:
            prefix = " " * len(f"{position}. ")
        lines.append(f"{prefix}{_score_line(score, language)}")
    return lines


def build_galeraza_pages(
    scores: list[GalerazaScore],
    language: str = DEFAULT_LANGUAGE,
    max_chars: int = MESSAGE_LIMIT,
) -> list[str]:
    header = build_galeraza_header(language)
    groups = build_page_line_groups(header, build_galeraza_lines(scores, language), max_chars)
    pages = []
    score_index = 0
    for group in groups:
        page_lines = list(group)
        if score_index and _shares_position(scores, score_index):
            position = _position_at(scores, score_index)
            prefix_length = len(f"{position}. ")
            page_lines[1] = f"{position}. {page_lines[1][prefix_length:]}"
        pages.append("\n".join(page_lines))
        score_index += len(page_lines) - 1
    return pages


def _score_line(score: GalerazaScore, language: str) -> str:
    if score.display_name:
        name = score.display_name
    elif score.username:
        name = score.username
    else:
        name = t(language, "user.unknown")

    return f"{name} ({score.user_id}) => {score.points}"


def _shares_position(scores: list[GalerazaScore], index: int) -> bool:
    return scores[index].points == scores[index - 1].points


def _position_at(scores: list[GalerazaScore], index: int) -> int:
    points = scores[index].points
    return next(position for position, score in enumerate(scores, start=1) if score.points == points)
