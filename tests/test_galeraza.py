from __future__ import annotations

import unittest

from galerazo_bot.database import GalerazaScore
from galerazo_bot.galeraza import build_galeraza_lines, render_galeraza_page


class GalerazaRenderingTests(unittest.TestCase):
    def test_uses_display_names_and_never_mentions_usernames(self) -> None:
        scores = [
            GalerazaScore("1", "alias", "Nombre Visible", 3),
            GalerazaScore("2", "alias_sin_nombre", None, 2),
            GalerazaScore("3", None, None, 1),
        ]

        lines = build_galeraza_lines(scores, language="es")

        self.assertEqual(
            lines,
            [
                "Nombre Visible (1) => 3",
                "alias_sin_nombre (2) => 2",
                "Usuario (3) => 1",
            ],
        )
        self.assertNotIn("@", "\n".join(lines))

    def test_uses_table_title(self) -> None:
        page = render_galeraza_page([], page=1, language="es")

        self.assertTrue(page.text.startswith("Tabla de Galerazas"))


if __name__ == "__main__":
    unittest.main()
