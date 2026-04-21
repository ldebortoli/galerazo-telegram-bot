from __future__ import annotations

from dataclasses import dataclass

from .database import GalerazaScore


HEADER = "Galeraza!"
MESSAGE_LIMIT = 4096
BUTTON_PREFIX = "galeraza"


@dataclass(frozen=True)
class GalerazaPage:
    text: str
    page: int
    total_pages: int


def build_galeraza_pages(
    scores: list[GalerazaScore],
    max_chars: int = MESSAGE_LIMIT,
) -> list[str]:
    lines = [HEADER]
    for score in scores:
        lines.append(f"{_score_name(score)} => {score.points}")

    pages: list[str] = []
    current_lines = [HEADER]
    current_len = len(HEADER)

    for line in lines[1:]:
        next_len = current_len + 1 + len(line)
        if len(current_lines) > 1 and next_len > max_chars:
            pages.append("\n".join(current_lines))
            current_lines = [HEADER, line]
            current_len = len(HEADER) + 1 + len(line)
            continue

        current_lines.append(line)
        current_len = next_len

    pages.append("\n".join(current_lines))
    return pages


def render_galeraza_page(
    scores: list[GalerazaScore],
    page: int,
    max_chars: int = MESSAGE_LIMIT,
) -> GalerazaPage:
    pages = build_galeraza_pages(scores, max_chars)
    total_pages = len(pages)
    safe_page = min(max(page, 1), total_pages)
    return GalerazaPage(text=pages[safe_page - 1], page=safe_page, total_pages=total_pages)


def build_galeraza_keyboard(
    message_id: str,
    page: int,
    total_pages: int,
    unlocked: bool,
) -> dict | None:
    if total_pages <= 1:
        return {
            "inline_keyboard": [[_lock_button(message_id, page, unlocked), _delete_button(message_id)]]
        }

    page_buttons = []
    for item in _page_button_items(page, total_pages):
        if item == "first":
            page_buttons.append(_page_button(message_id, 1, "<<"))
        elif item == "last":
            page_buttons.append(_page_button(message_id, total_pages, ">>"))
        else:
            label = f"[ {item} ]" if item == page else str(item)
            page_buttons.append(_page_button(message_id, item, label))

    return {
        "inline_keyboard": [
            page_buttons,
            [_lock_button(message_id, page, unlocked), _delete_button(message_id)],
        ]
    }


def parse_callback_data(data: str) -> tuple[str, str, str | None] | None:
    parts = data.split(":")
    if len(parts) < 3 or parts[0] != BUTTON_PREFIX:
        return None

    action = parts[1]
    message_id = parts[2]
    value = parts[3] if len(parts) > 3 else None
    return action, message_id, value


def _score_name(score: GalerazaScore) -> str:
    if score.username:
        return f"@{score.username}"
    if score.display_name:
        return score.display_name
    return score.user_id


def _page_button_items(page: int, total_pages: int) -> list[int | str]:
    if total_pages <= 5:
        return list(range(1, total_pages + 1))

    if page <= 2:
        return [1, 2, 3, 4, "last"]
    if page >= total_pages - 1:
        return ["first", total_pages - 3, total_pages - 2, total_pages - 1, total_pages]

    return ["first", page - 1, page, page + 1, "last"]


def _page_button(message_id: str, page: int, label: str) -> dict:
    return {"text": label, "callback_data": f"{BUTTON_PREFIX}:page:{message_id}:{page}"}


def _lock_button(message_id: str, page: int, unlocked: bool) -> dict:
    label = "🔓" if unlocked else "🔒"
    return {"text": label, "callback_data": f"{BUTTON_PREFIX}:unlock:{message_id}:{page}"}


def _delete_button(message_id: str) -> dict:
    return {"text": "❌", "callback_data": f"{BUTTON_PREFIX}:delete:{message_id}"}
