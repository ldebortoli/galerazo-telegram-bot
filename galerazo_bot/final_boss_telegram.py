"""Telegram presentation for the persistent cooperative Final Boss."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.error import BadRequest

from .final_boss import BossActionResult, BossState, FinalBossStore
from .hisopos import random_next_day_datetime
from .i18n import t
from .pagination import build_keyboard, build_pages


BOSS_PREFIX = "hisopo:boss"
REFRESH_SECONDS = 3


def boss_file_id(settings, phase: int = 1, won: bool = False, lost: bool = False) -> str:
    suffix = "victorious" if lost else "defeated" if won else f"phase_{phase}"
    value = getattr(settings, f"telegram_hisopo_final_boss_{suffix}_file_id")
    if not value:
        raise ValueError(f"Falta configurar TELEGRAM_HISOPO_FINAL_BOSS_{suffix.upper()}_FILE_ID.")
    return value


def parse_boss_callback(data: str) -> tuple[int, int | None] | None:
    parts = data.split(":")
    if len(parts) not in (3, 4) or parts[:2] != ["hisopo", "boss"]:
        return None
    try:
        phase = int(parts[2])
        slot = int(parts[3]) if len(parts) == 4 else None
    except ValueError:
        return None
    if phase in (1, 2) and slot is None:
        return phase, None
    if phase in (3, 4) and slot is not None and 0 <= slot < 20:
        return phase, slot
    return None


def boss_keyboard(language: str, phase: int, current: int = 0,
                  required: int = 1, used_slots: tuple[int, ...] = ()) -> InlineKeyboardMarkup:
    if phase in (1, 2):
        key = "boss.help_button" if phase == 1 else "boss.tap_button"
        return InlineKeyboardMarkup([[InlineKeyboardButton(
            t(language, key, current=current, required=required),
            callback_data=f"{BOSS_PREFIX}:{phase}",
        )]])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{'✓ ' if slot in used_slots else ''}{slot + 1}",
            callback_data=f"{BOSS_PREFIX}:{phase}:{slot}",
        ) for slot in range(start, start + 5)]
        for start in range(0, 20, 5)
    ])


def boss_presentation(boss: BossState, language: str) -> tuple[str, InlineKeyboardMarkup | None]:
    if boss.status == "won":
        return t(language, "boss.won_caption", participants=len(boss.participant_user_ids)), None
    if boss.status == "lost":
        caption = t(language, "boss.lost_caption", phase=boss.phase,
                    reason=t(language, f"boss.reason.{boss.reason}"))
        return caption, None
    counts = {1: len(boss.phase1_users), 2: boss.phase2_total, 3: boss.phase3_count, 4: 0}
    targets = {1: boss.required_helpers, 2: 1000, 3: 20, 4: 20}
    minutes = {1: 60, 2: 30, 3: 30, 4: 10}
    caption = t(language, f"boss.phase{boss.phase}_caption", current=counts[boss.phase],
                required=targets[boss.phase], minutes=minutes[boss.phase],
                clue=3 * (boss.safe_slot + 1) + 7)
    return caption, boss_keyboard(language, boss.phase, counts[boss.phase], targets[boss.phase],
                                   tuple(slot for slot, _ in boss.phase3_slots) if boss.phase == 3 else ())


def queue_boss_refresh(application, chat_id: str, message_id: str, *, immediate: bool = False) -> None:
    key = (chat_id, message_id)
    pending = application.bot_data.setdefault("boss_refresh_pending", set())
    name = f"boss-refresh:{chat_id}:{message_id}"
    if key in pending:
        if not immediate:
            return
        for job in application.job_queue.get_jobs_by_name(name):
            job.schedule_removal()
    pending.add(key)
    application.job_queue.run_once(
        refresh_boss_job, when=0 if immediate else REFRESH_SECONDS,
        data={"chat_id": chat_id, "message_id": message_id}, name=name,
    )


async def handle_boss_callback(application, callback_query, user_id: str, spawn,
                               language: str, now: datetime, schedule_expiration,
                               schedule_appearance) -> BossActionResult:
    parsed = (1, None) if callback_query.data == "hisopo:capture" else parse_boss_callback(callback_query.data or "")
    if parsed is None:
        await callback_query.answer(t(language, "hisopos.unavailable_alert"), show_alert=True)
        return BossActionResult("invalid", None)
    store = FinalBossStore(application.bot_data["state"].db)
    result = store.contribute(
        spawn.chat_id, spawn.message_id, user_id, callback_query.id,
        parsed[0], now, parsed[1], next_scheduled_for=random_next_day_datetime(now),
    )
    if result.status == "advanced":
        schedule_expiration(application, store.db.get_hisopo_spawn(spawn.chat_id, spawn.message_id))
    if result.schedule is not None:
        schedule_appearance(application, result.schedule)
    if result.status in {"joined", "advanced", "won", "lost", "finished", "stale"}:
        queue_boss_refresh(application, spawn.chat_id, spawn.message_id,
                           immediate=result.status != "joined" or parsed[0] != 2)
    keys = {
        "joined": "joined_popup", "advanced": "advanced_popup", "won": "won_popup",
        "lost": "lost_popup", "already_joined": "already_joined_popup",
        "throttled": "throttled_popup", "stale": "stale_popup",
    }
    if result.status == "duplicate":
        await callback_query.answer()
    else:
        key = f"boss.{keys[result.status]}" if result.status in keys else "hisopos.unavailable_alert"
        await callback_query.answer(t(language, key), show_alert=result.status in {"won", "lost", "invalid"})
    return result


async def _announce_result(application, boss: BossState, language: str) -> None:
    state = application.bot_data["state"]
    store = FinalBossStore(state.db)
    if boss.announcement_complete:
        return
    if boss.announcement_message_id is not None:
        saved = state.db.get_paginated_message_state(boss.chat_id, boss.announcement_message_id)
        if saved is not None:
            pages = json.loads(saved.content_json)["pages"]
            await _set_announcement_keyboard(application, boss.chat_id, boss.announcement_message_id, len(pages))
        store.complete_announcement(boss.chat_id, boss.message_id)
        return
    if boss.status == "won":
        header = t(language, "boss.congratulations", group=t(language, "boss.group_label"),
                   participants=len(boss.participant_user_ids))
    else:
        header = t(language, "boss.lost_caption", phase=boss.phase,
                   reason=t(language, f"boss.reason.{boss.reason}"))
    lines = []
    if boss.status == "lost" and boss.offender_user_id is not None:
        offender = state.db.get_user(boss.offender_user_id)
        name = (offender.display_name or offender.username) if offender is not None else None
        label = " ".join((name or boss.offender_user_id).split())[:120]
        lines.append(t(language, "boss.offender", user=f"{label} ({boss.offender_user_id})"))
    if boss.status == "lost" and boss.phase == 4:
        lines.append(t(language, "boss.solution", answer=boss.safe_slot + 1,
                       clue=3 * (boss.safe_slot + 1) + 7))
    for user_id, points in boss.awards:
        user = state.db.get_user(user_id)
        label = (user.display_name or user.username) if user is not None else None
        label = " ".join((label or user_id).split())[:120]
        lines.append(t(language, "boss.score_line", user=f"{label} ({user_id})", points=points))
    if not boss.awards:
        lines.append(t(language, "boss.loss_summary", points=0, participants=0))
    pages = build_pages(header, lines, max_chars=1900)
    sent = await application.bot.send_message(chat_id=int(boss.chat_id), text=pages[0])
    message_id = str(sent.message_id)
    if len(pages) > 1:
        state.db.save_paginated_message_state(
            chat_id=boss.chat_id, message_id=message_id, list_type="boss_rewards",
            requester_user_id="0", content_json=json.dumps({"pages": pages}, ensure_ascii=False),
            unlocked=True, current_page=1,
        )
    store.mark_announced(boss.chat_id, boss.message_id, message_id)
    if len(pages) > 1:
        await _set_announcement_keyboard(application, boss.chat_id, message_id, len(pages))
    store.complete_announcement(boss.chat_id, boss.message_id)


async def _set_announcement_keyboard(application, chat_id: str, message_id: str, total_pages: int) -> None:
    try:
        await application.bot.edit_message_reply_markup(
            chat_id=int(chat_id), message_id=int(message_id),
            reply_markup=build_keyboard(message_id, 1, total_pages, unlocked=True),
        )
    except BadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


async def refresh_boss_job(context) -> None:
    application = context.application
    state = application.bot_data["state"]
    chat_id = state.db.resolve_chat_id(str(context.job.data["chat_id"]))
    message_id = str(context.job.data["message_id"])
    application.bot_data.setdefault("boss_refresh_pending", set()).discard((chat_id, message_id))
    locks = application.bot_data.setdefault("boss_render_locks", {})
    async with locks.setdefault((chat_id, message_id), asyncio.Lock()):
        boss = FinalBossStore(state.db).get(chat_id, message_id)
        if boss is None:
            return
        spawn = state.db.get_hisopo_spawn(chat_id, message_id)
        if boss.status == "active" and spawn.appearance_type == "mystery":
            return
        language = state.db.get_chat_settings(chat_id).language
        caption, keyboard = boss_presentation(boss, language)
        cache = application.bot_data.setdefault("boss_rendered_media", {})
        media_key = (boss.phase, boss.status)
        try:
            if cache.get((chat_id, message_id)) != media_key:
                await application.bot.edit_message_media(
                    chat_id=int(chat_id), message_id=int(message_id),
                    media=InputMediaPhoto(media=boss_file_id(state.settings, boss.phase, boss.status == "won", boss.status == "lost"), caption=caption),
                    reply_markup=keyboard,
                )
                cache[(chat_id, message_id)] = media_key
            else:
                await application.bot.edit_message_caption(
                    chat_id=int(chat_id), message_id=int(message_id), caption=caption, reply_markup=keyboard,
                )
        except BadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise
        if boss.status != "active":
            await _announce_result(application, boss, language)


async def recover_boss_results(context) -> None:
    application = context.application
    db = application.bot_data["state"].db
    store = FinalBossStore(db)
    has_work = False
    for spawn in db.list_active_hisopo_spawns():
        if spawn.hisopo_type == "final_boss":
            has_work = True
            store.expire(spawn.chat_id, spawn.message_id, datetime.now(timezone.utc))
            queue_boss_refresh(application, spawn.chat_id, spawn.message_id, immediate=True)
    for boss in store.get_pending_results():
        has_work = True
        queue_boss_refresh(application, boss.chat_id, boss.message_id, immediate=True)
    if not has_work:
        for job in application.job_queue.get_jobs_by_name("boss-results"):
            job.schedule_removal()


def schedule_boss_recovery(application) -> None:
    if not application.job_queue.get_jobs_by_name("boss-results"):
        application.job_queue.run_repeating(recover_boss_results, interval=60, first=1, name="boss-results")
