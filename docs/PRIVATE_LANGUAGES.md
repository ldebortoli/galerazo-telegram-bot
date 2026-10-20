# Inventario privado de 250 referencias · 2026-10-20

Fuentes 0.80/0.1.27: **139 idiomas del bot (+27) y 192 de Mini App (+52)**.
Se evaluaron las 250 opciones instaladas, idénticas en Linterna PREMIUM y Gemidos
PREMIUM. La referencia congelada y sus hashes están en `LANGUAGE-REFERENCE-250.json`;
`PRIVATE-LANGUAGE-INVENTORY-250-20261020.json` registra cada admisión/exclusión,
campos y causas. Se preservan las 112/140 opciones anteriores y sus códigos,
incluido el alias explícito `pa`→`pa-Guru`. No se modifica la portada pública de 176 opciones.

Los 111 candidatos excluidos del bot y 58 de Mini App siguen fuera del selector.
Se intentaron reparaciones protegidas y con contexto para variables, comandos,
HTML, URLs, cifras, textos de compra y fragmentos fuente, usando sólo texto
estático del repositorio y el endpoint público existente. No se reintenta Bing HTTP401,
no se envían datos de visitantes y no hay traducción remota en runtime.

La admisión exige 316 mensajes del bot o 88 textos de UI/18 nombres naturales/21
pares de productos, además del comercio propio de 12 plantillas y facturas válidas.
Marcas, comandos, unidades (`pt`), tecnicismos y cognados comprobados no son
relleno. Para opciones nuevas se usa la etiqueta inequívoca GitHub en su enlace
al repositorio. Los títulos conservan marca y encabezado traducido al normalizar
el separador. No se recortan reglas ni se eliminan cantidades para superar límites.
Se corrigieron además 131 campos de 76 idiomas ya habilitados en la Mini App,
incluidos cinco nombres de compra y un nombre natural turcos. La guardia contra
el sustantivo inglés `swab` recorre todos los catálogos habilitados. CLDR sólo se
usa cuando su escritura resuelta coincide con la solicitada; NKo conserva NKo.
Las coincidencias dudosas de términos sin revisión suficiente permanecen excluidas;
el recibo no afirma que una lengua carezca de esos términos o sea intraducible.

Las traducciones admitidas son automáticas, con aviso localizado y sin certificación
nativa. CLDR aporta exónimos cuando existen; en otros casos se conserva el autónimo
con una etiqueta de idioma localizada, sin heredar el idioma del sistema.
Los nuevos idiomas privados sin portada pública vuelven a una ruta existente;
URL/localStorage conservan su idioma para regresar a la Mini App.

Validación final: bot 718 pruebas/100% (6748 sentencias y 2084 ramas); web 77 privadas,
98 Node completas y 203 Vitest públicas con 100% en las métricas disponibles. Build 354
representaciones públicas/176 idiomas, check e índice LF/autocrlf=true correctos.
Chrome local: 192 idiomas×320/768/1440,36864 etiquetas por ancho; datos finales con
movimiento reducido, texto 200%, NKo/árabe, errores/persistencia y viewport reducido.
Detalle auditable: `TRANSLATION-250-VALIDATION-20261020.json`.

Los idiomas nuevos de facturas requieren desplegar Galerazobot 0.80 junto a
Mini App 0.1.27: backend 0.77 no contiene esos catálogos.

Entrega de código: no incluye despliegue, reinicio productivo, broadcast ni compras.
El borrador editorial 0.80 cubre desde 0.77 y sigue sin aprobación. Los recibos 17/10
que siguen son históricos; las pruebas activas usan el inventario vigente de 250 opciones.

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

## Required language review for every change

Standing request from Lucas, 2026-10-20: every addition or modification must
consider every language enabled in Galerazobot. Read the current
`galerazo_bot.language_catalogs.LANGUAGE_OPTIONS` inventory (139 options today),
not a fixed Spanish/English subset or the global nine-language default. If the
change touches the Mini App, review its complete current inventory too (192
options today), in the sibling frontend project.

Update all affected user-facing text in the same delivery: command responses,
help, menus, buttons, callback popups, errors, game rules/results, item names,
payment text and announcements. Check key and placeholder parity, invariant
commands/URLs, HTML, Unicode, Telegram size limits and, where relevant, RTL/LTR,
pagination and saved language selection. A Spanish/English fallback does not
complete a translation. Keep explicit legacy limitations recorded as blocked;
do not claim they are fixed or add empty catalogs to satisfy a gate.

Before completion, run the relevant language tests across the complete enabled
inventory and record the outcome. For a change without localized content,
record that impact assessment. The existing bot regression set is:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_i18n.py tests/test_private_language_inventory.py tests/test_language_inventory_250.py tests/test_translation_completeness.py tests/test_language_pagination.py tests/test_commerce_languages.py tests/test_release_broadcast.py
```

Select additional domain tests for the behavior changed. This policy does not
require a production deployment, Telegram send or paid translation service.

## Existing-content audit · 2026-10-20

Source versions: bot0.79 and Mini App0.1.26. The enabled inventories remain
112 and140 options respectively. `TRANSLATION-AUDIT-20261020.json` records the
scope and validation. This supersedes the legacy payment exception below.

- Help, donation/privacy/payment prose, gift responses and role labels have local
  text throughout the bot inventory. Latin, Japanese, Southern Quechua and Korean
  invoices now use their own catalogs. No locale aliases a Spanish payment catalog.
- Corrected embedded source phrases in UI, rules, natural items and products.
  Language selectors use CLDR exonyms; where CLDR has no exonym, a localized
  language label accompanies the verified autonym. Afar/Ewe/Basque labels retain
  their linguistic identity. Numbers, URLs, commands, SKUs and brands stay invariant.
- Per-chat Telegram command scopes and the private Mini App button follow the
  selected bot language, including three-letter locales. Global es/en scopes stay
  as the compatibility defaults; development commands remain hidden.
- Mini App language changes keep gift names, in-flight purchase errors and privacy
  state coherent. Errors appear at their initiating action and disappear on retry.
  Unsupported Intl date locales use ISO dates rather than the host language.
- Optional `name_fallback`/`title_fallback` metadata distinguishes generated user and
  group labels from authored names. Public unnamed donors alone receive a fallback
  ID; anonymous donors expose no ID. Older backend payloads remain accepted; full
  generated-name localization requires rollout of both sources.

Acquisition sends only static repository text to the existing public Google
Translate consumer endpoint. Protected literals and variables are checked before
atomic writes; targeted Southern Quechua and label corrections supplement it.
These are automatic translations, without native-speaker certification. User-authored
names and announcement bodies, including previously approved release broadcasts,
retain their original text. Their surrounding application UI is localized. The
Spanish initial HTML/noscript is the default shell; selected language is applied by
JavaScript, which the private Telegram app requires.

No deployment, production restart, new Telegram message, purchase or billing change
is part of this audit. Release editorial approval remains pending. Real Telegram
initData, native screen readers and a real mobile keyboard remain outside the local
fixture harness. No remote CI polling is required.

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
- Historical exception (resolved by the 2026-10-20 audit): la, ja, quz and ko
  previously reused Spanish payment presentation. All four now use own catalogs;
  this does not certify native linguistic quality.

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

Historical expansion snapshot from 2026-10-17 follows; current production
operations are documented in [DEPLOY_VPS.md](DEPLOY_VPS.md).
Source versions were bot0.76 and web0.1.23. That run authorized no deployment, backend
restart or Telegram announcement. Publication remains behind the existing BCC flow,
release authorization and editorial broadcast approval. Code readiness is not production
activation; verified production at that date was bot0.68/web0.1.22.

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
