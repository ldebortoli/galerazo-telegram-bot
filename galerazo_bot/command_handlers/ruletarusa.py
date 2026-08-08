from __future__ import annotations

import sqlite3

from ..command_model import Command
from ..database import Database
from ..roles import CommandContext, RussianRouletteHitResult, UserLevel


async def ruletarusa(context: CommandContext, db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"} or context.chat_id is None:
        return context.t("roulette.group_only")
    if context.can_run_russian_roulette is None or context.resolve_russian_roulette_hit is None:
        return context.t("roulette.not_configured")
    if not await context.can_run_russian_roulette():
        return context.t("roulette.bot_permissions")

    target_user_id = context.sender_id
    if context.user_level >= UserLevel.ADMIN and context.reply_to_user_id is not None:
        target_user_id = context.reply_to_user_id
        db.get_or_create_user(
            target_user_id,
            context.reply_to_display_name,
            context.reply_to_username,
        )

    shot = db.play_russian_roulette(context.chat_id, target_user_id)
    if not shot.hit:
        if shot.remaining_shots == 1:
            return context.t("roulette.miss_last")
        return context.t("roulette.miss", remaining=shot.remaining_shots)

    result = await context.resolve_russian_roulette_hit(target_user_id)
    result_key = {
        RussianRouletteHitResult.BANNED: "roulette.hit_banned",
        RussianRouletteHitResult.BOT_IMMUNE: "roulette.hit_bot",
        RussianRouletteHitResult.ADMIN_IMMUNE: "roulette.hit_admin",
        RussianRouletteHitResult.DEV_IMMUNE: "roulette.hit_dev",
        RussianRouletteHitResult.FAILED: "roulette.hit_failed",
    }[result]
    return context.t(result_key)


def migrate_chat_data(conn: sqlite3.Connection, old_chat_id: str, new_chat_id: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO russian_roulette_states (
            chat_id, user_id, bullet_position, shots_fired, created_at, updated_at
        )
        SELECT ?, user_id, bullet_position, shots_fired, created_at, CURRENT_TIMESTAMP
        FROM russian_roulette_states
        WHERE chat_id = ?
        """,
        (new_chat_id, old_chat_id),
    )
    conn.execute("DELETE FROM russian_roulette_states WHERE chat_id = ?", (old_chat_id,))


COMMANDS = {
    "ruletarusa": Command(
        "ruletarusa",
        "juega a la ruleta rusa",
        ruletarusa,
        configurable_group="ruletarusa",
    ),
}
