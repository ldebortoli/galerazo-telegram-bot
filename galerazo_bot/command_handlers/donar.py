from __future__ import annotations

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext


def handle(context: CommandContext, _db: Database):
    if context.send_donation_menu is None:
        return context.t("donation.text")
    return _send_menu(context)


async def _send_menu(context: CommandContext) -> str | None:
    if not await context.send_donation_menu():
        return context.t("donation.send_failed")
    return None


def handle_donors(context: CommandContext, db: Database) -> str:
    visibility = context.args.casefold().strip()
    if visibility in {"publico", "público", "public"}:
        db.set_donor_display_public(context.sender_id, True)
        return context.t("donors.public")
    if visibility in {"anonimo", "anónimo", "privado", "anonymous", "private"}:
        db.set_donor_display_public(context.sender_id, False)
        return context.t("donors.anonymous")
    entries = db.get_donor_leaderboard()
    if not entries:
        return context.t("donors.empty")
    lines = [context.t("donors.header")]
    for position, entry in enumerate(entries, start=1):
        if entry.display_public:
            name = entry.display_name or (f"@{entry.username}" if entry.username else f"ID {entry.user_id}")
        else:
            name = context.t("donors.hidden_name")
        lines.append(f"{position}. {name} — ⭐ {entry.amount_stars}")
    lines.extend(("", context.t("donors.privacy_hint")))
    return "\n".join(lines)


def handle_support(context: CommandContext, _db: Database) -> str:
    return context.t("payments.support")


def handle_terms(context: CommandContext, _db: Database) -> str:
    return context.t("payments.terms")


COMMANDS = {
    "donar": Command("donar", "muestra como apoyar al bot", handle),
    "donantes": Command("donantes", "muestra el top de colaboradores", handle_donors),
    "paysupport": Command("paysupport", "muestra la ayuda para pagos", handle_support),
    "terminos": Command("terminos", "muestra las condiciones de compras y membresía", handle_terms),
}
