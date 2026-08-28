from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Awaitable, Callable

from .announcements import AnnouncementBroadcastResult
from .expenses import ExpenseSheetStatus, ExpenseSubmissionResult, ExpenseSyncResult
from .i18n import DEFAULT_LANGUAGE, t


class UserLevel(IntEnum):
    COMMON = 1
    ADMIN = 2
    DEV = 3

    @property
    def label(self) -> str:
        return {
            UserLevel.COMMON: "common",
            UserLevel.ADMIN: "admin",
            UserLevel.DEV: "dev",
        }[self]


class RussianRouletteHitResult(StrEnum):
    BANNED = "banned"
    BOT_IMMUNE = "bot_immune"
    ADMIN_IMMUNE = "admin_immune"
    DEV_IMMUNE = "dev_immune"
    FAILED = "failed"


class TriggerModerationResult(StrEnum):
    SKIPPED = "skipped"
    SAFE = "safe"
    BLOCKED = "blocked"
    TOO_LARGE = "too_large"
    ERROR = "error"


@dataclass(frozen=True)
class BackupResult:
    path: Path
    size_bytes: int
    max_size_bytes: int
    sent: bool


@dataclass(frozen=True)
class TriggerPayload:
    text: str | None = None
    media_type: str | None = None
    file_id: str | None = None
    caption: str | None = None
    data: dict[str, object] | None = None
    mime_type: str | None = None
    moderation_file_id: str | None = None
    moderation_file_size: int | None = None


@dataclass(frozen=True)
class CommandContext:
    sender_id: str
    chat_id: str | None
    chat_type: str | None
    user_level: UserLevel
    raw_text: str
    args: str
    language: str = DEFAULT_LANGUAGE
    bot_user_id: str | None = None
    sender_username: str | None = None
    sender_display_name: str | None = None
    send_announcement: Callable[[str], Awaitable[bool]] | None = None
    broadcast_announcement: Callable[[str], Awaitable[AnnouncementBroadcastResult]] | None = None
    send_report: Callable[[str], Awaitable[bool]] | None = None
    submit_expense: Callable[[str, str, str, str, str], Awaitable[ExpenseSubmissionResult]] | None = None
    sync_expenses: Callable[[], Awaitable[ExpenseSyncResult]] | None = None
    get_expense_sheet_status: Callable[[], ExpenseSheetStatus] | None = None
    create_backup: Callable[[], Awaitable[BackupResult]] | None = None
    send_debug_update: Callable[[], Awaitable[bool]] | None = None
    send_galerazas: Callable[[], Awaitable[bool]] | None = None
    send_hisopos: Callable[[], Awaitable[bool]] | None = None
    send_hisopo_collection: Callable[[], Awaitable[bool]] | None = None
    send_donation_menu: Callable[[], Awaitable[bool]] | None = None
    send_config_menu: Callable[[], Awaitable[bool]] | None = None
    create_restart_confirmation: Callable[[], Awaitable[bool]] | None = None
    create_shutdown_confirmation: Callable[[], Awaitable[bool]] | None = None
    leave_chat: Callable[[], Awaitable[bool]] | None = None
    can_run_russian_roulette: Callable[[], Awaitable[bool]] | None = None
    resolve_russian_roulette_hit: Callable[[str], Awaitable[RussianRouletteHitResult]] | None = None
    moderate_trigger_payload: Callable[[TriggerPayload], Awaitable[TriggerModerationResult]] | None = None
    reply_to_user_id: str | None = None
    reply_to_username: str | None = None
    reply_to_display_name: str | None = None
    reply_to_trigger_payload: TriggerPayload | None = None

    def t(self, key: str, **kwargs) -> str:
        return t(self.language, key, **kwargs)
