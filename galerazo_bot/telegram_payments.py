from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, WebAppInfo
from telegram.error import TelegramError

from .database import Database
from .i18n import t
from .commerce_i18n import commerce_text, localized_invoice_spec, payment_language, cosmetic_name, commerce_language
from .monetization import (
    CLUB_HISOPO,
    DONATION_TIERS,
    STARS_CURRENCY,
    InvoiceSpec,
    PaymentIntent,
    PaymentPayloadError,
    create_payment_payload,
    invoice_spec,
    PAID_HISOPO_BY_KEY,
    parse_payment_payload,
)


logger = logging.getLogger(__name__)
CAFE_URL = "https://cafecito.app/galerazobot"
PaymentLogCallback = Callable[[str], Awaitable[bool]]


async def create_invoice_url(
    bot: Any,
    bot_token: str,
    *,
    kind: str,
    item_key: str,
    user_id: str,
    source_chat_id: str | None,
    recipient_user_id: str | None = None,
    language: str = "es",
) -> str:
    spec = localized_invoice_spec(kind, item_key, language)
    payload = create_payment_payload(
        bot_token,
        kind=kind,
        item_key=item_key,
        user_id=user_id,
        recipient_user_id=recipient_user_id,
        source_chat_id=source_chat_id,
    )
    kwargs: dict[str, Any] = {}
    if spec.subscription_period is not None:
        kwargs["subscription_period"] = spec.subscription_period
    return await bot.create_invoice_link(
        title=spec.title,
        description=spec.description,
        payload=payload,
        currency=STARS_CURRENCY,
        prices=[LabeledPrice(spec.title, spec.amount_stars)],
        **kwargs,
    )


async def send_donation_menu(
    *,
    bot: Any,
    bot_token: str,
    message: Message,
    user_id: str,
    language: str,
    mini_app_url: str | None,
    db: Database | None = None,
) -> bool:
    try:
        donation_urls = [
            await create_invoice_url(
                bot,
                bot_token,
                kind="donation",
                item_key=str(amount),
                user_id=user_id,
                source_chat_id=str(message.chat.id),
                language=language,
            )
            for amount in DONATION_TIERS
        ]
        club_url = await create_invoice_url(
            bot,
            bot_token,
            kind="subscription",
            item_key="club",
            user_id=user_id,
            source_chat_id=str(message.chat.id),
            language=language,
        )
        rows = [
            [
                InlineKeyboardButton(f"⭐ {amount}", url=url)
                for amount, url in zip(DONATION_TIERS, donation_urls)
            ],
            [InlineKeyboardButton(f"✦ Club del Hisopo · ⭐ {CLUB_HISOPO.price_stars}", url=club_url)],
        ]
        if mini_app_url and message.chat.type == "private":
            rows.append(
                [
                    InlineKeyboardButton(
                        t(language, "donation.open_mini_app"),
                        web_app=WebAppInfo(mini_app_url),
                    )
                ]
            )
        rows.append([InlineKeyboardButton("Cafecito", url=CAFE_URL)])
        await message.reply_text(
            t(language, "donation.menu"),
            reply_markup=InlineKeyboardMarkup(rows),
            do_quote=True,
        )
        if db is not None:
            db.set_payment_language(user_id, commerce_language(language))
        return True
    except TelegramError as exc:
        logger.warning("No pude crear el menú de aportes con Stars: %s", exc)
        return False


async def answer_pre_checkout_query(
    *,
    query: Any,
    db: Database,
    bot_token: str,
) -> None:
    language = payment_language(db, str(query.from_user.id), str(query.from_user.id))
    try:
        intent = parse_payment_payload(
            bot_token,
            query.invoice_payload,
            expected_user_id=str(query.from_user.id),
        )
        spec = invoice_spec(intent.kind, intent.item_key)
        if query.currency != STARS_CURRENCY or query.total_amount != spec.amount_stars:
            raise PaymentPayloadError("El importe del pago no coincide con el producto.")
    except PaymentPayloadError as exc:
        await query.answer(ok=False, error_message=(str(exc) if language in {"es", "es_ES"} else commerce_text(language, "invalid"))[:200])
        return
    await query.answer(ok=True)


async def process_successful_payment(
    *,
    message: Message,
    db: Database,
    bot_token: str,
    log_payment: PaymentLogCallback | None = None,
) -> bool:
    payment = message.successful_payment
    user = message.from_user
    if payment is None or user is None:
        return False
    language = payment_language(db, str(user.id), str(message.chat.id))
    try:
        intent = parse_payment_payload(
            bot_token,
            payment.invoice_payload,
            expected_user_id=str(user.id),
        )
        spec = invoice_spec(intent.kind, intent.item_key)
        if payment.currency != STARS_CURRENCY or payment.total_amount != spec.amount_stars:
            raise PaymentPayloadError("El pago confirmado no coincide con el producto.")
    except PaymentPayloadError as exc:
        logger.error("Pago de Stars confirmado con payload inválido: %s", exc)
        await message.reply_text(commerce_text(language, "uncredited"))
        return False
    paid_at = _message_datetime(message).isoformat()
    expiration = payment.subscription_expiration_date
    expiration_text = expiration.isoformat() if expiration is not None else None
    recorded = db.record_star_payment(
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id or None,
        user_id=intent.user_id,
        kind=intent.kind,
        item_key=intent.item_key,
        amount_stars=payment.total_amount,
        currency=payment.currency,
        invoice_payload=payment.invoice_payload,
        source_chat_id=intent.source_chat_id,
        reward_hisopo_key=spec.reward_hisopo_key,
        paid_at=paid_at,
        is_recurring=bool(payment.is_recurring),
        is_first_recurring=bool(payment.is_first_recurring),
        subscription_expiration_date=expiration_text,
        recipient_user_id=intent.recipient_user_id,
    )
    if not recorded:
        return False
    if log_payment is not None:
        try:
            await log_payment(
                _successful_payment_log_text(
                    message=message,
                    db=db,
                    intent=intent,
                    spec=spec,
                    payment=payment,
                )
            )
        except Exception:
            logger.exception(
                "No pude registrar en el canal de logging el pago de Stars %s.",
                payment.telegram_payment_charge_id,
            )
    if intent.kind == "donation":
        response = commerce_text(language, "donation", amount=payment.total_amount)
    elif intent.kind == "subscription":
        response = commerce_text(language, "subscription")
    elif intent.recipient_user_id != intent.user_id:
        response = commerce_text(language, "gift", title=cosmetic_name(PAID_HISOPO_BY_KEY[intent.item_key], language), recipient=intent.recipient_user_id)
    else:
        response = commerce_text(language, "product", title=cosmetic_name(PAID_HISOPO_BY_KEY[intent.item_key], language))
    await message.reply_text(response)
    return True


async def process_refunded_payment(*, message: Message, db: Database) -> bool:
    payment = message.refunded_payment
    if payment is None:
        return False
    refunded = db.refund_star_payment(
        payment.telegram_payment_charge_id,
        refunded_at=_message_datetime(message).isoformat(),
    )
    if refunded:
        language = payment_language(db, str(getattr(message.from_user, "id", message.chat.id)), str(message.chat.id))
        await message.reply_text(
            commerce_text(language, "refund")
        )
    return refunded


def _message_datetime(message: Message) -> datetime:
    value = message.date or datetime.now(timezone.utc)
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _successful_payment_log_text(
    *,
    message: Message,
    db: Database,
    intent: PaymentIntent,
    spec: InvoiceSpec,
    payment: Any,
) -> str:
    is_gift = intent.kind == "product" and intent.recipient_user_id != intent.user_id
    if intent.kind == "donation":
        operation = "Donación"
    elif intent.kind == "subscription":
        if payment.is_first_recurring:
            operation = "Club del Hisopo · primera cuota"
        elif payment.is_recurring:
            operation = "Club del Hisopo · renovación"
        else:
            operation = "Club del Hisopo · cuota"
    elif is_gift:
        operation = "Regalo"
    else:
        operation = "Compra"

    lines = [
        "⭐ Pago confirmado por Telegram",
        f"Operación: {operation}",
        f"Comprador: {_telegram_user_label(message.from_user, intent.user_id)}",
        f"Importe: ⭐ {payment.total_amount}",
    ]
    if intent.kind != "donation":
        lines.append(f"Concepto: {spec.title}")
    if is_gift:
        lines.append(
            f"Destinatario: {_stored_user_label(db, intent.recipient_user_id)}"
        )
    if intent.source_chat_id is not None:
        lines.append(f"Origen: chat {intent.source_chat_id}")
    lines.append(f"Cobro Telegram: {payment.telegram_payment_charge_id}")
    return "\n".join(lines)


def _telegram_user_label(user: Any, fallback_user_id: str) -> str:
    user_id = str(getattr(user, "id", None) or fallback_user_id)
    display_name = getattr(user, "full_name", None)
    username = getattr(user, "username", None)
    return _account_label(user_id, display_name, username)


def _stored_user_label(db: Database, user_id: str) -> str:
    user = db.get_user(user_id)
    if user is None:
        return f"ID {user_id}"
    return _account_label(user_id, user.display_name, user.username)


def _account_label(
    user_id: str,
    display_name: object,
    username: object,
) -> str:
    name = display_name.strip() if isinstance(display_name, str) else ""
    alias = username.removeprefix("@").strip() if isinstance(username, str) else ""
    if name and alias:
        return f"{name} (@{alias}) · ID {user_id}"
    if name:
        return f"{name} · ID {user_id}"
    if alias:
        return f"@{alias} · ID {user_id}"
    return f"ID {user_id}"
