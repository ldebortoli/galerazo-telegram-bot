from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from galerazo_bot.chat_config import (
    build_command_group_menu,
    build_command_groups_menu,
    build_language_menu,
    build_main_menu,
    parse_config_callback,
)
from galerazo_bot.roles import UserLevel
from galerazo_bot.telegram_bot import _config_callback_entrypoint


def _callback_data(markup) -> list[str | None]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def _callback_fixture() -> tuple[object, object, object, object]:
    db = MagicMock()
    db.is_user_blocked.return_value = False
    db.is_user_restricted_in_chat.return_value = False
    db.get_chat_settings.return_value = SimpleNamespace(language="es")

    message = MagicMock()
    message.chat = SimpleNamespace(id=-1, type="group")
    message.delete = AsyncMock()

    callback_query = MagicMock()
    callback_query.data = "config:close"
    callback_query.message = message
    callback_query.answer = AsyncMock()

    update = MagicMock()
    update.callback_query = callback_query
    update.effective_user = SimpleNamespace(id=10, full_name="User", username="user")

    context = MagicMock()
    context.bot = MagicMock()
    state = SimpleNamespace(
        db=db,
        settings=SimpleNamespace(telegram_dev_user_ids=frozenset()),
    )
    return update, context, state, message


class ConfigMenuTests(unittest.IsolatedAsyncioTestCase):
    def test_every_config_menu_has_close_button(self) -> None:
        menus = (
            build_main_menu("es"),
            build_language_menu("es"),
            build_command_groups_menu("es"),
            build_command_group_menu("galeraza", True, "es"),
        )

        for menu in menus:
            self.assertIn("config:close", _callback_data(menu))

    def test_close_callback_is_parsed(self) -> None:
        self.assertEqual(parse_config_callback("config:close"), ("close",))

    async def test_common_user_cannot_close_config_menu(self) -> None:
        update, context, state, message = _callback_fixture()

        with (
            patch("galerazo_bot.telegram_bot._state", return_value=state),
            patch(
                "galerazo_bot.telegram_bot._resolve_user_level",
                new=AsyncMock(return_value=UserLevel.COMMON),
            ),
        ):
            await _config_callback_entrypoint(update, context)

        message.delete.assert_not_awaited()
        update.callback_query.answer.assert_awaited_once_with(
            "No tenés permisos suficientes para usar esta botonera."
        )

    async def test_admin_and_dev_can_close_config_menu(self) -> None:
        for level in (UserLevel.ADMIN, UserLevel.DEV):
            with self.subTest(level=level):
                update, context, state, message = _callback_fixture()
                with (
                    patch("galerazo_bot.telegram_bot._state", return_value=state),
                    patch(
                        "galerazo_bot.telegram_bot._resolve_user_level",
                        new=AsyncMock(return_value=level),
                    ),
                ):
                    await _config_callback_entrypoint(update, context)

                message.delete.assert_awaited_once_with()
                update.callback_query.answer.assert_awaited_once_with(text="mensaje eliminado")


if __name__ == "__main__":
    unittest.main()
