from __future__ import annotations

import re
import unittest

from galerazo_bot.i18n import TRANSLATIONS


class SpanishTranslationsTests(unittest.TestCase):
    def test_languages_have_the_same_keys(self) -> None:
        self.assertEqual(set(TRANSLATIONS["es"]), set(TRANSLATIONS["en"]))

    def test_common_missing_accents_do_not_return(self) -> None:
        spanish = "\n".join(TRANSLATIONS["es"].values())
        missing_accents = re.compile(
            r"\b(tenes|podes|configuracion|estadisticas|ultimos|todavia|vacio|vacia)\b",
            re.IGNORECASE,
        )

        self.assertIsNone(missing_accents.search(spanish))
        self.assertIn("Usá /help", TRANSLATIONS["es"]["start.response"])
        self.assertIn("respondé", TRANSLATIONS["es"]["salir.usage"])

    def test_translations_do_not_contain_utf8_mojibake(self) -> None:
        mojibake_markers = ("\u00c3", "\u00c2", "\ufffd")
        for translations in TRANSLATIONS.values():
            for text in translations.values():
                self.assertFalse(any(marker in text for marker in mojibake_markers), text)


if __name__ == "__main__":
    unittest.main()
