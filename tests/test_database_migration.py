from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from galerazo_bot.database import Database, RussianRouletteShot


class DatabaseMigrationTests(unittest.TestCase):
    def test_group_data_survives_supergroup_migration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.get_or_create_user("1", "Owner")
            db.get_or_create_user("2", "Member")
            db.register_chat("-1", "group", "Group", "1")
            db.set_chat_language("-1", "en")
            db.set_command_group_enabled("-1", "triggers", False)
            db.restrict_user_in_chat("-1", "2", "1")
            db.try_award_daily_galeraza("-1", "2026-07-10", "2", "100")
            now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
            db.set_command_group_enabled("-1", "hisopos", True)
            db.set_hisopo_intensity_percent("-1", 20)
            db.save_hisopo_spawn(
                "-1", "300", "silver", 2, "message", now.isoformat(),
                (now + timedelta(minutes=20)).isoformat(),
            )
            db.capture_hisopo("-1", "300", "2", now, now + timedelta(days=1))
            db.save_hisopo_spawn(
                "-1", "301", "common", 1, "message", now.isoformat(),
                (now + timedelta(minutes=20)).isoformat(),
                appearance_type="mystery",
            )
            db.save_hisopo_spawn(
                "-1", "303", "giant", 4, "message", now.isoformat(),
                (now + timedelta(minutes=20)).isoformat(),
                required_helpers=2,
            )
            db.contribute_to_giant_hisopo(
                "-1", "303", "2", now, now + timedelta(days=1)
            )
            db.save_paginated_message_state("-1", "200", "test", "1", '{"lines": []}')
            db.save_paginated_message_state("-1", "201", "galeraza", "1", '{"lines": []}')
            db.try_record_daily_report("2", "2026-07-10", "-1")
            db.add_trigger(
                "-1",
                "saludo",
                "Saludo",
                "Hola",
                None,
                None,
                None,
                "1",
                '{"test": true}',
            )
            db.add_expense("-1", "2", 1234, "ARS", "efectivo", "kiosco", "agua")
            db.play_russian_roulette("-1", "2", bullet_position=5)
            db.register_chat("-1001", "supergroup", "Supergroup", "1")
            db.try_award_daily_galeraza("-1001", "2026-07-10", "1", "999")
            db.set_hisopo_intensity_percent("-1001", 1)
            db.save_hisopo_spawn(
                "-1001", "302", "common", 1, "message", now.isoformat(),
                (now + timedelta(minutes=20)).isoformat(),
            )
            db.capture_hisopo("-1001", "302", "1", now, now + timedelta(days=1))
            db.save_paginated_message_state(
                "-1001",
                "200",
                "destination",
                "1",
                '{"destination": true}',
            )

            self.assertTrue(db.migrate_chat_id("-1", "-1001"))
            self.assertFalse(db.migrate_chat_id("-1", "-1001"))

            self.assertEqual(db.resolve_chat_id("-1"), "-1001")
            self.assertEqual(db.get_chat_settings("-1001").language, "en")
            self.assertFalse(db.is_command_group_enabled("-1001", "triggers"))
            self.assertTrue(db.is_command_group_enabled("-1001", "hisopos"))
            self.assertEqual(db.get_hisopo_intensity_percent("-1001"), 20)
            self.assertTrue(db.is_user_restricted_in_chat("-1001", "2"))
            self.assertEqual(
                {score.user_id: score.points for score in db.get_galeraza_scores("-1001")},
                {"1": 1, "2": 1},
            )
            self.assertEqual(
                {score.user_id: score.points for score in db.get_hisopo_scores("-1001")},
                {"1": 1, "2": 2},
            )
            self.assertEqual(db.get_hisopo_spawn("-1001", "301").chat_id, "-1001")
            self.assertEqual(
                db.get_hisopo_spawn("-1001", "301").appearance_type,
                "mystery",
            )
            self.assertEqual(db.get_hisopo_spawn("-1001", "303").required_helpers, 2)
            self.assertEqual(db.get_giant_contribution_count("-1001", "303"), 1)
            self.assertTrue(
                all(schedule.chat_id == "-1001" for schedule in db.list_pending_hisopo_schedules())
            )
            pagination = db.get_paginated_message_state("-1001", "200")
            self.assertEqual(pagination.chat_id, "-1001")
            self.assertEqual(pagination.list_type, "destination")
            galeraza_pagination = db.get_paginated_message_state("-1001", "201")
            self.assertEqual(galeraza_pagination.chat_id, "-1001")
            self.assertEqual(galeraza_pagination.list_type, "galeraza")
            with db._connect() as conn:
                report = conn.execute(
                    "SELECT chat_id FROM daily_user_reports WHERE user_id = ? AND report_date = ?",
                    ("2", "2026-07-10"),
                ).fetchone()
            self.assertEqual(report["chat_id"], "-1001")
            self.assertEqual(db.list_triggers("-1001")[0].display_name, "Saludo")
            self.assertEqual(db.list_triggers("-1001")[0].payload_json, '{"test": true}')
            self.assertEqual(db.list_recent_expenses("-1001")[0].description, "agua")
            self.assertEqual(
                db.play_russian_roulette("-1001", "2"),
                RussianRouletteShot(False, 4),
            )


if __name__ == "__main__":
    unittest.main()
