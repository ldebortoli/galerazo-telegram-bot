from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from telegram.error import TimedOut

from galerazo_bot.monetization import create_payment_payload, parse_payment_payload
from galerazo_bot.telegram_payments import (
    _message_datetime,
    answer_pre_checkout_query,
    create_invoice_url,
    process_refunded_payment,
    process_successful_payment,
    send_donation_menu,
)


def payment_message(payment=None, *, user_id=1, date=None):
    return SimpleNamespace(
        successful_payment=payment,
        refunded_payment=payment,
        from_user=SimpleNamespace(id=user_id) if user_id is not None else None,
        date=date,
        chat=SimpleNamespace(id=-1001, type="private"),
        reply_text=AsyncMock(),
    )


def successful_payment(
    payload: str,
    *,
    amount: int,
    charge_id: str = "charge",
    currency: str = "XTR",
    expiration=None,
    recurring=False,
    first=False,
):
    return SimpleNamespace(
        invoice_payload=payload,
        currency=currency,
        total_amount=amount,
        telegram_payment_charge_id=charge_id,
        provider_payment_charge_id="provider",
        subscription_expiration_date=expiration,
        is_recurring=recurring,
        is_first_recurring=first,
    )


class TelegramPaymentTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_invoice_links_for_product_donation_and_subscription(self) -> None:
        bot = SimpleNamespace(create_invoice_link=AsyncMock(return_value="https://t.me/invoice"))
        result = await create_invoice_url(
            bot,
            "token",
            kind="product",
            item_key="massive",
            user_id="1",
            source_chat_id="-1",
            recipient_user_id="2",
        )
        self.assertEqual(result, "https://t.me/invoice")
        call = bot.create_invoice_link.await_args.kwargs
        self.assertEqual((call["currency"], call["prices"][0].amount), ("XTR", 150))
        self.assertNotIn("provider_token", call)
        self.assertNotIn("subscription_period", call)
        self.assertEqual(
            parse_payment_payload("token", call["payload"]).recipient_user_id,
            "2",
        )

        await create_invoice_url(
            bot,
            "token",
            kind="subscription",
            item_key="club",
            user_id="1",
            source_chat_id=None,
        )
        self.assertEqual(bot.create_invoice_link.await_args.kwargs["subscription_period"].days, 30)

    async def test_donation_menu_private_group_and_failure(self) -> None:
        bot = SimpleNamespace(create_invoice_link=AsyncMock(side_effect=lambda **kwargs: f"https://pay/{kwargs['prices'][0].amount}"))
        private = payment_message()
        self.assertTrue(
            await send_donation_menu(
                bot=bot,
                bot_token="token",
                message=private,
                user_id="1",
                language="es",
                mini_app_url="https://example.test",
            )
        )
        markup = private.reply_text.await_args.kwargs["reply_markup"]
        self.assertEqual(len(markup.inline_keyboard), 4)
        self.assertEqual(markup.inline_keyboard[2][0].web_app.url, "https://example.test")

        group = payment_message()
        group.chat.type = "group"
        self.assertTrue(
            await send_donation_menu(
                bot=bot,
                bot_token="token",
                message=group,
                user_id="1",
                language="es",
                mini_app_url="https://example.test",
            )
        )
        self.assertEqual(len(group.reply_text.await_args.kwargs["reply_markup"].inline_keyboard), 3)

        bot.create_invoice_link.side_effect = TimedOut()
        self.assertFalse(
            await send_donation_menu(
                bot=bot,
                bot_token="token",
                message=group,
                user_id="1",
                language="es",
                mini_app_url=None,
            )
        )

    async def test_precheckout_accepts_valid_and_rejects_invalid_payments(self) -> None:
        db = MagicMock()
        query = SimpleNamespace(
            invoice_payload=create_payment_payload(
                "token", kind="product", item_key="massive", user_id="1"
            ),
            from_user=SimpleNamespace(id=1),
            currency="XTR",
            total_amount=150,
            answer=AsyncMock(),
        )
        await answer_pre_checkout_query(query=query, db=db, bot_token="token")
        query.answer.assert_awaited_once_with(ok=True)

        for mutate, expected in (
            ({"invoice_payload": "bad"}, "identificador"),
            ({"currency": "USD"}, "importe"),
            ({"total_amount": 149}, "importe"),
        ):
            with self.subTest(mutate=mutate):
                current = SimpleNamespace(**{**query.__dict__, **mutate, "answer": AsyncMock()})
                await answer_pre_checkout_query(query=current, db=db, bot_token="token")
                self.assertFalse(current.answer.await_args.kwargs["ok"])
                self.assertIn(expected, current.answer.await_args.kwargs["error_message"])

        # Tenerlo previamente no bloquea una compra adicional.
        query.answer.reset_mock()
        await answer_pre_checkout_query(query=query, db=db, bot_token="token")
        query.answer.assert_awaited_once_with(ok=True)

    async def test_successful_payments_are_recorded_and_acknowledged(self) -> None:
        db = MagicMock()
        db.record_star_payment.return_value = True
        cases = (
            ("donation", "25", 25, "Gracias", None),
            ("product", "massive", 150, "Compra confirmada", None),
            (
                "subscription",
                "club",
                100,
                "Club del Hisopo",
                datetime(2026, 9, 26, tzinfo=timezone.utc),
            ),
        )
        for index, (kind, item_key, amount, expected, expiration) in enumerate(cases):
            with self.subTest(kind=kind):
                payload = create_payment_payload(
                    "token",
                    kind=kind,
                    item_key=item_key,
                    user_id="1",
                    source_chat_id="-1",
                )
                payment = successful_payment(
                    payload,
                    amount=amount,
                    charge_id=f"charge-{index}",
                    expiration=expiration,
                    recurring=kind == "subscription",
                    first=kind == "subscription",
                )
                message = payment_message(
                    payment,
                    date=datetime(2026, 8, 27, tzinfo=timezone.utc),
                )
                self.assertTrue(
                    await process_successful_payment(message=message, db=db, bot_token="token")
                )
                self.assertIn(expected, message.reply_text.await_args.args[0])
                kwargs = db.record_star_payment.call_args.kwargs
                self.assertEqual(kwargs["source_chat_id"], "-1")
                self.assertEqual(kwargs["recipient_user_id"], "1")
                self.assertEqual(kwargs["subscription_expiration_date"], expiration.isoformat() if expiration else None)

        gift_payload = create_payment_payload(
            "token",
            kind="product",
            item_key="massive",
            user_id="1",
            recipient_user_id="2",
        )
        gift_message = payment_message(successful_payment(gift_payload, amount=150))
        self.assertTrue(
            await process_successful_payment(
                message=gift_message, db=db, bot_token="token"
            )
        )
        self.assertEqual(db.record_star_payment.call_args.kwargs["recipient_user_id"], "2")
        self.assertIn("Regalo confirmado", gift_message.reply_text.await_args.args[0])

        db.record_star_payment.return_value = False
        duplicate_payload = create_payment_payload(
            "token", kind="donation", item_key="25", user_id="1"
        )
        duplicate = payment_message(successful_payment(duplicate_payload, amount=25))
        self.assertFalse(
            await process_successful_payment(message=duplicate, db=db, bot_token="token")
        )
        duplicate.reply_text.assert_not_awaited()

    async def test_successful_payment_rejects_missing_or_invalid_confirmation(self) -> None:
        db = MagicMock()
        self.assertFalse(
            await process_successful_payment(
                message=payment_message(None), db=db, bot_token="token"
            )
        )
        missing_user = payment_message(SimpleNamespace(), user_id=None)
        self.assertFalse(
            await process_successful_payment(message=missing_user, db=db, bot_token="token")
        )

        invalid = payment_message(successful_payment("bad", amount=25))
        self.assertFalse(
            await process_successful_payment(message=invalid, db=db, bot_token="token")
        )
        self.assertIn("/paysupport", invalid.reply_text.await_args.args[0])

        wrong_amount_payload = create_payment_payload(
            "token", kind="donation", item_key="25", user_id="1"
        )
        wrong = payment_message(successful_payment(wrong_amount_payload, amount=24))
        self.assertFalse(
            await process_successful_payment(message=wrong, db=db, bot_token="token")
        )

    async def test_refunds_and_message_dates(self) -> None:
        db = MagicMock()
        missing = payment_message(None)
        self.assertFalse(await process_refunded_payment(message=missing, db=db))

        payment = SimpleNamespace(telegram_payment_charge_id="charge")
        message = payment_message(payment, date=datetime(2026, 8, 27, 10, 0))
        db.refund_star_payment.return_value = False
        self.assertFalse(await process_refunded_payment(message=message, db=db))
        message.reply_text.assert_not_awaited()

        db.refund_star_payment.return_value = True
        self.assertTrue(await process_refunded_payment(message=message, db=db))
        message.reply_text.assert_awaited_once()
        self.assertEqual(_message_datetime(message).tzinfo, timezone.utc)
        self.assertEqual(_message_datetime(payment_message()).tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main()
