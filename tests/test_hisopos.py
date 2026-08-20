from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.error import TimedOut

from galerazo_bot.command_handlers import hisopos as hisopo_handlers
from galerazo_bot.database import Database, HisopoScore
from galerazo_bot.hisopos import (
    COMMON_HISOPO,
    DIAMOND_HISOPO,
    FAKE_HISOPO,
    FLEETING_HISOPO,
    GOLD_HISOPO,
    HISOPO_FLEETING_EXPIRATION,
    HISOPO_PROBABILITY_RANGES,
    MYSTERY_POINT_VALUES,
    PUTRID_HISOPO,
    RADIOACTIVE_POINT_VALUES,
    SILVER_HISOPO,
    TWIN_HISOPO,
    build_hisopo_lines,
    build_hisopo_pages,
    hisopo_kind_for_spawn,
    intensity_translation_key,
    random_next_day_datetime,
    render_hisopo_page,
    select_hisopo_kind,
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
            45: COMMON_HISOPO,
            46: SILVER_HISOPO,
            58: SILVER_HISOPO,
            59: GOLD_HISOPO,
            68: GOLD_HISOPO,
            69: FLEETING_HISOPO,
            75: FLEETING_HISOPO,
            83: PUTRID_HISOPO,
            87: PUTRID_HISOPO,
            92: FAKE_HISOPO,
            93: FAKE_HISOPO,
            94: TWIN_HISOPO,
            95: TWIN_HISOPO,
            96: DIAMOND_HISOPO,
            100: DIAMOND_HISOPO,
        }
        for roll, kind in expected.items():
            with self.subTest(roll=roll):
                self.assertEqual(select_hisopo_kind(roll), kind)

        mystery = select_hisopo_kind(76, randbelow=lambda _limit: 0)
        radioactive = select_hisopo_kind(88, randbelow=lambda limit: limit - 1)
        self.assertEqual(mystery.points, MYSTERY_POINT_VALUES[0])
        self.assertTrue(mystery.hides_points)
        self.assertEqual(radioactive.points, RADIOACTIVE_POINT_VALUES[-1])
        self.assertEqual(FLEETING_HISOPO.expiration, HISOPO_FLEETING_EXPIRATION)
        self.assertEqual(FAKE_HISOPO.next_day_spawns, 0)
        self.assertEqual(TWIN_HISOPO.next_day_spawns, 2)
        self.assertEqual(hisopo_kind_for_spawn("mystery", 10).points, 10)
        with self.assertRaisesRegex(ValueError, "desconocido"):
            hisopo_kind_for_spawn("unknown", 0)
        self.assertEqual(
            sum(upper - lower + 1 for lower, upper in HISOPO_PROBABILITY_RANGES.values()),
            100,
        )
        for roll in (0, 101):
            with self.subTest(roll=roll), self.assertRaisesRegex(ValueError, "tipo"):
                select_hisopo_kind(roll)

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
