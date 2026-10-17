# Private language expansion · 2026-10-17

The frozen reference has 176 public language/script/region options. This delivery
admits only complete private catalogs for their own screens and operations.
Bot: 18 existing + 94 added = 112; 64 omitted.
Miniapp: 21 existing + 119 added = 140; 36 omitted.
These counts include script/region variants, not countries or a certification of
native linguistic quality. New catalogs show a localized automatic translation notice.

Acquisition used only static English repository text with the public Google
Translate consumer service. No visitor data, accounts, paid APIs or new services.
The separate Bing consumer form returned HTTP401; no bypass or repeated access
attempt was made. Its 13 reference variants are omitted. Other omissions include
untranslated prose, damaged variables/literals, incomplete payment text or Telegram
message/invoice size limits. The receipts list exact missing fields and reasons.
No Spanish placeholder catalogs are added. Existing locales are preserved.

## Runtime and contracts

- Catalogs are packaged locally; there is no translation request at runtime.
- The bot selector has 12 choices per page, two per row, bilingual isolated labels,
  localized previous/next arrows and current/total indicator. Opening selects the
  page containing the saved choice. Navigation changes no preference. Unsupported
  indices, off-page choices and stale inventory/language callbacks make no change.
  Existing blocked/restricted/admin checks remain. Every handled callback is answered,
  including edit failures. Telegram decides its native font size and button rendering.
- Miniapp applies lang/dir, bidi isolation, all UI/ARIA/errors/items and a localized
  notice. Its scrollable selector, URL and localStorage retain the selection.
- Invoice requests may optionally include language. Missing language preserves the
  existing Spanish behavior. An unknown language is rejected before creating an invoice.
  Existing clients, h2 signatures, SKU keys, amounts, grants, permissions and API response
  contracts remain unchanged. Product names longer than Telegram's 32-character title
  limit are retained in full at the start of the description under the Galerazo Bot title.
- The independent payment_language_preferences table stores the authenticated payer's
  last successful invoice language. It does not change group configuration. Receipts,
  errors and refunds reuse it. Cosmetic names also use the local catalog in bot albums.
- Existing legacy payment presentation remains Spanish for la, ja, quz, ko:
  the new payment catalog could not be verified for these pre-existing locales. They
  are not counted as new complete catalogs; no existing locale is removed or relabeled
  as natively reviewed. This limitation is explicit rather than a new fallback catalog.

## Validation and publication

Bot local gate: .venv/Scripts/python.exe -m coverage run -m pytest; coverage json
and scripts/check_coverage.py require exactly 100% statements and branches.
Run scripts/runtime_versions.py, pip check, compileall and log_checkpoint as well.
Web gates: npm run check, npm test, npm run coverage and npm run build; supported
line/branch/function/statement metrics retain their 100% gates. Browser QA is opt-in:
scripts/check-miniapp-languages-ui.mjs and npm run test:shared-visits with the existing
QA_NODE_MODULES runtime. No real Telegram login, money transfer or remote CI monitoring.
Native Telegram mobile/Desktop and a real software keyboard are not certified by
the headless harness. Public landing inventories and translations remain unchanged.

Source versions are bot0.76 and web0.1.23. This run authorizes no deployment, backend
restart or Telegram announcement. Publication remains behind the existing BCC flow,
release authorization and editorial broadcast approval. Code readiness is not production
activation; the prior verified production remains bot0.68/web0.1.22.

## Frozen inventory reconciliation

| Route | Native name | Bot | Miniapp |
| --- | --- | --- | --- |
| `es` | Español (Argentina) | Existing | Existing |
| `es-ES` | Español (España) | Existing | Existing |
| `en` | English | Existing | Existing |
| `ru` | Русский | Existing | Existing |
| `la` | Latine | Existing | Existing |
| `ja` | 日本語 | Existing | Existing |
| `it` | Italiano | Existing | Existing |
| `fr` | Français | Existing | Existing |
| `de` | Deutsch | Existing | Existing |
| `nl` | Nederlands | Existing | Existing |
| `zh` | 中文（简体） | Existing | Existing |
| `zh-Hant` | 中文（繁體） | Existing | Existing |
| `pt` | Português (Brasil) | Existing | Existing |
| `pt-PT` | Português (Portugal) | Existing | Existing |
| `ca` | Català | Existing | Existing |
| `eu` | Euskara | Existing | Existing |
| `gn` | Avañe'ẽ | Existing | Existing |
| `quz` | Runa Simi | Existing | Existing |
| `cmn-Hans` | 普通话 | Added | Existing |
| `yue-Hant` | 粵語 | Added | Existing |
| `ko` | 한국어 | Omitted | Existing |
| `ach` | Acholi | Added | Added |
| `aa` | Qafar | Omitted | Added |
| `af` | Afrikaans | Added | Added |
| `sq` | shqip | Added | Added |
| `alz` | Alur | Omitted | Omitted |
| `am` | አማርኛ | Added | Added |
| `ar` | العربية | Added | Added |
| `hy` | հայերեն | Added | Added |
| `az` | azərbaycan | Added | Added |
| `bm` | bamanakan | Added | Added |
| `bci` | Baɔlɛ . | Omitted | Omitted |
| `bts` | Batak Simalungun | Added | Added |
| `be` | беларуская | Added | Added |
| `bn` | বাংলা | Added | Added |
| `bew` | Betawi | Added | Added |
| `bik` | Bikol | Omitted | Added |
| `bs` | bosanski | Added | Added |
| `br` | brezhoneg | Omitted | Omitted |
| `bg` | български | Added | Added |
| `bua` | буряад | Added | Added |
| `ceb` | Cebuano | Omitted | Omitted |
| `ch` | Chamorro | Omitted | Added |
| `ny` | Chichewa | Omitted | Omitted |
| `cv` | чӑваш чӗлхи | Added | Added |
| `co` | Corsu | Added | Added |
| `hr` | hrvatski | Added | Added |
| `cs` | čeština | Added | Added |
| `da` | dansk | Added | Added |
| `dov` | Dombe | Added | Added |
| `dyu` | Diyula | Omitted | Omitted |
| `eo` | Esperanto | Added | Added |
| `et` | eesti | Added | Added |
| `ee` | eʋegbe | Added | Added |
| `fil` | Filipino | Omitted | Omitted |
| `fi` | suomi | Added | Added |
| `fon` | Fɔn | Omitted | Omitted |
| `fr-CA` | français canadien | Omitted | Added |
| `fy` | Frysk | Added | Added |
| `gl` | galego | Omitted | Omitted |
| `ka` | ქართული | Added | Added |
| `el` | Ελληνικά | Added | Added |
| `gu` | ગુજરાતી | Added | Added |
| `ht` | Kreyòl ayisyen | Added | Added |
| `cnh` | Hakha Chin | Added | Added |
| `ha` | Hausa | Added | Omitted |
| `haw` | ʻŌlelo Hawaiʻi | Omitted | Added |
| `he` | עברית | Added | Added |
| `hil` | Hiligaynon | Omitted | Added |
| `hi` | हिन्दी | Added | Added |
| `hmn` | hmoob | Omitted | Added |
| `hu` | magyar | Added | Added |
| `is` | íslenska | Added | Added |
| `ilo` | Ilocano | Omitted | Added |
| `id` | Indonesia | Added | Added |
| `ga` | Gaeilge | Added | Added |
| `jv` | Jawa | Added | Added |
| `kn` | ಕನ್ನಡ | Added | Added |
| `pam` | Kapampangan | Omitted | Added |
| `kk` | қазақ тілі | Added | Added |
| `km` | ខ្មែរ | Added | Added |
| `gom` | कोंकणी | Omitted | Omitted |
| `kri` | Krio, we de na di wɔl | Omitted | Added |
| `ku` | kurdî (kurmancî) | Added | Added |
| `ckb` | کوردیی ناوەندی | Omitted | Omitted |
| `ky` | кыргызча | Added | Added |
| `lo` | ລາວ | Omitted | Added |
| `ltg` | Latgalīšu . | Omitted | Omitted |
| `lv` | latviešu | Added | Added |
| `li` | Limburges | Added | Added |
| `ln` | lingála | Omitted | Added |
| `lt` | lietuvių | Added | Added |
| `lg` | Luganda | Added | Added |
| `lb` | Lëtzebuergesch | Added | Added |
| `mk` | македонски | Added | Added |
| `mad` | Bhâsa Madhurâ | Omitted | Added |
| `mak` | Makassar | Omitted | Added |
| `mg` | Malagasy | Omitted | Omitted |
| `ms` | Melayu | Added | Added |
| `ms-Arab` | ملايو ﴿جاوي﴾ | Omitted | Added |
| `ml` | മലയാളം | Added | Added |
| `mam` | Mam | Omitted | Omitted |
| `mi` | Māori | Added | Added |
| `mr` | मराठी | Added | Added |
| `mh` | Ri-Ṃajeḷ | Omitted | Omitted |
| `mfe` | kreol morisien | Added | Added |
| `chm` | Луговой марий | Added | Added |
| `lus` | Mizo | Omitted | Added |
| `mn` | монгол | Added | Added |
| `nhe` | Nahuatl (Huasteca Oriental) | Omitted | Omitted |
| `nr` | IsiNdebele (Sewula) | Added | Added |
| `ne` | नेपाली | Added | Added |
| `no` | norsk | Added | Added |
| `oc` | occitan | Omitted | Added |
| `om` | Oromoo | Omitted | Added |
| `os` | ирон | Added | Added |
| `pag` | Pangasinan | Omitted | Added |
| `pap` | Papiamentu | Added | Added |
| `ps` | پښتو | Added | Added |
| `fa` | فارسی | Added | Added |
| `pl` | polski | Omitted | Added |
| `pa` | ਪੰਜਾਬੀ (ਗੁਰਮੁਖੀ) | Added | Added |
| `rom` | Romani | Added | Added |
| `ro` | română | Added | Added |
| `se` | davvisámegiella | Omitted | Added |
| `sm` | Samoa | Added | Added |
| `sa` | संस्कृत भाषा | Added | Added |
| `gd` | Gàidhlig | Omitted | Omitted |
| `nso` | Sesotho sa Leboa | Omitted | Added |
| `st` | Sesotho | Added | Added |
| `sd` | سنڌي | Omitted | Added |
| `si` | සිංහල | Added | Added |
| `sk` | slovenčina | Added | Added |
| `sl` | slovenščina | Added | Added |
| `so` | Soomaali | Added | Added |
| `su` | Basa Sunda | Added | Added |
| `sw` | Kiswahili | Added | Added |
| `sv` | svenska | Added | Added |
| `tg` | тоҷикӣ | Added | Added |
| `ta` | தமிழ் | Added | Added |
| `te` | తెలుగు | Omitted | Omitted |
| `tet` | Tetum . | Added | Added |
| `th` | ไทย | Added | Added |
| `bo` | བོད་སྐད་ | Omitted | Omitted |
| `ti` | ትግርኛ | Added | Added |
| `tpi` | Tok Pisin | Omitted | Added |
| `to` | lea fakatonga | Omitted | Omitted |
| `lua` | Tshiluba | Omitted | Added |
| `ts` | Vatsonga | Omitted | Added |
| `tr` | Türkçe | Added | Added |
| `tyv` | Тыва | Added | Added |
| `ak` | Akan | Omitted | Added |
| `udm` | Удмурт | Added | Added |
| `uk` | українська | Added | Added |
| `uz` | o‘zbek | Omitted | Omitted |
| `vec` | veneto | Omitted | Added |
| `vi` | Tiếng Việt | Added | Added |
| `cy` | Cymraeg | Added | Added |
| `xh` | IsiXhosa | Added | Added |
| `sah` | саха тыла | Added | Added |
| `yo` | Èdè Yorùbá | Added | Added |
| `yua` | Maaya Yucateca | Omitted | Omitted |
| `zu` | isiZulu | Added | Added |
| `brx` | बर’ | Omitted | Omitted |
| `dsb` | dolnoserbšćina | Omitted | Omitted |
| `hne` | छत्तीसगढ़ी | Omitted | Omitted |
| `hsb` | hornjoserbšćina | Omitted | Omitted |
| `ikt` | Inuinnaqtun | Omitted | Omitted |
| `mww` | Hmoob Daw | Omitted | Omitted |
| `otq` | Hingar ñhöñhö | Omitted | Omitted |
| `tlh-Latn` | tlhIngan Hol (latin) | Omitted | Omitted |
| `arz` | العربية المصرية | Omitted | Omitted |
| `nn` | norsk nynorsk | Omitted | Omitted |
| `sc` | sardu | Omitted | Omitted |
| `sr-Latn` | srpski (latinica) | Omitted | Omitted |
| `ydd` | ייִדיש | Omitted | Omitted |
