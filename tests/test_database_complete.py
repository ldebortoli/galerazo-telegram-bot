from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from galerazo_bot.database import Database, _normalize_username, _table_exists


class DatabaseCompleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.db = Database(self.root / "db.sqlite3")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_connection_rolls_back_and_user_lookup_variants(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "rollback"):
            with self.db._connect() as connection:
                connection.execute("INSERT INTO users (user_id) VALUES ('rollback')")
                raise RuntimeError("rollback")
        self.assertIsNone(self.db.get_user("rollback"))
        user = self.db.get_or_create_user("1", "Name", "@Alias")
        self.assertEqual(user.username, "Alias")
        self.assertEqual(self.db.get_user("1"), user)
        self.assertEqual(self.db.get_user_by_username("@alias"), user)
        self.assertIsNone(self.db.get_user_by_username(""))
        self.assertIsNone(self.db.get_user_by_username("missing"))
        self.assertIsNone(_normalize_username(None))
        self.assertIsNone(_normalize_username("@"))

    def test_chat_registration_migrations_cycle_stats_and_settings(self) -> None:
        self.db.get_or_create_user("1")
        self.db.register_chat("-1", "group", "Old", "1")
        self.db.save_restart_confirmation("-1", "99", "1")
        self.assertEqual(self.db.get_chat_added_by_user_id("-1"), "1")
        self.assertIsNone(self.db.get_chat_added_by_user_id("missing"))
        self.db.register_chat("-2", "supergroup", "New")
        self.db.migrate_chat_id("-1", "-2")
        self.assertEqual(self.db.resolve_chat_id("-1"), "-2")
        self.assertEqual(self.db.get_chat_added_by_user_id("-2"), "1")
        self.assertEqual(self.db.get_restart_confirmation("-2", "99").requester_user_id, "1")
        self.db.migrate_chat_id("-2", "-2")
        self.db.migrate_chat_id("missing-old", "-3")
        self.assertEqual(self.db.resolve_chat_id("missing-old"), "-3")
        self.db.migrate_chat_id("another-missing", "-2")

        with self.db._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO chat_migrations (old_chat_id, new_chat_id) VALUES ('cycle-a', 'cycle-b')"
            )
            connection.execute(
                "INSERT OR REPLACE INTO chat_migrations (old_chat_id, new_chat_id) VALUES ('cycle-b', 'cycle-a')"
            )
        self.assertIn(self.db.resolve_chat_id("cycle-a"), {"cycle-a", "cycle-b"})

        self.assertEqual(self.db.get_chat_settings("-2").language, "es")
        self.db.set_chat_language("-2", "en")
        self.assertEqual(self.db.get_chat_settings("-2").language, "en")
        self.assertTrue(self.db.get_chat_settings("-2").announcements_enabled)
        self.db.set_chat_announcements_enabled("-2", False)
        self.assertFalse(self.db.get_chat_settings("-2").announcements_enabled)
        self.assertEqual({chat.chat_id for chat in self.db.list_active_chats()}, {"-2", "-3"})
        self.assertTrue(self.db.is_command_group_enabled("-2", "galeraza"))
        self.assertFalse(self.db.is_command_group_enabled("-2", "ruletarusa"))
        self.db.set_command_group_enabled("-2", "ruletarusa", True)
        self.assertTrue(self.db.is_command_group_enabled("-2", "ruletarusa"))
        self.db.mark_chat_inactive("-2", "removed")
        stats = self.db.get_chat_stats()
        self.assertEqual(sum(row.inactive for row in stats), 1)
        self.db.register_chat("-2", "supergroup")
        self.assertEqual(sum(row.active for row in self.db.get_chat_stats()), 2)

    def test_blacklist_restrictions_messages_backup_and_reports(self) -> None:
        self.db.register_chat("-1", "group", "G")
        self.db.get_or_create_user("1", "One")
        self.db.get_or_create_user("2", "Two")
        self.db.save_incoming_message("1", "hello", "-1")
        self.db.save_incoming_message("1", "private", None)
        self.db.block_user("2", "1")
        self.assertTrue(self.db.is_user_blocked("2"))
        self.assertEqual(self.db.list_blocked_users()[0].display_name, "Two")
        self.assertTrue(self.db.unblock_user("2"))
        self.assertFalse(self.db.unblock_user("2"))
        self.assertFalse(self.db.is_user_blocked("2"))

        self.db.restrict_user_in_chat("-1", "2", "1")
        self.assertTrue(self.db.is_user_restricted_in_chat("-1", "2"))
        self.assertEqual(self.db.list_restricted_users_in_chat("-1")[0].user_id, "2")
        self.assertTrue(self.db.unrestrict_user_in_chat("-1", "2"))
        self.assertFalse(self.db.unrestrict_user_in_chat("-1", "2"))
        self.assertFalse(self.db.is_user_restricted_in_chat("-1", "2"))

        backup = self.db.create_backup(self.root / "backups")
        self.assertTrue(backup.is_file())
        with closing(sqlite3.connect(backup)) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertTrue(self.db.try_record_daily_report("1", "2026-07-22"))
        self.assertFalse(self.db.try_record_daily_report("1", "2026-07-22"))
        self.assertTrue(self.db.try_record_daily_report("1", "2026-07-23", "-1"))
        self.assertIsNone(self.db.get_announced_release_version())
        self.db.set_announced_release_version("0.1")
        self.assertEqual(self.db.get_announced_release_version(), "0.1")
        self.db.set_announced_release_version("0.2")
        self.assertEqual(self.db.get_announced_release_version(), "0.2")

    def test_galeraza_pagination_and_compatibility_wrappers(self) -> None:
        self.db.register_chat("-1", "group", "G")
        self.assertTrue(self.db.try_award_daily_galeraza("-1", "2026-07-22", "1", "10"))
        self.assertFalse(self.db.try_award_daily_galeraza("-1", "2026-07-22", "2", "11"))
        self.assertEqual(self.db.get_galeraza_scores("-1")[0].points, 1)
        self.assertIsNone(self.db.get_paginated_message_state("-1", "missing"))
        self.db.save_paginated_message_state("-1", "10", "users", "1", "{}", False, 1)
        self.db.save_paginated_message_state("-1", "10", "users", "1", '{"x":1}', True, 2)
        state = self.db.get_paginated_message_state("-1", "10")
        self.assertTrue(state.unlocked)
        self.assertEqual(state.current_page, 2)
        self.assertEqual(len(self.db.list_paginated_message_states_before("9999-01-01")), 1)
        self.db.set_paginated_message_unlocked("-1", "10", False)
        self.db.set_paginated_message_page("-1", "10", 3)
        state = self.db.get_paginated_message_state("-1", "10")
        self.assertFalse(state.unlocked)
        self.assertEqual(state.current_page, 3)
        self.db.delete_paginated_message_state("-1", "10")
        self.assertIsNone(self.db.get_paginated_message_state("-1", "10"))

        self.db.save_restart_confirmation("-1", "30", "1")
        confirmation = self.db.get_restart_confirmation("-1", "30")
        self.assertEqual(confirmation.requester_user_id, "1")
        self.assertEqual(len(self.db.list_restart_confirmations_before("9999-01-01")), 1)
        self.db.delete_restart_confirmation("-1", "30")
        self.assertIsNone(self.db.get_restart_confirmation("-1", "30"))

        self.db.save_galeraza_message_state("-1", "20", "1", True, 2)
        self.assertTrue(self.db.get_galeraza_message_state("-1", "20").unlocked)
        self.db.set_galeraza_message_unlocked("-1", "20", False)
        self.db.set_galeraza_message_page("-1", "20", 4)
        self.assertEqual(self.db.get_galeraza_message_state("-1", "20").current_page, 4)
        self.db.delete_galeraza_message_state("-1", "20")
        self.assertIsNone(self.db.get_galeraza_message_state("-1", "20"))

    def test_triggers_roulette_and_expenses(self) -> None:
        self.db.register_chat("-1", "group", "G")
        self.assertTrue(self.db.add_trigger("-1", "name", "Name", "text", None, None, None, "1", "{}"))
        self.assertFalse(self.db.add_trigger("-1", "name", "Name", "text", None, None, None, "1"))
        self.assertEqual(self.db.get_trigger("-1", "name").payload_json, "{}")
        self.assertIsNone(self.db.get_trigger("-1", "missing"))
        self.assertEqual(len(self.db.list_triggers("-1")), 1)
        self.assertTrue(self.db.delete_trigger("-1", "name"))
        self.assertFalse(self.db.delete_trigger("-1", "name"))
        with self.assertRaises(ValueError):
            self.db.play_russian_roulette("-1", "1", bullet_position=6)
        with patch("galerazo_bot.database.secrets.randbelow", return_value=5):
            self.assertFalse(self.db.play_russian_roulette("-1", "1").hit)

        expense = self.db.add_expense("-1", "1", 100, "ARS", "cash", "box", "food")
        self.assertEqual(expense.sheet_status, "pending")
        self.assertEqual(self.db.count_pending_expenses("-1"), 1)
        self.assertEqual(len(self.db.list_pending_expenses("-1", 1)), 1)
        self.db.mark_expense_failed(expense.expense_id, "network")
        self.assertEqual(self.db.list_recent_expenses("-1", 1)[0].sheet_error, "network")
        self.db.mark_expense_synced(expense.expense_id)
        self.assertEqual(self.db.count_pending_expenses("-1"), 0)
        self.assertEqual(self.db.list_pending_expenses("-1"), [])
        self.assertEqual(self.db.list_recent_expenses("-1")[0].sheet_status, "synced")

    def test_count_pending_defensive_none_row(self) -> None:
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = None

        @contextmanager
        def fake_connect():
            yield connection

        with patch.object(self.db, "_connect", fake_connect), patch.object(
            self.db, "resolve_chat_id", return_value="-1"
        ):
            self.assertEqual(self.db.count_pending_expenses("-1"), 0)

    def test_legacy_tables_are_upgraded_and_migrated(self) -> None:
        path = self.root / "legacy.sqlite3"
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(
                """
                CREATE TABLE paginated_message_states (
                    chat_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    list_type TEXT NOT NULL,
                    requester_user_id TEXT NOT NULL,
                    unlocked INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, message_id)
                );
                CREATE TABLE galeraza_message_states (
                    chat_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    requester_user_id TEXT NOT NULL,
                    unlocked INTEGER NOT NULL DEFAULT 0,
                    current_page INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chat_id, message_id)
                );
                INSERT INTO galeraza_message_states (chat_id, message_id, requester_user_id)
                VALUES ('-1', '10', '1');
                """
            )
        legacy = Database(path)
        state = legacy.get_paginated_message_state("-1", "10")
        self.assertEqual(state.list_type, "galeraza")
        with legacy._connect() as connection:
            self.assertTrue(_table_exists(connection, "galeraza_message_states"))
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(paginated_message_states)")}
        self.assertIn("content_json", columns)
        self.assertIn("current_page", columns)


if __name__ == "__main__":
    unittest.main()
