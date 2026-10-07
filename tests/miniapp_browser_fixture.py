"""Loopback-only Mini App API for the optional cross-repository browser test.

Run with ``python -m tests.miniapp_browser_fixture --directory <temp-dir>``.
All identities and credentials are fixtures; no .env, polling or Telegram calls.
The caller owns the temporary directory and this child process's lifecycle.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiohttp import web

from galerazo_bot.database import Database
from galerazo_bot.mini_app import PRODUCTION_MINI_APP_URL, build_mini_app
from galerazo_bot.monetization import create_shared_album_context
from tests.test_mini_app import signed_init_data


TOKEN = "token"
PROXY_SECRET = "browser-fixture-proxy-secret-000000000000"


def prepare(directory: Path):
    db = Database(directory / "browser-fixture.sqlite3")
    db.get_or_create_user("1", "Ada (fixture)", "ada_fixture")
    db.get_or_create_user("2", "Bob (fixture)", "bob_fixture")
    for recipient, item in (("1", "stellar"), ("2", "massive")):
        db.grant_paid_hisopo(gifted_by_user_id="2", recipient_user_id=recipient,
                            hisopo_key=item, gifted_at="2026-10-07")
    for chat, title in (("-1", "Shared group"), ("-2", "My group"),
                        ("-9", "Hidden owner group"), ("-3", "Empty group")):
        db.register_chat(chat, "supergroup", title)
    with db._connect() as connection:
        for chat, owner, count in (("-1", "1", 3), ("-2", "2", 7), ("-9", "1", 99)):
            connection.execute(
                "INSERT INTO hisopo_collections VALUES (?, ?, 'common', ?, 'first', 'last')",
                (chat, owner, count),
            )
    shared = create_shared_album_context(TOKEN, chat_id="-1", user_id="1")
    empty = create_shared_album_context(TOKEN, chat_id="-3", user_id="1")
    visitor = {"id": 2, "first_name": "Bob (fixture)"}
    contexts = {
        "shared": signed_init_data(user=visitor, start_param=shared),
        "own": signed_init_data(user=visitor),
        "owner": signed_init_data(start_param=shared),
        "empty": signed_init_data(user=visitor, start_param=empty),
        "invalid": signed_init_data(user=visitor, start_param="s1_invalid"),
        "expired": signed_init_data(user=visitor, start_param=shared, auth_date=int(
            (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())),
    }
    bot = SimpleNamespace(create_invoice_link=AsyncMock(return_value="https://t.me/$fixture"))
    app = build_mini_app(db=db, bot=bot, bot_token=TOKEN,
                         public_url=PRODUCTION_MINI_APP_URL, proxy_secret=PROXY_SECRET)
    return app, {"proxySecret": PROXY_SECRET, "initData": contexts}


async def serve(directory: Path):
    app, configuration = prepare(directory)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    try:
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        configuration["origin"] = f"http://127.0.0.1:{runner.addresses[0][1]}"
        target = directory / "fixture.json"
        temporary = directory / "fixture.pending"
        temporary.write_text(json.dumps(configuration), encoding="utf-8")
        temporary.replace(target)
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if not args.directory.is_dir() or any(args.directory.iterdir()):
        parser.error("Use an existing empty temporary directory")
    asyncio.run(serve(args.directory))
