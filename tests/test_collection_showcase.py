"""Collection ownership, bot showcase and exact JSON integer boundaries."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiohttp import web
from telegram import User

from galerazo_bot.command_handlers.hisopos import handle_collection
from galerazo_bot.database import Database
from galerazo_bot.hisopos import COLLECTIBLE_HISOPO_KEYS, MAX_HISOPO_QUANTITY, render_hisopo_collection
from galerazo_bot.i18n import TRANSLATIONS
from galerazo_bot.mini_app import MiniAppApi, _json_count
from galerazo_bot.monetization import CLUB_HISOPO, PAID_HISOPOS
from galerazo_bot.roles import CommandContext, UserLevel
from galerazo_bot.telegram_bot import _collection_target_user, _send_hisopo_collection
from tests.test_mini_app import request_stub, signed_init_data
from tests.test_telegram_bot_monetization import settings
from galerazo_bot.monetization import create_shared_album_context


@pytest.mark.parametrize("author, sender_chat", [(None, None), (User(0, "Unknown", False), None), (User(2, "Anonymous", True), object())])
def test_reply_without_personal_author_falls_back_to_requester(author, sender_chat):
    requester = User(1, "Requester", False)
    reply = SimpleNamespace(from_user=author, sender_chat=sender_chat)
    assert _collection_target_user(SimpleNamespace(reply_to_message=reply), requester) is requester


def test_real_users_and_bots_can_be_collection_targets():
    requester = User(1, "Requester", False)
    assert _collection_target_user(SimpleNamespace(reply_to_message=None), requester) is requester
    for author in (User(2, "User", False), User(99, "Galerazo Bot", True)):
        reply = SimpleNamespace(from_user=author, sender_chat=None)
        assert _collection_target_user(SimpleNamespace(reply_to_message=reply), requester) is author


def test_showcase_is_complete_exact_and_fits_telegram_in_every_language():
    for language in TRANSLATIONS:
        text = render_hisopo_collection([], "Galerazo Bot", "99", language=language, showcase=True)
        assert text.count(f": {MAX_HISOPO_QUANTITY}") == len(COLLECTIBLE_HISOPO_KEYS) + len(PAID_HISOPOS) + 1
        assert str(len(COLLECTIBLE_HISOPO_KEYS) * MAX_HISOPO_QUANTITY) in text
        assert "❓" not in text
        assert len(text.encode("utf-16-le")) // 2 <= 4096


async def test_bot_showcase_command_and_shared_album_never_write_inventory(tmp_path):
    db = Database(tmp_path / "db.sqlite3")
    db.get_or_create_user("1", "Viewer")
    token = "99:fixture"
    bot = User(99, "Galerazo Bot", True)
    requester = User(1, "Viewer", False)
    api = MiniAppApi(db=db, bot_token=token, bot=SimpleNamespace(), public_url="https://example.test")
    for chat_id in ("-1", "-2"):
        db.register_chat(chat_id, "supergroup", f"Group {chat_id}")
        context = CommandContext(sender_id="1", chat_id=chat_id, chat_type="supergroup", user_level=UserLevel.COMMON,
                                 raw_text="/coleccionhisopos", args="", bot_user_id="99", reply_to_user_id="99", reply_to_display_name="Galerazo Bot")
        assert f"Hisopo Mosquito: {MAX_HISOPO_QUANTITY}" in handle_collection(context, db)
        message = SimpleNamespace(chat=SimpleNamespace(id=int(chat_id), type="supergroup"), reply_text=AsyncMock())
        assert await _send_hisopo_collection(db=db, message=message, requester=requester, target_user=bot,
                                            settings=settings(), bot_username="galerazo_bot", bot_user_id="99")
        assert f"Hisopo Mosquito: {MAX_HISOPO_QUANTITY}" in message.reply_text.await_args.args[0]
        headers = {"X-Telegram-Init-Data": signed_init_data(token, start_param=create_shared_album_context(token, chat_id=chat_id, user_id="99"))}
        payload = json.loads((await api.bootstrap(request_stub(headers=headers))).text)
        assert payload["view"] == "shared"
        assert payload["album_owner"]["id"] == "99"
        assert payload["user"]["id"] == "1"
        assert all(item["quantity"] == str(MAX_HISOPO_QUANTITY) for item in payload["natural_hisopos"] + payload["paid_hisopos"])
        assert payload["albums"] == [{"chat_id": chat_id, "title": f"Group {chat_id}", "discovered": len(COLLECTIBLE_HISOPO_KEYS), "captures": str(MAX_HISOPO_QUANTITY * len(COLLECTIBLE_HISOPO_KEYS))}]
        assert next(item for item in payload["paid_hisopos"] if item["key"] == "dengue")["name"] == "Hisopo Mosquito"
        with pytest.raises(web.HTTPForbidden):
            await api.bootstrap(request_stub(headers=headers, query={"chat_id": "all"}))
        own = json.loads((await api.bootstrap(request_stub(headers=headers, query={"view": "mine"}))).text)
        assert own["view"] == "own"
        assert all(item["quantity"] == 0 for item in own["natural_hisopos"] + own["paid_hisopos"])
        assert db.get_hisopo_collection(chat_id, "99") == []
        assert db.get_paid_hisopo_ownership("99") == []
    assert db.get_hisopo_scores("-1") == []


def test_json_count_preserves_exact_boundary_and_real_inventory(tmp_path):
    assert _json_count(0) == 0
    assert _json_count(2**53 - 1) == 2**53 - 1
    assert _json_count(2**53) == str(2**53)
    assert _json_count(MAX_HISOPO_QUANTITY) == str(MAX_HISOPO_QUANTITY)
    db = Database(tmp_path / "db.sqlite3")
    db.get_or_create_user("1", "Collector")
    db.register_chat("-1", "group", "Group")
    with db._connect() as conn:
        conn.execute("INSERT INTO hisopo_collections VALUES ('-1','1','common',?,'first','last')", (MAX_HISOPO_QUANTITY,))
        conn.execute("INSERT INTO paid_hisopo_ownership VALUES ('1',?,?, 'first','last')", (CLUB_HISOPO.key, MAX_HISOPO_QUANTITY))
    assert db.get_hisopo_collection("-1", "1")[0].capture_count == MAX_HISOPO_QUANTITY
    assert db.get_paid_hisopo_ownership("1")[0].quantity == MAX_HISOPO_QUANTITY
