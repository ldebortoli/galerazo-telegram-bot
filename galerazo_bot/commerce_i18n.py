"""Presentation of payments; canonical prices, rewards and payloads stay unchanged."""
from dataclasses import replace

from .language_catalogs import CATALOGS
from .monetization import PaidHisopo, InvoiceSpec, invoice_spec

COMMERCE = CATALOGS["commerce"]
COMMERCE_ALIASES = CATALOGS["commerceAliases"]


def is_commerce_language(language: object) -> bool:
    return isinstance(language, str) and language in COMMERCE_ALIASES


def commerce_language(language: object) -> str:
    return COMMERCE_ALIASES.get(language, "es") if isinstance(language, str) else "es"


def commerce_text(language: object, key: str, **values) -> str:
    return COMMERCE[commerce_language(language)]["text"][key].format(**values)


def cosmetic_name(product: PaidHisopo, language: object) -> str:
    locale = commerce_language(language)
    if locale in {"es", "es_ES"}:
        return product.public_name
    key = "special-67" if product.key == "dengue" else product.key
    return COMMERCE[locale]["products"][key][0]


def localized_invoice_spec(kind: str, item_key: str, language: object) -> InvoiceSpec:
    spec = invoice_spec(kind, item_key)
    locale = commerce_language(language)
    if locale in {"es", "es_ES"}:
        return spec
    if kind == "donation":
        return replace(spec, title=commerce_text(locale, "donation_title"), description=commerce_text(locale, "donation_description"))
    if kind == "subscription":
        return replace(spec, description=commerce_text(locale, "club_description"))
    key = "special-67" if item_key == "dengue" else item_key
    name, description = COMMERCE[locale]["products"][key]
    description = commerce_text(locale, "permanent_description", description=description)
    # Telegram caps invoice titles at 32 characters. Keep the entire item name
    # in the description when the brand must occupy the short title.
    if len(name) > 32:
        return replace(spec, title="Galerazo Bot", description=name + ". " + description)
    return replace(spec, title=name, description=description)


def payment_language(db, user_id: str, chat_id: str) -> str:
    default = db.get_chat_settings(chat_id).language
    return commerce_language(db.get_payment_language(user_id, default))
