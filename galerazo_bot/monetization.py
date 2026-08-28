from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import timedelta


STARS_CURRENCY = "XTR"
CLUB_SUBSCRIPTION_PERIOD = timedelta(days=30)
PAYMENT_PAYLOAD_VERSION = "h1"


@dataclass(frozen=True)
class PaidHisopo:
    key: str
    name: str
    description: str
    price_stars: int
    image_name: str
    accent: str


@dataclass(frozen=True)
class PaymentIntent:
    kind: str
    item_key: str
    user_id: str
    source_chat_id: str | None


@dataclass(frozen=True)
class InvoiceSpec:
    title: str
    description: str
    amount_stars: int
    reward_hisopo_key: str | None = None
    subscription_period: timedelta | None = None


PAID_HISOPOS: tuple[PaidHisopo, ...] = (
    PaidHisopo(
        "poop",
        "Hisopo de Caca",
        "Una edición marrón, brillante y orgullosamente ridícula.",
        35,
        "hisopo-de-caca.png",
        "#9a673d",
    ),
    PaidHisopo(
        "serene",
        "Hisopo Sereno",
        "Una edición calma de aura verde salvia.",
        50,
        "hisopo-sereno.png",
        "#9cab84",
    ),
    PaidHisopo(
        "crimson",
        "Hisopo Carmesí",
        "Una edición de terciopelo rojo y carácter intenso.",
        75,
        "hisopo-carmesi.png",
        "#b34b62",
    ),
    PaidHisopo(
        "colossal",
        "Hisopo Colosal",
        "Una pieza monumental de grafito y bronce.",
        100,
        "hisopo-colosal.png",
        "#a98b69",
    ),
    PaidHisopo(
        "massive",
        "Hisopo Masivo",
        "Dos brazos, dos bíceps y cero puntos extra.",
        150,
        "hisopo-masivo.png",
        "#d09a62",
    ),
    PaidHisopo(
        "bacteriophage",
        "Hisopo Bacteriófago",
        "Una rareza microscópica de cápside y fibras bioluminiscentes.",
        200,
        "hisopo-bacteriofago.png",
        "#53b7ad",
    ),
    PaidHisopo(
        "world",
        "Hisopo Mundial",
        "Un coleccionable orbital con la Tierra de fondo.",
        250,
        "hisopo-mundial.png",
        "#36b8c6",
    ),
    PaidHisopo(
        "invisible",
        "Hisopo Invisible",
        "No se ve porque, efectivamente, es invisible.",
        300,
        "hisopo-invisible.png",
        "#64717c",
    ),
    PaidHisopo(
        "isotope",
        "Isótopo",
        "La variante atómica del universo Hisopo.",
        350,
        "hisopo-isotopo.png",
        "#4ca9e8",
    ),
    PaidHisopo(
        "infinite",
        "Hisopo Infinito",
        "Una edición cósmica envuelta en un lazo interminable.",
        500,
        "hisopo-infinito.png",
        "#8c78dc",
    ),
    PaidHisopo(
        "quasar",
        "Hisopo Cuásar",
        "Una pieza galáctica atravesada por chorros de luz.",
        650,
        "hisopo-cuasar.png",
        "#7669d6",
    ),
    PaidHisopo(
        "big_bang",
        "Hisopo Big Bang",
        "El nacimiento de un universo concentrado en un Hisopo.",
        1000,
        "hisopo-big-bang.png",
        "#d38362",
    ),
    PaidHisopo(
        "dengue",
        "Hisopo Dengue",
        "La edición suprema de marcas Aedes y probóscide, en honor al Licenciado Dengue.",
        5000,
        "hisopo-dengue.png",
        "#d7d2c7",
    ),
)
PAID_HISOPO_BY_KEY = {hisopo.key: hisopo for hisopo in PAID_HISOPOS}

CLUB_HISOPO = PaidHisopo(
    "stellar",
    "Hisopo Estelar",
    "Edición exclusiva que acredita cada período pagado del Club del Hisopo.",
    100,
    "hisopo-estelar.png",
    "#d5aa55",
)

DONATION_TIERS: tuple[int, ...] = (25, 100, 500)


class PaymentPayloadError(ValueError):
    """The invoice payload is malformed, forged or belongs to another user."""


def invoice_spec(kind: str, item_key: str) -> InvoiceSpec:
    if kind == "donation" and item_key.isascii() and item_key.isdecimal():
        amount = int(item_key)
        if amount in DONATION_TIERS:
            return InvoiceSpec(
                "Aporte a Galerazo Bot",
                "Apoyo voluntario. No compra puntos ni ventajas.",
                amount,
            )
    if kind == "product" and item_key in PAID_HISOPO_BY_KEY:
        product = PAID_HISOPO_BY_KEY[item_key]
        return InvoiceSpec(
            product.name,
            f"Hisopo cosmético permanente. {product.description}",
            product.price_stars,
            reward_hisopo_key=product.key,
        )
    if kind == "subscription" and item_key == "club":
        return InvoiceSpec(
            "Club del Hisopo",
            "Membresía renovable cada 30 días con una edición Estelar por período pagado.",
            CLUB_HISOPO.price_stars,
            reward_hisopo_key=CLUB_HISOPO.key,
            subscription_period=CLUB_SUBSCRIPTION_PERIOD,
        )
    raise PaymentPayloadError("El producto de Stars no existe.")


def create_payment_payload(
    bot_token: str,
    *,
    kind: str,
    item_key: str,
    user_id: str,
    source_chat_id: str | None = None,
) -> str:
    invoice_spec(kind, item_key)
    chat_value = source_chat_id or "0"
    unsigned = ":".join((PAYMENT_PAYLOAD_VERSION, kind, item_key, user_id, chat_value))
    signature = _signature(bot_token, "payment", unsigned)
    payload = f"{unsigned}:{signature}"
    if len(payload.encode("utf-8")) > 128:  # Telegram's invoice payload limit.
        raise PaymentPayloadError("El identificador del pago supera el límite de Telegram.")
    return payload


def parse_payment_payload(
    bot_token: str,
    payload: str,
    *,
    expected_user_id: str | None = None,
) -> PaymentIntent:
    parts = payload.split(":")
    if len(parts) != 6:
        raise PaymentPayloadError("El identificador del pago no es válido.")
    version, kind, item_key, user_id, chat_value, signature = parts
    unsigned = ":".join(parts[:-1])
    expected_signature = _signature(bot_token, "payment", unsigned)
    if version != PAYMENT_PAYLOAD_VERSION or not hmac.compare_digest(signature, expected_signature):
        raise PaymentPayloadError("La firma del pago no es válida.")
    if expected_user_id is not None and user_id != expected_user_id:
        raise PaymentPayloadError("Este pago fue creado para otra persona.")
    invoice_spec(kind, item_key)
    return PaymentIntent(
        kind=kind,
        item_key=item_key,
        user_id=user_id,
        source_chat_id=None if chat_value == "0" else chat_value,
    )


def create_album_context(bot_token: str, *, chat_id: str, user_id: str) -> str:
    unsigned = f"a1.{chat_id}.{user_id}"
    return f"{unsigned}.{_signature(bot_token, 'album', unsigned)}"


def parse_album_context(bot_token: str, value: str, *, expected_user_id: str) -> str:
    parts = value.split(".")
    if len(parts) != 4:
        raise ValueError("El contexto del álbum no es válido.")
    version, chat_id, user_id, signature = parts
    unsigned = ".".join(parts[:-1])
    expected = _signature(bot_token, "album", unsigned)
    if version != "a1" or user_id != expected_user_id or not hmac.compare_digest(signature, expected):
        raise ValueError("El contexto del álbum no es válido.")
    return chat_id


def _signature(bot_token: str, domain: str, value: str) -> str:
    key = hashlib.sha256(f"galerazo:{domain}:{bot_token}".encode("utf-8")).digest()
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
