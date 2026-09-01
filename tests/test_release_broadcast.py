from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from galerazo_bot.release_broadcast import (
    release_broadcast_entries,
    release_broadcast_entry,
    release_broadcast_notes,
    validate_release_broadcast,
)
from galerazo_bot.versioning import CURRENT_VERSION


class ReleaseBroadcastTests(unittest.TestCase):
    def _file(self, text: str) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "BROADCAST_CHANGELOG.md"
        path.write_text(text, encoding="utf-8")
        return temporary, path

    def test_current_release_has_an_approved_telegram_safe_broadcast(self) -> None:
        entry, maximum_length = validate_release_broadcast(CURRENT_VERSION, 4096)
        self.assertEqual(entry.status, "aprobado")
        self.assertEqual(entry.previous_version, "0.10")
        self.assertLessEqual(maximum_length, 4096)

    def test_parses_approved_and_initial_entries_without_preamble(self) -> None:
        temporary, path = self._file(
            "Introduccion\n\n"
            "## [0.2] desde=[0.1] estado=aprobado\n\n"
            "Novedades de Galerazo Bot v0.2\n\n- Cambio.\n"
            "## [0.1] desde=[ninguna] estado=borrador\n\n"
            "Novedades de Galerazo Bot v0.1\n"
        )
        with temporary:
            entries = release_broadcast_entries(path)
        self.assertEqual([entry.version for entry in entries], ["0.2", "0.1"])
        self.assertEqual(entries[0].previous_version, "0.1")
        self.assertIsNone(entries[1].previous_version)
        self.assertEqual(entries[0].status, "aprobado")
        self.assertTrue(entries[0].text.endswith("- Cambio."))

    def test_rejects_duplicate_missing_draft_empty_and_wrong_title(self) -> None:
        duplicate = (
            "## [0.2] desde=[0.1] estado=aprobado\nNovedades de Galerazo Bot v0.2\n"
            "## [0.2] desde=[0.1] estado=aprobado\nNovedades de Galerazo Bot v0.2\n"
        )
        temporary, path = self._file(duplicate)
        with temporary, self.assertRaisesRegex(ValueError, "duplicadas"):
            release_broadcast_entries(path)

        cases = (
            ("## [0.2] desde=[0.1] estado=borrador\nNovedades de Galerazo Bot v0.2\n", "borrador"),
            ("## [0.2] desde=[0.1] estado=aprobado\n", "vacio"),
            ("## [0.2] desde=[0.1] estado=aprobado\nOtro titulo\n", "debe comenzar"),
        )
        for text, error in cases:
            temporary, path = self._file(text)
            with temporary, self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                validate_release_broadcast("0.2", 4096, path=path)

        temporary, path = self._file("")
        with temporary, self.assertRaisesRegex(ValueError, "no contiene"):
            release_broadcast_entry("0.2", path)

    def test_validates_length_approval_and_announced_version_contract(self) -> None:
        text = (
            "## [0.2] desde=[0.1] estado=borrador\n\n"
            "Novedades de Galerazo Bot v0.2\n\n- Cambio.\n"
        )
        temporary, path = self._file(text)
        with temporary:
            draft, length = validate_release_broadcast(
                "0.2", 4096, path=path, require_approved=False
            )
        self.assertEqual(draft.status, "borrador")
        self.assertLess(length, 4096)

        approved = text.replace("estado=borrador", "estado=aprobado")
        temporary, path = self._file(approved)
        with temporary:
            entry, length = validate_release_broadcast("0.2", 4096, path=path)
            self.assertEqual(
                release_broadcast_notes("0.2", "0.1", 4096, path=path),
                entry.text,
            )
            with self.assertRaisesRegex(ValueError, "produccion tiene anunciado 0.0"):
                release_broadcast_notes("0.2", "0.0", 4096, path=path)
            with self.assertRaisesRegex(ValueError, "supera"):
                validate_release_broadcast("0.2", length - 1, path=path)
