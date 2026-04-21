from __future__ import annotations

from .database import GalerazaScore
from .pagination import PaginatedPage, render_page


HEADER = "Galeraza!"


def render_galeraza_page(scores: list[GalerazaScore], page: int) -> PaginatedPage:
    return render_page(HEADER, build_galeraza_lines(scores), page)


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
