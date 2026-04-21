from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Awaitable, Callable

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
    send_report: Callable[[str], Awaitable[bool]] | None = None
    create_backup: Callable[[], Awaitable[BackupResult]] | None = None
    send_debug_update: Callable[[], Awaitable[bool]] | None = None
    send_galerazas: Callable[[], Awaitable[bool]] | None = None
    send_config_menu: Callable[[], Awaitable[bool]] | None = None
    leave_chat: Callable[[], Awaitable[bool]] | None = None
    reply_to_user_id: str | None = None
    reply_to_username: str | None = None
    reply_to_display_name: str | None = None
    reply_to_trigger_payload: TriggerPayload | None = None

    def t(self, key: str, **kwargs) -> str:
        return t(self.language, key, **kwargs)
