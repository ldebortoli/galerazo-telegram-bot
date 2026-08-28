from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote

from aiohttp import web
from telegram import LabeledPrice

from .database import Database
from .hisopos import COLLECTIBLE_HISOPO_KEYS
from .i18n import t
from .monetization import (
    CLUB_HISOPO,
    DONATION_TIERS,
    PAID_HISOPOS,
    STARS_CURRENCY,
    create_album_context,
    create_payment_payload,
    invoice_spec,
    parse_album_context,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MINI_APP_ROOT = PROJECT_ROOT / "mini_app"
HISOPO_ASSET_ROOT = PROJECT_ROOT / "assets" / "hisopos"
MAX_INIT_DATA_AGE_SECONDS = 60 * 60
ALL_GROUPS_CHAT_ID = "all"


NATURAL_HISOPO_IMAGES = {
    "common": "hisopo-comun.png",
    "silver": "hisopo-plateado.png",
    "gold": "hisopo-dorado.png",
    "diamond": "hisopo-diamante.png",
    "fleeting": "hisopo-fugaz.png",
    "mystery": "hisopo-misterioso.png",
    "putrid": "hisopo-putrefacto.png",
    "radioactive": "hisopo-radiactivo.png",
    "fake": "hisopo-falso.png",
    "twin": "hisopo-gemelo.png",
    "giant": "hisopo-gigante.png",
    "miracle": "hisopo-milagroso.png",
    "bomb": "hisopo-bomba.png",
    "frenetic": "hisopo-frenetico.png",
    "black_hole": "hisopo-agujero-negro.png",
    "expired": "hisopo-vencido.png",
}


@dataclass(frozen=True)
class MiniAppUser:
    user_id: str
    display_name: str
    username: str | None
    start_param: str | None


class InitDataError(ValueError):
    """Telegram Mini App authentication failed."""


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    now: datetime | None = None,
    max_age_seconds: int = MAX_INIT_DATA_AGE_SECONDS,
) -> MiniAppUser:
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    if not received_hash:
        raise InitDataError("Falta la firma de Telegram.")
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(received_hash, calculated_hash):
        raise InitDataError("La firma de Telegram no es válida.")
    try:
        auth_date = int(values["auth_date"])
        user_data = json.loads(values["user"])
        user_id = str(user_data["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InitDataError("Los datos de Telegram están incompletos.") from exc
    current_time = now or datetime.now(timezone.utc)
    age = int(current_time.timestamp()) - auth_date
    if age < 0 or age > max_age_seconds:
        raise InitDataError("La sesión de Telegram venció.")
    first_name = str(user_data.get("first_name") or "Usuario")
    last_name = str(user_data.get("last_name") or "")
    display_name = " ".join(part for part in (first_name, last_name) if part)
    username = user_data.get("username")
    return MiniAppUser(
        user_id=user_id,
        display_name=display_name,
        username=str(username) if username else None,
        start_param=values.get("start_param") or None,
    )


def direct_mini_app_url(
    bot_token: str,
    *,
    bot_username: str,
    short_name: str,
    chat_id: str,
    user_id: str,
) -> str:
    context = create_album_context(bot_token, chat_id=chat_id, user_id=user_id)
    return (
        f"https://t.me/{bot_username.removeprefix('@')}/{short_name}"
        f"?startapp={quote(context, safe='')}"
    )


class MiniAppApi:
    def __init__(
        self,
        *,
        db: Database,
        bot_token: str,
        bot: Any | None,
        public_url: str,
        preview_mode: bool = False,
    ) -> None:
        self.db = db
        self.bot_token = bot_token
        self.bot = bot
        self.public_url = public_url.rstrip("/")
        self.preview_mode = preview_mode
        self.preview_public = False

    def authenticate(self, request: web.Request) -> MiniAppUser:
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        if self.preview_mode and not init_data:
            return MiniAppUser("preview", "Cale", "cale", None)
        return validate_init_data(init_data, self.bot_token)

    async def index(self, _request: web.Request) -> web.FileResponse:
        return web.FileResponse(MINI_APP_ROOT / "index.html")

    async def bootstrap(self, request: web.Request) -> web.Response:
        try:
            user = self.authenticate(request)
        except InitDataError as exc:
            raise web.HTTPUnauthorized(text=str(exc)) from exc
        if self.preview_mode and user.user_id == "preview":
            return web.json_response(
                self._preview_bootstrap(user, request.query.get("chat_id"))
            )
        self.db.get_or_create_user(user.user_id, user.display_name, user.username)
        albums = self.db.list_hisopo_albums_for_user(user.user_id)
        aggregate_collection = self.db.get_hisopo_collection_totals(user.user_id)
        aggregate_counts = {
            entry.hisopo_type: entry.capture_count for entry in aggregate_collection
        }
        selected_chat_id = self._selected_chat_id(
            user,
            albums,
            request.query.get("chat_id"),
        )
        collection = (
            aggregate_collection
            if selected_chat_id == ALL_GROUPS_CHAT_ID
            else (
                self.db.get_hisopo_collection(selected_chat_id, user.user_id)
                if selected_chat_id is not None
                else []
            )
        )
        counts = {entry.hisopo_type: entry.capture_count for entry in collection}
        ownership = {
            entry.hisopo_key: entry.quantity
            for entry in self.db.get_paid_hisopo_ownership(user.user_id)
        }
        membership = self.db.get_club_membership(user.user_id)
        return web.json_response(
            self._bootstrap_payload(
                user=user,
                albums=albums,
                selected_chat_id=selected_chat_id,
                counts=counts,
                aggregate_counts=aggregate_counts,
                ownership=ownership,
                club_periods=membership.periods_paid if membership else 0,
                club_active_until=membership.active_until if membership else None,
                donor_public=self.db.is_donor_display_public(user.user_id),
            )
        )

    async def create_invoice(self, request: web.Request) -> web.Response:
        try:
            user = self.authenticate(request)
            body = await request.json()
            kind = str(body["kind"])
            item_key = str(body["item_key"])
            spec = invoice_spec(kind, item_key)
        except InitDataError as exc:
            raise web.HTTPUnauthorized(text=str(exc)) from exc
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise web.HTTPBadRequest(text="El producto solicitado no es válido.") from exc
        recipient_user_id, recipient_label = self._purchase_recipient(
            user,
            kind=kind,
            value=body.get("recipient"),
        )
        if self.preview_mode and user.user_id == "preview":
            action = f"Regalo para {recipient_label}" if recipient_label else "Compra"
            return web.json_response(
                {
                    "preview": True,
                    "message": f"{action} de {spec.amount_stars} Stars simulada.",
                }
            )
        self.db.get_or_create_user(user.user_id, user.display_name, user.username)
        source_chat_id = self._valid_source_chat_id(user.user_id, body.get("source_chat_id"))
        payload = create_payment_payload(
            self.bot_token,
            kind=kind,
            item_key=item_key,
            user_id=user.user_id,
            recipient_user_id=recipient_user_id,
            source_chat_id=source_chat_id,
        )
        kwargs: dict[str, Any] = {}
        if spec.subscription_period is not None:
            kwargs["subscription_period"] = spec.subscription_period
        description = spec.description
        if recipient_label:
            description = f"Regalo para {recipient_label}. {description}"
        invoice_url = await self.bot.create_invoice_link(
            title=spec.title,
            description=description,
            payload=payload,
            currency=STARS_CURRENCY,
            prices=[LabeledPrice(spec.title, spec.amount_stars)],
            **kwargs,
        )
        return web.json_response(
            {"invoice_url": invoice_url, "recipient_user_id": recipient_user_id}
        )

    async def donor_visibility(self, request: web.Request) -> web.Response:
        try:
            user = self.authenticate(request)
            body = await request.json()
        except InitDataError as exc:
            raise web.HTTPUnauthorized(text=str(exc)) from exc
        except json.JSONDecodeError as exc:
            raise web.HTTPBadRequest(text="El pedido no es válido.") from exc
        if not isinstance(body.get("public"), bool):
            raise web.HTTPBadRequest(text="La visibilidad debe ser pública o anónima.")
        if self.preview_mode and user.user_id == "preview":
            self.preview_public = body["public"]
        else:
            self.db.set_donor_display_public(user.user_id, body["public"])
        return web.json_response({"public": body["public"]})

    def _selected_chat_id(
        self,
        user: MiniAppUser,
        albums: list[Any],
        query_chat_id: str | None,
    ) -> str | None:
        available = {album.chat_id for album in albums}
        if user.start_param:
            try:
                requested = parse_album_context(
                    self.bot_token,
                    user.start_param,
                    expected_user_id=user.user_id,
                )
            except ValueError:
                requested = None
            if requested in available:
                return requested
        if query_chat_id == ALL_GROUPS_CHAT_ID:
            return ALL_GROUPS_CHAT_ID if available else None
        if query_chat_id in available:
            return query_chat_id
        return ALL_GROUPS_CHAT_ID if available else None

    def _valid_source_chat_id(self, user_id: str, value: Any) -> str | None:
        if value is None:
            return None
        chat_id = str(value)
        if chat_id == ALL_GROUPS_CHAT_ID:
            return None
        available = {album.chat_id for album in self.db.list_hisopo_albums_for_user(user_id)}
        if chat_id not in available:
            raise web.HTTPBadRequest(text="Ese álbum no pertenece al usuario.")
        return chat_id

    def _purchase_recipient(
        self,
        user: MiniAppUser,
        *,
        kind: str,
        value: Any,
    ) -> tuple[str, str | None]:
        recipient = "" if value is None else str(value).strip()
        if kind != "product":
            if recipient:
                raise web.HTTPBadRequest(text="Solo se pueden regalar Hisopos de la tienda.")
            return user.user_id, None
        if not recipient:
            return user.user_id, None
        if recipient.isascii() and recipient.isdecimal():
            if int(recipient) <= 0:
                raise web.HTTPBadRequest(text="El user ID de destino no es válido.")
            return recipient, recipient
        alias = recipient.removeprefix("@")
        if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", alias):
            raise web.HTTPBadRequest(text="Ingresá un @alias o user ID válido.")
        if self.preview_mode and user.user_id == "preview":
            return f"preview-{alias.lower()}", f"@{alias}"
        recipient_user = self.db.get_user_by_username(alias)
        if recipient_user is None:
            raise web.HTTPBadRequest(
                text=f"No conozco a @{alias} todavía. Probá con su user ID."
            )
        return recipient_user.user_id, f"@{recipient_user.username or alias}"

    def _bootstrap_payload(
        self,
        *,
        user: MiniAppUser,
        albums: list[Any],
        selected_chat_id: str | None,
        counts: dict[str, int],
        aggregate_counts: dict[str, int],
        ownership: dict[str, int],
        club_periods: int,
        club_active_until: str | None,
        donor_public: bool,
    ) -> dict[str, Any]:
        leaderboard = self.db.get_donor_leaderboard()
        natural = []
        for key in COLLECTIBLE_HISOPO_KEYS:
            translation_key = "hisopos.collection.type.giant" if key == "giant" else f"hisopos.type.{key}"
            natural.append(
                {
                    "key": key,
                    "name": t("es", translation_key).capitalize(),
                    "image": f"/assets/hisopos/{NATURAL_HISOPO_IMAGES[key]}",
                    "quantity": counts.get(key, 0),
                }
            )
        paid = [self._paid_product_payload(product, ownership) for product in PAID_HISOPOS]
        paid.append(self._paid_product_payload(CLUB_HISOPO, ownership, club_only=True))
        album_payload = [
            {
                "chat_id": album.chat_id,
                "title": album.title or f"Grupo {album.chat_id}",
                "discovered": album.discovered_count,
                "captures": album.capture_count,
            }
            for album in albums
        ]
        if albums:
            album_payload.insert(
                0,
                {
                    "chat_id": ALL_GROUPS_CHAT_ID,
                    "title": "Todos los grupos",
                    "discovered": sum(count > 0 for count in aggregate_counts.values()),
                    "captures": sum(album.capture_count for album in albums),
                },
            )
        return {
            "user": {"id": user.user_id, "name": user.display_name},
            "albums": album_payload,
            "selected_chat_id": selected_chat_id,
            "natural_hisopos": natural,
            "paid_hisopos": paid,
            "donation_tiers": list(DONATION_TIERS),
            "club": {
                "price_stars": CLUB_HISOPO.price_stars,
                "periods_paid": club_periods,
                "active_until": club_active_until,
            },
            "donor_public": donor_public,
            "donors": [
                {
                    "name": (
                        entry.display_name
                        or (f"@{entry.username}" if entry.username else f"Usuario {entry.user_id}")
                    )
                    if entry.display_public
                    else "Anónimo",
                    "amount_stars": entry.amount_stars,
                    "public": entry.display_public,
                }
                for entry in leaderboard
            ],
        }

    @staticmethod
    def _paid_product_payload(product: Any, ownership: dict[str, int], *, club_only: bool = False) -> dict[str, Any]:
        return {
            "key": product.key,
            "name": product.name,
            "description": product.description,
            "price_stars": product.price_stars,
            "image": f"/assets/hisopos/{product.image_name}",
            "accent": product.accent,
            "quantity": ownership.get(product.key, 0),
            "club_only": club_only,
        }

    def _preview_bootstrap(
        self,
        user: MiniAppUser,
        requested_chat_id: str | None = None,
    ) -> dict[str, Any]:
        class Album:
            chat_id = "-1004440313456"
            title = "Codex - Logs"
            discovered_count = 11
            capture_count = 37

        class SecondAlbum:
            chat_id = "-1004433295809"
            title = "Bots y Automatizaciones"
            discovered_count = 7
            capture_count = 19

        aggregate_counts = {
            key: count
            for key, count in zip(COLLECTIBLE_HISOPO_KEYS, (12, 7, 4, 1, 3, 2, 0, 1, 2, 3, 1))
        }
        selected_chat_id = (
            requested_chat_id
            if requested_chat_id
            in {ALL_GROUPS_CHAT_ID, Album.chat_id, SecondAlbum.chat_id}
            else ALL_GROUPS_CHAT_ID
        )
        counts = aggregate_counts
        if selected_chat_id == SecondAlbum.chat_id:
            counts = {
                key: count
                for key, count in zip(COLLECTIBLE_HISOPO_KEYS, (5, 1, 0, 0, 1, 0, 0))
            }
        return self._bootstrap_payload(
            user=user,
            albums=[Album(), SecondAlbum()],
            selected_chat_id=selected_chat_id,
            counts=counts,
            aggregate_counts=aggregate_counts,
            ownership={"serene": 1, "crimson": 1},
            club_periods=2,
            club_active_until="2026-09-26T12:00:00+00:00",
            donor_public=self.preview_public,
        )


MINI_APP_API_KEY = web.AppKey("mini_app_api", MiniAppApi)


@web.middleware
async def security_headers(request: web.Request, handler: Any) -> web.StreamResponse:
    response = await handler(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' https://telegram.org; connect-src 'self'"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def build_mini_app(
    *,
    db: Database,
    bot_token: str,
    bot: Any | None,
    public_url: str,
    preview_mode: bool = False,
) -> web.Application:
    api = MiniAppApi(
        db=db,
        bot_token=bot_token,
        bot=bot,
        public_url=public_url,
        preview_mode=preview_mode,
    )
    app = web.Application(middlewares=[security_headers], client_max_size=64 * 1024)
    app[MINI_APP_API_KEY] = api
    app.router.add_get("/", api.index)
    app.router.add_get("/api/bootstrap", api.bootstrap)
    app.router.add_post("/api/invoice", api.create_invoice)
    app.router.add_post("/api/donor-visibility", api.donor_visibility)
    app.router.add_static("/static", MINI_APP_ROOT, show_index=False)
    app.router.add_static("/assets/hisopos", HISOPO_ASSET_ROOT, show_index=False)
    return app


@dataclass
class MiniAppService:
    runner: web.AppRunner
    site: web.TCPSite

    async def stop(self) -> None:
        await self.runner.cleanup()


async def start_mini_app(
    *,
    db: Database,
    bot_token: str,
    bot: Any,
    public_url: str,
    host: str,
    port: int,
) -> MiniAppService:
    app = build_mini_app(
        db=db,
        bot_token=bot_token,
        bot=bot,
        public_url=public_url,
    )
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    return MiniAppService(runner, site)
