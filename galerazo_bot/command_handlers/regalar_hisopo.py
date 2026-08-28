from __future__ import annotations

import re
import unicodedata

from ..command_model import Command
from ..database import Database
from ..monetization import CLUB_HISOPO, PAID_HISOPOS, PaidHisopo
from ..roles import CommandContext, UserLevel


GIFTABLE_HISOPOS = (*PAID_HISOPOS, CLUB_HISOPO)
GIFT_TYPE_HINTS = (
    "caca",
    "sereno",
    "carmesi",
    "colosal",
    "masivo",
    "bacteriofago",
    "mundial",
    "invisible",
    "isotopo",
    "infinito",
    "cuasar",
    "bigbang",
    "dengue",
    "estelar",
)


def _normalize_selector(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .casefold()
    )
    return re.sub(r"[^a-z0-9]+", "", ascii_value)


def _build_aliases() -> dict[str, PaidHisopo]:
    aliases: dict[str, PaidHisopo] = {}
    for hisopo in GIFTABLE_HISOPOS:
        normalized_name = _normalize_selector(hisopo.name)
        aliases[_normalize_selector(hisopo.key)] = hisopo
        aliases[normalized_name] = hisopo
        if normalized_name.startswith("hisopo"):
            aliases[normalized_name.removeprefix("hisopo")] = hisopo
    aliases.update(
        {
            "caca": next(item for item in GIFTABLE_HISOPOS if item.key == "poop"),
            "estelar": CLUB_HISOPO,
            "estrella": CLUB_HISOPO,
        }
    )
    return aliases


HISOPO_BY_GIFT_ALIAS = _build_aliases()


def handle(context: CommandContext, db: Database) -> str:
    if context.chat_type != "private":
        return "Usá este comando únicamente en el chat privado del bot."
    parts = context.args.split()
    available = ", ".join(GIFT_TYPE_HINTS)
    if len(parts) != 2:
        return f"Uso: /regalarhisopo tipo user_id\nTipos: {available}"
    selector, recipient_user_id = parts
    hisopo = HISOPO_BY_GIFT_ALIAS.get(_normalize_selector(selector))
    if hisopo is None:
        return f"Ese tipo de Hisopo no existe. Tipos: {available}"
    if not recipient_user_id.isascii() or not recipient_user_id.isdecimal() or int(recipient_user_id) <= 0:
        return "El user_id debe ser un entero positivo de Telegram."
    quantity = db.grant_paid_hisopo(
        recipient_user_id=recipient_user_id,
        hisopo_key=hisopo.key,
        gifted_by_user_id=context.sender_id,
    )
    return (
        f"Regalaste un {hisopo.name} a {recipient_user_id}. "
        f"Ahora tiene {quantity} en su colección cosmética global."
    )


COMMANDS = {
    "regalarhisopo": Command(
        "regalarhisopo",
        "acredita un Hisopo cosmético a un usuario",
        handle,
        UserLevel.DEV,
        hidden=True,
    )
}
