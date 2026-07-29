from __future__ import annotations

from dataclasses import dataclass

from .i18n import t


@dataclass(frozen=True)
class AnnouncementBroadcastResult:
    too_long: bool = False
    sent_count: int = 0
    skipped_count: int = 0
    inactive_count: int = 0
    failed_count: int = 0
    announcement_channel_sent: bool = False


def format_announcement(text: str, language: str) -> str:
    return f"{text}\n\n{t(language, 'donation.text')}\n{t(language, 'announcement.footer')}"


def announcement_fits(text: str, max_chars: int) -> bool:
    return all(len(format_announcement(text, language)) <= max_chars for language in ("es", "en"))
