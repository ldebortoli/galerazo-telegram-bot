from __future__ import annotations

import unittest

from galerazo_bot.announcements import format_announcement
from galerazo_bot.i18n import t


class AnnouncementFormattingTests(unittest.TestCase):
    def test_donation_and_configuration_footer_are_consecutive_lines(self) -> None:
        for language in ("es", "en"):
            formatted = format_announcement("Novedades", language)
            self.assertEqual(
                formatted,
                f"Novedades\n\n{t(language, 'donation.text')}\n{t(language, 'announcement.footer')}",
            )

