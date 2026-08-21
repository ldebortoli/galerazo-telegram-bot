from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.error import TimedOut

from galerazo_bot import hisopos as hisopo_rules
from galerazo_bot.command_handlers import hisopos as hisopo_handlers
from galerazo_bot.database import (
    MAX_HISOPO_SCHEDULES_PER_CHAT_DAY,
    Database,
    HisopoCollectionEntry,
    HisopoMessageCleanup,
    HisopoScore,
)
from galerazo_bot.hisopos import (
    COLLECTIBLE_HISOPO_KEYS,
    COMMON_HISOPO,
    DIAMOND_HISOPO,
    FAKE_HISOPO,
    FLEETING_HISOPO,
    GOLD_HISOPO,
    HISOPO_DISGUISE_PROBABILITY_RANGES,
    HISOPO_EXPIRATION,
    HISOPO_FLEETING_EXPIRATION,
    HISOPO_TYPE_ROLL_MAX,
    HISOPO_PROBABILITY_RANGES,
    GIANT_HISOPO,
    MIRACLE_HISOPO,
    MYSTERY_HISOPO,
    PUTRID_HISOPO,
    RADIOACTIVE_HISOPO,
    RADIOACTIVE_POINT_VALUES,
    SILVER_HISOPO,
    TWIN_HISOPO,
    build_hisopo_lines,
    build_hisopo_pages,
    giant_required_helpers,
    hisopo_kind_for_spawn,
    intensity_translation_key,
    is_fleeting_window_expired,
    radioactive_points_at,
    random_next_day_datetime,
    render_hisopo_collection,
    render_hisopo_page,
    select_hisopo_disguise,
    select_hisopo_kind,
    select_hisopo_spawn,
    should_spawn_hisopo,
)
from galerazo_bot.roles import CommandContext, UserLevel


class HisopoRulesTests(unittest.TestCase):
    def test_spawn_rolls_and_invalid_values(self) -> None:
        self.assertTrue(should_spawn_hisopo(1, 1))
        self.assertFalse(should_spawn_hisopo(1, 2))
        self.assertTrue(should_spawn_hisopo(20, 20))
        self.assertFalse(should_spawn_hisopo(20, 21))
        with self.assertRaisesRegex(ValueError, "Intensidad"):
            should_spawn_hisopo(2, 1)
        for roll in (0, 101):
            with self.subTest(roll=roll), self.assertRaisesRegex(ValueError, "tirada"):
                should_spawn_hisopo(10, roll)

    def test_type_boundaries_and_invalid_values(self) -> None:
        expected = {
            1: COMMON_HISOPO,
            4665: COMMON_HISOPO,
            4666: SILVER_HISOPO,
            6065: SILVER_HISOPO,
            6066: GOLD_HISOPO,
            7065: GOLD_HISOPO,
            7066: FLEETING_HISOPO,
            7765: FLEETING_HISOPO,
            7766: MYSTERY_HISOPO,
            8465: MYSTERY_HISOPO,
            8466: PUTRID_HISOPO,
            8965: PUTRID_HISOPO,
            8966: RADIOACTIVE_HISOPO,
            9365: RADIOACTIVE_HISOPO,
            9366: FAKE_HISOPO,
            9665: FAKE_HISOPO,
            9666: TWIN_HISOPO,
            9865: TWIN_HISOPO,
            9866: DIAMOND_HISOPO,
            9965: DIAMOND_HISOPO,
            9966: GIANT_HISOPO,
            9990: GIANT_HISOPO,
            9991: MIRACLE_HISOPO,
            10000: MIRACLE_HISOPO,
        }
        for roll, kind in expected.items():
            with self.subTest(roll=roll):
                self.assertEqual(select_hisopo_kind(roll), kind)

        mystery = select_hisopo_kind(7766, randbelow=lambda _limit: 0)
        radioactive = select_hisopo_kind(8966, randbelow=lambda limit: limit - 1)
        self.assertEqual(mystery, MYSTERY_HISOPO)
        self.assertTrue(mystery.hides_points)
        self.assertEqual(radioactive, RADIOACTIVE_HISOPO)
        self.assertTrue(radioactive.hides_points)
        self.assertEqual(FLEETING_HISOPO.expiration, HISOPO_FLEETING_EXPIRATION)
        self.assertEqual(FAKE_HISOPO.next_day_spawns, 0)
        self.assertEqual(TWIN_HISOPO.next_day_spawns, 1)
        self.assertEqual(TWIN_HISOPO.immediate_spawns, 1)
        self.assertTrue(MIRACLE_HISOPO.hides_points)
        self.assertEqual(hisopo_kind_for_spawn("mystery", 10).points, 10)
        with self.assertRaisesRegex(ValueError, "desconocido"):
            hisopo_kind_for_spawn("unknown", 0)
        self.assertEqual(
            sum(upper - lower + 1 for lower, upper in HISOPO_PROBABILITY_RANGES.values()),
            HISOPO_TYPE_ROLL_MAX,
        )
        probabilities = {
            key: upper - lower + 1
            for key, (lower, upper) in HISOPO_PROBABILITY_RANGES.items()
        }
        self.assertEqual(
            probabilities,
            {
                "common": 4665,
                "silver": 1400,
                "gold": 1000,
                "fleeting": 700,
                "mystery": 700,
                "putrid": 500,
                "radioactive": 400,
                "fake": 300,
                "twin": 200,
                "diamond": 100,
                "giant": 25,
                "miracle": 10,
            },
        )
        for more_likely in ("twin", "fake", "radioactive", "putrid"):
            self.assertGreater(probabilities[more_likely], probabilities["diamond"])
        for roll in (0, HISOPO_TYPE_ROLL_MAX + 1):
            with self.subTest(roll=roll), self.assertRaisesRegex(ValueError, "tipo"):
                select_hisopo_kind(roll)

    def test_fake_and_mystery_selections_keep_appearance_separate(self) -> None:
        common = select_hisopo_spawn(1)
        self.assertEqual(common.actual, COMMON_HISOPO)
        self.assertEqual(common.appearance, COMMON_HISOPO)

        fake = select_hisopo_spawn(9366, randbelow=lambda _limit: 0)
        self.assertEqual(fake.actual, FAKE_HISOPO)
        self.assertEqual(fake.appearance, COMMON_HISOPO)

        putrid = select_hisopo_spawn(8466, randbelow=lambda _limit: 99)
        self.assertEqual(putrid.actual, PUTRID_HISOPO)
        self.assertEqual(putrid.appearance, DIAMOND_HISOPO)

        mystery_common = select_hisopo_spawn(7766, randbelow=lambda _limit: 0)
        self.assertEqual(mystery_common.actual, COMMON_HISOPO)
        self.assertEqual(mystery_common.appearance, MYSTERY_HISOPO)
        self.assertEqual(mystery_common.appearance.expiration, HISOPO_EXPIRATION)

        mystery_fake = select_hisopo_spawn(7766, randbelow=lambda _limit: 8665)
        self.assertEqual(mystery_fake.actual, FAKE_HISOPO)
        self.assertEqual(mystery_fake.appearance, MYSTERY_HISOPO)

        rolls = iter((8265,))
        mystery_radioactive = select_hisopo_spawn(7766, randbelow=lambda _limit: next(rolls))
        self.assertEqual(mystery_radioactive.actual.key, "radioactive")
        self.assertEqual(mystery_radioactive.actual.points, 0)

        expected_actuals = {
            0: "common",
            4664: "common",
            4665: "silver",
            6064: "silver",
            6065: "gold",
            7064: "gold",
            7065: "fleeting",
            7764: "fleeting",
            7765: "putrid",
            8264: "putrid",
            8265: "radioactive",
            8664: "radioactive",
            8665: "fake",
            8964: "fake",
            8965: "twin",
            9164: "twin",
            9165: "diamond",
            9264: "diamond",
            9265: "giant",
            9289: "giant",
            9290: "miracle",
            9299: "miracle",
        }
        for weighted_roll, expected_key in expected_actuals.items():
            with self.subTest(weighted_roll=weighted_roll):
                selected = select_hisopo_spawn(
                    7766,
                    randbelow=lambda _limit, value=weighted_roll: value,
                )
                self.assertEqual(selected.actual.key, expected_key)
        with self.assertRaisesRegex(RuntimeError, "seleccionar"):
            hisopo_rules._select_weighted_non_mystery_kind(lambda limit: limit)

    def test_giant_helper_threshold_uses_every_small_chat_member_and_caps_at_fifteen(self) -> None:
        self.assertEqual(giant_required_helpers(1), 1)
        self.assertEqual(giant_required_helpers(6), 5)
        self.assertEqual(giant_required_helpers(16), 15)
        self.assertEqual(giant_required_helpers(500), 15)
        with self.assertRaisesRegex(ValueError, "miembros"):
            giant_required_helpers(0)

    def test_disguise_probabilities_and_radioactive_timeline(self) -> None:
        self.assertEqual(RADIOACTIVE_POINT_VALUES, (-3, -1, 2, 4, 6))
        expected_disguises = {
            0: COMMON_HISOPO,
            74: COMMON_HISOPO,
            75: SILVER_HISOPO,
            88: SILVER_HISOPO,
            89: GOLD_HISOPO,
            98: GOLD_HISOPO,
            99: DIAMOND_HISOPO,
        }
        for disguise_roll, expected in expected_disguises.items():
            with self.subTest(disguise_roll=disguise_roll):
                self.assertEqual(
                    select_hisopo_disguise(lambda _limit, value=disguise_roll: value),
                    expected,
                )
        probabilities = {
            key: upper - lower + 1
            for key, (lower, upper) in HISOPO_DISGUISE_PROBABILITY_RANGES.items()
        }
        self.assertEqual(
            probabilities,
            {"common": 75, "silver": 14, "gold": 10, "diamond": 1},
        )
        self.assertEqual(sum(probabilities.values()), 100)

        spawned_at = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
        expected_points = {
            timedelta(minutes=-1): -3,
            timedelta(0): -3,
            timedelta(minutes=4, seconds=59): -3,
            timedelta(minutes=5): -1,
            timedelta(minutes=9, seconds=59): -1,
            timedelta(minutes=10): 2,
            timedelta(minutes=14, seconds=59): 2,
            timedelta(minutes=15): 4,
            timedelta(minutes=17, seconds=59): 4,
            timedelta(minutes=18): 6,
            timedelta(minutes=19, seconds=59): 6,
        }
        for elapsed, points in expected_points.items():
            with self.subTest(elapsed=elapsed):
                self.assertEqual(
                    radioactive_points_at(spawned_at, spawned_at + elapsed),
                    points,
                )
        self.assertEqual(
            radioactive_points_at(
                datetime(2026, 8, 20, 12),
                datetime(2026, 8, 20, 12, 18),
            ),
            6,
        )

        self.assertFalse(
            is_fleeting_window_expired(
                spawned_at,
                spawned_at + timedelta(seconds=59, milliseconds=999),
            )
        )
        self.assertTrue(
            is_fleeting_window_expired(
                spawned_at,
                spawned_at + HISOPO_FLEETING_EXPIRATION,
            )
        )
        self.assertTrue(
            is_fleeting_window_expired(
                datetime(2026, 8, 20, 12),
                datetime(2026, 8, 20, 12, 1),
            )
        )

    def test_next_day_is_random_local_calendar_day(self) -> None:
        now = datetime(2026, 8, 20, 23, 30, tzinfo=timezone.utc)
        scheduled = random_next_day_datetime(now, randbelow=lambda _limit: 3600)
        self.assertEqual(scheduled, datetime(2026, 8, 21, 4, 0, tzinfo=timezone.utc))
        naive = random_next_day_datetime(
            datetime(2026, 8, 20, 3, 0),
            randbelow=lambda _limit: 0,
        )
        self.assertEqual(naive, datetime(2026, 8, 21, 3, 0, tzinfo=timezone.utc))

    def test_intensity_labels_and_ranking_pages(self) -> None:
        self.assertEqual(intensity_translation_key(1), "hisopos.intensity.very_low")
        self.assertEqual(intensity_translation_key(20), "hisopos.intensity.very_high")
        with self.assertRaisesRegex(ValueError, "Intensidad"):
            intensity_translation_key(3)

        scores = [
            HisopoScore("1", None, "Ana", 5),
            HisopoScore("2", "bea", None, 5),
            HisopoScore("3", None, None, 2),
        ]
        lines = build_hisopo_lines(scores)
        self.assertEqual(lines[0], "1. Ana (1) => 5")
        self.assertEqual(lines[1], "-  bea (2) => 5")
        self.assertEqual(lines[2], "3. Usuario (3) => 2")
        self.assertEqual(build_hisopo_lines([]), ["Nadie capturó Hisopos hasta ahora."])
        pages = build_hisopo_pages(scores, max_chars=38)
        self.assertGreater(len(pages), 1)
        self.assertIn("1. bea", pages[1])
        self.assertEqual(render_hisopo_page([], 99).page, 1)

    def test_collection_renders_real_types_counts_and_progress(self) -> None:
        entries = [
            HisopoCollectionEntry("common", 3, "2026-08-20T12:00:00+00:00", "2026-08-20T13:00:00+00:00"),
            HisopoCollectionEntry("diamond", 1, "2026-08-20T14:00:00+00:00", "2026-08-20T14:00:00+00:00"),
            HisopoCollectionEntry("mystery", 9, "2026-08-20T15:00:00+00:00", "2026-08-20T15:00:00+00:00"),
        ]

        rendered = render_hisopo_collection(entries, "Ana", "2")

        self.assertEqual(len(COLLECTIBLE_HISOPO_KEYS), 11)
        self.assertNotIn("mystery", COLLECTIBLE_HISOPO_KEYS)
        self.assertIn("Colección histórica de Ana (2)", rendered)
        self.assertIn("Tipos descubiertos: 2/11 · Capturas: 4", rendered)
        self.assertIn("✅ hisopo común: 3", rendered)
        self.assertIn("⬜ hisopo plateado: 0", rendered)
        self.assertIn("✅ hisopo diamante: 1", rendered)
        self.assertNotIn("hisopo misterioso:", rendered)
        self.assertIn("cuenta como el tipo real", rendered)


class HisopoDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temporary.name) / "db.sqlite3")
        self.db.get_or_create_user("1", "Owner")
        self.db.get_or_create_user("2", "Winner", "winner")
        self.db.get_or_create_user("3", "Later")
        self.db.register_chat("-1", "group", "Group", "1")
        self.now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _spawn(self, message_id: str, points: int = 2, expires_delta: timedelta = timedelta(minutes=20)):
        return self.db.save_hisopo_spawn(
            "-1",
            message_id,
            "silver" if points == 2 else "common",
            points,
            "message",
            self.now.isoformat(),
            (self.now + expires_delta).isoformat(),
        )

    def test_settings_capture_score_and_schedule_lifecycle(self) -> None:
        self.assertTrue(self.db.is_command_group_enabled("-1", "hisopos"))
        self.db.set_command_group_enabled("-1", "hisopos", False)
        self.assertFalse(self.db.is_command_group_enabled("-1", "hisopos"))
        self.assertEqual(self.db.get_hisopo_intensity_percent("-1"), 10)
        self.db.set_hisopo_intensity_percent("-1", 20)
        self.assertEqual(self.db.get_hisopo_intensity_percent("-1"), 20)
        with self.assertRaisesRegex(ValueError, "intensidad"):
            self.db.set_hisopo_intensity_percent("-1", 3)

        spawn = self._spawn("100")
        self.assertEqual(self.db.get_hisopo_spawn("-1", "100"), spawn)
        self.assertEqual(self.db.list_active_hisopo_spawns(), [spawn])
        self.assertIsNone(self.db.get_hisopo_spawn("-1", "missing"))
        missing = self.db.capture_hisopo(
            "-1", "missing", "2", self.now, self.now + timedelta(days=1)
        )
        self.assertEqual(missing.status, "missing")

        next_day = self.now + timedelta(days=1, hours=3)
        captured = self.db.capture_hisopo("-1", "100", "2", self.now, next_day)
        self.assertEqual(captured.status, "captured")
        self.assertEqual(captured.spawn.winner_user_id, "2")
        self.assertEqual(captured.schedule.scheduled_for, next_day.isoformat())
        self.assertEqual(self.db.get_hisopo_scores("-1")[0].points, 2)
        self.assertEqual(
            self.db.capture_hisopo("-1", "100", "3", self.now, next_day).status,
            "taken",
        )
        self.assertFalse(self.db.mark_hisopo_rotten("-1", "100", self.now + timedelta(days=1)))

        pending = self.db.list_pending_hisopo_schedules()
        self.assertEqual(len(pending), 1)
        claimed = self.db.claim_hisopo_schedule(pending[0].schedule_id)
        self.assertEqual(claimed.status, "processing")
        self.assertIsNone(self.db.claim_hisopo_schedule(pending[0].schedule_id))
        self.db.reset_processing_hisopo_schedules()
        pending = self.db.list_pending_hisopo_schedules()
        self.assertEqual(len(pending), 1)
        self.db.claim_hisopo_schedule(pending[0].schedule_id)
        with self.assertRaisesRegex(ValueError, "Estado"):
            self.db.complete_hisopo_schedule(pending[0].schedule_id, "unknown")
        self.db.complete_hisopo_schedule(pending[0].schedule_id, "sent")
        self.assertEqual(self.db.list_pending_hisopo_schedules(), [])

    def test_message_cleanup_state_tracks_deleted_expired_and_failed_attempts(self) -> None:
        for message_id, age in (("recent", 23), ("deleted", 25), ("expired", 49), ("failed", 26)):
            spawned_at = self.now - timedelta(hours=age)
            self.db.save_hisopo_spawn(
                "-1",
                message_id,
                "common",
                1,
                "message",
                spawned_at.isoformat(),
                (spawned_at + timedelta(minutes=20)).isoformat(),
            )

        self.assertEqual(
            [cleanup.message_id for cleanup in self.db.list_pending_hisopo_message_cleanups("-1")],
            ["expired", "failed", "deleted", "recent"],
        )
        self.db.mark_hisopo_messages_deleted("-1", ["deleted"], self.now)
        self.db.mark_hisopo_messages_cleanup_expired(
            "-1",
            ["expired"],
            self.now,
            "Fuera de ventana",
        )
        self.db.record_hisopo_message_cleanup_failure(
            "-1",
            ["failed"],
            self.now,
            "Timeout",
            3,
        )
        cleanup = {
            item.message_id: item
            for item in self.db.list_pending_hisopo_message_cleanups("-1")
        }
        self.assertEqual(cleanup["failed"].attempts, 1)
        self.assertEqual(cleanup["failed"].last_attempt_at, self.now.isoformat())
        self.assertIn("recent", cleanup)
        self.assertNotIn("deleted", cleanup)
        self.assertNotIn("expired", cleanup)

        self.db.record_hisopo_message_cleanup_failure(
            "-1", ["failed"], self.now + timedelta(minutes=10), "Timeout 2", 3
        )
        self.db.record_hisopo_message_cleanup_failure(
            "-1", ["failed"], self.now + timedelta(minutes=20), "Timeout 3", 3
        )
        self.assertNotIn(
            "failed",
            {
                item.message_id
                for item in self.db.list_pending_hisopo_message_cleanups("-1")
            },
        )
        with self.db._connect() as conn:
            rows = {
                row["message_id"]: row
                for row in conn.execute(
                    """
                    SELECT message_id, message_cleanup_status, message_cleanup_attempts,
                           message_deleted_at, message_cleanup_error
                    FROM hisopo_spawns
                    WHERE chat_id = '-1'
                    """
                ).fetchall()
            }
        self.assertEqual(rows["deleted"]["message_cleanup_status"], "deleted")
        self.assertEqual(rows["deleted"]["message_deleted_at"], self.now.isoformat())
        self.assertIsNone(rows["deleted"]["message_cleanup_error"])
        self.assertEqual(rows["expired"]["message_cleanup_status"], "expired")
        self.assertEqual(rows["expired"]["message_cleanup_error"], "Fuera de ventana")
        self.assertEqual(rows["failed"]["message_cleanup_status"], "failed")
        self.assertEqual(rows["failed"]["message_cleanup_attempts"], 3)
        self.assertEqual(rows["failed"]["message_cleanup_error"], "Timeout 3")
        with self.assertRaisesRegex(ValueError, "al menos un intento"):
            self.db.record_hisopo_message_cleanup_failure(
                "-1", ["recent"], self.now, "bad", 0
            )

    def test_next_day_schedule_cap_is_per_chat_and_argentine_calendar_day(self) -> None:
        target_times = tuple(
            datetime(2026, 8, 21, 3, 30, tzinfo=timezone.utc)
            + timedelta(hours=index * 2)
            for index in range(MAX_HISOPO_SCHEDULES_PER_CHAT_DAY)
        )
        self._spawn("cap-batch", points=1)
        batch = self.db.capture_hisopo(
            "-1",
            "cap-batch",
            "2",
            self.now,
            target_times,
        )
        self.assertEqual(len(batch.schedules), MAX_HISOPO_SCHEDULES_PER_CHAT_DAY)

        # This UTC instant falls on 2026-08-21 in Argentina, even though its UTC
        # date is already 2026-08-22.
        self._spawn("cap-overflow", points=1)
        overflow = self.db.capture_hisopo(
            "-1",
            "cap-overflow",
            "2",
            self.now,
            datetime(2026, 8, 22, 1, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(overflow.status, "captured")
        self.assertEqual(overflow.schedules, ())
        self.assertEqual(self.db.get_hisopo_scores("-1")[0].points, 2)

        self._spawn("next-date", points=1)
        next_date = self.db.capture_hisopo(
            "-1",
            "next-date",
            "2",
            self.now,
            datetime(2026, 8, 22, 3, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(len(next_date.schedules), 1)

        self.db.register_chat("-2", "group", "Other group", "1")
        self.db.save_hisopo_spawn(
            "-2",
            "other-chat",
            "common",
            1,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
        )
        other_chat = self.db.capture_hisopo(
            "-2",
            "other-chat",
            "2",
            self.now,
            datetime(2026, 8, 21, 12),
        )
        self.assertEqual(len(other_chat.schedules), 1)

    def test_completed_giant_keeps_rewards_when_daily_schedule_cap_is_full(self) -> None:
        self._spawn("cap-seed", points=1)
        scheduled_for = datetime(2026, 8, 21, 12, tzinfo=timezone.utc)
        seed = self.db.capture_hisopo(
            "-1",
            "cap-seed",
            "2",
            self.now,
            (scheduled_for,) * MAX_HISOPO_SCHEDULES_PER_CHAT_DAY,
        )
        self.assertEqual(len(seed.schedules), MAX_HISOPO_SCHEDULES_PER_CHAT_DAY)
        self.db.save_hisopo_spawn(
            "-1",
            "giant-at-cap",
            "giant",
            4,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
            required_helpers=1,
        )

        result = self.db.contribute_to_giant_hisopo(
            "-1",
            "giant-at-cap",
            "3",
            self.now,
            scheduled_for,
        )

        self.assertEqual(result.status, "completed")
        self.assertIsNone(result.schedule)
        self.assertEqual(
            {score.user_id: score.points for score in self.db.get_hisopo_scores("-1")},
            {"2": 1, "3": 4},
        )

    def test_rotten_paths(self) -> None:
        self._spawn("200", points=1)
        self.assertFalse(self.db.mark_hisopo_rotten("-1", "200", self.now))
        self.assertTrue(
            self.db.mark_hisopo_rotten("-1", "200", self.now + timedelta(minutes=20))
        )
        self.assertFalse(
            self.db.mark_hisopo_rotten("-1", "200", self.now + timedelta(minutes=21))
        )
        result = self.db.capture_hisopo(
            "-1", "200", "2", self.now + timedelta(minutes=21), self.now + timedelta(days=1)
        )
        self.assertEqual(result.status, "rotten")

        self._spawn("201", expires_delta=timedelta(minutes=-1))
        expired = self.db.capture_hisopo(
            "-1", "201", "2", self.now, self.now + timedelta(days=1)
        )
        self.assertEqual(expired.status, "rotten")
        self.assertEqual(self.db.get_hisopo_spawn("-1", "201").status, "rotten")

    def test_negative_zero_and_twin_rewards(self) -> None:
        self.db.save_hisopo_spawn(
            "-1",
            "300",
            "putrid",
            -2,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
        )
        negative = self.db.capture_hisopo("-1", "300", "3", self.now, ())
        self.assertEqual(negative.spawn.points, -2)
        self.assertEqual(negative.schedules, ())
        self.assertEqual(self.db.get_hisopo_scores("-1")[0].points, -2)

        self.db.save_hisopo_spawn(
            "-1",
            "301",
            "fake",
            0,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
        )
        fake = self.db.capture_hisopo("-1", "301", "2", self.now, ())
        self.assertIsNone(fake.schedule)
        self.assertEqual(fake.schedules, ())

        self.db.save_hisopo_spawn(
            "-1",
            "302",
            "twin",
            4,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
        )
        schedule_times = (
            self.now + timedelta(days=1),
            self.now + timedelta(days=1, hours=1),
        )
        twin = self.db.capture_hisopo("-1", "302", "2", self.now, schedule_times)
        self.assertEqual(len(twin.schedules), 2)
        self.assertEqual(
            tuple(schedule.scheduled_for for schedule in twin.schedules),
            tuple(value.isoformat() for value in schedule_times),
        )
        self.assertEqual(
            {score.user_id: score.points for score in self.db.get_hisopo_scores("-1")},
            {"2": 4, "3": -2},
        )

        self.db.save_hisopo_spawn(
            "-1",
            "303",
            "radioactive",
            0,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
        )
        radioactive = self.db.capture_hisopo(
            "-1",
            "303",
            "2",
            self.now + timedelta(minutes=18),
            (),
            points_at_capture=6,
        )
        self.assertEqual(radioactive.spawn.points, 6)
        self.assertEqual(self.db.get_hisopo_spawn("-1", "303").points, 6)
        self.assertEqual(
            {score.user_id: score.points for score in self.db.get_hisopo_scores("-1")},
            {"2": 10, "3": -2},
        )
        self.assertEqual(
            {entry.hisopo_type: entry.capture_count for entry in self.db.get_hisopo_collection("-1", "2")},
            {"fake": 1, "radioactive": 1, "twin": 1},
        )
        self.assertEqual(
            {entry.hisopo_type: entry.capture_count for entry in self.db.get_hisopo_collection("-1", "3")},
            {"putrid": 1},
        )

    def test_giant_contributions_are_unique_atomic_and_reward_every_helper(self) -> None:
        self.db.get_or_create_user("4", "Final")
        spawn = self.db.save_hisopo_spawn(
            "-1",
            "400",
            "giant",
            4,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
            appearance_type="mystery",
            required_helpers=3,
        )
        self.assertEqual(spawn.required_helpers, 3)
        scheduled_for = self.now + timedelta(days=1)

        first = self.db.contribute_to_giant_hisopo(
            "-1", "400", "2", self.now, scheduled_for
        )
        self.assertEqual(first.status, "joined")
        self.assertTrue(first.revealed)
        self.assertEqual(first.spawn.appearance_type, "giant")
        self.assertEqual(first.participant_user_ids, ("2",))
        self.assertEqual(self.db.get_giant_contribution_count("-1", "400"), 1)

        duplicate = self.db.contribute_to_giant_hisopo(
            "-1", "400", "2", self.now, scheduled_for
        )
        self.assertEqual(duplicate.status, "already_joined")
        self.assertEqual(duplicate.contribution_count, 1)
        self.assertEqual(self.db.get_hisopo_scores("-1"), [])

        second = self.db.contribute_to_giant_hisopo(
            "-1", "400", "3", self.now + timedelta(seconds=1), scheduled_for
        )
        self.assertEqual(second.status, "joined")
        completed = self.db.contribute_to_giant_hisopo(
            "-1", "400", "4", self.now + timedelta(seconds=2), scheduled_for
        )
        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.contribution_count, 3)
        self.assertEqual(completed.participant_user_ids, ("2", "3", "4"))
        self.assertEqual(completed.schedule.scheduled_for, scheduled_for.isoformat())
        self.assertEqual(
            {score.user_id: score.points for score in self.db.get_hisopo_scores("-1")},
            {"2": 4, "3": 4, "4": 4},
        )
        for user_id in ("2", "3", "4"):
            self.assertEqual(
                [(entry.hisopo_type, entry.capture_count) for entry in self.db.get_hisopo_collection("-1", user_id)],
                [("giant", 1)],
            )
        self.assertEqual(
            self.db.contribute_to_giant_hisopo(
                "-1", "400", "1", self.now + timedelta(seconds=3), scheduled_for
            ).status,
            "taken",
        )

    def test_miracle_adds_at_least_fifteen_or_half_the_leader_rounded_up(self) -> None:
        for message_id, kind, points in (
            ("410", "putrid", -2),
            ("411", "miracle", 15),
        ):
            self.db.save_hisopo_spawn(
                "-1",
                message_id,
                kind,
                points,
                "message",
                self.now.isoformat(),
                (self.now + timedelta(minutes=20)).isoformat(),
            )
            result = self.db.capture_hisopo(
                "-1",
                message_id,
                "3",
                self.now,
                self.now + timedelta(days=1),
            )
            self.assertEqual(result.status, "captured")
        self.assertEqual(self.db.get_hisopo_scores("-1")[0].points, 13)

        self.db.get_or_create_user("5", "Leader")
        self.db.save_hisopo_spawn(
            "-1",
            "412",
            "common",
            31,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
        )
        self.db.capture_hisopo(
            "-1", "412", "5", self.now, self.now + timedelta(days=1)
        )
        self.db.save_hisopo_spawn(
            "-1",
            "413",
            "miracle",
            15,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
        )
        miracle = self.db.capture_hisopo(
            "-1", "413", "3", self.now, self.now + timedelta(days=1)
        )
        self.assertEqual(miracle.spawn.points, 16)
        self.assertEqual(
            {score.user_id: score.points for score in self.db.get_hisopo_scores("-1")},
            {"5": 31, "3": 29},
        )

    def test_miracle_without_an_existing_leader_adds_fifteen(self) -> None:
        self.db.save_hisopo_spawn(
            "-1",
            "414",
            "miracle",
            15,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
        )
        result = self.db.capture_hisopo(
            "-1", "414", "2", self.now, self.now + timedelta(days=1)
        )
        self.assertEqual(result.spawn.points, 15)
        self.assertEqual(self.db.get_hisopo_scores("-1")[0].points, 15)

    def test_incomplete_giant_expires_without_points_or_schedule(self) -> None:
        with self.assertRaisesRegex(ValueError, "participante"):
            self.db.save_hisopo_spawn(
                "-1",
                "invalid",
                "giant",
                4,
                "message",
                self.now.isoformat(),
                (self.now + timedelta(minutes=20)).isoformat(),
                required_helpers=0,
            )
        self.db.save_hisopo_spawn(
            "-1",
            "401",
            "giant",
            4,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
            required_helpers=2,
        )
        self.assertEqual(
            self.db.contribute_to_giant_hisopo(
                "-1", "401", "2", self.now, self.now + timedelta(days=1)
            ).status,
            "joined",
        )
        expired = self.db.contribute_to_giant_hisopo(
            "-1",
            "401",
            "3",
            self.now + timedelta(minutes=20),
            self.now + timedelta(days=1),
        )
        self.assertEqual(expired.status, "rotten")
        self.assertEqual(self.db.get_hisopo_scores("-1"), [])
        self.assertEqual(self.db.list_pending_hisopo_schedules(), [])

        self.assertEqual(
            self.db.contribute_to_giant_hisopo(
                "-1", "missing", "2", self.now, self.now + timedelta(days=1)
            ).status,
            "missing",
        )
        self._spawn("402")
        self.assertEqual(
            self.db.contribute_to_giant_hisopo(
                "-1", "402", "2", self.now, self.now + timedelta(days=1)
            ).status,
            "invalid",
        )
        self.db.save_hisopo_spawn(
            "-1",
            "403",
            "giant",
            4,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
        )
        self.assertTrue(
            self.db.mark_hisopo_rotten("-1", "403", self.now + timedelta(minutes=20))
        )
        self.assertEqual(
            self.db.contribute_to_giant_hisopo(
                "-1", "403", "2", self.now, self.now + timedelta(days=1)
            ).status,
            "rotten",
        )

    def test_expired_hidden_fleeting_does_not_enter_collection(self) -> None:
        self.db.save_hisopo_spawn(
            "-1",
            "fleeting-mystery",
            "fleeting",
            5,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
            appearance_type="mystery",
        )

        result = self.db.capture_hisopo(
            "-1",
            "fleeting-mystery",
            "2",
            self.now + timedelta(minutes=2),
            (),
            points_at_capture=0,
        )

        self.assertEqual(result.status, "captured")
        self.assertEqual(result.spawn.points, 0)
        self.assertEqual(self.db.get_hisopo_collection("-1", "2"), [])

    def test_collection_migration_backfills_existing_normal_and_giant_captures(self) -> None:
        self._spawn("historic-common", points=1)
        self.db.capture_hisopo("-1", "historic-common", "2", self.now, ())
        self.db.save_hisopo_spawn(
            "-1",
            "historic-fleeting",
            "fleeting",
            5,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
            appearance_type="mystery",
        )
        self.db.capture_hisopo(
            "-1",
            "historic-fleeting",
            "3",
            self.now + timedelta(minutes=2),
            (),
            points_at_capture=0,
        )
        self.db.save_hisopo_spawn(
            "-1",
            "historic-giant",
            "giant",
            4,
            "message",
            self.now.isoformat(),
            (self.now + timedelta(minutes=20)).isoformat(),
            required_helpers=2,
        )
        self.db.contribute_to_giant_hisopo(
            "-1", "historic-giant", "2", self.now, self.now + timedelta(days=1)
        )
        self.db.contribute_to_giant_hisopo(
            "-1",
            "historic-giant",
            "3",
            self.now + timedelta(seconds=1),
            self.now + timedelta(days=1),
        )
        with self.db._connect() as conn:
            conn.execute("DROP TABLE hisopo_collections")
            conn.execute(
                "DELETE FROM schema_migrations WHERE migration_id = ?",
                ("20260820_add_hisopo_collections",),
            )

        rebuilt = Database(self.db.path)

        self.assertEqual(
            {entry.hisopo_type: entry.capture_count for entry in rebuilt.get_hisopo_collection("-1", "2")},
            {"common": 1, "giant": 1},
        )
        self.assertEqual(
            {entry.hisopo_type: entry.capture_count for entry in rebuilt.get_hisopo_collection("-1", "3")},
            {"giant": 1},
        )


class HisopoCommandTests(unittest.IsolatedAsyncioTestCase):
    def _context(self, **overrides) -> CommandContext:
        values = dict(
            sender_id="1",
            chat_id="-1",
            chat_type="group",
            user_level=UserLevel.COMMON,
            raw_text="/hisopos",
            args="",
        )
        values.update(overrides)
        return CommandContext(**values)

    async def test_handler_paths(self) -> None:
        self.assertIn("grupos", await hisopo_handlers.handle(self._context(chat_type="private"), MagicMock()))
        self.assertIn("configurado", await hisopo_handlers.handle(self._context(), MagicMock()))
        self.assertIn(
            "mostrar",
            await hisopo_handlers.handle(
                self._context(send_hisopos=AsyncMock(return_value=False)), MagicMock()
            ),
        )
        self.assertIsNone(
            await hisopo_handlers.handle(
                self._context(send_hisopos=AsyncMock(return_value=True)), MagicMock()
            )
        )

    async def test_rules_are_available_even_when_the_game_is_disabled(self) -> None:
        response = hisopo_handlers.handle_rules(self._context(), MagicMock())

        self.assertIn("Reglas del Recolector de Hisopos", response)
        self.assertIn("Común: 46,65 %", response)
        self.assertIn("Diamante: 1 %", response)
        self.assertIn("Gigante cooperativo: 0,25 %", response)
        self.assertIn("total de miembros que informa Telegram menos Galerazo", response)
        self.assertIn("otros bots", response)
        self.assertIn("Milagroso: 0,10 %", response)
        self.assertIn("mitad del puntaje del líder", response)
        self.assertIn("no le quita puntos a nadie", response)
        self.assertIn("/coleccionhisopos", response)
        self.assertIn("/hisopos", response)
        self.assertLessEqual(len(response), 4096)

    async def test_collection_handler_uses_self_or_replied_user(self) -> None:
        db = MagicMock()
        db.get_hisopo_collection.return_value = [
            HisopoCollectionEntry("gold", 2, "first", "last")
        ]
        own = hisopo_handlers.handle_collection(
            self._context(sender_display_name="Owner"),
            db,
        )
        self.assertIn("Owner (1)", own)
        self.assertIn("hisopo dorado: 2", own)
        db.get_hisopo_collection.assert_called_with("-1", "1")

        replied = hisopo_handlers.handle_collection(
            self._context(
                reply_to_user_id="2",
                reply_to_display_name="Winner",
            ),
            db,
        )
        self.assertIn("Winner (2)", replied)
        db.get_hisopo_collection.assert_called_with("-1", "2")
        self.assertIn(
            "grupos",
            hisopo_handlers.handle_collection(self._context(chat_type="private"), db),
        )

    async def test_send_ranking_success_pagination_and_failure(self) -> None:
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="es")
        message = MagicMock()
        message.chat.id = -1
        result = MagicMock(message_id=10)
        result.edit_text = AsyncMock()
        message.reply_text = AsyncMock(return_value=result)

        db.get_hisopo_scores.return_value = []
        self.assertTrue(await hisopo_handlers.send_hisopos(db, message, "1"))
        db.save_paginated_message_state.assert_not_called()

        db.get_hisopo_scores.return_value = [
            HisopoScore(str(index), None, "X" * 40, 500 - index)
            for index in range(150)
        ]
        self.assertTrue(await hisopo_handlers.send_hisopos(db, message, "1"))
        db.save_paginated_message_state.assert_called_once()
        result.edit_text.assert_awaited_once()

        message.reply_text.side_effect = TimedOut()
        self.assertFalse(await hisopo_handlers.send_hisopos(db, message, "1"))
