from __future__ import annotations

from .database import GalerazaScore
from .i18n import DEFAULT_LANGUAGE, t
from .pagination import PaginatedPage, render_page


def render_galeraza_page(scores: list[GalerazaScore], page: int, language: str = DEFAULT_LANGUAGE) -> PaginatedPage:
    return render_page(t(language, "galeraza.header"), build_galeraza_lines(scores), page)


def build_galeraza_lines(scores: list[GalerazaScore]) -> list[str]:
    return [_score_line(score) for score in scores]


def _score_line(score: GalerazaScore) -> str:
    if score.username:
        name = f"@{score.username}"
    elif score.display_name:
        name = score.display_name
    else:
        name = score.user_id

    return f"{name} => {score.points}"
