from __future__ import annotations

import unittest

from galerazo_bot.announcements import (
    announcement_fits,
    format_announcement,
    maximum_formatted_announcement_length,
)
from galerazo_bot.i18n import TRANSLATIONS, t


class AnnouncementFormattingTests(unittest.TestCase):
    def test_announcement_channel_donation_repository_and_configuration_footer_are_consecutive_lines(self) -> None:
        for language in TRANSLATIONS:
            formatted = format_announcement("Novedades", language)
            self.assertEqual(
                formatted,
                f"Novedades\n\n{t(language, 'announcement.channel')}\n"
                f"{t(language, 'donation.text')}\n{t(language, 'announcement.repository')}\n"
                f"{t(language, 'announcement.footer')}",
            )

    def test_maximum_length_and_fit_use_every_supported_language(self) -> None:
        text = "Novedades"
        expected = max(len(format_announcement(text, language)) for language in TRANSLATIONS)
        self.assertEqual(maximum_formatted_announcement_length(text), expected)
        self.assertTrue(announcement_fits(text, expected))
        self.assertFalse(announcement_fits(text, expected - 1))
