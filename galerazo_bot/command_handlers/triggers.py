from __future__ import annotations

import json

from ..commands import Command
from ..database import Database, Trigger
from ..roles import CommandContext


MIN_TRIGGER_NAME_LENGTH = 5
MAX_TRIGGER_NAME_LENGTH = 32


def agregartrigger(context: CommandContext, db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"}:
        return context.t("triggers.group_only")

    trigger_name = _parse_trigger_name(context)
    if trigger_name is None:
        return context.t("triggers.add_usage")
    if not _is_valid_trigger_name(trigger_name):
        return context.t("triggers.invalid_name")
    if context.chat_id is None:
        return context.t("triggers.group_only")
    if context.reply_to_trigger_payload is None:
        return context.t("triggers.reply_required")
    if not _is_valid_payload(context.reply_to_trigger_payload):
        return context.t("triggers.invalid_message")

    normalized_name = _normalize_trigger_name(trigger_name)
    was_added = db.add_trigger(
        chat_id=context.chat_id,
        trigger_name=normalized_name,
        display_name=trigger_name,
        text=context.reply_to_trigger_payload.text,
        media_type=context.reply_to_trigger_payload.media_type,
        file_id=context.reply_to_trigger_payload.file_id,
        caption=context.reply_to_trigger_payload.caption,
        created_by_user_id=context.sender_id,
        payload_json=(
            json.dumps(context.reply_to_trigger_payload.data, ensure_ascii=False)
            if context.reply_to_trigger_payload.data is not None
            else None
        ),
    )
    if not was_added:
        return context.t("triggers.duplicate", trigger=trigger_name)

    return context.t("triggers.added", trigger=trigger_name)


def borrartrigger(context: CommandContext, db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"}:
        return context.t("triggers.group_only")

    trigger_name = _parse_trigger_name(context)
    if trigger_name is None:
        return context.t("triggers.delete_usage")
    if not _is_valid_trigger_name(trigger_name):
        return context.t("triggers.invalid_name")
    if context.chat_id is None:
        return context.t("triggers.group_only")

    was_deleted = db.delete_trigger(context.chat_id, _normalize_trigger_name(trigger_name))
    if not was_deleted:
        return context.t("triggers.not_found", trigger=trigger_name)
    return context.t("triggers.deleted", trigger=trigger_name)


def triggers(context: CommandContext, db: Database) -> str:
    if context.chat_type not in {"group", "supergroup"}:
        return context.t("triggers.group_only")
    if context.chat_id is None:
        return context.t("triggers.group_only")

    rows = db.list_triggers(context.chat_id)
    if not rows:
        return context.t("triggers.empty")

    lines = [context.t("triggers.header")]
    lines.extend(_trigger_line(row) for row in rows)
    return "\n".join(lines)


def _parse_trigger_name(context: CommandContext) -> str | None:
    trigger_name = " ".join(context.args.split())
    return trigger_name or None


def _is_valid_trigger_name(trigger_name: str) -> bool:
    return MIN_TRIGGER_NAME_LENGTH <= len(trigger_name) <= MAX_TRIGGER_NAME_LENGTH


def _normalize_trigger_name(trigger_name: str) -> str:
    return trigger_name.casefold()


def _is_valid_payload(payload) -> bool:
    return bool(payload.text or payload.file_id or payload.data)


def _trigger_line(trigger: Trigger) -> str:
    return f"- {trigger.display_name}"


COMMANDS = {
    "agregartrigger": Command(
        "agregartrigger",
        "agrega un trigger al grupo",
        agregartrigger,
        configurable_group="triggers",
    ),
    "agrtrigger": Command(
        "agrtrigger",
        "agrega un trigger al grupo",
        agregartrigger,
        command_key="agregartrigger",
        configurable_group="triggers",
    ),
    "borrartrigger": Command(
        "borrartrigger",
        "borra un trigger del grupo",
        borrartrigger,
        configurable_group="triggers",
    ),
    "eliminartrigger": Command(
        "eliminartrigger",
        "borra un trigger del grupo",
        borrartrigger,
        command_key="borrartrigger",
        configurable_group="triggers",
    ),
    "eltrigger": Command(
        "eltrigger",
        "borra un trigger del grupo",
        borrartrigger,
        command_key="borrartrigger",
        configurable_group="triggers",
    ),
    "triggers": Command(
        "triggers",
        "muestra los triggers del grupo",
        triggers,
        configurable_group="triggers",
        list_response=True,
    ),
}
