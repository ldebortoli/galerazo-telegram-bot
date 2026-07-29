from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from galerazo_bot import versioning


class VersioningTests(unittest.TestCase):
    def test_current_release_notes_reads_current_entry_and_rejects_invalid_changelog(self) -> None:
        self.assertIn(f"Galerazo Bot v{versioning.CURRENT_VERSION}", versioning.current_release_notes())

        with tempfile.TemporaryDirectory() as directory:
            changelog = Path(directory) / "CHANGELOG.md"
            changelog.write_text("# Changelog\n", encoding="utf-8")
            with patch.object(versioning, "CHANGELOG_PATH", changelog):
                with self.assertRaisesRegex(ValueError, "no contiene la version"):
                    versioning.current_release_notes()

            changelog.write_text(f"## [{versioning.CURRENT_VERSION}]\n\n## [0.3]\n", encoding="utf-8")
            with patch.object(versioning, "CHANGELOG_PATH", changelog):
                with self.assertRaisesRegex(ValueError, "no contiene cambios"):
                    versioning.current_release_notes()

            changelog.write_text(
                f"## [{versioning.CURRENT_VERSION}]\n\n- Usar `/comando` y `valor`.\n",
                encoding="utf-8",
            )
            with patch.object(versioning, "CHANGELOG_PATH", changelog):
                self.assertIn("- Usar /comando y valor.", versioning.current_release_notes())
                self.assertNotIn("`", versioning.current_release_notes())

        with patch.object(versioning, "CHANGELOG_PATH", Path("missing.md")):
            with self.assertRaises(FileNotFoundError):
                versioning.current_release_notes()
