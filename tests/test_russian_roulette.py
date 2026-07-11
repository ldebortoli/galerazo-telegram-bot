from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram import ChatMember

from galerazo_bot.command_handlers.ruletarusa import ruletarusa
from galerazo_bot.database import Database, RussianRouletteShot
from galerazo_bot.roles import CommandContext, RussianRouletteHitResult, UserLevel
from galerazo_bot.telegram_bot import _bot_can_ban_members, _resolve_russian_roulette_hit


class RussianRouletteDatabaseTests(unittest.TestCase):
    def test_chambers_advance_and_reset_after_hit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.register_chat("-1", "group", "Group")

            self.assertEqual(
                db.play_russian_roulette("-1", "1", bullet_position=2),
                RussianRouletteShot(False, 5),
            )
            self.assertEqual(db.play_russian_roulette("-1", "1"), RussianRouletteShot(False, 4))
            self.assertEqual(db.play_russian_roulette("-1", "1"), RussianRouletteShot(True, 0))
            self.assertEqual(
                db.play_russian_roulette("-1", "1", bullet_position=5),
                RussianRouletteShot(False, 5),
            )

    def test_state_migrates_from_group_to_supergroup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.register_chat("-1", "group", "Group")
            db.play_russian_roulette("-1", "1", bullet_position=5)

            db.migrate_chat_id("-1", "-1001")

            self.assertEqual(
                db.play_russian_roulette("-1001", "1"),
                RussianRouletteShot(False, 4),
            )

    def test_group_is_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "test.sqlite3")
            db.register_chat("-1", "group", "Group")

            self.assertFalse(db.is_command_group_enabled("-1", "ruletarusa"))


class RussianRouletteCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_common_user_always_targets_self(self) -> None:
        db = SimpleNamespace(
            play_russian_roulette=lambda chat_id, user_id: RussianRouletteShot(False, 5),
            get_or_create_user=lambda *args: None,
        )
        context = CommandContext(
            sender_id="1",
            chat_id="-1",
            chat_type="group",
            user_level=UserLevel.COMMON,
            raw_text="/ruletarusa",
            args="",
            reply_to_user_id="2",
            can_run_russian_roulette=AsyncMock(return_value=True),
            resolve_russian_roulette_hit=AsyncMock(),
        )
        with patch.object(db, "play_russian_roulette", wraps=db.play_russian_roulette) as play:
            response = await ruletarusa(context, db)

        play.assert_called_once_with("-1", "1")
        self.assertIn("5", response)

    async def test_admin_can_target_reply_and_dev_is_immune(self) -> None:
        db = SimpleNamespace(
            play_russian_roulette=lambda chat_id, user_id: RussianRouletteShot(True, 0),
            get_or_create_user=lambda *args: None,
        )
        context = CommandContext(
            sender_id="1",
            chat_id="-1",
            chat_type="group",
            user_level=UserLevel.ADMIN,
            raw_text="/ruletarusa",
            args="",
            reply_to_user_id="2",
            can_run_russian_roulette=AsyncMock(return_value=True),
            resolve_russian_roulette_hit=AsyncMock(
                return_value=RussianRouletteHitResult.DEV_IMMUNE
            ),
        )

        response = await ruletarusa(context, db)

        context.resolve_russian_roulette_hit.assert_awaited_once_with("2")
        self.assertIn("indestructible", response)

    async def test_no_shot_is_consumed_without_bot_permissions(self) -> None:
        db = SimpleNamespace(
            play_russian_roulette=unittest.mock.Mock(),
            get_or_create_user=lambda *args: None,
        )
        context = CommandContext(
            sender_id="1",
            chat_id="-1",
            chat_type="group",
            user_level=UserLevel.COMMON,
            raw_text="/ruletarusa",
            args="",
            can_run_russian_roulette=AsyncMock(return_value=False),
            resolve_russian_roulette_hit=AsyncMock(),
        )

        response = await ruletarusa(context, db)

        db.play_russian_roulette.assert_not_called()
        self.assertIn("administrador", response)


class RussianRouletteTelegramTests(unittest.IsolatedAsyncioTestCase):
    async def test_bot_needs_restrict_members_permission(self) -> None:
        bot = SimpleNamespace(get_chat_member=AsyncMock())
        bot.get_chat_member.return_value = SimpleNamespace(
            status=ChatMember.ADMINISTRATOR,
            can_restrict_members=False,
        )
        self.assertFalse(await _bot_can_ban_members(bot, -1, "10"))

        bot.get_chat_member.return_value.can_restrict_members = True
        self.assertTrue(await _bot_can_ban_members(bot, -1, "10"))

    async def test_regular_hit_bans_but_protected_users_are_immune(self) -> None:
        bot = SimpleNamespace(get_chat_member=AsyncMock(), ban_chat_member=AsyncMock())
        bot.get_chat_member.return_value = SimpleNamespace(status=ChatMember.MEMBER)

        result = await _resolve_russian_roulette_hit(bot, -1, "20", "10", frozenset())

        self.assertEqual(result, RussianRouletteHitResult.BANNED)
        bot.ban_chat_member.assert_awaited_once_with(
            chat_id=-1,
            user_id=20,
            revoke_messages=False,
        )
        self.assertEqual(
            await _resolve_russian_roulette_hit(bot, -1, "10", "10", frozenset()),
            RussianRouletteHitResult.BOT_IMMUNE,
        )
        self.assertEqual(
            await _resolve_russian_roulette_hit(bot, -1, "30", "10", frozenset({"30"})),
            RussianRouletteHitResult.DEV_IMMUNE,
        )


if __name__ == "__main__":
    unittest.main()
