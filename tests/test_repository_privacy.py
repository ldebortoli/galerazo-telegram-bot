from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class RepositoryPrivacyTests(unittest.TestCase):
    def test_public_environment_example_has_no_operational_identifiers(self) -> None:
        values = {}
        for line in (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key] = value

        for key in (
            "TELEGRAM_BOT_TOKEN",
            "OPENAI_API_KEY",
            "TELEGRAM_DEV_USER_IDS",
            "TELEGRAM_EXPENSE_USER_IDS",
            "TELEGRAM_OWNER_USER_ID",
            "TELEGRAM_LOG_CHAT_ID",
            "TELEGRAM_ANNOUNCEMENTS_CHAT_ID",
        ):
            self.assertEqual(values[key], "")

    def test_local_operational_files_and_credentials_are_ignored(self) -> None:
        ignored = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

        for pattern in (
            ".env.*",
            "!.env.example",
            "/secrets/",
            "/.codex/",
            "/AGENTS.md",
            "/assets/codex-logs.png",
        ):
            self.assertIn(pattern, ignored)

    def test_security_policy_uses_private_reporting(self) -> None:
        policy = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")

        self.assertIn("Security > Report a vulnerability", policy)
        self.assertIn("no la elimina del historial", policy)


if __name__ == "__main__":
    unittest.main()
