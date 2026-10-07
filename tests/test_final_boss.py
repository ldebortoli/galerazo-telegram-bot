from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from galerazo_bot.database import Database
from galerazo_bot.final_boss import BossActionResult, FinalBossStore


class FinalBossTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.db = Database(Path(self.temporary.name) / "boss.sqlite3")
        self.db.register_chat("-1", "group", "Fixture")
        self.store = FinalBossStore(self.db)
        self.now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
        self.sequence = 0

    def spawn(self, *, helpers=2, mystery=False, message="10"):
        self.db.save_hisopo_spawn(
            "-1", message, "final_boss", 0, "message", self.now.isoformat(),
            (self.now + timedelta(hours=1)).isoformat(),
            appearance_type="mystery" if mystery else None, required_helpers=helpers,
        )
        return self.store.create("-1", message, self.now, 7)

    def press(self, user="1", phase=1, slot=None, *, now=None, callback=None, chat="-1", message="10"):
        self.sequence += 1
        return self.store.contribute(chat, message, user, callback or f"query-{self.sequence}", phase, now or self.now, slot)

    def phase_three_fixture(self):
        """Restore a legitimate persisted phase-three game without 1000 network events."""
        self.spawn(helpers=1)
        self.press("1")
        for user in ("1", "2"):
            self.db.get_or_create_user(user)
        with self.db._connect() as conn:
            conn.executemany(
                "INSERT INTO final_boss_events VALUES ('-1','10',?, ?,2,NULL,?,1)",
                [(f"seed-{i}", "1" if i < 500 else "2", (self.now + timedelta(milliseconds=i * 100)).isoformat()) for i in range(1000)],
            )
            conn.execute("UPDATE final_boss_states SET phase = 3 WHERE chat_id = '-1'")
        self.now += timedelta(minutes=2)

    def phase_four_fixture(self):
        self.phase_three_fixture()
        for slot in range(20):
            result = self.press(str(slot // 5 + 1), 3, slot)
        self.assertEqual(result.status, "advanced")
        return result.state

    def scores(self, chat="-1"):
        return {row.user_id: row.points for row in self.db.get_hisopo_scores(chat)}

    def seed_scores(self):
        self.db.register_chat("-2", "group", "Other")
        with self.db._connect() as conn:
            conn.executemany("INSERT INTO hisopo_scores (chat_id,user_id,points) VALUES (?,?,?)", [("-1", "1", 30), ("-1", "2", 20), ("-1", "3", 10), ("-2", "1", 99)])

    def test_creation_requires_valid_spawn_and_preserves_original_state(self):
        self.assertIsNone(self.store.get("-1", "missing"))
        self.assertEqual(BossActionResult("missing", None).awards, ())
        for slot in (-1, 20):
            with self.assertRaises(ValueError):
                self.store.create("-1", "10", self.now, slot)
        with self.assertRaisesRegex(ValueError, "saved"):
            self.store.create("-1", "missing", self.now, 0)
        self.db.save_hisopo_spawn("-1", "wrong", "common", 1, "message", self.now.isoformat(), self.now.isoformat())
        with self.assertRaisesRegex(ValueError, "saved"):
            self.store.create("-1", "wrong", self.now, 0)
        state = self.spawn()
        self.assertEqual(state.safe_slot, 7)
        self.assertEqual(state.phase, 1)
        self.assertEqual(state.expires_at, (self.now + timedelta(hours=1)).isoformat())
        self.assertEqual(self.store.create("-1", "10", self.now + timedelta(hours=2), 19), state)
        self.assertEqual([row.message_id for row in self.db.list_pending_hisopo_message_cleanups("-1")], ["wrong"])
        self.assertEqual(self.store.get_pending_results(), ())
        self.store.mark_announced("-1", "10", "ignored-active")
        self.assertIsNone(self.store.get("-1", "10").announcement_message_id)
        with self.assertRaises(ValueError):
            self.store.mark_announced("-1", "10", "")

    def test_spawn_is_preserved_even_if_initialization_was_interrupted(self):
        self.db.save_hisopo_spawn("-1", "10", "final_boss", 0, "message", self.now.isoformat(), (self.now + timedelta(hours=1)).isoformat())
        self.assertEqual(self.db.list_pending_hisopo_message_cleanups("-1"), [])
        self.assertEqual(self.press().status, "missing")
        self.assertEqual(self.store.expire("-1", "10", self.now).status, "missing")

    def test_validation_replays_and_each_phase_one_user_counts_once(self):
        self.spawn()
        for phase, slot in ((0, None), (5, None), (1, 0), (2, 0), (3, None), (4, -1), (4, 20)):
            self.assertEqual(self.press(phase=phase, slot=slot).status, "invalid")
        self.assertEqual(self.store.contribute("-1", "10", "1", "", 1, self.now).status, "invalid")
        self.assertEqual(self.press(phase=2, callback="future").status, "stale")
        self.assertEqual(self.press(phase=2, callback="future").status, "duplicate")
        result = self.press(callback="first")
        self.assertEqual(result.status, "joined")
        self.assertEqual(result.state.phase1_users, ("1",))
        self.assertEqual(self.press(callback="first").status, "duplicate")
        self.assertEqual(self.press().status, "already_joined")
        next_time = self.now + timedelta(minutes=50)
        result = self.press("2", now=next_time)
        self.assertEqual(result.status, "advanced")
        self.assertEqual(result.state.phase, 2)
        self.assertEqual(result.state.expires_at, (next_time + timedelta(minutes=30)).isoformat())
        self.assertEqual(self.press("3", now=next_time).status, "stale")
        self.assertEqual(self.scores(), {})

    def test_all_phases_real_counts_deferred_awards_and_restart_idempotence(self):
        self.spawn(mystery=True)
        self.press("1")
        self.press("2")
        self.assertEqual(self.db.get_hisopo_collection("-1", "1"), [])
        for i in range(5):
            result = self.press("2", 2, now=self.now + timedelta(milliseconds=i * 100))
            self.assertEqual(result.status, "joined")
        # Persist the middle of a valid run; test both sides of the real boundary.
        with self.db._connect() as conn:
            conn.executemany(
                "INSERT INTO final_boss_events VALUES ('-1','10',?,'2',2,NULL,?,1)",
                [(f"middle-{i}", (self.now + timedelta(milliseconds=i * 100)).isoformat()) for i in range(5, 999)],
            )
        self.assertEqual(self.store.get("-1", "10").phase2_total, 999)
        self.assertEqual(self.scores(), {})
        result = self.press("2", 2, now=self.now + timedelta(milliseconds=99900))
        self.assertEqual(result.status, "advanced")
        self.assertEqual(result.state.phase2_total, 1000)
        self.assertEqual(result.state.phase2_counts, (("2", 1000),))
        self.assertEqual(result.state.expires_at, (self.now + timedelta(milliseconds=99900, minutes=30)).isoformat())
        self.now += timedelta(minutes=2)
        for slot in range(20):
            result = self.press(str(slot // 5 + 1), 3, slot)
            self.assertEqual(result.status, "advanced" if slot == 19 else "joined")
        self.assertEqual(result.state.phase3_count, 20)
        self.assertEqual(result.state.expires_at, (self.now + timedelta(minutes=10)).isoformat())
        self.assertEqual(self.scores(), {})
        self.assertEqual(self.db.get_hisopo_collection("-1", "1"), [])
        result = self.store.contribute("-1", "10", "9", "winning", 4, self.now, 7, self.now + timedelta(days=1))
        self.assertEqual(result.schedule.source_message_id, "10")
        self.assertEqual(result.schedule.scheduled_for, (self.now + timedelta(days=1)).isoformat())
        expected = {"1": 800, "2": 1800, "3": 600, "4": 600, "9": 600}
        self.assertEqual(result.status, "won")
        self.assertEqual(dict(result.awards), expected)
        self.assertEqual(self.scores(), expected)
        self.assertEqual(result.state.participant_user_ids, ("1", "2", "3", "4", "9"))
        self.assertEqual({item.hisopo_type for item in self.db.get_hisopo_collection("-1", "1")}, {"final_boss", "mystery"})
        for user in ("2", "3", "4", "9"):
            self.assertEqual([item.hisopo_type for item in self.db.get_hisopo_collection("-1", user)], ["final_boss"])
        self.store = FinalBossStore(Database(self.db.path))
        self.assertEqual(self.press("9", 4, 7, callback="winning").status, "duplicate")
        self.assertEqual(self.press("9", 4, 7).status, "finished")
        self.assertEqual(self.store.expire("-1", "10", self.now + timedelta(days=1)).status, "finished")
        self.assertEqual(self.scores(), expected)
        self.assertEqual(len(self.store.get_pending_results()), 1)
        self.store.mark_announced("-1", "10", "1000")
        self.store.mark_announced("-1", "10", "1001")
        self.assertEqual(self.store.get("-1", "10").announcement_message_id, "1000")
        self.assertFalse(self.store.get("-1", "10").announcement_complete)
        self.assertEqual(len(self.store.get_pending_results()), 1)
        self.store.complete_announcement("-1", "10")
        self.assertTrue(self.store.get("-1", "10").announcement_complete)
        self.assertEqual(self.store.get_pending_results(), ())
        spawn = self.db.get_hisopo_spawn("-1", "10")
        self.assertEqual((spawn.status, spawn.winner_user_id), ("captured", "9"))
        self.assertEqual(self.db.list_pending_hisopo_message_cleanups("-1"), [])

    def test_rate_limit_is_per_user_replayed_rejection_never_counts(self):
        self.spawn(helpers=1)
        self.press()
        self.assertEqual(self.press("1", 2).status, "joined")
        self.assertEqual(self.press("1", 2, callback="fast", now=self.now + timedelta(milliseconds=99)).status, "throttled")
        self.assertEqual(self.press("2", 2).status, "joined")
        self.assertEqual(self.press("1", 2, now=self.now + timedelta(milliseconds=100)).status, "joined")
        result = self.press("1", 2, callback="fast", now=self.now + timedelta(seconds=1))
        self.assertEqual(result.status, "duplicate")
        self.assertEqual(result.state.phase2_total, 3)

    def test_abandoned_penalty_applies_once_to_only_this_chat_scoreboard(self):
        self.seed_scores()
        self.spawn(mystery=True)
        deadline = self.now + timedelta(hours=1)
        self.assertEqual(self.store.expire("-1", "10", deadline - timedelta(microseconds=1)).status, "not_due")
        result = self.store.expire("-1", "10", deadline)
        self.assertEqual((result.status, result.state.reason), ("lost", "abandoned"))
        self.assertEqual(dict(result.awards), {"1": -10, "2": -10, "3": -10})
        self.assertEqual(self.scores(), {"1": 20, "2": 10, "3": 0})
        self.assertEqual(self.scores("-2"), {"1": 99})
        self.assertEqual(self.press(now=deadline).status, "finished")
        self.assertEqual(self.store.expire("-1", "10", deadline).status, "finished")
        self.assertEqual(self.db.get_hisopo_collection("-1", "1"), [])
        self.assertEqual(self.db.list_pending_hisopo_message_cleanups("-1"), [])

    def test_phase_one_started_penalty_excludes_helpers_and_late_click(self):
        self.seed_scores()
        self.spawn()
        self.press("1")
        result = self.press("2", now=self.now + timedelta(hours=1))
        self.assertEqual(result.state.reason, "timeout")
        self.assertEqual(dict(result.awards), {"2": -2, "3": -2})
        self.assertEqual(self.scores(), {"1": 30, "2": 18, "3": 8})
        self.assertEqual(result.state.phase1_users, ("1",))

    def test_expiry_by_callback_before_first_press_is_abandoned(self):
        self.spawn()
        result = self.press(now=self.now + timedelta(hours=1))
        self.assertEqual(result.state.reason, "abandoned")
        self.assertEqual(result.awards, ())

    def test_phase_two_timeout_has_no_awards(self):
        self.spawn(helpers=1)
        self.press()
        self.press("2", 2)
        result = self.store.expire("-1", "10", self.now + timedelta(minutes=30))
        self.assertEqual(result.state.reason, "timeout")
        self.assertEqual(result.awards, ())
        self.assertEqual(self.scores(), {})

    def test_phase_three_duplicate_loses_and_excludes_offender_even_from_prior_phase(self):
        self.phase_three_fixture()
        self.press("3", 3, 0, callback="button")
        self.assertEqual(self.press("3", 3, 0, callback="button").status, "duplicate")
        result = self.press("1", 3, 0)
        self.assertEqual((result.status, result.state.reason, result.state.offender_user_id), ("lost", "duplicate_slot", "1"))
        self.assertEqual(dict(result.awards), {"2": 1, "3": 1})
        self.assertEqual(result.state.phase3_slots, ((0, "3"),))
        self.assertEqual(self.scores(), {"2": 1, "3": 1})

    def test_phase_three_sixth_unique_button_loses(self):
        self.phase_three_fixture()
        for slot in range(5):
            self.assertEqual(self.press("1", 3, slot).status, "joined")
        result = self.press("1", 3, 5)
        self.assertEqual(result.state.reason, "user_limit")
        self.assertEqual(result.state.phase3_count, 5)
        self.assertEqual(dict(result.awards), {"2": 1})

    def test_phase_three_timeout_consoles_all_valid_contributors(self):
        self.phase_three_fixture()
        self.press("3", 3, 0)
        result = self.store.expire("-1", "10", self.now + timedelta(hours=1))
        self.assertEqual(dict(result.awards), {"1": 1, "2": 1, "3": 1})
        self.assertEqual(result.state.offender_user_id, None)

    def test_phase_four_explosion_and_timeout_have_distinct_exclusions(self):
        state = self.phase_four_fixture()
        result = self.press("1", 4, 6)
        self.assertEqual(result.state.reason, "exploded")
        self.assertEqual(dict(result.awards), {"2": 2, "3": 2, "4": 2})
        self.assertEqual(self.db.get_hisopo_collection("-1", "2"), [])
        with self.db._connect() as conn:
            conn.execute("UPDATE final_boss_states SET status = 'active' WHERE message_id = '10'")
            conn.execute("DELETE FROM hisopo_scores")
        result = self.store.expire("-1", "10", datetime.fromisoformat(state.expires_at))
        self.assertEqual(result.state.reason, "timeout")
        self.assertEqual(dict(result.awards), {"1": 2, "2": 2, "3": 2, "4": 2})

    def test_transaction_rolls_back_winning_press_if_collection_write_fails(self):
        self.phase_four_fixture()
        with patch("galerazo_bot.final_boss._increment_hisopo_collection", side_effect=RuntimeError("fixture storage failure")):
            with self.assertRaisesRegex(RuntimeError, "storage"):
                self.press("5", 4, 7, callback="winning")
        self.assertEqual(self.scores(), {})
        self.assertEqual(self.store.get("-1", "10").status, "active")
        self.assertIsNone(self.store.get("-1", "10").final_user_id)
        self.assertEqual(self.press("5", 4, 7, callback="winning").status, "won")
        self.assertEqual(self.scores()["5"], 600)

    def test_simultaneous_phase_one_callbacks_cannot_duplicate_helpers(self):
        self.spawn()
        def contribute(index):
            return self.store.contribute("-1", "10", "1", f"parallel-{index}", 1, self.now)
        with ThreadPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(contribute, range(4)))
        self.assertEqual(sorted(result.status for result in outcomes), ["already_joined"] * 3 + ["joined"])
        self.assertEqual(self.store.get("-1", "10").phase1_users, ("1",))

    def test_migration_moves_progress_and_idempotency_records(self):
        self.spawn()
        self.press("1", callback="original")
        self.assertTrue(self.db.migrate_chat_id("-1", "-100"))
        state = self.store.get("-1", "10")
        self.assertEqual(state.chat_id, "-100")
        self.assertEqual(state.phase1_users, ("1",))
        self.assertEqual(self.press("1", chat="-100", callback="original").status, "duplicate")
        self.assertEqual(self.press("2", chat="-100").status, "advanced")
        self.assertEqual(self.db.list_pending_hisopo_message_cleanups("-100"), [])

    def test_announcement_schema_upgrades_and_completion_requires_confirmed_message(self):
        self.spawn()
        state = self.store.expire("-1", "10", self.now + timedelta(hours=1)).state
        self.assertFalse(state.announcement_complete)
        self.store.complete_announcement("-1", "10")
        self.assertEqual(len(self.store.get_pending_results()), 1)
        with self.db._connect() as conn:
            conn.execute("ALTER TABLE final_boss_states DROP COLUMN announcement_complete")
        self.store = FinalBossStore(Database(self.db.path))
        self.assertFalse(self.store.get("-1", "10").announcement_complete)
        self.store.mark_announced("-1", "10", "confirmed")
        self.store.complete_announcement("-1", "10")
        self.assertEqual(self.store.get_pending_results(), ())

    def test_migration_does_not_attach_progress_to_colliding_different_spawn(self):
        self.spawn()
        self.press("1")
        self.db.register_chat("-100", "supergroup", "Destination")
        self.db.save_hisopo_spawn("-100", "10", "common", 1, "message", self.now.isoformat(), self.now.isoformat())
        self.db.migrate_chat_id("-1", "-100")
        self.assertIsNone(self.store.get("-100", "10"))
        with self.db._connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM final_boss_events").fetchone()[0], 0)
