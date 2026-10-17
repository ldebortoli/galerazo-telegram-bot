import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from galerazo_bot.database import Database
from galerazo_bot.monetization import invoice_spec, parse_payment_payload
from galerazo_bot.mini_app import MiniAppApi
from tests.test_mini_app import request_stub, signed_init_data


class CommerceLanguageTests(unittest.IsolatedAsyncioTestCase):
    async def test_invoice_language_is_validated_persisted_and_cannot_change_identity_or_price(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Database(Path(directory)/'db.sqlite3')
            bot=SimpleNamespace(create_invoice_link=AsyncMock(return_value='https://t.me/invoice'))
            api=MiniAppApi(db=db,bot_token='token',bot=bot,public_url='https://example.test/miniapp')
            self.assertEqual(db.get_payment_language('1','en'),'en')
            body={'kind':'product','item_key':'mini','language':'ar'}
            response=await api.create_invoice(request_stub(headers={'X-Telegram-Init-Data':signed_init_data()},body=body))
            self.assertEqual(response.status,200)
            self.assertEqual(db.get_payment_language('1','es'),'ar')
            spec=bot.create_invoice_link.await_args.kwargs
            self.assertNotEqual(spec['title'],invoice_spec('product','mini').title)
            self.assertEqual(spec['prices'][0].amount,invoice_spec('product','mini').amount_stars)
            self.assertEqual(parse_payment_payload('token',spec['payload']).user_id,'1')
            reopened=Database(Path(directory)/'db.sqlite3')
            self.assertEqual(reopened.get_payment_language('1','es'),'ar')
            from aiohttp import web
            for language in ('invented',{},'__proto__'):
                with self.assertRaises(web.HTTPBadRequest):
                    await api.create_invoice(request_stub(headers={'X-Telegram-Init-Data':signed_init_data()},body={**body,'language':language}))
            self.assertEqual(db.get_payment_language('1','es'),'ar')

    def test_all_new_locales_have_complete_commerce_and_cosmetic_text(self):
        from galerazo_bot.commerce_i18n import COMMERCE, localized_invoice_spec, commerce_text
        from galerazo_bot.language_catalogs import CATALOGS
        from galerazo_bot.monetization import PAID_HISOPOS
        for option in CATALOGS['options']:
            if not option['machine']:
                continue
            language=option['code']
            self.assertIn(language,COMMERCE)
            for product in PAID_HISOPOS:
                spec=localized_invoice_spec('product',product.key,language)
                self.assertEqual(spec.amount_stars,product.price_stars)
                self.assertLessEqual(len(spec.title),32)
                self.assertLessEqual(len(spec.description),255)
            for kind,key in (('donation','25'),('subscription','club')):
                spec=localized_invoice_spec(kind,key,language)
                self.assertEqual(spec.amount_stars,invoice_spec(kind,key).amount_stars)
                self.assertLessEqual(len(spec.description),255)
            self.assertIn('12',commerce_text(language,'donation',amount=12))

    async def test_bot_menu_updates_the_last_invoice_preference_and_receipts_keep_full_item_names(self):
        from galerazo_bot.telegram_payments import send_donation_menu, process_successful_payment
        from galerazo_bot.commerce_i18n import COMMERCE, cosmetic_name, localized_invoice_spec, commerce_text
        from galerazo_bot.monetization import PAID_HISOPO_BY_KEY, create_payment_payload
        from tests.test_telegram_payments import payment_message, successful_payment
        with tempfile.TemporaryDirectory() as directory:
            db=Database(Path(directory)/'db.sqlite3')
            db.set_payment_language('1','ar')
            bot=SimpleNamespace(create_invoice_link=AsyncMock(return_value='https://t.me/$fixture'))
            message=payment_message()
            self.assertTrue(await send_donation_menu(bot=bot,bot_token='token',message=message,user_id='1',language='en',mini_app_url=None,db=db))
            self.assertEqual(db.get_payment_language('1','es'),'en')
            language='ach'
            product=PAID_HISOPO_BY_KEY['invisible']
            self.assertEqual(localized_invoice_spec('product',product.key,language).title,'Galerazo Bot')
            db.set_payment_language('1',language)
            db.get_or_create_user('1','Ada','ada')
            payload=create_payment_payload('token',kind='product',item_key=product.key,user_id='1')
            payment=successful_payment(payload,amount=product.price_stars)
            message=payment_message(payment)
            self.assertTrue(await process_successful_payment(message=message,db=db,bot_token='token'))
            self.assertIn(cosmetic_name(product,language),message.reply_text.await_args.args[0])

    async def test_precheckout_errors_and_refunds_use_the_saved_language(self):
        from galerazo_bot.telegram_payments import answer_pre_checkout_query, process_refunded_payment
        from galerazo_bot.commerce_i18n import commerce_text
        from tests.test_telegram_payments import payment_message
        from unittest.mock import MagicMock
        db=MagicMock()
        db.get_payment_language.return_value='ar'
        query=SimpleNamespace(from_user=SimpleNamespace(id=1),invoice_payload='invalid',answer=AsyncMock())
        await answer_pre_checkout_query(query=query,db=db,bot_token='token')
        query.answer.assert_awaited_once_with(ok=False,error_message=commerce_text('ar','invalid'))
        db.refund_star_payment.return_value=True
        message=payment_message(SimpleNamespace(telegram_payment_charge_id='fixture'))
        self.assertTrue(await process_refunded_payment(message=message,db=db))
        message.reply_text.assert_awaited_once_with(commerce_text('ar','refund'))
        senderless=payment_message(SimpleNamespace(telegram_payment_charge_id='fixture'),user_id=None)
        self.assertTrue(await process_refunded_payment(message=senderless,db=db))
        senderless.reply_text.assert_awaited_once_with(commerce_text('ar','refund'))
