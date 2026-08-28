from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telegram import (
    Bot,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
)

from galerazo_bot.i18n import DEFAULT_LANGUAGE
from galerazo_bot.roles import UserLevel
from galerazo_bot.telegram_bot import _suggested_bot_commands, _sync_botfather_commands


EXPECTED_USERNAME = "galerazo_bot"


async def synchronize() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN.")
    async with Bot(token) as bot:
        identity = await bot.get_me()
        if identity.username != EXPECTED_USERNAME:
            raise RuntimeError(
                f"Identidad incorrecta: se esperaba @{EXPECTED_USERNAME} y se obtuvo @{identity.username}."
            )
        await _sync_botfather_commands(bot)
        definitions = (
            (BotCommandScopeAllPrivateChats(), UserLevel.COMMON, False),
            (BotCommandScopeAllGroupChats(), UserLevel.COMMON, True),
            (BotCommandScopeAllChatAdministrators(), UserLevel.ADMIN, True),
        )
        for language_code in (None, "en"):
            language = language_code or DEFAULT_LANGUAGE
            for scope, level, include_groups in definitions:
                expected = _suggested_bot_commands(language, level, include_groups)
                actual = await bot.get_my_commands(scope=scope, language_code=language_code)
                if actual != expected:
                    raise RuntimeError(
                        f"La verificación de BotFather falló para {type(scope).__name__}/{language_code or 'default'}."
                    )
            defaults = await bot.get_my_commands(
                scope=BotCommandScopeDefault(),
                language_code=language_code,
            )
            if defaults:
                raise RuntimeError(
                    f"El scope global de BotFather no quedó vacío para {language_code or 'default'}."
                )
        print(f"BotFather sincronizado y verificado en @{identity.username}: 6 scopes y 2 defaults vacíos.")


if __name__ == "__main__":
    asyncio.run(synchronize())
