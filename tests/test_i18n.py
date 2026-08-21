from __future__ import annotations

import re
import unittest

from galerazo_bot.i18n import TRANSLATIONS
from galerazo_bot.hisopo_translations import (
    HISOPO_GIANT_COUNT_RULES,
    HISOPO_SCHEDULE_CAP_RULES,
)


class TranslationTests(unittest.TestCase):
    def test_languages_have_the_same_keys(self) -> None:
        for language, translations in TRANSLATIONS.items():
            with self.subTest(language=language):
                self.assertEqual(set(TRANSLATIONS["es"]), set(translations))

    def test_format_syntax_and_commands_are_preserved_in_every_language(self) -> None:
        placeholder_pattern = re.compile(r"\{[^{}]+\}")
        command_pattern = re.compile(
            r"/(?:agregartrigger|anuncio|apagar|backup|bloquear|borrartrigger|bloqueados|chats|config|debug|"
            r"desbloquear|desloquear|donar|gasto|galeraza|galerazas|habilitar|hola|listanegra|nivel|novedad|"
            r"hisopos|reiniciarbot|reportar|restringir|salir|start|triggers|version)"
        )
        url_pattern = re.compile(r"https?://[^\s]+")
        for key, spanish_text in TRANSLATIONS["es"].items():
            expected = (
                placeholder_pattern.findall(spanish_text),
                command_pattern.findall(spanish_text),
                url_pattern.findall(spanish_text),
            )
            for language, translations in TRANSLATIONS.items():
                with self.subTest(language=language, key=key):
                    actual = (
                        placeholder_pattern.findall(translations[key]),
                        command_pattern.findall(translations[key]),
                        url_pattern.findall(translations[key]),
                    )
                    self.assertEqual(actual, expected)

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

    def test_guarani_catalog_has_no_spurious_prefix(self) -> None:
        self.assertTrue(
            all(not text.startswith("rehegua\n") for text in TRANSLATIONS["gn"].values())
        )

    def test_hisopo_rules_fit_in_one_telegram_message(self) -> None:
        self.assertEqual(set(HISOPO_GIANT_COUNT_RULES), set(TRANSLATIONS))
        self.assertEqual(set(HISOPO_SCHEDULE_CAP_RULES), set(TRANSLATIONS))
        for language, translations in TRANSLATIONS.items():
            with self.subTest(language=language):
                self.assertLessEqual(len(translations["hisopos.rules"]), 4096)
                self.assertIn("/config", translations["hisopos.rules"])
                self.assertIn("/hisopos", translations["hisopos.rules"])
                self.assertIn(
                    HISOPO_GIANT_COUNT_RULES[language],
                    translations["hisopos.rules"],
                )
                self.assertIn(
                    HISOPO_SCHEDULE_CAP_RULES[language],
                    translations["hisopos.rules"],
                )

    def test_southern_quechua_preserves_named_game_and_message_lines(self) -> None:
        self.assertIn("Galeraza", TRANSLATIONS["quz"]["galeraza.header"])
        self.assertEqual(
            TRANSLATIONS["quz"]["announcement.sent"].count("\n"),
            TRANSLATIONS["es"]["announcement.sent"].count("\n"),
        )


if __name__ == "__main__":
    unittest.main()
