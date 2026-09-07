from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, quote, urlsplit

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


logger = logging.getLogger(__name__)


class MiniAppTransportLogFilter(logging.Filter):
    """aiohttp parser errors happen before middleware and may contain raw headers."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = "Mini App HTTP transport event."
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


transport_logger = logging.getLogger(f"{__name__}.transport")
transport_logger.addFilter(MiniAppTransportLogFilter())

PRODUCTION_MINI_APP_URL = "https://galerazo.com/miniapp"
PROXY_SECRET_HEADER = "X-Galerazo-Proxy-Secret"
MAX_INIT_DATA_BYTES = 8192
MAX_INIT_DATA_AGE_SECONDS = 60 * 60
ALL_GROUPS_CHAT_ID = "all"


def valid_proxy_secret(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[A-Za-z0-9_-]{32,256}", value))


def validate_mini_app_runtime(
    *, public_url: str, proxy_secret: str | None, host: str, bot_username: str
) -> None:
    url = urlsplit(public_url)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment):
        raise ValueError("TELEGRAM_MINI_APP_URL debe ser una URL HTTPS sin credenciales.")
    if not valid_proxy_secret(proxy_secret):
        raise ValueError("MINI_APP_PROXY_SECRET requiere 32 a 256 caracteres URL-safe.")
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("MINI_APP_BIND_HOST debe ser loopback para el proxy privado.")
    if url.hostname in {"galerazo.com", "www.galerazo.com"} and (
        public_url != PRODUCTION_MINI_APP_URL or bot_username != "galerazo_bot"
    ):
        raise ValueError("La Mini App publica requiere @galerazo_bot y su URL canonica.")


NATURAL_HISOPO_IMAGES = {
    "common": "hisopo-comun.png",
    "silver": "hisopo-plateado.png",
    "gold": "hisopo-dorado.png",
    "diamond": "hisopo-diamante.png",
    "fleeting": "hisopo-fugaz.png",
    "mystery": "hisopo-misterioso.png",
    "putrid": "hisopo-putrefacto.png",
    "used": "hisopo-usado.png",
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
    if len(init_data.encode("utf-8")) > MAX_INIT_DATA_BYTES:
        raise InitDataError("Los datos de Telegram exceden el limite permitido.")
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True, max_num_fields=32)
    except ValueError as exc:
        raise InitDataError("Los datos de Telegram no son validos.") from exc
    values = dict(pairs)
    if len(pairs) != len(values):
        raise InitDataError("Los datos de Telegram contienen campos duplicados.")
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
    if not re.fullmatch(r"[0-9a-f]{64}", received_hash) or not hmac.compare_digest(received_hash, calculated_hash):
        raise InitDataError("La firma de Telegram no es válida.")
    try:
        auth_date = int(values["auth_date"])
        user_data = json.loads(values["user"])
        raw_user_id = user_data["id"]
        if type(raw_user_id) is not int or not 0 < raw_user_id < 2**63:
            raise ValueError("Invalid user ID")
        user_id = str(raw_user_id)
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
        proxy_secret: str | None = None,
    ) -> None:
        self.db = db
        self.bot_token = bot_token
        self.bot = bot
        self.public_url = public_url.rstrip("/")
        self.proxy_secret = proxy_secret

    def authenticate(self, request: web.Request) -> MiniAppUser:
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        return validate_init_data(init_data, self.bot_token)

    async def bootstrap(self, request: web.Request) -> web.Response:
        try:
            user = self.authenticate(request)
        except InitDataError as exc:
            raise web.HTTPUnauthorized(text=str(exc)) from exc
        if any(key != "chat_id" for key in request.query) or len(request.query) > 1:
            raise web.HTTPBadRequest(text="El pedido no es valido.")
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
            if not isinstance(body, dict):
                raise ValueError("Invalid request")
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
        if not isinstance(body, dict) or not isinstance(body.get("public"), bool):
            raise web.HTTPBadRequest(text="La visibilidad debe ser pública o anónima.")
        self.db.get_or_create_user(user.user_id, user.display_name, user.username)
        self.db.set_donor_display_public(user.user_id, body["public"])
        return web.json_response({"public": body["public"]})

    def _selected_chat_id(
        self,
        user: MiniAppUser,
        albums: list[Any],
        query_chat_id: str | None,
    ) -> str | None:
        available = {album.chat_id for album in albums}
        requested = None
        if user.start_param:
            try:
                requested = parse_album_context(
                    self.bot_token,
                    user.start_param,
                    expected_user_id=user.user_id,
                )
            except ValueError as exc:
                raise web.HTTPForbidden(text="El enlace del album no es valido para este usuario.") from exc
            if requested not in available:
                raise web.HTTPForbidden(text="Ese album no pertenece al usuario.")
        if query_chat_id == ALL_GROUPS_CHAT_ID:
            return ALL_GROUPS_CHAT_ID if available else None
        if query_chat_id is not None:
            if query_chat_id not in available:
                raise web.HTTPForbidden(text="Ese album no pertenece al usuario.")
            return query_chat_id
        if requested in available:
            return requested
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



MINI_APP_API_KEY = web.AppKey("mini_app_api", MiniAppApi)


@web.middleware
async def security_headers(request: web.Request, handler: Any) -> web.StreamResponse:
    try:
        response = await handler(request)
    except web.HTTPException as exc:
        response = web.json_response({"error": f"http_{exc.status}"}, status=exc.status)
    except Exception as exc:
        # Do not log exception details: HTTP clients may include headers or initData.
        logger.warning("Mini App API fallo (%s).", type(exc).__name__)
        response = web.json_response({"error": "temporarily_unavailable"}, status=502)
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@web.middleware
async def authenticate_proxy(request: web.Request, handler: Any) -> web.StreamResponse:
    if request.path.startswith("/api/"):
        secret = request.app[MINI_APP_API_KEY].proxy_secret
        if not valid_proxy_secret(secret):
            raise web.HTTPServiceUnavailable()
        supplied = request.headers.get(PROXY_SECRET_HEADER, "")
        if not hmac.compare_digest(supplied.encode("utf-8", errors="replace"), secret.encode("ascii")):
            raise web.HTTPForbidden()
    return await handler(request)


def build_mini_app(
    *,
    db: Database,
    bot_token: str,
    bot: Any | None,
    public_url: str,
    proxy_secret: str | None = None,
) -> web.Application:
    api = MiniAppApi(
        db=db,
        bot_token=bot_token,
        bot=bot,
        public_url=public_url,
        proxy_secret=proxy_secret,
    )
    app = web.Application(middlewares=[security_headers, authenticate_proxy], client_max_size=16 * 1024)
    app[MINI_APP_API_KEY] = api
    app.router.add_get("/api/bootstrap", api.bootstrap, allow_head=False)
    app.router.add_post("/api/invoice", api.create_invoice)
    app.router.add_post("/api/donor-visibility", api.donor_visibility)
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
    proxy_secret: str,
    host: str,
    port: int,
) -> MiniAppService:
    app = build_mini_app(
        db=db,
        bot_token=bot_token,
        bot=bot,
        public_url=public_url,
        proxy_secret=proxy_secret,
    )
    runner = web.AppRunner(app, access_log=None, logger=transport_logger)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    return MiniAppService(runner, site)
