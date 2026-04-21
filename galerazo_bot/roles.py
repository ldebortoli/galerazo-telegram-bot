from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Callable


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
class CommandContext:
    sender_id: str
    chat_id: str | None
    user_level: UserLevel
    raw_text: str
    args: str
    send_announcement: Callable[[str], bool] | None = None
    create_backup: Callable[[], BackupResult] | None = None
    send_debug_update: Callable[[], bool] | None = None
    reply_to_user_id: str | None = None
    reply_to_username: str | None = None
    reply_to_display_name: str | None = None
