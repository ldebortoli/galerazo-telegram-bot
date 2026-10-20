from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.error import TimedOut

from galerazo_bot import chat_config, telegram_bot
from galerazo_bot.command_handlers import donar, help as help_command, nivel, regalar_hisopo
from galerazo_bot.commands import iter_commands
from galerazo_bot.database import Database
from galerazo_bot.commerce_i18n import (
    COMMERCE,
    commerce_language,
    commerce_text,
    cosmetic_name,
    localized_invoice_spec,
)
from galerazo_bot.i18n import TRANSLATIONS, t
from galerazo_bot.language_catalogs import LANGUAGE_OPTIONS
from galerazo_bot.mini_app import MiniAppApi
from galerazo_bot.monetization import CLUB_HISOPO, PAID_HISOPOS, create_shared_album_context
from galerazo_bot.roles import CommandContext, UserLevel
from tests.test_mini_app import request_stub, signed_init_data


# These complete sentences were copied from English into older catalogs. Short
# shared labels, brands, commands and cognates are deliberately not classified.
AUDITED_MONETIZATION_PROSE = (
    "help.donantes",
    "help.paysupport",
    "help.terminos",
    "donation.not_configured",
    "donation.send_failed",
    "donation.menu",
    "donors.public",
    "donors.anonymous",
    "donors.empty",
    "donors.header",
    "donors.privacy_hint",
    "payments.support",
    "payments.terms",
)


def command_context(
    language: str,
    *,
    args: str = "",
    level: UserLevel = UserLevel.DEV,
    chat_type: str = "private",
) -> CommandContext:
    return CommandContext(
        sender_id="1",
        chat_id="1" if chat_type == "private" else "-1",
        chat_type=chat_type,
        user_level=level,
        raw_text="",
        args=args,
        language=language,
    )


class TranslationCompletenessTests(unittest.TestCase):
    def test_enabled_catalogs_do_not_reuse_audited_english_or_spanish_prose(self):
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            if language in {"es", "es_ES", "en"}:
                continue
            for key in AUDITED_MONETIZATION_PROSE:
                with self.subTest(language=language, key=key):
                    self.assertNotIn(
                        TRANSLATIONS[language][key],
                        (TRANSLATIONS["en"][key], TRANSLATIONS["es"][key]),
                    )

    def test_older_non_english_catalogs_localize_the_three_audited_button_labels(self):
        keys = (
            "donation.open_mini_app",
            "hisopos.collection.open_app",
            "donors.hidden_name",
        )
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            if option["machine"] or language in {"es", "es_ES", "en"}:
                continue
            for key in keys:
                with self.subTest(language=language, key=key):
                    self.assertNotEqual(TRANSLATIONS[language][key], TRANSLATIONS["en"][key])

    def test_audited_spanish_sentences_do_not_reappear_in_other_languages(self):
        copied = {
            "eu": ("chats.active", "triggers.not_found"),
            "ca": ("help.reportar",),
            "la": ("announcement.sent", "backup.too_large", "salir.group_only"),
        }
        for language, keys in copied.items():
            for key in keys:
                with self.subTest(language=language, key=key):
                    self.assertNotEqual(TRANSLATIONS[language][key], TRANSLATIONS["es"][key])

    def test_machine_catalogs_do_not_keep_the_english_swab_placeholder(self):
        for option in LANGUAGE_OPTIONS:
            if not option["machine"]:
                continue
            language = option["code"]
            untranslated = [
                key
                for key, text in TRANSLATIONS[language].items()
                if re.search(r"(?i)\bswabs?\b", text)
            ]
            with self.subTest(language=language):
                self.assertEqual(untranslated, [])

    def test_every_language_has_a_localized_telegram_mini_app_menu_label(self):
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            with self.subTest(language=language):
                self.assertTrue("miniapp.menu" in TRANSLATIONS[language], language)
                self.assertTrue(TRANSLATIONS[language]["miniapp.menu"].strip())

    def test_every_enabled_language_has_its_own_complete_payment_catalog(self):
        english = COMMERCE["en"]
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            with self.subTest(language=language):
                self.assertEqual(commerce_language(language), language)
                self.assertIn(language, COMMERCE)
                catalog = COMMERCE[language]
                self.assertEqual(set(catalog["text"]), set(english["text"]))
                self.assertEqual(set(catalog["products"]), set(english["products"]))
                self.assertTrue(all(value.strip() for value in catalog["text"].values()))
                for name, description in catalog["products"].values():
                    self.assertTrue(name.strip())
                    self.assertTrue(description.strip())

    def test_legacy_payment_receipts_and_invoices_are_localized_without_changing_prices(self):
        for language in ("la", "ja", "quz"):
            for key, values in (
                ("donation", {"amount": 25}),
                ("product", {"title": "fixture"}),
                ("invalid", {}),
                ("refund", {}),
            ):
                with self.subTest(language=language, key=key):
                    self.assertNotEqual(
                        commerce_text(language, key, **values),
                        commerce_text("es", key, **values),
                    )
            for product in PAID_HISOPOS:
                with self.subTest(language=language, product=product.key):
                    spec = localized_invoice_spec("product", product.key, language)
                    self.assertEqual(spec.amount_stars, product.price_stars)
                    self.assertLessEqual(len(spec.title), 32)
                    self.assertLessEqual(len(spec.description), 255)
                    self.assertNotEqual(
                        spec.description,
                        localized_invoice_spec("product", product.key, "es").description,
                    )

    def test_gift_usage_and_errors_follow_every_enabled_language(self):
        cases = (
            ("", "group", "gift.private_only", {}),
            ("", "private", "gift.usage", {"types": ", ".join(regalar_hisopo.GIFT_TYPE_HINTS)}),
            ("invented 2", "private", "gift.invalid_type", {"types": ", ".join(regalar_hisopo.GIFT_TYPE_HINTS)}),
            ("mini abc", "private", "gift.invalid_recipient", {}),
            ("mini 0", "private", "gift.invalid_recipient", {}),
            ("mini １２", "private", "gift.invalid_recipient", {}),
        )
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            for args, chat_type, key, values in cases:
                with self.subTest(language=language, args=args, chat_type=chat_type):
                    self.assertTrue(key in TRANSLATIONS[language], f"{language}:{key}")
                    db = MagicMock()
                    response = regalar_hisopo.handle(
                        command_context(language, args=args, chat_type=chat_type), db
                    )
                    self.assertEqual(response, t(language, key, **values))
                    db.grant_paid_hisopo.assert_not_called()

    def test_gift_confirmation_uses_the_localized_product_name_and_keeps_identity(self):
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            for product in (PAID_HISOPOS[0], CLUB_HISOPO):
                with self.subTest(language=language, product=product.key):
                    self.assertTrue("gift.confirmed" in TRANSLATIONS[language], language)
                    db = MagicMock()
                    db.grant_paid_hisopo.return_value = 2
                    response = regalar_hisopo.handle(
                        command_context(language, args=f"{product.key} 123456"), db
                    )
                    self.assertEqual(
                        response,
                        t(
                            language,
                            "gift.confirmed",
                            name=cosmetic_name(product, language),
                            recipient="123456",
                            quantity=2,
                        ),
                    )
                    db.grant_paid_hisopo.assert_called_once_with(
                        recipient_user_id="123456",
                        hisopo_key=product.key,
                        gifted_by_user_id="1",
                    )

    def test_user_level_label_is_localized_for_all_levels_and_languages(self):
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            for level in UserLevel:
                with self.subTest(language=language, level=level):
                    key = f"role.{level.label}"
                    self.assertTrue(key in TRANSLATIONS[language], f"{language}:{key}")
                    response = nivel.handle(command_context(language, level=level), MagicMock())
                    self.assertEqual(
                        response,
                        t(language, "nivel.response", level=t(language, key)),
                    )

    def test_payment_help_and_terms_commands_use_the_selected_language(self):
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            for handler, key in (
                (donar.handle_support, "payments.support"),
                (donar.handle_terms, "payments.terms"),
            ):
                with self.subTest(language=language, command=key):
                    response = handler(command_context(language), MagicMock())
                    self.assertEqual(response, TRANSLATIONS[language][key])
                    if language not in {"es", "es_ES", "en"}:
                        self.assertNotIn(
                            response,
                            (TRANSLATIONS["es"][key], TRANSLATIONS["en"][key]),
                        )
                    if key == "payments.support":
                        self.assertIn("/reportar", response)
                    else:
                        self.assertIn("https://telegram.org/tos/stars", response)

    def test_help_keeps_every_visible_command_localized_and_hidden_commands_private(self):
        for option in LANGUAGE_OPTIONS:
            language = option["code"]
            for chat_type in ("private", "group"):
                for level in UserLevel:
                    with self.subTest(language=language, chat_type=chat_type, level=level):
                        response = help_command.handle(
                            command_context(language, level=level, chat_type=chat_type), MagicMock()
                        )
                        visible = {
                            command.name: command
                            for command in iter_commands()
                            if not command.hidden
                            and level >= command.min_level
                            and (chat_type == "private" or command.min_level != UserLevel.DEV)
                        }
                        rendered = set(re.findall(r"^/([^:]+):", response, flags=re.MULTILINE))
                        self.assertEqual(rendered, set(visible))
                        self.assertNotIn("regalarhisopo", rendered)
                        for name, command in visible.items():
                            key = f"help.{command.command_key}"
                            self.assertIn(key, TRANSLATIONS[language])
                            self.assertIn(f"/{name}: {TRANSLATIONS[language][key]}", response)
                        if chat_type == "group" and level >= UserLevel.DEV:
                            self.assertIn(TRANSLATIONS[language]["help.dev_private_hint"], response)


class PrivateMiniAppMenuLanguageTests(unittest.IsolatedAsyncioTestCase):
    def menu_fixture(self, db, *, chat_type="private", public_url="https://example.test/miniapp"):
        bot = SimpleNamespace(set_chat_menu_button=AsyncMock(), set_my_commands=AsyncMock())
        chat_id = 10 if chat_type == "private" else -1
        db.set_chat_language(str(chat_id), "es")
        state = SimpleNamespace(
            db=db,
            bot_username="galerazo_bot",
            settings=SimpleNamespace(
                telegram_dev_user_ids=frozenset(),
                telegram_mini_app_url=public_url,
                mini_app_proxy_secret="s" * 32,
                mini_app_bind_host="127.0.0.1",
            ),
        )
        message = SimpleNamespace(
            chat=SimpleNamespace(id=chat_id, type=chat_type), edit_text=AsyncMock()
        )
        markup = chat_config.build_language_menu("es", chat_config.selected_language_page("en"))
        choice = next(
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data.startswith("config:lang:en:")
        )
        callback = SimpleNamespace(message=message, data=choice, answer=AsyncMock())
        update = SimpleNamespace(
            callback_query=callback,
            effective_user=SimpleNamespace(id=10, full_name="Ada", username="ada"),
        )
        return state, bot, update, SimpleNamespace(bot=bot)

    async def test_private_language_selection_updates_only_that_users_menu(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "languages.sqlite3")
            bot = SimpleNamespace(set_chat_menu_button=AsyncMock(), set_my_commands=AsyncMock())
            state = SimpleNamespace(
                db=db,
                bot_username="galerazo_bot",
                settings=SimpleNamespace(
                    telegram_dev_user_ids=frozenset(),
                    telegram_mini_app_url="https://example.test/miniapp",
                    mini_app_proxy_secret="s" * 32,
                    mini_app_bind_host="127.0.0.1",
                ),
            )
            message = SimpleNamespace(
                chat=SimpleNamespace(id=10, type="private"),
                edit_text=AsyncMock(),
            )
            callback = SimpleNamespace(message=message, data="", answer=AsyncMock())
            update = SimpleNamespace(
                callback_query=callback,
                effective_user=SimpleNamespace(id=10, full_name="Ada", username="ada"),
            )
            context = SimpleNamespace(bot=bot)
            for option in LANGUAGE_OPTIONS:
                language = option["code"]
                source = "en" if language == "es" else "es"
                db.set_chat_language("10", source)
                page = chat_config.selected_language_page(language)
                markup = chat_config.build_language_menu(source, page)
                callback.data = next(
                    button.callback_data
                    for row in markup.inline_keyboard
                    for button in row
                    if button.callback_data.startswith(f"config:lang:{language}:")
                )
                bot.set_chat_menu_button.reset_mock()
                bot.set_my_commands.reset_mock()
                with self.subTest(language=language), (
                    patch.object(telegram_bot, "_state", return_value=state)
                ), (
                    patch.object(
                        telegram_bot,
                        "_resolve_user_level",
                        AsyncMock(return_value=UserLevel.COMMON),
                    )
                ):
                    await telegram_bot._config_callback_entrypoint(update, context)
                    self.assertEqual(db.get_chat_settings("10").language, language)
                    bot.set_chat_menu_button.assert_awaited_once()
                    call = bot.set_chat_menu_button.await_args.kwargs
                    self.assertEqual(str(call["chat_id"]), "10")
                    self.assertEqual(call["menu_button"].text, t(language, "miniapp.menu"))
                    self.assertEqual(
                        call["menu_button"].web_app.url,
                        "https://example.test/miniapp",
                    )
                    bot.set_my_commands.assert_awaited_once()
                    command_call = bot.set_my_commands.await_args
                    self.assertFalse(command_call.kwargs.get("language_code"))
                    self.assertEqual(command_call.kwargs["scope"].type, "chat")
                    self.assertEqual(str(command_call.kwargs["scope"].chat_id), "10")
                    commands = command_call.args[0] if command_call.args else command_call.kwargs["commands"]
                    self.assertEqual(
                        tuple(commands),
                        telegram_bot._suggested_bot_commands(
                            language, UserLevel.COMMON, include_group_commands=False
                        ),
                    )
                    self.assertNotIn("regalarhisopo", {command.command for command in commands})

    async def test_group_language_selection_updates_common_and_admin_command_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "languages.sqlite3")
            bot = SimpleNamespace(set_chat_menu_button=AsyncMock(), set_my_commands=AsyncMock())
            state = SimpleNamespace(
                db=db,
                bot_username="galerazo_bot",
                settings=SimpleNamespace(telegram_dev_user_ids=frozenset()),
            )
            message = SimpleNamespace(
                chat=SimpleNamespace(id=-1, type="supergroup"), edit_text=AsyncMock()
            )
            callback = SimpleNamespace(message=message, data="", answer=AsyncMock())
            update = SimpleNamespace(
                callback_query=callback,
                effective_user=SimpleNamespace(id=10, full_name="Ada", username="ada"),
            )
            context = SimpleNamespace(bot=bot)
            for option in LANGUAGE_OPTIONS:
                language = option["code"]
                source = "en" if language == "es" else "es"
                db.set_chat_language("-1", source)
                markup = chat_config.build_language_menu(
                    source, chat_config.selected_language_page(language)
                )
                callback.data = next(
                    button.callback_data
                    for row in markup.inline_keyboard
                    for button in row
                    if button.callback_data.startswith(f"config:lang:{language}:")
                )
                bot.set_my_commands.reset_mock()
                with self.subTest(language=language), (
                    patch.object(telegram_bot, "_state", return_value=state)
                ), (
                    patch.object(
                        telegram_bot,
                        "_resolve_user_level",
                        AsyncMock(return_value=UserLevel.ADMIN),
                    )
                ):
                    await telegram_bot._config_callback_entrypoint(update, context)
                    self.assertEqual(db.get_chat_settings("-1").language, language)
                    self.assertEqual(bot.set_my_commands.await_count, 2)
                    calls = {
                        call.kwargs["scope"].type: call
                        for call in bot.set_my_commands.await_args_list
                    }
                    self.assertEqual(set(calls), {"chat", "chat_administrators"})
                    for scope, level in (("chat", UserLevel.COMMON), ("chat_administrators", UserLevel.ADMIN)):
                        call = calls[scope]
                        self.assertEqual(str(call.kwargs["scope"].chat_id), "-1")
                        self.assertFalse(call.kwargs.get("language_code"))
                        commands = call.args[0] if call.args else call.kwargs["commands"]
                        self.assertEqual(
                            tuple(commands),
                            telegram_bot._suggested_bot_commands(
                                language, level, include_group_commands=True
                            ),
                        )
                        names = {command.command for command in commands}
                        self.assertNotIn("regalarhisopo", names)
                        self.assertNotIn("apagar", names)
                        self.assertNotIn("anuncio", names)
                    bot.set_chat_menu_button.assert_not_awaited()

    async def test_private_language_change_keeps_commands_when_mini_app_url_is_absent_or_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "url-errors.sqlite3")
            for public_url in (None, "http://example.test/miniapp"):
                with self.subTest(public_url=public_url):
                    state, bot, update, context = self.menu_fixture(db, public_url=public_url)
                    with (
                        patch.object(telegram_bot, "_state", return_value=state),
                        patch.object(
                            telegram_bot, "_resolve_user_level", AsyncMock(return_value=UserLevel.COMMON)
                        ),
                    ):
                        await telegram_bot._config_callback_entrypoint(update, context)
                    self.assertEqual(db.get_chat_settings("10").language, "en")
                    bot.set_my_commands.assert_awaited_once()
                    bot.set_chat_menu_button.assert_not_awaited()
                    update.callback_query.answer.assert_awaited_once_with(
                        text=t("en", "config.language_updated")
                    )

    async def test_telegram_menu_failures_keep_saved_language_and_answer_the_callback(self):
        cases = (
            ("private", "commands"),
            ("private", "miniapp"),
            ("supergroup", "admin_commands"),
        )
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "telegram-errors.sqlite3")
            for chat_type, failure in cases:
                with self.subTest(chat_type=chat_type, failure=failure):
                    state, bot, update, context = self.menu_fixture(db, chat_type=chat_type)
                    if failure == "miniapp":
                        bot.set_chat_menu_button.side_effect = TimedOut("fixture")
                    elif failure == "admin_commands":
                        bot.set_my_commands.side_effect = [None, TimedOut("fixture")]
                    else:
                        bot.set_my_commands.side_effect = TimedOut("fixture")
                    with (
                        patch.object(telegram_bot, "_state", return_value=state),
                        patch.object(
                            telegram_bot, "_resolve_user_level", AsyncMock(return_value=UserLevel.ADMIN)
                        ),
                        self.assertLogs(telegram_bot.logger, level="WARNING") as captured,
                    ):
                        await telegram_bot._config_callback_entrypoint(update, context)
                    self.assertTrue(any("menús localizados" in line for line in captured.output))
                    chat_id = "10" if chat_type == "private" else "-1"
                    self.assertEqual(db.get_chat_settings(chat_id).language, "en")
                    update.callback_query.answer.assert_awaited_once_with(
                        text=t("en", "config.language_updated")
                    )
                    if failure == "commands":
                        bot.set_my_commands.assert_awaited_once()
                        bot.set_chat_menu_button.assert_not_awaited()
                    elif failure == "miniapp":
                        bot.set_chat_menu_button.assert_awaited_once()
                    else:
                        self.assertEqual(bot.set_my_commands.await_count, 2)
                        bot.set_chat_menu_button.assert_not_awaited()


class MiniAppFallbackMetadataTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.directory.name) / "fallbacks.sqlite3")
        self.db.get_or_create_user("123")
        self.db.get_or_create_user("124", "Usuario 123")
        self.db.get_or_create_user("125", username="alias125")
        self.db.get_or_create_user("126", "Private donor", "private_alias")
        self.db.register_chat("-1", "group", None)
        self.api = MiniAppApi(
            db=self.db, bot_token="token", bot=None, public_url="https://example.test/miniapp"
        )

    def tearDown(self):
        self.directory.cleanup()

    async def test_shared_owner_and_album_mark_real_fallbacks_without_rewriting_literal_names(self):
        headers = {
            "X-Telegram-Init-Data": signed_init_data(
                start_param=create_shared_album_context("token", chat_id="-1", user_id="123")
            )
        }
        payload = json.loads((await self.api.bootstrap(request_stub(headers=headers))).text)
        self.assertEqual(payload["album_owner"]["id"], "123")
        self.assertTrue(payload["album_owner"].get("name_fallback"))
        self.assertTrue(payload["albums"][0].get("title_fallback"))
        self.db.get_or_create_user("123", "Usuario 123")
        self.db.register_chat("-1", "group", "Grupo -1")
        named = json.loads((await self.api.bootstrap(request_stub(headers=headers))).text)
        self.assertEqual(named["album_owner"]["name"], "Usuario 123")
        self.assertIs(named["album_owner"].get("name_fallback"), False)
        self.assertEqual(named["albums"][0]["title"], "Grupo -1")
        self.assertIs(named["albums"][0].get("title_fallback"), False)

    async def test_authenticated_missing_name_is_distinct_from_literal_usuario(self):
        for user, expected_fallback, expected_name in (
            ({"id": 10}, True, "Usuario"),
            ({"id": 11, "first_name": "Usuario"}, False, "Usuario"),
            ({"id": 12, "last_name": "Surname only"}, False, "Surname only"),
        ):
            with self.subTest(user=user):
                response = await self.api.bootstrap(
                    request_stub(headers={"X-Telegram-Init-Data": signed_init_data(user=user)})
                )
                owner = json.loads(response.text)["album_owner"]
                self.assertIs(owner.get("name_fallback"), expected_fallback)
                self.assertEqual(owner["name"], expected_name)

    async def test_donor_fallback_ids_are_only_exposed_for_public_unnamed_donors(self):
        for index, user_id in enumerate(("123", "124", "125", "126"), start=1):
            self.db.record_star_payment(
                telegram_payment_charge_id=f"fixture-{index}",
                provider_payment_charge_id=None,
                user_id=user_id,
                kind="donation",
                item_key="25",
                amount_stars=100 + index,
                currency="XTR",
                invoice_payload="fixture",
                source_chat_id=None,
                reward_hisopo_key=None,
                paid_at="2026-10-20T12:00:00+00:00",
            )
            self.db.set_donor_display_public(user_id, user_id != "126")
        response = await self.api.bootstrap(
            request_stub(headers={"X-Telegram-Init-Data": signed_init_data()})
        )
        donors = {entry["amount_stars"]: entry for entry in json.loads(response.text)["donors"]}
        self.assertIs(donors[101].get("name_fallback"), True)
        self.assertEqual(donors[101].get("user_id"), "123")
        self.assertEqual(donors[102]["name"], "Usuario 123")
        self.assertIs(donors[102].get("name_fallback"), False)
        self.assertNotIn("user_id", donors[102])
        self.assertEqual(donors[103]["name"], "@alias125")
        self.assertIs(donors[103].get("name_fallback"), False)
        self.assertNotIn("user_id", donors[103])
        self.assertIs(donors[104]["public"], False)
        self.assertIs(donors[104].get("name_fallback"), False)
        for key in ("user_id", "id", "username"):
            self.assertNotIn(key, donors[104])
        self.assertNotIn("Private donor", donors[104]["name"])
        self.assertNotIn("private_alias", donors[104]["name"])

    async def test_name_fallback_survives_opening_the_same_album_through_a_shared_link(self):
        own_response = await self.api.bootstrap(
            request_stub(
                headers={"X-Telegram-Init-Data": signed_init_data(user={"id": 10})}
            )
        )
        own_owner = json.loads(own_response.text)["album_owner"]
        self.assertIs(own_owner.get("name_fallback"), True)
        shared_response = await self.api.bootstrap(
            request_stub(
                headers={
                    "X-Telegram-Init-Data": signed_init_data(
                        start_param=create_shared_album_context(
                            "token", chat_id="-1", user_id="10"
                        )
                    )
                }
            )
        )
        shared_owner = json.loads(shared_response.text)["album_owner"]
        self.assertEqual(shared_owner["id"], "10")
        self.assertIs(shared_owner.get("name_fallback"), True)

    async def test_invoice_and_visibility_do_not_save_synthetic_names_or_erase_real_names(self):
        self.api.bot = SimpleNamespace(
            create_invoice_link=AsyncMock(return_value="https://t.me/invoice-fixture")
        )
        for endpoint, body in (
            (self.api.create_invoice, {"kind": "donation", "item_key": "25", "language": "en"}),
            (self.api.donor_visibility, {"public": True}),
        ):
            for user_id, expected_name in ((20, None), (124, "Usuario 123")):
                with self.subTest(endpoint=endpoint.__name__, user_id=user_id):
                    response = await endpoint(
                        request_stub(
                            headers={
                                "X-Telegram-Init-Data": signed_init_data(user={"id": user_id})
                            },
                            body=body,
                        )
                    )
                    self.assertEqual(response.status, 200)
                    self.assertEqual(self.db.get_user(str(user_id)).display_name, expected_name)


class SavedPrivateLanguageStartTests(unittest.IsolatedAsyncioTestCase):
    def start_fixture(self, *, public_url="https://example.test/miniapp"):
        db = MagicMock()
        db.get_chat_settings.return_value = SimpleNamespace(language="ja")
        db.get_or_create_user.return_value = SimpleNamespace(display_name="Ada")
        db.get_chat_added_by_user_id.return_value = None
        db.is_user_blocked.return_value = False
        bot = SimpleNamespace(set_my_commands=AsyncMock(), set_chat_menu_button=AsyncMock())
        state = SimpleNamespace(
            db=db,
            bot_user_id="99",
            bot_username="galerazo_bot",
            settings=SimpleNamespace(
                telegram_dev_user_ids=frozenset(),
                telegram_log_chat_id=None,
                telegram_mini_app_url=public_url,
                mini_app_proxy_secret="s" * 32,
                mini_app_bind_host="127.0.0.1",
            ),
        )
        chat = SimpleNamespace(id=10, type="private")
        user = SimpleNamespace(id=10, full_name="Ada", username="ada")
        message = SimpleNamespace(
            chat=chat, text="/start", reply_to_message=None, reply_text=AsyncMock()
        )
        update = SimpleNamespace(
            effective_message=message, effective_user=user, effective_chat=chat
        )
        return state, bot, message, update, SimpleNamespace(bot=bot)

    async def test_start_restores_commands_and_mini_app_for_the_saved_japanese_language(self):
        state, bot, message, update, context = self.start_fixture()
        with patch.object(telegram_bot, "_state", return_value=state):
            await telegram_bot._handle_command_update(update, context)
        self.assertEqual(message.reply_text.await_args.args[0], t("ja", "start.response", name="Ada"))
        state.db.set_chat_language.assert_not_called()
        bot.set_my_commands.assert_awaited_once()
        command_call = bot.set_my_commands.await_args
        commands = command_call.args[0] if command_call.args else command_call.kwargs["commands"]
        self.assertEqual(
            tuple(commands),
            telegram_bot._suggested_bot_commands("ja", UserLevel.COMMON, False),
        )
        self.assertEqual(command_call.kwargs["scope"].type, "chat")
        self.assertEqual(str(command_call.kwargs["scope"].chat_id), "10")
        self.assertFalse(command_call.kwargs.get("language_code"))
        bot.set_chat_menu_button.assert_awaited_once()
        menu_call = bot.set_chat_menu_button.await_args.kwargs
        self.assertEqual(str(menu_call["chat_id"]), "10")
        self.assertEqual(menu_call["menu_button"].text, t("ja", "miniapp.menu"))
        self.assertEqual(menu_call["menu_button"].web_app.url, "https://example.test/miniapp")

    async def test_start_keeps_native_commands_when_mini_app_url_is_absent_or_invalid(self):
        for public_url in (None, "http://example.test/miniapp"):
            with self.subTest(public_url=public_url):
                state, bot, message, update, context = self.start_fixture(public_url=public_url)
                with patch.object(telegram_bot, "_state", return_value=state):
                    await telegram_bot._handle_command_update(update, context)
                self.assertEqual(message.reply_text.await_args.args[0], t("ja", "start.response", name="Ada"))
                bot.set_my_commands.assert_awaited_once()
                bot.set_chat_menu_button.assert_not_awaited()
                state.db.set_chat_language.assert_not_called()

    async def test_start_reply_survives_telegram_command_or_button_failure(self):
        for failing_menu in ("commands", "miniapp"):
            with self.subTest(failing_menu=failing_menu):
                state, bot, message, update, context = self.start_fixture()
                if failing_menu == "commands":
                    bot.set_my_commands.side_effect = TimedOut("fixture")
                else:
                    bot.set_chat_menu_button.side_effect = TimedOut("fixture")
                with patch.object(telegram_bot, "_state", return_value=state):
                    await telegram_bot._handle_command_update(update, context)
                self.assertEqual(message.reply_text.await_args.args[0], t("ja", "start.response", name="Ada"))
                bot.set_my_commands.assert_awaited_once()
                if failing_menu == "miniapp":
                    bot.set_chat_menu_button.assert_awaited_once()
                else:
                    bot.set_chat_menu_button.assert_not_awaited()
                state.db.set_chat_language.assert_not_called()


class SourceProseParityTests(unittest.TestCase):
    def test_enabled_catalogs_do_not_copy_complete_english_prose(self):
        invariants = re.compile(
            r"https?://[^\s<>]+|\{[^{}]+\}|</?[^>]+>|/[a-zA-Z][a-zA-Z0-9_]*|"
            r"\b(?:user_id|Galerazo|Bot|Club|Hisopo|Hisopos|Telegram|GitHub|Cafecito|Stars|Estelar|LIL)\b"
        )
        # These are also natural target-language expressions, not fallback prose.
        shared_cognates = {("af", "miniapp.menu"), ("da", "chats.private")}
        for locale, catalog in TRANSLATIONS.items():
            if locale in {"es", "es_ES", "en"}:
                continue
            for key, text in catalog.items():
                if (locale, key) in shared_cognates:
                    continue
                if len(re.findall(r"[A-Za-z]{2,}", invariants.sub("", text))) < 2:
                    continue
                with self.subTest(locale=locale, key=key):
                    self.assertNotEqual(text, TRANSLATIONS["en"][key])


if __name__ == "__main__":
    unittest.main()
