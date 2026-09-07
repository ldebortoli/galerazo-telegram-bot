from __future__ import annotations

import json
import re
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

from galerazo_bot import config, telegram_bot as tb
from galerazo_bot.database import Database
from galerazo_bot.mini_app import (
    InitDataError, PRODUCTION_MINI_APP_URL, PROXY_SECRET_HEADER,
    build_mini_app, start_mini_app, validate_init_data, validate_mini_app_runtime,
)
from galerazo_bot.monetization import create_album_context, parse_album_context, parse_payment_payload, _signature
from galerazo_bot.telegram_payments import answer_pre_checkout_query, process_successful_payment
from tests.test_mini_app import signed_init_data
from tests.test_telegram_bot_monetization import settings, state
from tests.test_telegram_payments import payment_message, successful_payment


SECRET = "proxy-test-secret-" * 3


@pytest.fixture
def backend(tmp_path):
    db = Database(tmp_path / "api.sqlite3")
    db.get_or_create_user("1", "Alice", "alice")
    db.get_or_create_user("2", "Bob", "bobby")
    for chat, user, count in (("-1", "1", 3), ("-2", "1", 2), ("-3", "2", 9)):
        db.register_chat(chat, "supergroup", f"Album {chat}")
        with db._connect() as conn:
            conn.execute(
                "INSERT INTO hisopo_collections VALUES (?, ?, 'common', ?, 'first', 'last')",
                (chat, user, count),
            )
    bot = SimpleNamespace(create_invoice_link=AsyncMock(return_value="https://t.me/$fixture"))
    return db, bot


@pytest.fixture
async def client(backend):
    db, bot = backend
    app = build_mini_app(db=db, bot=bot, bot_token="token", public_url=PRODUCTION_MINI_APP_URL, proxy_secret=SECRET)
    async with TestClient(TestServer(app)) as client:
        yield client


def headers(*, init_data=None, secret=SECRET):
    return {PROXY_SECRET_HEADER: secret, "X-Telegram-Init-Data": init_data or signed_init_data()}


@pytest.mark.parametrize("secret", [None, "", "short", "x" * 257, " " * 32])
async def test_missing_or_invalid_proxy_configuration_fails_closed(backend, secret):
    db, bot = backend
    app = build_mini_app(db=db, bot=bot, bot_token="token", public_url=PRODUCTION_MINI_APP_URL, proxy_secret=secret)
    async with TestClient(TestServer(app)) as client:
        response = await client.get("/api/bootstrap", headers=headers())
        assert response.status == 503
        assert response.headers["Cache-Control"] == "no-store"
        assert await response.json() == {"error": "http_503"}
        bot.create_invoice_link.assert_not_called()


async def test_proxy_and_telegram_are_separate_authentication_gates(client, backend):
    db, bot = backend
    for supplied, expected in (
        ({}, 403),
        (headers(secret="wrong"), 403),
        ({PROXY_SECRET_HEADER: SECRET}, 401),
        (headers(init_data=signed_init_data("other-bot")), 401),
        (headers(init_data=signed_init_data(auth_date=int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()))), 401),
    ):
        response = await client.get("/api/bootstrap", headers=supplied)
        assert response.status == expected
        assert "Access-Control-Allow-Origin" not in response.headers
        assert response.headers["Cache-Control"] == "no-store"
        assert "hash=" not in await response.text()
    assert not db.get_paid_hisopo_ownership("1")
    bot.create_invoice_link.assert_not_called()


@pytest.mark.parametrize("path", ["/", "/static/app.js", "/assets/hisopos/hisopo-comun.png", "/miniapp", "/preview"])
async def test_backend_has_no_frontend_assets_or_preview_routes(client, path):
    response = await client.get(path)
    assert response.status == 404
    assert response.headers["Cache-Control"] == "no-store"


async def test_signed_album_can_switch_to_another_owned_album(client):
    signed = signed_init_data(start_param=create_album_context("token", chat_id="-1", user_id="1"))
    for query, selected, count in (("", "-1", 3), ("?chat_id=-2", "-2", 2), ("?chat_id=all", "all", 5)):
        response = await client.get("/api/bootstrap" + query, headers=headers(init_data=signed))
        assert response.status == 200
        data = await response.json()
        assert data["selected_chat_id"] == selected
        assert next(x for x in data["natural_hisopos"] if x["key"] == "common")["quantity"] == count
        assert {x["chat_id"] for x in data["albums"]} == {"all", "-1", "-2"}
        assert len(data["paid_hisopos"]) == 21
        assert not data.get("preview")


async def test_foreign_tampered_and_replayed_album_contexts_are_rejected(client):
    contexts = [
        "invalid",
        create_album_context("token", chat_id="-1", user_id="2"),
        create_album_context("other", chat_id="-1", user_id="1"),
        create_album_context("token", chat_id="-3", user_id="1"),
        "a1.-1.1.\u00f1",
    ]
    for context in contexts:
        response = await client.get("/api/bootstrap", headers=headers(init_data=signed_init_data(start_param=context)))
        assert response.status == 403
    response = await client.get("/api/bootstrap?chat_id=-3", headers=headers())
    assert response.status == 403
    for query in ("?unexpected=true", "?chat_id=-1&chat_id=-2"):
        response = await client.get("/api/bootstrap" + query, headers=headers())
        assert response.status == 400


@pytest.mark.parametrize("body", [None, [], "text", True, {"public": "true"}])
async def test_invalid_json_shapes_cannot_mutate_privacy_or_create_invoices(client, backend, body):
    for endpoint in ("donor-visibility", "invoice"):
        response = await client.post(f"/api/{endpoint}", data=json.dumps(body), headers={**headers(), "Content-Type": "application/json"})
        assert response.status == 400
    backend[1].create_invoice_link.assert_not_called()


async def test_api_bounds_and_failures_do_not_expose_credentials(client, backend, caplog):
    response = await client.post("/api/invoice", data='{"padding":"' + "x" * 17000 + '"}', headers=headers())
    assert response.status == 413
    assert response.headers["Cache-Control"] == "no-store"
    response = await client.post("/api/missing", headers=headers())
    assert response.status == 404
    response = await client.post("/api/bootstrap", headers=headers())
    assert response.status == 405
    init = signed_init_data()
    backend[1].create_invoice_link.side_effect = RuntimeError(f"{SECRET} {init}")
    response = await client.post("/api/invoice", headers=headers(init_data=init), json={"kind": "product", "item_key": "massive"})
    assert response.status == 502
    assert await response.json() == {"error": "temporarily_unavailable"}
    assert SECRET not in caplog.text and init not in caplog.text


async def test_http_parser_failures_never_log_raw_authentication_headers(backend, caplog):
    db, bot = backend
    service = await start_mini_app(db=db, bot=bot, bot_token="token", public_url=PRODUCTION_MINI_APP_URL, proxy_secret=SECRET, host="127.0.0.1", port=0)
    init = signed_init_data()
    try:
        port = service.site._server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            writer.write(("GET /api/bootstrap HTTP/1.1\r\nHost: localhost\r\n"
                          f"{PROXY_SECRET_HEADER}: {SECRET}\r\n"
                          f"X-Telegram-Init-Data: {init}\x00\r\n\r\n").encode())
            await writer.drain()
            response = await asyncio.wait_for(reader.read(16384), 5)
            assert b"400 Bad Request" in response
        finally:
            writer.close()
            await writer.wait_closed()
    finally:
        await service.stop()
    assert "Mini App HTTP transport event." in caplog.text
    assert SECRET not in caplog.text and init not in caplog.text


async def test_invoice_gift_to_payment_keeps_authoritative_price_owner_and_idempotency(client, backend):
    db, bot = backend
    response = await client.post("/api/invoice", headers=headers(), json={
        "kind": "product", "item_key": "dengue", "source_chat_id": "-1", "recipient": "@bobby",
        "user_id": "2", "price": 1, "quantity": 999,
    })
    assert response.status == 200
    assert (await response.json())["invoice_url"] == "https://t.me/$fixture"
    invoice = bot.create_invoice_link.await_args.kwargs
    assert invoice["title"] == "Hisopo 67"
    assert "Dengue" not in invoice["description"]
    assert invoice["currency"] == "XTR" and invoice["prices"][0].amount == 5000
    intent = parse_payment_payload("token", invoice["payload"])
    assert (intent.user_id, intent.recipient_user_id, intent.item_key, intent.source_chat_id) == ("1", "2", "dengue", "-1")
    assert not db.get_paid_hisopo_ownership("2")
    query = SimpleNamespace(invoice_payload=invoice["payload"], from_user=SimpleNamespace(id=2), currency="XTR", total_amount=5000, answer=AsyncMock())
    await answer_pre_checkout_query(query=query, db=db, bot_token="token")
    assert query.answer.await_args.kwargs["ok"] is False
    query.from_user.id = 1
    query.total_amount = 1
    await answer_pre_checkout_query(query=query, db=db, bot_token="token")
    assert query.answer.await_args.kwargs["ok"] is False
    query.total_amount = 5000
    await answer_pre_checkout_query(query=query, db=db, bot_token="token")
    query.answer.assert_awaited_with(ok=True)
    message = payment_message(successful_payment(invoice["payload"], amount=5000, charge_id="fixture-charge"))
    assert await process_successful_payment(message=message, db=db, bot_token="token")
    assert not await process_successful_payment(message=message, db=db, bot_token="token")
    assert "Hisopo 67" in message.reply_text.await_args.args[0]
    assert not db.get_paid_hisopo_ownership("1")
    assert [(x.hisopo_key, x.quantity) for x in db.get_paid_hisopo_ownership("2")] == [("dengue", 1)]
    assert not db.get_hisopo_scores("-1")


async def test_donor_visibility_is_owned_and_anonymous_by_default(client, backend):
    db, bot = backend
    response = await client.post("/api/invoice", headers=headers(), json={"kind": "donation", "item_key": "25"})
    assert response.status == 200
    message = payment_message(successful_payment(bot.create_invoice_link.await_args.kwargs["payload"], amount=25))
    await process_successful_payment(message=message, db=db, bot_token="token")
    for visible in (False, True, False):
        response = await client.post("/api/donor-visibility", headers=headers(), json={"public": visible, "user_id": "2"})
        assert response.status == 200 and (await response.json())["public"] == visible
        assert db.is_donor_display_public("1") == visible
        assert db.is_donor_display_public("2") is False
        data = await (await client.get("/api/bootstrap", headers=headers())).json()
        donor = data["donors"][0]
        assert donor["public"] == visible
        if not visible:
            assert donor["name"] == "Anónimo"
        assert set(donor) == {"name", "public", "amount_stars"}


def test_init_data_rejects_ambiguous_oversized_and_malformed_identity():
    for data in (
        "x" * 8193, "broken", "&".join(f"k{i}=v" for i in range(33)),
        signed_init_data() + "&auth_date=1", signed_init_data() + "&hash=\u00f1",
        signed_init_data(extra={"user": "[]"}),
        *(signed_init_data(user={"id": value}) for value in (True, 0, -1, "1", 2**63)),
    ):
        with pytest.raises(InitDataError):
            validate_init_data(data, "token")


def test_album_link_uses_url_safe_alphabet_and_accepts_legacy_signatures():
    current = create_album_context("token", chat_id="-1001234567890", user_id="123456789")
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,512}", current)
    assert parse_album_context("token", current, expected_user_id="123456789") == "-1001234567890"
    legacy = "a1.-1.1"
    assert parse_album_context("token", legacy + "." + _signature("token", "album", legacy), expected_user_id="1") == "-1"
    with pytest.raises(ValueError):
        parse_album_context("token", "a2_invalid", expected_user_id="1")


def test_runtime_configuration_checks_public_identity_secret_and_loopback():
    good = dict(public_url=PRODUCTION_MINI_APP_URL, proxy_secret=SECRET, host="127.0.0.1", bot_username="galerazo_bot")
    validate_mini_app_runtime(**good)
    for overrides in (
        {"public_url": "http://galerazo.com/miniapp"},
        {"public_url": "https://name:password@example.test"},
        {"public_url": "https://example.test/?token=secret"},
        {"public_url": "https://example.test/#token"},
        {"proxy_secret": None}, {"proxy_secret": "too-short"},
        {"host": "0.0.0.0"}, {"host": "::"},
        {"bot_username": "testeoMensajePrivadoBot"},
        {"public_url": "https://galerazo.com/other"},
    ):
        with pytest.raises(ValueError):
            validate_mini_app_runtime(**{**good, **overrides})
    with patch.dict("os.environ", {"MINI_APP_PROXY_SECRET": SECRET}, clear=True), patch.object(config, "load_dotenv"):
        current = config.load_settings()
    assert current.mini_app_proxy_secret == SECRET
    assert SECRET not in repr(current)


async def test_invalid_runtime_hides_buttons_and_does_not_start_or_mutate_bot():
    current = settings(telegram_mini_app_url=PRODUCTION_MINI_APP_URL)
    assert tb._available_mini_app_url(current, "galerazo_bot") is None
    current = settings(telegram_mini_app_url=PRODUCTION_MINI_APP_URL, mini_app_proxy_secret=SECRET)
    assert tb._available_mini_app_url(current, "testeoMensajePrivadoBot") is None
    bot = SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username="wrong_bot")), set_chat_menu_button=AsyncMock())
    app = SimpleNamespace(bot_data={"state": state(current)}, bot=bot)
    with patch.object(tb, "start_mini_app", AsyncMock()) as start:
        assert not await tb._configure_mini_app(app)
        start.assert_not_called()
    bot.set_chat_menu_button.assert_not_called()
