from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from galerazo_bot import chat_config as menu
from galerazo_bot.database import Database
from galerazo_bot.telegram_bot import _handle_config_callback, _config_callback_entrypoint
from galerazo_bot.roles import UserLevel


def callbacks(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


class LanguagePaginationTests(unittest.IsolatedAsyncioTestCase):
    def test_all_languages_reachable_in_both_directions_with_partial_last_page(self):
        from galerazo_bot.i18n import t
        for language in ('es','es_ES'):
            self.assertEqual(t(language,'config.back'),'Volver')
            self.assertEqual(t(language,'config.previous_page'),'Volver')
        count = menu.language_page_count()
        self.assertGreater(count, 1)
        seen = []
        for page in list(range(count)) + list(reversed(range(count))):
            markup = menu.build_language_menu('es', page)
            data = callbacks(markup)
            choices = [v for v in data if v.startswith('config:lang:')]
            self.assertGreater(len(choices), 0)
            self.assertLessEqual(len(choices), menu.LANGUAGES_PER_PAGE)
            seen.extend(v.split(':')[2] for v in choices)
            arrows = [v for v in data if v.startswith('config:langpage:')]
            self.assertEqual(len(arrows), int(page > 0) + int(page < count-1))
            self.assertIn(f'{page+1}', markup.inline_keyboard[-2][0 if page == 0 else 1].text)
            for v in data:
                self.assertLessEqual(len(v.encode()), 64)
        self.assertEqual(set(seen), {o.code for o in menu.LANGUAGES})
        self.assertEqual(len(seen), 2*len(menu.LANGUAGES))
        for value in (-1, count, True, '1'):
            with self.assertRaises(ValueError):
                menu.build_language_menu('es', value)

    async def test_navigation_never_changes_persisted_language_and_selection_remains_marked(self):
        with TemporaryDirectory() as directory:
            db = Database(Path(directory) / 'fixture.sqlite3')
            db.set_chat_language('-1', 'en')
            message = SimpleNamespace(chat=SimpleNamespace(id=-1), edit_text=AsyncMock())
            for page in (0, menu.language_page_count()-1, 0):
                markup=menu.build_language_menu('en', page)
                navigation=next(v for v in callbacks(markup) if v.startswith('config:langpage:'))
                await _handle_config_callback(db, message, tuple(navigation.split(':')[1:]))
                self.assertEqual(db.get_chat_settings('-1').language, 'en')
            markup=menu.build_language_menu('en', 0)
            choice=next(v for v in callbacks(markup) if v.startswith('config:lang:es:'))
            await _handle_config_callback(db, message, tuple(choice.split(':')[1:]))
            self.assertEqual(db.get_chat_settings('-1').language, 'es')
            self.assertTrue(message.edit_text.await_args.kwargs['reply_markup'].inline_keyboard[0][0].text.startswith('['))

    async def test_stale_tampered_unknown_and_off_page_choices_do_not_mutate(self):
        db=MagicMock()
        db.get_chat_settings.return_value=SimpleNamespace(language='es')
        message=SimpleNamespace(chat=SimpleNamespace(id=-1), edit_text=AsyncMock())
        valid=next(v for v in callbacks(menu.build_language_menu('es', 0)) if v.startswith('config:lang:en:'))
        revision=valid.split(':')[-1]
        cases=[('lang','en'),('language','extra'),('langpage',),('langpage','-1','es',revision),('langpage','9999','es',revision),('langpage','１','es',revision),('langpage','bad','es',revision),('langpage','0','en',revision),('langpage','0','es','old'),('lang','bad','0','es',revision),('lang','en','1','es',revision),('lang','es','0','es',revision)]
        for parsed in cases:
            with self.subTest(parsed=parsed):
                await _handle_config_callback(db,message,parsed)
        await _handle_config_callback(db,message,('langpage',str(menu.language_page_count()),'es',revision))
        db.set_chat_language.assert_not_called()
        message.edit_text.assert_not_awaited()

    async def test_rtl_selected_page_notice_and_repeated_edits(self):
        from telegram.error import BadRequest
        self.assertEqual(menu.selected_language_page('unknown'),0)
        self.assertEqual(menu.language_menu_text('unknown'),'Idioma')
        menu.build_language_menu('unknown',0)
        rtl=[]
        from galerazo_bot.language_catalogs import LANGUAGE_OPTIONS
        for option in LANGUAGE_OPTIONS:
            language=option['code']
            markup=menu.build_language_menu(language)
            chosen=[b for row in markup.inline_keyboard for b in row if b.text.startswith('[')]
            self.assertEqual(len(chosen),1)
            self.assertIn(option['native'],chosen[0].text)
            if option['machine']:
                self.assertIn('\n\n',menu.language_menu_text(language))
            if option['direction']=='rtl':
                rtl.append(language)
                for button in markup.inline_keyboard[-2]:
                    if button.callback_data.startswith('config:langpage:'):
                        target=int(button.callback_data.split(':')[2])
                        self.assertIn('→' if target<menu.selected_language_page(language) else '←',button.text)
        self.assertTrue(rtl)
        db=MagicMock()
        db.get_chat_settings.return_value=SimpleNamespace(language='es')
        message=SimpleNamespace(chat=SimpleNamespace(id=-1),edit_text=AsyncMock(side_effect=BadRequest('Message is not modified')))
        self.assertIsNone(await _handle_config_callback(db,message,('language',)))

    async def test_failed_edit_still_answers_callback_and_retains_permissions(self):
        from tests.test_config_menu import _callback_fixture
        from telegram.error import BadRequest
        for level in (UserLevel.COMMON,UserLevel.ADMIN):
            update,context,state,message=_callback_fixture()
            update.callback_query.data='config:language'
            message.edit_text=AsyncMock(side_effect=BadRequest('network failed'))
            with patch('galerazo_bot.telegram_bot._state',return_value=state),patch('galerazo_bot.telegram_bot._resolve_user_level',AsyncMock(return_value=level)):
                if level==UserLevel.ADMIN:
                    with self.assertRaises(BadRequest):
                        await _config_callback_entrypoint(update,context)
                else:
                    await _config_callback_entrypoint(update,context)
                    message.edit_text.assert_not_awaited()
            update.callback_query.answer.assert_awaited_once()
