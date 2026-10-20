from __future__ import annotations

import re
import unicodedata

from ..command_model import Command
from ..commerce_i18n import cosmetic_name
from ..database import Database
from ..monetization import CLUB_HISOPO, PAID_HISOPOS, PaidHisopo
from ..roles import CommandContext, UserLevel


GIFTABLE_HISOPOS = (*PAID_HISOPOS, CLUB_HISOPO)
GIFT_TYPE_HINTS = (
    "mini",
    "caca",
    "pico",
    "pala",
    "sereno",
    "gota",
    "carmesi",
    "rosaceo",
    "colosal",
    "alfiler",
    "masivo",
    "bacteriofago",
    "mundial",
    "invisible",
    "isotopo",
    "infinito",
    "cuasar",
    "bigbang",
    "dengue",
    "galerazo",
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
        return context.t("gift.private_only")
    parts = context.args.split()
    available = ", ".join(GIFT_TYPE_HINTS)
    if len(parts) != 2:
        return context.t("gift.usage", types=available)
    selector, recipient_user_id = parts
    hisopo = HISOPO_BY_GIFT_ALIAS.get(_normalize_selector(selector))
    if hisopo is None:
        return context.t("gift.invalid_type", types=available)
    if not recipient_user_id.isascii() or not recipient_user_id.isdecimal() or int(recipient_user_id) <= 0:
        return context.t("gift.invalid_recipient")
    quantity = db.grant_paid_hisopo(
        recipient_user_id=recipient_user_id,
        hisopo_key=hisopo.key,
        gifted_by_user_id=context.sender_id,
    )
    return context.t("gift.confirmed", name=cosmetic_name(hisopo, context.language),
                     recipient=recipient_user_id, quantity=quantity)


COMMANDS = {
    "regalarhisopo": Command(
        "regalarhisopo",
        "acredita un Hisopo especial a un usuario",
        handle,
        UserLevel.DEV,
        hidden=True,
    )
}
