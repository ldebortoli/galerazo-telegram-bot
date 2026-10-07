from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.error import BadRequest, TimedOut

from galerazo_bot.database import Database
from galerazo_bot.final_boss import FinalBossStore
from galerazo_bot import final_boss_telegram as ui


class FinalBossTelegramTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.db = Database(Path(self.temporary.name) / "telegram-boss.sqlite3")
        self.db.register_chat("-1", "group", "Fixture")
        self.store = FinalBossStore(self.db)
        self.now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
        self.application = SimpleNamespace(
            bot_data={"state": SimpleNamespace(db=self.db)},
            job_queue=MagicMock(),
            bot=SimpleNamespace(
                send_message=AsyncMock(return_value=SimpleNamespace(message_id=500)),
                edit_message_media=AsyncMock(),
                edit_message_caption=AsyncMock(),
                edit_message_reply_markup=AsyncMock(),
            ),
        )
        self.context = SimpleNamespace(application=self.application, job=SimpleNamespace(data={"chat_id": "-1", "message_id": "10"}))

    def spawn(self, helpers=2, mystery=False):
        spawn = self.db.save_hisopo_spawn(
            "-1", "10", "final_boss", 0, "message", self.now.isoformat(),
            (self.now + timedelta(hours=1)).isoformat(),
            appearance_type="mystery" if mystery else None, required_helpers=helpers,
        )
        return spawn, self.store.create("-1", "10", self.now, 7)

    async def callback(self, data="hisopo:boss:1", user="1", query="query", now=None, spawn=None):
        callback = SimpleNamespace(data=data, id=query, answer=AsyncMock())
        expiration, appearance = MagicMock(), MagicMock()
        result = await ui.handle_boss_callback(
            self.application, callback, user, spawn or self.db.get_hisopo_spawn("-1", "10"),
            "es", now or self.now, expiration, appearance,
        )
        return result, callback, expiration, appearance

    def set_phase(self, phase):
        with self.db._connect() as conn:
            conn.execute("UPDATE final_boss_states SET phase = ? WHERE chat_id = '-1'", (phase,))

    def test_callback_parser_assets_keyboard_and_all_presentations(self):
        for data in ("", "wrong:boss:1", "hisopo:boss", "hisopo:boss:1:0:0", "hisopo:boss:a", "hisopo:boss:3:a", "hisopo:boss:0", "hisopo:boss:1:0", "hisopo:boss:3", "hisopo:boss:4:-1", "hisopo:boss:4:20"):
            self.assertIsNone(ui.parse_boss_callback(data), data)
        for data, expected in (("hisopo:boss:1", (1, None)), ("hisopo:boss:2", (2, None)), ("hisopo:boss:3:0", (3, 0)), ("hisopo:boss:4:19", (4, 19))):
            self.assertEqual(ui.parse_boss_callback(data), expected)
        self.assertEqual(ui.boss_asset().name, "hisopo-jefe-final-fase-1.png")
        self.assertEqual(ui.boss_asset(4, True).name, "hisopo-jefe-final-derrotado.png")
        _, state = self.spawn()
        for phase, fragment, count in ((1, "1/2", 1), (2, "10/1000", 10), (3, "1/20", 1), (4, "31", 0)):
            boss = replace(state, phase=phase, phase1_users=("1",), phase2_counts=(("1", 10),), phase3_slots=((0, "1"),))
            caption, keyboard = ui.boss_presentation(boss, "es")
            self.assertIn(fragment, caption)
            self.assertEqual(len(keyboard.inline_keyboard), 1 if phase < 3 else 4)
            if phase < 3:
                self.assertIn(str(count), keyboard.inline_keyboard[0][0].text)
            else:
                buttons = [button for row in keyboard.inline_keyboard for button in row]
                self.assertEqual(len(buttons), 20)
                self.assertEqual(buttons[0].text, "✓ 1" if phase == 3 else "1")
                self.assertEqual(buttons[-1].text, "20")
                self.assertEqual(buttons[-1].callback_data, f"hisopo:boss:{phase}:19")
        caption, keyboard = ui.boss_presentation(replace(state, status="won"), "es")
        self.assertIn("DERROTADO", caption)
        self.assertIsNone(keyboard)
        for reason, expected in (("duplicate_slot", "ya estaba usado"), ("user_limit", "sexto botón")):
            caption, keyboard = ui.boss_presentation(replace(state, status="lost", phase=3, reason=reason), "es")
            self.assertIn(expected, caption)
            self.assertIsNone(keyboard)

    def test_refresh_queue_coalesces_and_immediate_update_replaces_pending(self):
        ui.queue_boss_refresh(self.application, "-1", "10")
        self.assertEqual(self.application.job_queue.run_once.call_args.kwargs["when"], 3)
        ui.queue_boss_refresh(self.application, "-1", "10")
        self.assertEqual(self.application.job_queue.run_once.call_count, 1)
        job = MagicMock()
        self.application.job_queue.get_jobs_by_name.return_value = [job]
        ui.queue_boss_refresh(self.application, "-1", "10", immediate=True)
        job.schedule_removal.assert_called_once()
        self.assertEqual(self.application.job_queue.run_once.call_args.kwargs["when"], 0)
        self.assertEqual(self.application.bot_data["boss_refresh_pending"], {("-1", "10")})
        ui.schedule_boss_recovery(self.application)
        self.application.job_queue.run_repeating.assert_called_once_with(ui.recover_boss_results, interval=60, first=1, name="boss-results")

    async def test_callbacks_validate_and_report_unique_help_advance_throttle_and_stale(self):
        spawn, _ = self.spawn(mystery=True)
        for data in (None, "bad"):
            result, callback, _, _ = await self.callback(data)
            self.assertEqual(result.status, "invalid")
            self.assertTrue(callback.answer.call_args.kwargs["show_alert"])
        result, callback, _, _ = await self.callback("hisopo:capture")
        self.assertEqual(result.status, "joined")
        self.assertIn("registrado", callback.answer.call_args.args[0])
        self.assertEqual(self.application.job_queue.run_once.call_args.kwargs["when"], 0)
        result, callback, _, _ = await self.callback("hisopo:capture")
        self.assertEqual(result.status, "duplicate")
        callback.answer.assert_awaited_once_with()
        result, callback, _, _ = await self.callback(query="second")
        self.assertEqual(result.status, "already_joined")
        self.assertIn("Ya ayudaste", callback.answer.call_args.args[0])
        result, _, expiration, _ = await self.callback(user="2", query="advance")
        self.assertEqual(result.status, "advanced")
        expiration.assert_called_once()
        self.assertEqual(expiration.call_args.args[1].expires_at, (self.now + timedelta(minutes=30)).isoformat())
        result, _, _, _ = await self.callback(user="3", query="old")
        self.assertEqual(result.status, "stale")
        self.application.bot_data["boss_refresh_pending"].clear()
        result, _, _, _ = await self.callback("hisopo:boss:2", query="tap")
        self.assertEqual(result.status, "joined")
        self.assertEqual(self.application.job_queue.run_once.call_args.kwargs["when"], 3)
        result, callback, _, _ = await self.callback("hisopo:boss:2", query="rapid")
        self.assertEqual(result.status, "throttled")
        self.assertIn("rápido", callback.answer.call_args.args[0])
        missing = replace(spawn, message_id="absent")
        result, callback, _, _ = await self.callback(spawn=missing, query="absent")
        self.assertEqual(result.status, "missing")
        self.assertFalse(callback.answer.call_args.kwargs["show_alert"])

    async def test_winning_callback_schedules_reward_and_timeout_callback_reports_loss(self):
        self.spawn(helpers=1)
        await self.callback()
        self.set_phase(4)
        result, callback, _, appearance = await self.callback("hisopo:boss:4:7", user="2", query="win")
        self.assertEqual(result.status, "won")
        self.assertTrue(callback.answer.call_args.kwargs["show_alert"])
        appearance.assert_called_once_with(self.application, result.schedule)
        result, callback, _, _ = await self.callback("hisopo:boss:4:7", query="finished")
        self.assertEqual(result.status, "finished")
        self.assertFalse(callback.answer.call_args.kwargs["show_alert"])
        with self.db._connect() as conn:
            conn.execute("UPDATE final_boss_states SET status = 'active', phase = 2 WHERE chat_id = '-1'")
        result, callback, _, _ = await self.callback("hisopo:boss:2", query="late", now=self.now + timedelta(hours=1))
        self.assertEqual(result.status, "lost")
        self.assertTrue(callback.answer.call_args.kwargs["show_alert"])

    async def test_refresh_handles_missing_and_unrevealed_mystery_then_caches_photo(self):
        await ui.refresh_boss_job(self.context)
        self.application.bot.edit_message_media.assert_not_awaited()
        self.spawn(mystery=True)
        await ui.refresh_boss_job(self.context)
        self.application.bot.edit_message_media.assert_not_awaited()
        self.store.contribute("-1", "10", "1", "first", 1, self.now)
        self.application.bot_data["boss_refresh_pending"] = {("-1", "10")}
        await ui.refresh_boss_job(self.context)
        self.assertEqual(self.application.bot_data["boss_refresh_pending"], set())
        self.application.bot.edit_message_media.assert_awaited_once()
        self.assertIn("1/2", self.application.bot.edit_message_media.call_args.kwargs["media"].caption)
        await ui.refresh_boss_job(self.context)
        self.application.bot.edit_message_caption.assert_awaited_once()
        self.application.bot.send_message.assert_not_awaited()

    async def test_refresh_ignores_not_modified_but_keeps_other_errors_retryable(self):
        self.spawn()
        self.application.bot.edit_message_media.side_effect = BadRequest("Message is not modified")
        await ui.refresh_boss_job(self.context)
        self.assertEqual(self.application.bot_data["boss_rendered_media"], {})
        self.application.bot.edit_message_media.side_effect = BadRequest("message to edit not found")
        with self.assertRaisesRegex(BadRequest, "not found"):
            await ui.refresh_boss_job(self.context)
        self.application.bot.edit_message_media.side_effect = None
        await ui.refresh_boss_job(self.context)
        self.application.bot.edit_message_caption.side_effect = BadRequest("Message is not modified")
        await ui.refresh_boss_job(self.context)

    async def test_terminal_render_announces_once_and_retries_failed_delivery(self):
        self.spawn(helpers=1)
        self.store.contribute("-1", "10", "1", "start", 1, self.now)
        self.set_phase(4)
        self.store.contribute("-1", "10", "2", "win", 4, self.now, 7)
        self.application.bot.send_message.side_effect = TimedOut("temporary")
        with self.assertRaises(TimedOut):
            await ui.refresh_boss_job(self.context)
        self.assertEqual(len(self.store.get_pending_results()), 1)
        self.application.bot.send_message.side_effect = None
        await ui.refresh_boss_job(self.context)
        self.assertIn("Felicitaciones", self.application.bot.send_message.call_args.kwargs["text"])
        self.assertIn("+600 pt", self.application.bot.send_message.call_args.kwargs["text"])
        self.assertIn("DERROTADO", self.application.bot.edit_message_caption.call_args.kwargs["caption"])
        self.assertEqual(self.store.get_pending_results(), ())
        await ui.refresh_boss_job(self.context)
        self.assertEqual(self.application.bot.send_message.await_count, 2)
        self.assertEqual(self.store.get("-1", "10").announcement_message_id, "500")

    async def test_losing_announcement_names_offender_and_solution_only_in_final_phase(self):
        _, state = self.spawn()
        self.db.get_or_create_user("1", " Ana\n Pérez ", "ana")
        self.db.get_or_create_user("2", username="second")
        loss = replace(state, status="lost", phase=3, reason="duplicate_slot", offender_user_id="1", awards=(("2", 1), ("3", 1)))
        await ui._announce_result(self.application, loss, "es")
        text = self.application.bot.send_message.call_args.kwargs["text"]
        self.assertIn("ya estaba usado", text)
        self.assertIn("Ana Pérez (1)", text)
        self.assertIn("second (2)", text)
        self.assertIn("3 (3)", text)
        self.assertIn("+1 pt", text)
        self.assertNotIn("31", text)
        final_loss = replace(loss, phase=4, reason="exploded", offender_user_id="missing", awards=())
        await ui._announce_result(self.application, final_loss, "es")
        text = self.application.bot.send_message.call_args.kwargs["text"]
        self.assertIn("missing (missing)", text)
        self.assertIn("8", text)
        self.assertIn("31", text)
        self.assertIn("+0 pt", text)
        with self.assertRaises(ValueError):
            await ui._announce_result(self.application, replace(loss, awards=(("2", 1.5),)), "es")

    async def test_large_rewards_paginate_and_preserve_each_integer_score(self):
        self.spawn()
        state = self.store.expire("-1", "10", self.now + timedelta(hours=1)).state
        awards = tuple((str(user), 100 + user) for user in range(1, 121))
        for user in range(1, 121):
            self.db.get_or_create_user(str(user), "Long participant name " + str(user))
        self.application.bot.edit_message_reply_markup.side_effect = TimedOut("button installation failed")
        with self.assertRaises(TimedOut):
            await ui._announce_result(self.application, replace(state, status="won", awards=awards), "es")
        pending = self.store.get("-1", "10")
        self.assertEqual(pending.announcement_message_id, "500")
        self.assertFalse(pending.announcement_complete)
        self.assertEqual(len(self.store.get_pending_results()), 1)
        self.application.bot.edit_message_reply_markup.side_effect = BadRequest("Message is not modified")
        await ui._announce_result(self.application, pending, "es")
        self.assertEqual(self.application.bot.edit_message_reply_markup.await_count, 2)
        self.application.bot.send_message.assert_awaited_once()
        paginated = self.db.get_paginated_message_state("-1", "500")
        self.assertEqual(paginated.list_type, "boss_rewards")
        self.assertTrue(paginated.unlocked)
        pages = json.loads(paginated.content_json)["pages"]
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(len(page) <= 1900 for page in pages))
        for user, points in awards:
            self.assertIn(f"({user}): +{points} pt", "\n".join(pages))
        self.assertEqual(self.store.get("-1", "10").announcement_message_id, "500")
        self.assertTrue(self.store.get("-1", "10").announcement_complete)
        self.assertEqual(self.store.get_pending_results(), ())

    async def test_initial_markup_already_applied_is_success_and_other_bad_requests_remain_errors(self):
        self.application.bot.edit_message_reply_markup.side_effect = BadRequest("Message is not modified")
        await ui._set_announcement_keyboard(self.application, "-1", "500", 2)
        self.application.bot.edit_message_reply_markup.side_effect = BadRequest("message to edit not found")
        with self.assertRaisesRegex(BadRequest, "not found"):
            await ui._set_announcement_keyboard(self.application, "-1", "500", 2)
        self.application.bot.edit_message_reply_markup.side_effect = None
        await ui._set_announcement_keyboard(self.application, "-1", "500", 2)

    async def test_answer_failure_cannot_lose_committed_phase_advance_or_scheduled_refresh(self):
        spawn, _ = self.spawn(helpers=1)
        callback = SimpleNamespace(data="hisopo:boss:1", id="failed-answer", answer=AsyncMock(side_effect=TimedOut("answer failed")))
        expiration, appearance = MagicMock(), MagicMock()
        with self.assertRaises(TimedOut):
            await ui.handle_boss_callback(self.application, callback, "1", spawn, "es", self.now, expiration, appearance)
        self.assertEqual(self.store.get("-1", "10").phase, 2)
        expiration.assert_called_once()
        self.assertEqual(self.application.job_queue.run_once.call_args.kwargs["when"], 0)
        callback.answer.side_effect = None
        result = await ui.handle_boss_callback(self.application, callback, "1", spawn, "es", self.now, expiration, appearance)
        self.assertEqual(result.status, "duplicate")
        expiration.assert_called_once()
        self.assertEqual(self.store.get("-1", "10").phase1_users, ("1",))

    async def test_boss_reward_pagination_survives_metadata_ttl_and_old_cleanup(self):
        from galerazo_bot import telegram_bot

        for message_id, list_type in (("500", "boss_rewards"), ("501", "hisopos")):
            self.db.save_paginated_message_state(
                chat_id="-1", message_id=message_id, list_type=list_type, requester_user_id="0",
                content_json=json.dumps({"pages": ["First", "Second"]}), unlocked=True, current_page=1,
            )
        with self.db._connect() as conn:
            conn.execute("UPDATE paginated_message_states SET created_at = '2000-01-01 00:00:00'")
        old = self.db.list_paginated_message_states_before("2001-01-01 00:00:00")
        self.assertEqual([state.message_id for state in old], ["501"])
        message = SimpleNamespace(chat=SimpleNamespace(id=-1), message_id=500, delete=AsyncMock(), edit_text=AsyncMock())
        callback = SimpleNamespace(from_user=SimpleNamespace(id=1), message=message)
        response = await telegram_bot._handle_paginated_callback(callback, self.db, frozenset(), ("page", "500", "2"))
        self.assertIsNone(response)
        message.delete.assert_not_awaited()
        self.assertEqual(message.edit_text.call_args.kwargs["text"], "Second")
        bot = SimpleNamespace(delete_message=AsyncMock())
        await telegram_bot._cleanup_old_paginated_messages(self.db, bot)
        bot.delete_message.assert_awaited_once_with(chat_id=-1, message_id=501)
        self.assertIsNotNone(self.db.get_paginated_message_state("-1", "500"))

    async def test_confirmed_single_page_announcement_finishes_after_restart_without_resend(self):
        self.spawn()
        self.store.expire("-1", "10", self.now + timedelta(hours=1))
        self.store.mark_announced("-1", "10", "known-receipt")
        await ui._announce_result(self.application, self.store.get("-1", "10"), "es")
        self.application.bot.send_message.assert_not_awaited()
        self.application.bot.edit_message_reply_markup.assert_not_awaited()
        self.assertTrue(self.store.get("-1", "10").announcement_complete)

    async def test_recovery_checks_active_bosses_and_pending_results(self):
        self.spawn()
        self.db.save_hisopo_spawn("-1", "other", "common", 1, "message", self.now.isoformat(), (self.now + timedelta(hours=1)).isoformat())
        with patch.object(ui, "datetime") as clock:
            clock.now.return_value = self.now
            await ui.recover_boss_results(self.context)
            self.assertEqual(self.store.get("-1", "10").status, "active")
            clock.now.return_value = self.now + timedelta(hours=1)
            await ui.recover_boss_results(self.context)
        self.assertEqual(self.store.get("-1", "10").status, "lost")
        self.assertEqual(len(self.store.get_pending_results()), 1)
        self.assertEqual(self.application.job_queue.run_once.call_args.kwargs["name"], "boss-refresh:-1:10")
