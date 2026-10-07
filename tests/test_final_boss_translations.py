from __future__ import annotations

import unittest
from html import unescape
from string import Formatter

from galerazo_bot.final_boss_translations import FINAL_BOSS_TRANSLATIONS
from galerazo_bot.hisopo_translations import (
    HISOPO_COOPERATIVE_RULE_UPDATES,
    HISOPO_TRANSLATIONS,
)
from galerazo_bot.i18n import TRANSLATIONS, t


class FinalBossTranslationsTests(unittest.TestCase):
    def test_every_supported_language_has_complete_runtime_translations(self) -> None:
        self.assertEqual(set(FINAL_BOSS_TRANSLATIONS), set(HISOPO_TRANSLATIONS))
        self.assertEqual(len(FINAL_BOSS_TRANSLATIONS), 18)
        expected_keys = set(FINAL_BOSS_TRANSLATIONS["es"])
        required_keys = {
            "hisopos.type.final_boss", "boss.rules", "boss.rules_summary",
            "boss.phase1_caption", "boss.phase2_caption", "boss.phase3_caption",
            "boss.phase4_caption", "boss.help_button", "boss.tap_button",
            "boss.joined_popup", "boss.already_joined_popup", "boss.throttled_popup",
            "boss.stale_popup", "boss.advanced_popup", "boss.won_popup",
            "boss.lost_popup", "boss.won_caption", "boss.lost_caption",
            "boss.reason.abandoned", "boss.reason.timeout", "boss.reason.duplicate_slot",
            "boss.reason.user_limit", "boss.reason.exploded", "boss.group_label",
            "boss.congratulations", "boss.score_line", "boss.loss_summary",
            "boss.solution", "boss.offender",
        }
        self.assertTrue(required_keys <= expected_keys)
        for language, catalog in FINAL_BOSS_TRANSLATIONS.items():
            with self.subTest(language=language):
                self.assertEqual(set(catalog), expected_keys)
                for key, text in catalog.items():
                    self.assertTrue(text.strip(), key)
                    self.assertNotIn("\ufffd", text, key)
                    self.assertEqual(TRANSLATIONS[language][key], text)
        # Regional dictionaries must remain independent so later edits do not
        # accidentally modify the other region's strings.
        self.assertIsNot(FINAL_BOSS_TRANSLATIONS["es_ES"], FINAL_BOSS_TRANSLATIONS["es"])
        self.assertIsNot(FINAL_BOSS_TRANSLATIONS["pt_PT"], FINAL_BOSS_TRANSLATIONS["pt_BR"])

    def test_runtime_placeholders_are_identical_in_every_language(self) -> None:
        expected_fields = {
            "boss.phase1_caption": {"current", "required", "minutes"},
            "boss.phase2_caption": {"current", "required", "minutes"},
            "boss.phase3_caption": {"current", "required", "minutes"},
            "boss.phase4_caption": {"clue", "minutes"},
            "boss.help_button": {"current", "required"},
            "boss.tap_button": {"current", "required"},
            "boss.won_caption": {"participants"},
            "boss.lost_caption": {"phase", "reason"},
            "boss.congratulations": {"group", "participants"},
            "boss.score_line": {"user", "points"},
            "boss.loss_summary": {"participants", "points"},
            "boss.solution": {"answer", "clue"},
            "boss.offender": {"user"},
        }
        sample_values = {
            "current": 999, "required": 1000, "minutes": 30,
            "clue": 67, "answer": 20, "participants": 1044,
            "phase": 4, "reason": "Timeout", "group": "Test group",
            "user": "Test user", "points": 1300,
        }
        formatter = Formatter()
        for language, catalog in FINAL_BOSS_TRANSLATIONS.items():
            for key, template in catalog.items():
                with self.subTest(language=language, key=key):
                    actual = {field for _, field, _, _ in formatter.parse(template) if field}
                    self.assertEqual(actual, expected_fields.get(key, set()))
                    self.assertEqual(t(language, key, **sample_values), template.format(**sample_values))
                    self.assertNotRegex(t(language, key, **sample_values), r"\{\w+\}")

    def test_rules_captions_buttons_and_popups_fit_telegram_limits(self) -> None:
        for language, catalog in FINAL_BOSS_TRANSLATIONS.items():
            with self.subTest(language=language):
                rules = t(language, "boss.rules")
                self.assertLessEqual(len(rules.encode("utf-16-le")) // 2, 4096)
                general_rules = t(language, "hisopos.rules")
                self.assertLessEqual(len(general_rules), 4096)
                self.assertIn(catalog["boss.rules_summary"], general_rules)
                for phase, required, minutes in ((1, 15, 60), (2, 1000, 30), (3, 20, 30), (4, 20, 10)):
                    caption = t(language, f"boss.phase{phase}_caption", current=required, required=required, minutes=minutes, clue=67)
                    self.assertLessEqual(len(caption.encode("utf-16-le")) // 2, 1024)
                self.assertLessEqual(len(t(language, "boss.won_caption", participants=1044)), 1024)
                for reason in ("abandoned", "timeout", "duplicate_slot", "user_limit", "exploded"):
                    caption = t(language, "boss.lost_caption", phase=4, reason=t(language, f"boss.reason.{reason}"))
                    self.assertLessEqual(len(caption.encode("utf-16-le")) // 2, 1024)
                for key in catalog:
                    if key.endswith("_popup"):
                        self.assertLessEqual(len(catalog[key].encode("utf-16-le")) // 2, 200)
                for key in ("boss.help_button", "boss.tap_button"):
                    self.assertLessEqual(len(t(language, key, current=1000, required=1000)), 64)

    def test_probabilities_collection_and_boss_expiration_exceptions_are_visible(self) -> None:
        for language, catalog in HISOPO_TRANSLATIONS.items():
            with self.subTest(language=language):
                rules = unescape(catalog["hisopos.rules"])
                self.assertRegex(rules, r"29[,.]64")
                self.assertRegex(rules, r"13[,.]25")
                self.assertNotRegex(rules, r"29[,.]65|0[,.]25")
                self.assertRegex(t(language, "boss.rules_summary"), r"0[,.]01")
                giant_rule = HISOPO_COOPERATIVE_RULE_UPDATES[language][2].splitlines()[0]
                self.assertRegex(giant_rule, r"(?:1\s*%|%\s*1)")
                self.assertIn("18", rules)
                # Both the Mystery deadline and ordinary expiry now explicitly
                # acknowledge the Boss exception in every locale.
                self.assertIn("60", rules)
                self.assertIn("60", t(language, "boss.rules_phases"))
                for value in ("1000", "20", "5", "4", "30", "10"):
                    self.assertIn(value, t(language, "boss.rules_phases"))
                for value in ("100", "200", "500"):
                    self.assertIn(value, t(language, "boss.rules_win"))
                for value in ("−10", "−2", "+1", "+2"):
                    self.assertIn(value, t(language, "boss.rules_loss"))

    def test_solution_is_separate_from_active_phase_and_reports_signed_scores(self) -> None:
        for language in FINAL_BOSS_TRANSLATIONS:
            with self.subTest(language=language):
                # Only the post-battle text accepts an answer. The active phase
                # accepts the clue alone, so rendering cannot disclose it early.
                self.assertIn("{answer}", FINAL_BOSS_TRANSLATIONS[language]["boss.solution"])
                for phase in range(1, 5):
                    self.assertNotIn("{answer}", FINAL_BOSS_TRANSLATIONS[language][f"boss.phase{phase}_caption"])
                for answer in range(1, 21):
                    clue = answer * 3 + 7
                    solution = t(language, "boss.solution", answer=answer, clue=clue)
                    self.assertIn(f"{answer} × 3 + 7 = {clue}", solution)
                for points in (-10, -2, 0, 1, 2, 1300):
                    signed = f"{points:+d}"
                    self.assertIn(signed, t(language, "boss.score_line", user="Alice", points=points))
                    self.assertIn(signed, t(language, "boss.loss_summary", participants=4, points=points))
                self.assertIn("Alice", t(language, "boss.offender", user="Alice"))
                self.assertIn(t(language, "boss.group_label"), t(language, "boss.congratulations", group=t(language, "boss.group_label"), participants=4))
