from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.error import Forbidden

from galerazo_bot import telegram_bot as tb
from galerazo_bot.config import Settings
from galerazo_bot.database import Database
from galerazo_bot.final_boss import FinalBossStore
from galerazo_bot.final_boss_telegram import recover_boss_results, refresh_boss_job
from galerazo_bot.giant_participants import GiantParticipantCountError
from galerazo_bot.hisopos import FINAL_BOSS_HISOPO, HisopoSelection
from galerazo_bot.i18n import t
from galerazo_bot.mini_app import MiniAppApi, MiniAppUser
from galerazo_bot.roles import UserLevel
from tests.test_telegram_bot_complete import message_stub


NOW = datetime(2030, 10, 7, 12, tzinfo=timezone.utc)


class FinalBossIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.db = Database(Path(self.temporary.name) / "boss.sqlite3")
        self.db.register_chat("-1", "supergroup", "Boss group")
        self.db.get_or_create_user("1", "Alice", "alice")
        self.settings = Settings(
            telegram_bot_token="fixture-token", telegram_dev_user_ids=frozenset(),
            telegram_log_chat_id=None, telegram_announcements_chat_id=None,
            database_path=self.db.path, telegram_hisopo_common_file_id="common-file",
            telegram_hisopo_mystery_file_id="mystery-file",
            telegram_hisopo_expired_file_id="expired-file",
            telegram_hisopo_final_boss_phase_1_file_id="boss-phase-1",
            telegram_hisopo_final_boss_phase_2_file_id="boss-phase-2",
            telegram_hisopo_final_boss_phase_3_file_id="boss-phase-3",
            telegram_hisopo_final_boss_phase_4_file_id="boss-phase-4",
            telegram_hisopo_final_boss_defeated_file_id="boss-defeated",
            telegram_hisopo_final_boss_victorious_file_id="boss-victorious",
        )
        self.bot = SimpleNamespace(
            send_photo=AsyncMock(return_value=SimpleNamespace(message_id=100)),
            send_message=AsyncMock(return_value=SimpleNamespace(message_id=900)),
            delete_messages=AsyncMock(return_value=True),
            edit_message_media=AsyncMock(), edit_message_caption=AsyncMock(),
            edit_message_reply_markup=AsyncMock(),
        )
        self.state = tb.BotState(db=self.db, settings=self.settings, bot_user_id="99")
        self.jobs = MagicMock()
        self.jobs.get_jobs_by_name.return_value = ()
        self.counter = SimpleNamespace(count=AsyncMock(return_value=2))
        self.application = SimpleNamespace(
            bot_data={"state": self.state, "giant_participant_counter": self.counter},
            bot=self.bot, job_queue=self.jobs,
        )
        self.context = SimpleNamespace(application=self.application, bot=self.bot)
        self.store = FinalBossStore(self.db)

    def save_boss(self, message_id="100", *, required=2, hidden=False, initialize=True):
        # Hidden Bosses are legacy persisted fixtures; new draws are always visible.
        spawn = self.db.save_hisopo_spawn(
            chat_id="-1", message_id=message_id, hisopo_type="final_boss",
            appearance_type="mystery" if hidden else "final_boss", points=0,
            source="message", spawned_at=NOW.isoformat(),
            expires_at=(NOW + timedelta(hours=1)).isoformat(), required_helpers=required,
        )
        if initialize:
            self.store.create("-1", message_id, NOW, 12)
        return spawn

    def callback_update(self, data, message_id=100, user_id=1):
        user = SimpleNamespace(id=user_id, full_name=f"User {user_id}", username=None)
        callback = SimpleNamespace(
            id=f"callback-{message_id}-{data}-{user_id}", data=data,
            answer=AsyncMock(), from_user=user,
            message=message_stub(message_id=message_id),
        )
        return SimpleNamespace(callback_query=callback, effective_user=user), callback

    def job_context(self, message_id="100"):
        return SimpleNamespace(
            application=self.application, bot=self.bot,
            job=SimpleNamespace(data={"chat_id": "-1", "message_id": message_id}),
        )

    async def test_visible_spawn_uses_verified_target_and_persists_one_hour(self) -> None:
        for index, target in enumerate((1, 15), 100):
            with self.subTest(target=target):
                self.counter.count.return_value = target
                self.bot.send_photo.return_value = SimpleNamespace(message_id=index)
                selection = HisopoSelection(FINAL_BOSS_HISOPO, FINAL_BOSS_HISOPO)
                with patch.object(tb, "select_hisopo_spawn", return_value=selection), patch.object(tb.secrets, "randbelow", return_value=12):
                    spawn = await tb._spawn_hisopo(self.application, "-1", "message", now=NOW)
                self.assertEqual(spawn.hisopo_type, "final_boss")
                self.assertEqual(spawn.required_helpers, target)
                self.assertEqual(spawn.expires_at, (NOW + timedelta(hours=1)).isoformat())
                sent = self.bot.send_photo.await_args.kwargs
                self.assertEqual(sent["photo"], "boss-phase-1")
                self.assertEqual(sent["reply_markup"].inline_keyboard[0][0].callback_data,
                                 "hisopo:boss:1")
                self.assertIn("JEFE FINAL", sent["caption"])
                self.assertEqual(self.store.get("-1", str(index)).safe_slot, 12)
                reloaded = FinalBossStore(Database(self.db.path)).get("-1", str(index))
                self.assertEqual(reloaded.required_helpers, target)
                self.assertEqual(reloaded.expires_at, spawn.expires_at)
        self.assertEqual(self.counter.count.await_count, 2)
        self.counter.count.assert_awaited_with("-1")
        self.assertEqual(tb._hisopo_file_id(self.settings, "final_boss"), "boss-phase-1")
        await tb._cleanup_old_hisopo_messages(self.application, "-1", NOW + timedelta(hours=25))
        self.bot.delete_messages.assert_not_awaited()
        with self.db._connect() as conn:
            self.assertEqual({row[0] for row in conn.execute("SELECT message_cleanup_status FROM hisopo_spawns")}, {"preserved"})

    async def test_census_is_lazily_reused_and_failure_prevents_delivery(self) -> None:
        self.application.bot_data.pop("giant_participant_counter")
        selection = HisopoSelection(FINAL_BOSS_HISOPO, FINAL_BOSS_HISOPO)
        with patch.object(tb, "select_hisopo_spawn", return_value=selection), patch.object(
            tb, "GiantParticipantCounter", return_value=self.counter,
        ) as factory:
            await tb._spawn_hisopo(self.application, "-1", "message", now=NOW)
            self.counter.count.side_effect = GiantParticipantCountError("Members unavailable")
            with self.assertRaisesRegex(tb.HisopoSpawnError, "confirmar la meta"):
                await tb._spawn_hisopo(self.application, "-1", "scheduled", now=NOW)
        factory.assert_called_once_with(self.settings, "99")
        self.bot.send_photo.assert_awaited_once()
        self.assertEqual(len(self.db.list_active_hisopo_spawns()), 1)

    async def test_every_boss_file_id_is_required_before_a_boss_can_appear(self) -> None:
        fields = [f"telegram_hisopo_final_boss_phase_{phase}_file_id" for phase in range(1, 5)]
        fields.extend(("telegram_hisopo_final_boss_defeated_file_id", "telegram_hisopo_final_boss_victorious_file_id"))
        for index, field in enumerate(fields):
            with self.subTest(field=field):
                self.application.bot_data["state"] = replace(
                    self.state, settings=replace(self.settings, **{field: None}),
                )
                selection = HisopoSelection(FINAL_BOSS_HISOPO, FINAL_BOSS_HISOPO)
                message_id = 100 + index
                self.bot.send_photo.return_value = SimpleNamespace(message_id=message_id)
                with patch.object(tb, "select_hisopo_spawn", return_value=selection):
                    spawn = await tb._spawn_hisopo(self.application, "-1", "message", now=NOW)
                self.assertEqual((spawn.hisopo_type, spawn.appearance_type), ("common", "common"))
                self.assertEqual(self.bot.send_photo.await_args.kwargs["photo"], "common-file")
                self.assertEqual(spawn.expires_at, (NOW + timedelta(minutes=20)).isoformat())
                self.assertIsNone(self.store.get("-1", str(message_id)))
        self.counter.count.assert_not_awaited()

    async def test_first_help_updates_caption_then_phase_change_uses_next_file_id(self) -> None:
        selection = HisopoSelection(FINAL_BOSS_HISOPO, FINAL_BOSS_HISOPO)
        with patch.object(tb, "select_hisopo_spawn", return_value=selection):
            await tb._spawn_hisopo(self.application, "-1", "message", now=NOW)
        self.assertEqual(self.bot.send_photo.await_args.kwargs["photo"], "boss-phase-1")
        first_update, _ = self.callback_update("hisopo:boss:1")
        with patch.object(tb, "datetime", wraps=datetime) as clock:
            clock.now.return_value = NOW
            await tb._hisopo_callback_entrypoint(first_update, self.context)
            await refresh_boss_job(self.job_context())
            self.bot.edit_message_media.assert_not_awaited()
            self.assertIn("1/2", self.bot.edit_message_caption.await_args.kwargs["caption"])
            second_update, _ = self.callback_update("hisopo:boss:1", user_id=2)
            clock.now.return_value = NOW + timedelta(seconds=1)
            await tb._hisopo_callback_entrypoint(second_update, self.context)
        await refresh_boss_job(self.job_context())
        self.assertEqual(self.bot.edit_message_media.await_args.kwargs["media"].media, "boss-phase-2")
        self.assertEqual(self.store.get("-1", "100").phase, 2)

    async def test_unanswered_spawn_timeout_shows_victorious_boss_and_preserves_message(self) -> None:
        with self.db._connect() as conn:
            conn.execute("INSERT INTO hisopo_scores (chat_id,user_id,points) VALUES ('-1','1',50)")
        selection = HisopoSelection(FINAL_BOSS_HISOPO, FINAL_BOSS_HISOPO)
        with patch.object(tb, "select_hisopo_spawn", return_value=selection):
            await tb._spawn_hisopo(self.application, "-1", "message", now=NOW)
        self.assertEqual(self.bot.send_photo.await_args.kwargs["photo"], "boss-phase-1")
        with patch.object(tb, "datetime", wraps=datetime) as clock:
            clock.now.return_value = NOW + timedelta(hours=1)
            await tb._expire_hisopo_job(self.job_context())
        await refresh_boss_job(self.job_context())
        media = self.bot.edit_message_media.await_args.kwargs["media"]
        self.assertEqual(media.media, "boss-victorious")
        self.assertIn("sin ninguna ayuda", media.caption)
        self.assertIn("−10", media.caption)
        self.assertEqual(self.db.get_hisopo_scores("-1")[0].points, 40)
        self.assertEqual(self.db.get_hisopo_collection("-1", "1"), [])
        await tb._cleanup_old_hisopo_messages(self.application, "-1", NOW + timedelta(hours=25))
        self.bot.delete_messages.assert_not_awaited()
        with self.db._connect() as conn:
            self.assertEqual(conn.execute("SELECT message_cleanup_status FROM hisopo_spawns WHERE message_id='100'").fetchone()[0], "preserved")

    async def test_restoration_preserves_phase_deadline_and_recovers_missing_state(self) -> None:
        self.save_boss("100", required=1)
        late_help = NOW + timedelta(minutes=59)
        self.assertEqual(self.store.contribute("-1", "100", "1", "first", 1, late_help).status, "advanced")
        expected = self.store.get("-1", "100")
        missing = self.save_boss("101", hidden=True, initialize=False)
        self.assertIsNone(self.store.get("-1", "101"))
        with patch.object(tb, "datetime", wraps=datetime) as clock, patch.object(tb.secrets, "randbelow", return_value=3):
            clock.now.return_value = NOW + timedelta(minutes=59, seconds=5)
            tb._restore_hisopo_jobs(self.application)
        self.assertEqual(self.store.get("-1", "100"), expected)
        recovered = self.store.get("-1", "101")
        self.assertEqual((recovered.phase, recovered.safe_slot, recovered.expires_at), (1, 3, missing.expires_at))
        expiration_jobs = [call.kwargs for call in self.jobs.run_once.call_args_list if call.args[0] is tb._expire_hisopo_job]
        self.assertEqual({job["data"]["message_id"] for job in expiration_jobs}, {"100", "101"})
        self.jobs.run_repeating.assert_called_once_with(recover_boss_results, interval=60, first=1, name="boss-results")
        # Restoring the queued refresh must not reveal an untouched Mystery.
        await refresh_boss_job(self.job_context("101"))
        self.bot.edit_message_media.assert_not_awaited()
        self.bot.edit_message_caption.assert_not_awaited()

    async def test_expiration_penalty_once_and_old_timer_cannot_expire_a_new_phase(self) -> None:
        self.save_boss("100")
        with self.db._connect() as conn:
            conn.execute("INSERT INTO hisopo_scores (chat_id,user_id,points) VALUES ('-1','1',50)")
        with patch.object(tb, "datetime", wraps=datetime) as clock:
            clock.now.return_value = NOW + timedelta(hours=1)
            await tb._expire_hisopo_job(self.job_context())
            await tb._expire_hisopo_job(self.job_context())
        self.assertEqual(self.store.get("-1", "100").reason, "abandoned")
        self.assertEqual(self.db.get_hisopo_scores("-1")[0].points, 40)
        self.assertEqual(self.db.get_hisopo_spawn("-1", "100").status, "rotten")
        self.assertIn(("-1", "100"), self.application.bot_data["boss_refresh_pending"])

        self.save_boss("101", required=1)
        self.store.contribute("-1", "101", "1", "late-help", 1, NOW + timedelta(minutes=59))
        self.jobs.reset_mock()
        with patch.object(tb, "datetime", wraps=datetime) as clock:
            clock.now.return_value = NOW + timedelta(hours=1)
            await tb._expire_hisopo_job(self.job_context("101"))
            self.assertEqual(self.store.get("-1", "101").status, "active")
            self.jobs.run_once.assert_not_called()
            clock.now.return_value = NOW + timedelta(minutes=89)
            await tb._expire_hisopo_job(self.job_context("101"))
        self.assertEqual(self.store.get("-1", "101").reason, "timeout")
        self.assertEqual(self.store.get("-1", "101").awards, ())
        self.assertEqual(self.db.get_hisopo_scores("-1")[0].points, 40)

    async def test_callbacks_route_boss_before_ordinary_expiry_and_reveal_once(self) -> None:
        self.save_boss(hidden=True)
        update, callback = self.callback_update("hisopo:capture")
        with patch.object(tb, "datetime", wraps=datetime) as clock, patch.object(
            self.db, "claim_expired_hisopo", wraps=self.db.claim_expired_hisopo,
        ) as ordinary_expiry:
            clock.now.return_value = NOW + timedelta(minutes=30)
            await tb._hisopo_callback_entrypoint(update, self.context)
            self.assertEqual(self.store.get("-1", "100").phase1_users, ("1",))
            self.assertEqual(self.db.get_hisopo_spawn("-1", "100").appearance_type, "final_boss")
            self.assertEqual(self.store.get("-1", "100").reveal_user_id, "1")
            ordinary_expiry.assert_not_called()
            callback.answer.assert_awaited_once_with(t("es", "boss.joined_popup"), show_alert=False)

            expired, expired_callback = self.callback_update("hisopo:boss:1", user_id=2)
            clock.now.return_value = NOW + timedelta(hours=1)
            await tb._hisopo_callback_entrypoint(expired, self.context)
            ordinary_expiry.assert_not_called()
        self.assertEqual(self.store.get("-1", "100").reason, "timeout")
        expired_callback.answer.assert_awaited_once_with(t("es", "boss.lost_popup"), show_alert=True)
        self.assertEqual(self.db.get_hisopo_collection("-1", "2"), [])

    async def test_boss_buttons_cannot_capture_ordinary_or_missing_swabs_and_blocked_users_cannot_help(self) -> None:
        self.db.save_hisopo_spawn(
            "-1", "110", "common", 1, "message", NOW.isoformat(),
            (NOW + timedelta(minutes=20)).isoformat(),
        )
        for message_id in (110, 999):
            update, callback = self.callback_update("hisopo:boss:1", message_id)
            with patch.object(tb, "datetime", wraps=datetime) as clock:
                clock.now.return_value = NOW
                await tb._hisopo_callback_entrypoint(update, self.context)
            callback.answer.assert_awaited_once_with(t("es", "hisopos.unavailable_alert"), show_alert=True)
        self.assertEqual(self.db.get_hisopo_spawn("-1", "110").status, "active")
        self.assertEqual(self.db.get_hisopo_scores("-1"), [])
        self.save_boss()
        self.db.block_user("1", "1")
        update, callback = self.callback_update("hisopo:boss:1")
        await tb._hisopo_callback_entrypoint(update, self.context)
        callback.answer.assert_awaited_once_with()
        self.assertEqual(self.store.get("-1", "100").phase1_users, ())

    async def test_rules_command_sends_two_localized_messages_only_after_allowed_response(self) -> None:
        self.db.set_chat_language("-1", "en")
        message = message_stub(text="/reglashisopo")
        user = SimpleNamespace(id=1, full_name="Alice", username="alice")
        update = SimpleNamespace(effective_message=message, effective_user=user, effective_chat=message.chat)
        with patch.object(tb, "_resolve_user_level", AsyncMock(return_value=UserLevel.COMMON)):
            await tb._handle_command_update(update, self.context)
        self.assertEqual(message.reply_text.await_count, 2)
        first, second = message.reply_text.await_args_list
        self.assertEqual(first.args[0] if first.args else first.kwargs["text"], t("en", "hisopos.rules"))
        self.assertEqual(second.args[0], t("en", "boss.rules"))
        self.assertTrue(second.kwargs["do_quote"])

        message.reply_text.reset_mock()
        message.text = "/hola"
        with patch.object(tb, "_resolve_user_level", AsyncMock(return_value=UserLevel.COMMON)):
            await tb._handle_command_update(update, self.context)
        self.assertEqual(message.reply_text.await_count, 1)
        self.assertNotIn("FINAL BOSS", str(message.reply_text.await_args))
        self.db.block_user("1", "1")
        message.reply_text.reset_mock()
        message.text = "/reglashisopo"
        await tb._handle_command_update(update, self.context)
        message.reply_text.assert_not_awaited()

    async def test_second_rules_message_removal_error_marks_chat_inactive(self) -> None:
        message = message_stub(text="/reglashisopo")
        message.reply_text.side_effect = [SimpleNamespace(message_id=200), Forbidden("bot was kicked from the supergroup chat")]
        user = SimpleNamespace(id=1, full_name="Alice", username=None)
        update = SimpleNamespace(effective_message=message, effective_user=user, effective_chat=message.chat)
        with patch.object(tb, "_resolve_user_level", AsyncMock(return_value=UserLevel.COMMON)):
            await tb._handle_command_update(update, self.context)
        self.assertEqual(message.reply_text.await_count, 2)
        with self.db._connect() as conn:
            row = conn.execute("SELECT status,status_reason FROM chats WHERE chat_id='-1'").fetchone()
        self.assertEqual(tuple(row), ("inactive", "send_message_failed"))

    async def test_rewards_pagination_uses_saved_pages_and_bounds_page_requests(self) -> None:
        pages = ["Victory\nAlice: +1300", "Victory\nBob: +600"]
        self.db.save_paginated_message_state(
            "-1", "900", "boss_rewards", "0", json.dumps({"pages": pages}), unlocked=True,
        )
        message = message_stub(message_id=900)
        await tb._edit_paginated_message(self.db, message, "900", page=2, unlocked=True)
        self.assertEqual(message.edit_text.await_args.kwargs["text"], pages[1])
        self.assertEqual(self.db.get_paginated_message_state("-1", "900").current_page, 2)
        await tb._edit_paginated_message(self.db, message, "900", page=999, unlocked=True)
        self.assertEqual(message.edit_text.await_args.kwargs["text"], pages[1])
        self.assertEqual(self.db.get_paginated_message_state("-1", "900").current_page, 2)
        self.assertNotIn("entities", message.edit_text.await_args.kwargs)

    async def test_mini_app_collection_unlocks_boss_only_after_all_four_phases(self) -> None:
        self.save_boss(required=1)
        api = MiniAppApi(db=self.db, bot_token="fixture-token", bot=None, public_url="https://example.test")
        request = SimpleNamespace(headers={}, query={})
        async def boss_item():
            with patch.object(api, "authenticate", return_value=MiniAppUser("1", "Alice", None, None)):
                payload = json.loads((await api.bootstrap(request)).text)
            return next(item for item in payload["natural_hisopos"] if item["key"] == "final_boss")

        before = await boss_item()
        self.assertEqual(before["quantity"], 0)
        self.assertEqual(before["name"], "Hisopo jefe final")
        self.assertEqual(before["image"], "/assets/hisopos/hisopo-jefe-final-derrotado.png")
        self.assertTrue((Path(__file__).resolve().parents[1] / "assets" / "hisopos" / "hisopo-jefe-final-derrotado.png").is_file())
        self.assertEqual(self.store.contribute("-1", "100", "1", "p1", 1, NOW).status, "advanced")
        for tap in range(1000):
            result = self.store.contribute("-1", "100", "1", f"p2-{tap}", 2, NOW + timedelta(seconds=1, milliseconds=tap * 100))
        self.assertEqual(result.status, "advanced")
        self.assertEqual((await boss_item())["quantity"], 0)
        for slot in range(20):
            result = self.store.contribute("-1", "100", str(1 + slot // 5), f"p3-{slot}", 3, NOW + timedelta(minutes=3, seconds=slot), slot)
        self.assertEqual(result.status, "advanced")
        self.assertEqual((await boss_item())["quantity"], 0)
        self.assertEqual(self.db.get_hisopo_scores("-1"), [])
        result = self.store.contribute("-1", "100", "1", "p4", 4, NOW + timedelta(minutes=4), 12)
        self.assertEqual(result.status, "won")
        self.assertEqual((await boss_item())["quantity"], 1)
        self.assertEqual(dict(result.awards)["1"], 2300)
        await tb._cleanup_old_hisopo_messages(self.application, "-1", NOW + timedelta(hours=25))
        self.bot.delete_messages.assert_not_awaited()
