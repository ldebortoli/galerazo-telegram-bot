from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlencode

from aiohttp import web

from galerazo_bot.database import Database, DonorLeaderboardEntry
from galerazo_bot.mini_app import (
    InitDataError,
    MINI_APP_API_KEY,
    ALL_GROUPS_CHAT_ID,
    MiniAppApi,
    MiniAppService,
    MiniAppUser,
    build_mini_app,
    direct_mini_app_url,
    security_headers,
    start_mini_app,
    validate_init_data,
)
from galerazo_bot.monetization import create_album_context, parse_payment_payload


NOW = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)


def signed_init_data(
    token: str = "token",
    *,
    user: dict | None = None,
    auth_date: int | None = None,
    start_param: str | None = None,
    extra: dict[str, str] | None = None,
) -> str:
    values = {
        "auth_date": str(
            auth_date
            if auth_date is not None
            else int(datetime.now(timezone.utc).timestamp())
        ),
        "query_id": "query",
        "user": json.dumps(
            user or {"id": 1, "first_name": "Ada", "last_name": "Lovelace", "username": "ada"},
            separators=(",", ":"),
        ),
    }
    if start_param is not None:
        values["start_param"] = start_param
    if extra:
        values.update(extra)
    data_check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def request_stub(*, headers=None, query=None, body=None, json_error=None, path="/api/test"):
    json_method = AsyncMock(return_value=body)
    if json_error is not None:
        json_method.side_effect = json_error
    return SimpleNamespace(
        headers=headers or {},
        query=query or {},
        json=json_method,
        path=path,
    )


class MiniAppAuthenticationTests(unittest.TestCase):
    def test_support_copy_describes_club_and_privacy_without_stellar_reward(self) -> None:
        mini_app_root = Path(__file__).resolve().parent.parent / "mini_app"
        html = (mini_app_root / "index.html").read_text(encoding="utf-8")
        javascript = (mini_app_root / "app.js").read_text(encoding="utf-8")

        self.assertIn("Invitale Stars al proyecto", html)
        self.assertNotIn("Invitále", html)
        self.assertIn("Elegí cómo aparecer", html)
        self.assertNotIn("Tu nombre, solo si querés", html)
        self.assertIn("No entrega Hisopos, puntos ni ventajas", javascript)
        self.assertNotIn("Recibís un Hisopo Estelar", javascript)
        self.assertIn("Tus aportes aparecen como anónimos", javascript)

    def test_valid_init_data_and_direct_link(self) -> None:
        context = create_album_context("token", chat_id="-1001", user_id="1")
        user = validate_init_data(
            signed_init_data(
                auth_date=int(NOW.timestamp()),
                start_param=context,
                extra={"signature": "included-in-the-signed-data"},
            ),
            "token",
            now=NOW,
        )
        self.assertEqual(
            (user.user_id, user.display_name, user.username, user.start_param),
            ("1", "Ada Lovelace", "ada", context),
        )
        url = direct_mini_app_url(
            "token",
            bot_username="@galerazo_bot",
            short_name="hisopos",
            chat_id="-1001",
            user_id="1",
        )
        self.assertTrue(url.startswith("https://t.me/galerazo_bot/hisopos?startapp="))

        minimal = validate_init_data(
            signed_init_data(
                user={"id": 2, "first_name": "Solo"},
                auth_date=int(NOW.timestamp()),
            ),
            "token",
            now=NOW,
        )
        self.assertEqual((minimal.display_name, minimal.username, minimal.start_param), ("Solo", None, None))
        fallback_name = validate_init_data(
            signed_init_data(user={"id": 3}, auth_date=int(NOW.timestamp())),
            "token",
            now=NOW,
        )
        self.assertEqual(fallback_name.display_name, "Usuario")

    def test_init_data_rejections(self) -> None:
        with self.assertRaisesRegex(InitDataError, "Falta"):
            validate_init_data("auth_date=1", "token", now=NOW)
        with self.assertRaisesRegex(InitDataError, "firma"):
            validate_init_data(
                signed_init_data(auth_date=int(NOW.timestamp())) + "x", "token", now=NOW
            )

        malformed_values = {
            "auth_date": "not-an-int",
            "user": "not-json",
        }
        for overrides in (
            {"auth_date": "not-an-int"},
            {"user": "not-json"},
            {"user": "{}"},
        ):
            values = {
                "auth_date": str(int(NOW.timestamp())),
                "query_id": "query",
                "user": json.dumps({"id": 1, "first_name": "Ada"}),
                **overrides,
            }
            data_check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
            secret = hmac.new(b"WebAppData", b"token", hashlib.sha256).digest()
            values["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
            with self.subTest(overrides=overrides), self.assertRaisesRegex(InitDataError, "incompletos"):
                validate_init_data(urlencode(values), "token", now=NOW)
        self.assertEqual(set(malformed_values), {"auth_date", "user"})

        for auth_date in (
            int((NOW + timedelta(seconds=1)).timestamp()),
            int((NOW - timedelta(hours=2)).timestamp()),
        ):
            with self.subTest(auth_date=auth_date), self.assertRaisesRegex(InitDataError, "venció"):
                validate_init_data(signed_init_data(auth_date=auth_date), "token", now=NOW)


class MiniAppApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temporary.name) / "test.sqlite3")
        self.db.get_or_create_user("1", "Ada Lovelace", "ada")
        self.db.get_or_create_user("2", "Bob Builder", "bobby")
        self.db.register_chat("-1", "group", "Álbum Uno")
        with self.db._connect() as conn:
            conn.execute(
                """
                INSERT INTO hisopo_collections (
                    chat_id, user_id, hisopo_type, capture_count,
                    first_captured_at, last_captured_at
                ) VALUES ('-1', '1', 'common', 3, 'first', 'last')
                """
            )
        self.bot = SimpleNamespace(create_invoice_link=AsyncMock(return_value="https://t.me/invoice"))
        self.api = MiniAppApi(
            db=self.db,
            bot_token="token",
            bot=self.bot,
            public_url="https://example.test/",
        )
        self.headers = {"X-Telegram-Init-Data": signed_init_data()}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    async def test_index_authentication_and_preview_bootstrap(self) -> None:
        response = await self.api.index(request_stub())
        self.assertEqual(response._path.name, "index.html")
        self.assertEqual(response._path.parent.name, "mini_app")

        with self.assertRaises(web.HTTPUnauthorized):
            await self.api.bootstrap(request_stub())

        preview_db = MagicMock()
        preview_db.owns_paid_hisopo.return_value = False
        preview_db.get_donor_leaderboard.return_value = []
        preview = MiniAppApi(
            db=preview_db,
            bot_token="token",
            bot=None,
            public_url="http://localhost:8765",
            preview_mode=True,
        )
        user = preview.authenticate(request_stub())
        self.assertEqual(user.user_id, "preview")
        payload = json.loads((await preview.bootstrap(request_stub())).text)
        self.assertEqual(payload["albums"][0]["title"], "Todos los grupos")
        self.assertEqual(payload["selected_chat_id"], ALL_GROUPS_CHAT_ID)
        self.assertEqual(len(payload["albums"]), 3)
        self.assertEqual(
            next(item for item in payload["paid_hisopos"] if item["key"] == "serene")[
                "quantity"
            ],
            1,
        )
        self.assertEqual(len(payload["paid_hisopos"]), 15)
        self.assertEqual(payload["paid_hisopos"][-2]["key"], "galerazo")
        self.assertEqual(payload["paid_hisopos"][-2]["price_stars"], 6000)
        self.assertEqual(payload["club"]["periods_paid"], 2)

        group_payload = json.loads(
            (
                await preview.bootstrap(
                    request_stub(query={"chat_id": "-1004433295809"})
                )
            ).text
        )
        self.assertEqual(group_payload["selected_chat_id"], "-1004433295809")
        self.assertEqual(group_payload["natural_hisopos"][0]["quantity"], 5)

    async def test_real_bootstrap_selects_direct_query_fallback_and_empty_albums(self) -> None:
        direct_context = create_album_context("token", chat_id="-1", user_id="1")
        direct_headers = {
            "X-Telegram-Init-Data": signed_init_data(start_param=direct_context)
        }
        payload = json.loads(
            (await self.api.bootstrap(request_stub(headers=direct_headers))).text
        )
        self.assertEqual(payload["selected_chat_id"], "-1")
        self.assertEqual(payload["natural_hisopos"][0]["quantity"], 3)

        invalid_context_headers = {
            "X-Telegram-Init-Data": signed_init_data(start_param="invalid")
        }
        payload = json.loads(
            (await self.api.bootstrap(request_stub(headers=invalid_context_headers, query={"chat_id": "-1"}))).text
        )
        self.assertEqual(payload["selected_chat_id"], "-1")

        aggregate = json.loads(
            (await self.api.bootstrap(request_stub(headers=self.headers))).text
        )
        self.assertEqual(aggregate["selected_chat_id"], ALL_GROUPS_CHAT_ID)
        self.assertEqual(aggregate["albums"][0]["captures"], 3)

        no_album_data = signed_init_data(user={"id": 2, "first_name": "Grace"})
        payload = json.loads(
            (
                await self.api.bootstrap(
                    request_stub(
                        headers={"X-Telegram-Init-Data": no_album_data},
                        query={"chat_id": ALL_GROUPS_CHAT_ID},
                    )
                )
            ).text
        )
        self.assertIsNone(payload["selected_chat_id"])
        self.assertEqual(payload["albums"], [])

    async def test_invoice_preview_repeat_purchase_gifts_and_real_creation(self) -> None:
        with self.assertRaises(web.HTTPUnauthorized):
            await self.api.create_invoice(request_stub(body={"kind": "donation", "item_key": "25"}))
        with self.assertRaises(web.HTTPBadRequest):
            await self.api.create_invoice(request_stub(headers=self.headers, body={"kind": "bad"}))
        with self.assertRaises(web.HTTPBadRequest):
            await self.api.create_invoice(
                request_stub(
                    headers=self.headers,
                    json_error=json.JSONDecodeError("bad", "x", 0),
                )
            )

        self.db.record_star_payment(
            telegram_payment_charge_id="owned",
            provider_payment_charge_id=None,
            user_id="1",
            kind="product",
            item_key="serene",
            amount_stars=50,
            currency="XTR",
            invoice_payload="payload",
            source_chat_id=None,
            reward_hisopo_key="serene",
            paid_at="2026-08-27T10:00:00+00:00",
        )
        repeated = await self.api.create_invoice(
            request_stub(headers=self.headers, body={"kind": "product", "item_key": "serene"})
        )
        self.assertEqual(json.loads(repeated.text)["recipient_user_id"], "1")

        preview_db = MagicMock()
        preview_db.owns_paid_hisopo.return_value = False
        preview = MiniAppApi(
            db=preview_db,
            bot_token="token",
            bot=None,
            public_url="http://localhost",
            preview_mode=True,
        )
        preview_response = await preview.create_invoice(
            request_stub(body={"kind": "donation", "item_key": "25"})
        )
        self.assertTrue(json.loads(preview_response.text)["preview"])
        preview_gift = await preview.create_invoice(
            request_stub(
                body={"kind": "product", "item_key": "massive", "recipient": "@bobby"}
            )
        )
        self.assertIn("@bobby", json.loads(preview_gift.text)["message"])

        response = await self.api.create_invoice(
            request_stub(
                headers=self.headers,
                body={"kind": "product", "item_key": "massive", "source_chat_id": "-1"},
            )
        )
        self.assertEqual(json.loads(response.text)["invoice_url"], "https://t.me/invoice")
        self.assertNotIn("subscription_period", self.bot.create_invoice_link.await_args.kwargs)
        self.assertEqual(
            parse_payment_payload(
                "token", self.bot.create_invoice_link.await_args.kwargs["payload"]
            ).recipient_user_id,
            "1",
        )

        gifted = await self.api.create_invoice(
            request_stub(
                headers=self.headers,
                body={
                    "kind": "product",
                    "item_key": "massive",
                    "source_chat_id": ALL_GROUPS_CHAT_ID,
                    "recipient": "@bobby",
                },
            )
        )
        self.assertEqual(json.loads(gifted.text)["recipient_user_id"], "2")
        gift_call = self.bot.create_invoice_link.await_args.kwargs
        self.assertIn("Regalo para @bobby", gift_call["description"])
        gift_intent = parse_payment_payload("token", gift_call["payload"])
        self.assertEqual((gift_intent.user_id, gift_intent.recipient_user_id), ("1", "2"))

        numeric_gift = await self.api.create_invoice(
            request_stub(
                headers=self.headers,
                body={"kind": "product", "item_key": "massive", "recipient": "999"},
            )
        )
        self.assertEqual(json.loads(numeric_gift.text)["recipient_user_id"], "999")

        for body in (
            {"kind": "product", "item_key": "massive", "recipient": "bad!"},
            {"kind": "product", "item_key": "massive", "recipient": "0"},
            {"kind": "product", "item_key": "massive", "recipient": "@unknown"},
            {"kind": "donation", "item_key": "25", "recipient": "2"},
        ):
            with self.subTest(body=body), self.assertRaises(web.HTTPBadRequest):
                await self.api.create_invoice(request_stub(headers=self.headers, body=body))

        await self.api.create_invoice(
            request_stub(
                headers=self.headers,
                body={"kind": "subscription", "item_key": "club"},
            )
        )
        self.assertEqual(self.bot.create_invoice_link.await_args.kwargs["subscription_period"].days, 30)
        with self.assertRaises(web.HTTPBadRequest):
            await self.api.create_invoice(
                request_stub(
                    headers=self.headers,
                    body={"kind": "donation", "item_key": "25", "source_chat_id": "-999"},
                )
            )

    async def test_donor_visibility_preview_real_and_invalid(self) -> None:
        with self.assertRaises(web.HTTPUnauthorized):
            await self.api.donor_visibility(request_stub(body={"public": True}))
        with self.assertRaises(web.HTTPBadRequest):
            await self.api.donor_visibility(
                request_stub(
                    headers=self.headers,
                    json_error=json.JSONDecodeError("bad", "x", 0),
                )
            )
        with self.assertRaises(web.HTTPBadRequest):
            await self.api.donor_visibility(request_stub(headers=self.headers, body={"public": "yes"}))

        response = await self.api.donor_visibility(
            request_stub(headers=self.headers, body={"public": True})
        )
        self.assertTrue(json.loads(response.text)["public"])
        self.assertTrue(self.db.is_donor_display_public("1"))

        preview_db = MagicMock()
        preview = MiniAppApi(
            db=preview_db,
            bot_token="token",
            bot=None,
            public_url="http://localhost",
            preview_mode=True,
        )
        await preview.donor_visibility(request_stub(body={"public": True}))
        self.assertTrue(preview.preview_public)

    def test_payload_covers_album_and_donor_name_fallbacks(self) -> None:
        db = MagicMock()
        db.get_donor_leaderboard.return_value = [
            DonorLeaderboardEntry("1", "one", "One", 500, True),
            DonorLeaderboardEntry("2", "two", None, 100, True),
            DonorLeaderboardEntry("3", None, None, 50, True),
            DonorLeaderboardEntry("4", "four", "Four", 25, False),
        ]
        api = MiniAppApi(db=db, bot_token="token", bot=None, public_url="https://example.test")
        payload = api._bootstrap_payload(
            user=MiniAppUser("1", "One", "one", None),
            albums=[SimpleNamespace(chat_id="-1", title=None, discovered_count=1, capture_count=2)],
            selected_chat_id="-1",
            counts={"giant": 1},
            aggregate_counts={"giant": 1},
            ownership={"stellar": 2},
            club_periods=2,
            club_active_until=None,
            donor_public=True,
        )
        self.assertEqual(payload["albums"][0]["title"], "Todos los grupos")
        self.assertEqual(payload["albums"][1]["title"], "Grupo -1")
        self.assertEqual([entry["name"] for entry in payload["donors"]], ["One", "@two", "Usuario 3", "Anónimo"])
        self.assertEqual(payload["paid_hisopos"][-1]["quantity"], 2)
        self.assertEqual(next(item for item in payload["natural_hisopos"] if item["key"] == "giant")["quantity"], 1)

    async def test_security_headers_application_and_service_lifecycle(self) -> None:
        response = await security_headers(
            request_stub(path="/api/bootstrap"), AsyncMock(return_value=web.Response())
        )
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("default-src", response.headers["Content-Security-Policy"])
        static_response = await security_headers(
            request_stub(path="/static/app.js"), AsyncMock(return_value=web.Response())
        )
        self.assertNotIn("Cache-Control", static_response.headers)

        app = build_mini_app(
            db=self.db,
            bot_token="token",
            bot=self.bot,
            public_url="https://example.test",
            preview_mode=True,
        )
        self.assertIsInstance(app[MINI_APP_API_KEY], MiniAppApi)
        self.assertGreaterEqual(len(list(app.router.routes())), 7)

        service = await start_mini_app(
            db=self.db,
            bot_token="token",
            bot=self.bot,
            public_url="https://example.test",
            host="127.0.0.1",
            port=0,
        )
        self.assertIsInstance(service, MiniAppService)
        await service.stop()


if __name__ == "__main__":
    unittest.main()
