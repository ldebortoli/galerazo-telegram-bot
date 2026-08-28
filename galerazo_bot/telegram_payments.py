from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, WebAppInfo
from telegram.error import TelegramError

from .database import Database
from .i18n import t
from .monetization import (
    CLUB_HISOPO,
    DONATION_TIERS,
    STARS_CURRENCY,
    PaymentPayloadError,
    create_payment_payload,
    invoice_spec,
    parse_payment_payload,
)


logger = logging.getLogger(__name__)
CAFE_URL = "https://cafecito.app/galerazobot"


async def create_invoice_url(
    bot: Any,
    bot_token: str,
    *,
    kind: str,
    item_key: str,
    user_id: str,
    source_chat_id: str | None,
    recipient_user_id: str | None = None,
) -> str:
    spec = invoice_spec(kind, item_key)
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
        await query.answer(ok=False, error_message=str(exc)[:200])
        return
    await query.answer(ok=True)


async def process_successful_payment(
    *,
    message: Message,
    db: Database,
    bot_token: str,
) -> bool:
    payment = message.successful_payment
    user = message.from_user
    if payment is None or user is None:
        return False
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
        await message.reply_text("Recibí el pago, pero no pude acreditarlo. Usá /paysupport.")
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
    if intent.kind == "donation":
        response = f"¡Gracias por aportar ⭐ {payment.total_amount}! Tu apoyo no compra puntos ni ventajas."
    elif intent.kind == "subscription":
        response = "¡Gracias por sumarte al Club del Hisopo! Tu membresía de apoyo quedó activa."
    elif intent.recipient_user_id != intent.user_id:
        response = f"¡Regalo confirmado! {spec.title} fue acreditado al usuario {intent.recipient_user_id}."
    else:
        response = f"¡Compra confirmada! {spec.title} sumó una unidad a tu colección."
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
        await message.reply_text(
            "El reembolso de Stars quedó registrado y el beneficio asociado fue retirado."
        )
    return refunded


def _message_datetime(message: Message) -> datetime:
    value = message.date or datetime.now(timezone.utc)
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
