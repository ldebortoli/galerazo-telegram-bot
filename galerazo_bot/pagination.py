from __future__ import annotations

from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


MESSAGE_LIMIT = 4096
BUTTON_PREFIX = "paginated"


@dataclass(frozen=True)
class PaginatedPage:
    text: str
    page: int
    total_pages: int


def build_pages(header: str, lines: list[str], max_chars: int = MESSAGE_LIMIT) -> list[str]:
    pages: list[str] = []
    current_lines = [header]
    current_len = len(header)

    for line in lines:
        next_len = current_len + 1 + len(line)
        if len(current_lines) > 1 and next_len > max_chars:
            pages.append("\n".join(current_lines))
            current_lines = [header, line]
            current_len = len(header) + 1 + len(line)
            continue

        current_lines.append(line)
        current_len = next_len

    pages.append("\n".join(current_lines))
    return pages


def render_page(header: str, lines: list[str], page: int, max_chars: int = MESSAGE_LIMIT) -> PaginatedPage:
    pages = build_pages(header, lines, max_chars)
    total_pages = len(pages)
    safe_page = min(max(page, 1), total_pages)
    return PaginatedPage(text=pages[safe_page - 1], page=safe_page, total_pages=total_pages)


def build_keyboard(
    message_id: str,
    page: int,
    total_pages: int,
    unlocked: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if total_pages > 1:
        page_buttons = []
        for item in _page_button_items(page, total_pages):
            if item == "first":
                page_buttons.append(_page_button(message_id, 1, "<<"))
            elif item == "last":
                page_buttons.append(_page_button(message_id, total_pages, ">>"))
            else:
                label = f"[ {item} ]" if item == page else str(item)
                page_buttons.append(_page_button(message_id, item, label))
        rows.append(page_buttons)

    rows.append([_lock_button(message_id, page, unlocked), _delete_button(message_id)])
    return InlineKeyboardMarkup(rows)


def parse_callback_data(data: str) -> tuple[str, str, str | None] | None:
    parts = data.split(":")
    if len(parts) < 3 or parts[0] != BUTTON_PREFIX:
        return None

    action = parts[1]
    message_id = parts[2]
    value = parts[3] if len(parts) > 3 else None
    return action, message_id, value


def _page_button_items(page: int, total_pages: int) -> list[int | str]:
    if total_pages <= 5:
        return list(range(1, total_pages + 1))
    if page <= 2:
        return [1, 2, 3, 4, "last"]
    if page >= total_pages - 1:
        return ["first", total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
    return ["first", page - 1, page, page + 1, "last"]


def _page_button(message_id: str, page: int, label: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(label, callback_data=f"{BUTTON_PREFIX}:page:{message_id}:{page}")


def _lock_button(message_id: str, page: int, unlocked: bool) -> InlineKeyboardButton:
    label = "\U0001f513" if unlocked else "\U0001f512"
    return InlineKeyboardButton(label, callback_data=f"{BUTTON_PREFIX}:unlock:{message_id}:{page}")


def _delete_button(message_id: str) -> InlineKeyboardButton:
    return InlineKeyboardButton("\u274c", callback_data=f"{BUTTON_PREFIX}:delete:{message_id}")
