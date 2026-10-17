import json
import re
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from string import Formatter

from galerazo_bot.i18n import TRANSLATIONS
from galerazo_bot.language_catalogs import CATALOGS, LANGUAGE_OPTIONS, LANGUAGE_NAMES
from galerazo_bot.commerce_i18n import COMMERCE, commerce_language, commerce_text, is_commerce_language, localized_invoice_spec


class BalancedTelegramHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack=[]
    def handle_starttag(self,tag,attrs):
        self.stack.append(tag)
    def handle_endtag(self,tag):
        assert self.stack and self.stack.pop()==tag


class PrivateLanguageInventoryTests(unittest.TestCase):
    def test_frozen_inventory_partition_catalogs_names_and_machine_notices(self):
        root=Path(__file__).resolve().parents[1]
        receipt=json.loads((root/'docs/LANGUAGE-EXPANSION-RECEIPT-20261017.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['referenceTotal'],176)
        for surface in ('bot','miniapp'):
            value=receipt[surface]
            self.assertEqual(value['before']+len(value['added'])+len(value['omitted']),176)
            self.assertEqual(value['before']+len(value['added']),value['after'])
            added={x['route'] for x in value['added']}
            omitted={x['route'] for x in value['omitted']}
            self.assertFalse(added & omitted)
            self.assertTrue(all(x['reasons'] for x in value['omitted']))
        self.assertEqual(len(LANGUAGE_OPTIONS),receipt['bot']['after'])
        self.assertEqual({o['code'] for o in LANGUAGE_OPTIONS},set(TRANSLATIONS))
        self.assertEqual(len({o['route'] for o in LANGUAGE_OPTIONS}),len(LANGUAGE_OPTIONS))
        for option in LANGUAGE_OPTIONS:
            code=option['code']
            self.assertEqual(set(LANGUAGE_NAMES[code]),set(TRANSLATIONS))
            self.assertTrue(all(LANGUAGE_NAMES[code].values()))
            if option['machine']:
                self.assertEqual(set(TRANSLATIONS[code]),set(TRANSLATIONS['en']))
                self.assertTrue(TRANSLATIONS[code]['config.translation_notice'].strip())
                self.assertIn('/donantes public',TRANSLATIONS[code]['donors.privacy_hint'])
                self.assertIn('/donantes anonymous',TRANSLATIONS[code]['donors.privacy_hint'])
                for key,value in TRANSLATIONS[code].items():
                    self.assertTrue(value.strip(),(code,key))
                    parser=BalancedTelegramHTML();parser.feed(value)
                    self.assertFalse(parser.stack,(code,key))
        self.assertFalse(is_commerce_language('unsupported'))
        self.assertFalse(is_commerce_language({}))
        self.assertEqual(commerce_language('unsupported'),'es')
        self.assertEqual(commerce_language(None),'es')
        # The legacy exceptions are explicit, pre-existing locales, never newly
        # admitted incomplete translations.
        self.assertTrue(set(CATALOGS['legacyCommerceExceptions']) <= {'la','ja','quz','ko'})

    def test_commerce_templates_preserve_placeholders_and_telegram_limits(self):
        formatter=Formatter()
        expected={key:Counter(field for _,field,_,_ in formatter.parse(value) if field) for key,value in COMMERCE['en']['text'].items()}
        for language,catalog in COMMERCE.items():
            self.assertEqual(set(catalog['text']),set(expected))
            self.assertLessEqual(len(catalog['text']['invalid'].encode('utf-16-le'))//2,200)
            for key,value in catalog['text'].items():
                self.assertEqual(Counter(field for _,field,_,_ in formatter.parse(value) if field),expected[key])
                self.assertNotRegex(value,r'QZX|XZQ|\ufffd')
        self.assertEqual(localized_invoice_spec('product','mini','es_ES').title,localized_invoice_spec('product','mini','es').title)
