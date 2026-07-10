from __future__ import annotations

from .database import GalerazaScore
from .i18n import DEFAULT_LANGUAGE, t
from .pagination import PaginatedPage, render_page


def render_galeraza_page(scores: list[GalerazaScore], page: int, language: str = DEFAULT_LANGUAGE) -> PaginatedPage:
    return render_page(t(language, "galeraza.header"), build_galeraza_lines(scores, language), page)


def build_galeraza_lines(scores: list[GalerazaScore], language: str = DEFAULT_LANGUAGE) -> list[str]:
    return [_score_line(score, language) for score in scores]


def _score_line(score: GalerazaScore, language: str) -> str:
    if score.display_name:
        name = score.display_name
    elif score.username:
        name = score.username
    else:
        name = t(language, "user.unknown")

    return f"{name} ({score.user_id}) => {score.points}"
