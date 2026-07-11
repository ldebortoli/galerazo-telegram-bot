from __future__ import annotations

import unittest

from galerazo_bot.pagination import build_keyboard, build_pages


def _labels(markup) -> list[str]:
    return [button.text for button in markup.inline_keyboard[0]]


class PaginationTests(unittest.TestCase):
    def test_pages_never_split_a_line(self) -> None:
        lines = ["primera", "segunda-larga", "tercera"]

        pages = build_pages("Titulo", lines, max_chars=18)

        self.assertEqual(pages, ["Titulo\nprimera", "Titulo\nsegunda-larga", "Titulo\ntercera"])
        for line in lines:
            self.assertEqual(sum(line in page for page in pages), 1)

    def test_keyboard_has_five_page_buttons_and_correct_edges(self) -> None:
        cases = {
            1: ["[ 1 ]", "2", "3", "4", ">>"],
            3: ["<<", "2", "[ 3 ]", "4", ">>"],
            7: ["<<", "5", "6", "[ 7 ]", "8"],
            8: ["<<", "5", "6", "7", "[ 8 ]"],
        }

        for page, labels in cases.items():
            with self.subTest(page=page):
                self.assertEqual(_labels(build_keyboard("10", page, 8, False)), labels)

    def test_lock_and_delete_buttons_are_always_present(self) -> None:
        keyboard = build_keyboard("10", 1, 1, False)

        self.assertEqual(_labels(keyboard), ["🔒", "❌"])


if __name__ == "__main__":
    unittest.main()
