from __future__ import annotations

import json
import re
import unittest
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from string import Formatter

from galerazo_bot.commerce_i18n import COMMERCE, commerce_language, localized_invoice_spec
from galerazo_bot.commands import iter_commands
from galerazo_bot.i18n import TRANSLATIONS
from galerazo_bot.language_catalogs import LANGUAGE_NAMES, LANGUAGE_OPTIONS
from galerazo_bot.monetization import PAID_HISOPOS, invoice_spec


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = ROOT / "docs/LANGUAGE-REFERENCE-250.json"
RECEIPT_PATH = ROOT / "docs/PRIVATE-LANGUAGE-INVENTORY-250-20261020.json"
COMMAND_PATTERN = re.compile(
    r"/(?:" + "|".join(re.escape(command.name) for command in iter_commands()) + r")(?![A-Za-z0-9_])"
)


def format_fields(text: str) -> Counter:
    return Counter(
        (field, spec, conversion)
        for _, field, spec, conversion in Formatter().parse(text)
        if field is not None
    )


def invariants(text: str) -> tuple[Counter, Counter]:
    urls = re.findall(r"https?://[^\s<>\"']+", text)
    without_urls_or_markup = re.sub(r"https?://[^\s]+|<[^>]+>", "", text)
    commands = COMMAND_PATTERN.findall(without_urls_or_markup)
    return Counter(urls), Counter(commands)


class BalancedCatalogHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise AssertionError(f"Unbalanced catalog HTML: {tag}")


class PrivateLanguageInventory250Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
        cls.candidates = cls.reference["candidates"]
        cls.reference_by_code = {row["referenceCode"]: row for row in cls.candidates}

    def receipt(self):
        self.assertTrue(RECEIPT_PATH.is_file(), "Missing completed 250-language inventory receipt")
        return json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    def test_frozen_reference_contains_250_unique_candidates_and_preserves_punjabi_script(self):
        self.assertEqual(self.reference["reference"]["count"], 250)
        self.assertEqual(len(self.candidates), 250)
        for key in ("referenceCode", "route", "tag", "botCode"):
            self.assertEqual(len({row[key] for row in self.candidates}), 250, key)
        self.assertEqual(self.reference["baseline"], {"bot": 112, "miniapp": 140})
        self.assertEqual(sum(row["baselineBot"] for row in self.candidates), 112)
        self.assertEqual(sum(row["baselineMiniapp"] for row in self.candidates), 140)
        punjabi = next(row for row in self.candidates if row["route"] == "pa")
        self.assertEqual(punjabi["tag"], "pa-Guru")
        self.assertEqual(punjabi["botCode"], "pa")
        self.assertEqual(self.reference["reference"]["aliases"]["pa"], "pa-Guru")

    def test_receipt_preserves_the_exact_reference_and_every_candidate_record(self):
        receipt = self.receipt()
        self.assertEqual(receipt["reference"], self.reference["reference"])
        self.assertEqual(receipt["baseline"], self.reference["baseline"])
        self.assertIs(receipt["nativeReview"], False)
        self.assertEqual(len(receipt["candidates"]), 250)
        self.assertEqual(
            [row["referenceCode"] for row in receipt["candidates"]],
            [row["referenceCode"] for row in self.candidates],
        )
        for row in receipt["candidates"]:
            original = self.reference_by_code[row["referenceCode"]]
            with self.subTest(candidate=row["referenceCode"]):
                self.assertEqual(set(row), set(original) | {"bot", "miniapp"})
                self.assertEqual({key: row[key] for key in original}, original)

    def test_each_surface_has_a_complete_partition_and_evidence_for_every_exclusion(self):
        receipt = self.receipt()
        vague_fields = {"*", "all", "catalog", "translation", "translations", "commerce", "unknown", "n/a"}
        for surface in ("bot", "miniapp"):
            for row in receipt["candidates"]:
                with self.subTest(surface=surface, candidate=row["referenceCode"]):
                    status = row[surface]
                    self.assertEqual(set(status), {"status", "reasons", "missingFields"})
                    self.assertIn(status["status"], {"enabled", "excluded"})
                    self.assertIsInstance(status["reasons"], list)
                    self.assertIsInstance(status["missingFields"], list)
                    if status["status"] == "enabled":
                        self.assertEqual(status["reasons"], [])
                        self.assertEqual(status["missingFields"], [])
                    else:
                        self.assertTrue(status["reasons"], "An exclusion needs an observed reason")
                        self.assertTrue(status["missingFields"], "An exclusion needs concrete incomplete fields")
                        for reason in status["reasons"]:
                            self.assertIsInstance(reason, str)
                            self.assertTrue(reason.strip())
                        for field in status["missingFields"]:
                            self.assertIsInstance(field, str)
                            self.assertTrue(field.strip())
                            self.assertNotIn(field.strip().casefold(), vague_fields)

    def test_summary_matches_statuses_and_all_existing_options_remain_enabled(self):
        receipt = self.receipt()
        for surface, flag in (("bot", "baselineBot"), ("miniapp", "baselineMiniapp")):
            enabled = {row["referenceCode"] for row in receipt["candidates"] if row[surface]["status"] == "enabled"}
            excluded = {row["referenceCode"] for row in receipt["candidates"] if row[surface]["status"] == "excluded"}
            baseline = {row["referenceCode"] for row in self.candidates if row[flag]}
            with self.subTest(surface=surface):
                self.assertFalse(enabled & excluded)
                self.assertEqual(enabled | excluded, set(self.reference_by_code))
                self.assertTrue(baseline <= enabled, "Existing user language selections must survive expansion")
                self.assertEqual(
                    receipt["summary"][surface],
                    {"enabled": len(enabled), "added": len(enabled - baseline), "excluded": len(excluded)},
                )

    def test_bot_receipt_exactly_matches_runtime_options_and_translation_catalogs(self):
        receipt = self.receipt()
        enabled = {row["botCode"]: row for row in receipt["candidates"] if row["bot"]["status"] == "enabled"}
        excluded = {row["botCode"] for row in receipt["candidates"] if row["bot"]["status"] == "excluded"}
        actual = {option["code"]: option for option in LANGUAGE_OPTIONS}
        self.assertEqual(len(actual), len(LANGUAGE_OPTIONS))
        self.assertEqual(set(actual), set(enabled))
        self.assertEqual(set(TRANSLATIONS), set(enabled))
        self.assertFalse(excluded & set(actual))
        baseline = {row["botCode"] for row in self.candidates if row["baselineBot"]}
        self.assertTrue(baseline <= set(actual))
        for code, option in actual.items():
            with self.subTest(language=code):
                candidate = enabled[code]
                for key in ("route", "tag", "native", "direction"):
                    self.assertEqual(option[key], candidate[key], key)
                self.assertEqual(set(LANGUAGE_NAMES[code]), set(actual))
                self.assertTrue(all(isinstance(value, str) and value.strip() for value in LANGUAGE_NAMES[code].values()))

    def test_nko_names_do_not_use_the_latin_script_cldr_fallback(self):
        if "bm-Nkoo" not in TRANSLATIONS:
            return
        self.assertTrue(any("\u07ca" <= char <= "\u07ea" for char in LANGUAGE_NAMES["bm-Nkoo"]["en"]))

    def test_all_enabled_bot_catalogs_have_316_complete_format_safe_html_templates(self):
        expected = TRANSLATIONS["en"]
        self.assertEqual(len(expected), 316)
        expected_fields = {key: format_fields(value) for key, value in expected.items()}
        expected_invariants = {key: invariants(value) for key, value in expected.items()}
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            with self.subTest(language=language):
                catalog = TRANSLATIONS[language]
                self.assertEqual(set(catalog), set(expected))
                for key, text in catalog.items():
                    detail = f"{language}:{key}"
                    self.assertIsInstance(text, str, detail)
                    self.assertTrue(text.strip(), detail)
                    self.assertEqual(format_fields(text), expected_fields[key], detail)
                    self.assertEqual(invariants(text), expected_invariants[key], detail)
                    self.assertNotRegex(text, r"[\u00c3\u00c2][\u0080-\u00bf]|\ufffd", detail)
                    parser = BalancedCatalogHTML()
                    parser.feed(text)
                    parser.close()
                    self.assertEqual(parser.stack, [], detail)
                for key in ("hisopos.rules", "boss.rules"):
                    plain = re.sub(r"<[^>]+>", "", unescape(catalog[key]))
                    self.assertLessEqual(len(plain.encode("utf-16-le")) // 2, 4096, f"{language}:{key}")

    def test_enabled_catalogs_do_not_use_spanish_or_english_as_filler(self):
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            if language in {"es", "es_ES", "en"}:
                continue
            with self.subTest(language=language):
                catalog = TRANSLATIONS[language]
                self.assertTrue(catalog != TRANSLATIONS["es"], f"Spanish filler catalog: {language}")
                self.assertTrue(catalog != TRANSLATIONS["en"], f"English filler catalog: {language}")
                for key, text in catalog.items():
                    prose = re.sub(r"https?://[^\s]+|<[^>]+>|\{[^{}]*\}", "", text)
                    if len(re.findall(r"\b[A-Za-zÀ-ÖØ-öø-ÿ]{2,}\b", prose)) < 8:
                        continue
                    # Whole long sentences are evidence of untranslated prose;
                    # an isolated brand, command, cognate or native name is not.
                    self.assertNotIn(
                        text,
                        (TRANSLATIONS["en"][key], TRANSLATIONS["es"][key]),
                        f"{language}:{key}",
                    )

    def test_every_enabled_bot_language_has_its_own_complete_commerce_and_valid_invoices(self):
        english = COMMERCE["en"]
        fields = {key: format_fields(value) for key, value in english["text"].items()}
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            with self.subTest(language=language):
                self.assertEqual(commerce_language(language), language)
                self.assertTrue(language in COMMERCE, language)
                catalog = COMMERCE[language]
                self.assertEqual(set(catalog["text"]), set(english["text"]))
                self.assertEqual(set(catalog["products"]), set(english["products"]))
                if language not in {"es", "es_ES", "en"}:
                    self.assertTrue(catalog != english, f"English commerce filler: {language}")
                    self.assertTrue(catalog != COMMERCE["es"], f"Spanish commerce filler: {language}")
                for key, text in catalog["text"].items():
                    self.assertTrue(text.strip(), f"{language}:commerce.text.{key}")
                    self.assertEqual(format_fields(text), fields[key], f"{language}:{key}")
                    self.assertNotRegex(text, r"[\u00c3\u00c2][\u0080-\u00bf]|\ufffd|QZX|XZQ", f"{language}:{key}")
                    prose = re.sub(r"https?://[^\s]+|<[^>]+>|\{[^{}]*\}", "", text)
                    if language not in {"es", "es_ES", "en"} and len(re.findall(r"\b[A-Za-zÀ-ÖØ-öø-ÿ]{2,}\b", prose)) >= 8:
                        self.assertNotIn(
                            text,
                            (english["text"][key], COMMERCE["es"]["text"][key]),
                            f"{language}:commerce.text.{key}",
                        )
                for key, pair in catalog["products"].items():
                    self.assertEqual(len(pair), 2, f"{language}:{key}")
                    self.assertTrue(all(isinstance(value, str) and value.strip() for value in pair), f"{language}:{key}")
                    for index, value in enumerate(pair):
                        self.assertEqual(format_fields(value), format_fields(english["products"][key][index]), f"{language}:{key}:{index}")
                        self.assertEqual(invariants(value), invariants(english["products"][key][index]), f"{language}:{key}:{index}")
                for product in PAID_HISOPOS:
                    spec = localized_invoice_spec("product", product.key, language)
                    self.assertEqual(spec.amount_stars, product.price_stars)
                    self.assertLessEqual(len(spec.title), 32, f"{language}:{product.key}")
                    self.assertLessEqual(len(spec.description), 255, f"{language}:{product.key}")
                for kind, key in (("donation", "25"), ("subscription", "club")):
                    spec = localized_invoice_spec(kind, key, language)
                    original = invoice_spec(kind, key)
                    self.assertEqual(spec.amount_stars, original.amount_stars)
                    self.assertEqual(spec.subscription_period, original.subscription_period)
                    self.assertLessEqual(len(spec.title), 32, f"{language}:{kind}")
                    self.assertLessEqual(len(spec.description), 255, f"{language}:{kind}")


if __name__ == "__main__":
    unittest.main()
