from __future__ import annotations

import json
import logging
import traceback
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .commands import command_exists, handle_command, is_command_invocation
from .config import load_settings
from .database import Database
from .galeraza import build_galeraza_lines, render_galeraza_page
from .pagination import build_keyboard, parse_callback_data, render_page
from .roles import BackupResult, UserLevel


logger = logging.getLogger(__name__)
TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES = 50 * 1024 * 1024
TELEGRAM_MESSAGE_LIMIT_CHARS = 4096


class TelegramClient:
    def __init__(self, token: str) -> None:
        if not token:
            raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en el archivo .env")
        self.base_url = f"https://api.telegram.org/bot{token}"

    def get_updates(self, offset: int | None) -> list[dict]:
        params = {
            "timeout": 30,
            "allowed_updates": json.dumps(["message", "callback_query", "my_chat_member"]),
        }
        if offset is not None:
            params["offset"] = offset

        return self._request("getUpdates", params)["result"]

    def get_me(self) -> dict:
        return self._request("getMe", {})["result"]

    def get_chat_administrators(self, chat_id: int) -> list[dict]:
        return self._request("getChatAdministrators", {"chat_id": chat_id})["result"]

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_to_message_id: int | None = None,
        reply_markup: dict | None = None,
    ) -> dict:
        payload = {"chat_id": chat_id, "text": text}
        if reply_to_message_id is not None:
            payload["reply_parameters"] = json.dumps({"message_id": reply_to_message_id})
        if reply_markup is not None:
            payload["reply_markup"] = json.dumps(reply_markup)
        return self._request("sendMessage", payload)

    def edit_message_text(
        self,
        chat_id: int | str,
        message_id: int | str,
        text: str,
        reply_markup: dict | None = None,
    ) -> dict:
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = json.dumps(reply_markup)
        return self._request("editMessageText", payload)

    def delete_message(self, chat_id: int | str, message_id: int | str) -> None:
        self._request("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    def send_document(
        self,
        chat_id: int | str,
        document_path: Path,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
    ) -> None:
        fields = {"chat_id": str(chat_id)}
        if caption:
            fields["caption"] = caption
        if reply_to_message_id is not None:
            fields["reply_parameters"] = json.dumps({"message_id": reply_to_message_id})

        self._request_multipart("sendDocument", fields, "document", document_path)

    def answer_callback_query(self, callback_query_id: str) -> None:
        self._request("answerCallbackQuery", {"callback_query_id": callback_query_id})

    def leave_chat(self, chat_id: int | str) -> None:
        self._request("leaveChat", {"chat_id": chat_id})

    def _request(self, method: str, payload: dict) -> dict:
        data = urlencode(payload).encode("utf-8")
        request = Request(f"{self.base_url}/{method}", data=data, method="POST")

        with urlopen(request, timeout=35) as response:
            body = response.read().decode("utf-8")

        result = json.loads(body)
        if not result.get("ok"):
            raise RuntimeError(f"Telegram API error: {result}")
        return result

    def _request_multipart(
        self,
        method: str,
        fields: dict[str, str],
        file_field: str,
        file_path: Path,
    ) -> dict:
        boundary = f"----galerazo-{uuid.uuid4().hex}"
        parts: list[bytes] = []

        for name, value in fields.items():
            parts.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )

        parts.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{file_field}"; '
                    f'filename="{file_path.name}"\r\n'
                ).encode("utf-8"),
                b"Content-Type: application/octet-stream\r\n\r\n",
                file_path.read_bytes(),
                b"\r\n",
                f"--{boundary}--\r\n".encode("utf-8"),
            ]
        )

        request = Request(
            f"{self.base_url}/{method}",
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )

        with urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")

        result = json.loads(body)
        if not result.get("ok"):
            raise RuntimeError(f"Telegram API error: {result}")
        return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    settings = load_settings()
    db = Database(settings.database_path)
    telegram = TelegramClient(settings.telegram_bot_token)
    bot_user_id = str(telegram.get_me()["id"])
    offset: int | None = None

    logger.info("Galerazo Bot escuchando mensajes de Telegram.")
    _send_log_event(
        telegram,
        settings.telegram_log_chat_id,
        "Galerazo Bot iniciado.",
    )

    while True:
        try:
            for update in telegram.get_updates(offset):
                offset = update["update_id"] + 1
                try:
                    _handle_update(
                        update,
                        db,
                        telegram,
                        bot_user_id,
                        settings.telegram_dev_user_ids,
                        settings.telegram_announcements_chat_id,
                    )
                except Exception as exc:
                    logger.exception("Error no handleado procesando update.")
                    _send_unhandled_error_event(telegram, settings.telegram_log_chat_id, exc)
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            logger.exception("Error no handleado leyendo Telegram.")
            _send_unhandled_error_event(telegram, settings.telegram_log_chat_id, exc)
            time.sleep(5)
        except Exception as exc:
            logger.exception("Error no handleado en el loop principal.")
            _send_unhandled_error_event(telegram, settings.telegram_log_chat_id, exc)
            time.sleep(5)


def _handle_update(
    update: dict,
    db: Database,
    telegram: TelegramClient,
    bot_user_id: str,
    dev_user_ids: frozenset[str],
    announcements_chat_id: str | None = None,
) -> None:
    callback_query = update.get("callback_query")
    if callback_query:
        _handle_callback_query(callback_query, db, telegram, dev_user_ids)
        return

    my_chat_member = update.get("my_chat_member")
    if my_chat_member:
        _handle_my_chat_member_update(my_chat_member, db, bot_user_id)
        return

    message = update.get("message", {})
    if _handle_chat_migration(message, db):
        return
    _register_chat_from_message(message, db)
    _register_bot_added_event(message, db, bot_user_id)
    _register_bot_removed_event(message, db, bot_user_id)

    text = message.get("text")
    chat = message.get("chat", {})
    user = message.get("from", {})
    chat_id = chat.get("id")
    user_id = user.get("id")
    message_id = message.get("message_id")

    if chat_id is None or user_id is None:
        return

    display_name = _display_name(user)
    username = user.get("username")
    db.get_or_create_user(str(user_id), display_name, username)

    if db.is_user_blocked(str(user_id)):
        return

    _maybe_award_daily_galeraza(
        db=db,
        telegram=telegram,
        chat_id=chat_id,
        chat_type=chat.get("type", "private"),
        user_id=str(user_id),
        message_id=message_id,
    )

    if not text:
        return

    if not is_command_invocation(text):
        db.save_incoming_message(sender_id=str(user_id), text=text, chat_id=str(chat_id))
        return

    user_level = UserLevel.COMMON
    if command_exists(text):
        user_level = _resolve_user_level(
            user_id=str(user_id),
            chat_id=chat_id,
            chat_type=chat.get("type", "private"),
            db=db,
            telegram=telegram,
            dev_user_ids=dev_user_ids,
        )

    reply_to_user = message.get("reply_to_message", {}).get("from", {})
    reply_to_user_id = reply_to_user.get("id")

    response = handle_command(
        text=text,
        sender_id=str(user_id),
        db=db,
        chat_id=str(chat_id),
        user_level=user_level,
        reply_to_user_id=str(reply_to_user_id) if reply_to_user_id is not None else None,
        reply_to_username=reply_to_user.get("username"),
        reply_to_display_name=_display_name(reply_to_user),
        chat_type=chat.get("type"),
        bot_user_id=bot_user_id,
        send_announcement=lambda text: _send_announcement(telegram, announcements_chat_id, text),
        create_backup=lambda: _create_and_send_backup(db, telegram, chat_id, message_id),
        send_debug_update=lambda: _send_debug_update(telegram, chat_id, message_id, update),
        send_galerazas=lambda: _send_galerazas(db, telegram, chat_id, str(user_id), message_id),
        leave_chat=lambda: _leave_chat(db, telegram, chat_id),
    )
    if response is not None:
        try:
            _send_text_response(
                db=db,
                telegram=telegram,
                chat_id=chat_id,
                text=response,
                requester_user_id=str(user_id),
                reply_to_message_id=message_id,
                list_type="command",
            )
        except RuntimeError as exc:
            if _is_bot_removed_error(exc):
                db.mark_chat_inactive(str(chat_id), "send_message_failed")
                return
            raise


def _display_name(user: dict) -> str | None:
    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip()
    return full_name or user.get("username")


def _handle_callback_query(
    callback_query: dict,
    db: Database,
    telegram: TelegramClient,
    dev_user_ids: frozenset[str],
) -> None:
    user = callback_query.get("from", {})
    user_id = user.get("id")
    callback_query_id = callback_query.get("id")

    if user_id is None:
        return

    db.get_or_create_user(str(user_id), _display_name(user), user.get("username"))
    if db.is_user_blocked(str(user_id)):
        if callback_query_id is not None:
            telegram.answer_callback_query(str(callback_query_id))
        return

    data = callback_query.get("data", "")
    parsed = parse_callback_data(data)
    if parsed is not None:
        _handle_paginated_callback(callback_query, db, telegram, dev_user_ids, parsed)
        if callback_query_id is not None:
            telegram.answer_callback_query(str(callback_query_id))
        return

    if callback_query_id is not None:
        telegram.answer_callback_query(str(callback_query_id))


def _handle_my_chat_member_update(update: dict, db: Database, bot_user_id: str) -> None:
    chat = update.get("chat", {})
    new_chat_member = update.get("new_chat_member", {})
    from_user = update.get("from", {})
    user = new_chat_member.get("user", {})
    chat_id = chat.get("id")

    if chat_id is None or str(user.get("id")) != bot_user_id:
        return

    status = new_chat_member.get("status")
    db.register_chat(
        chat_id=str(chat_id),
        chat_type=chat.get("type", "private"),
        title=chat.get("title"),
        added_by_user_id=str(from_user.get("id")) if from_user.get("id") is not None else None,
    )

    if status in {"left", "kicked"}:
        db.mark_chat_inactive(str(chat_id), status)


def _maybe_award_daily_galeraza(
    db: Database,
    telegram: TelegramClient,
    chat_id: int,
    chat_type: str,
    user_id: str,
    message_id: int | None,
) -> None:
    if chat_type not in {"group", "supergroup"} or message_id is None:
        return

    game_date = _today_key()
    awarded = db.try_award_daily_galeraza(
        chat_id=str(chat_id),
        game_date=game_date,
        user_id=user_id,
        message_id=str(message_id),
    )
    if not awarded:
        return

    telegram.send_message(
        chat_id=chat_id,
        text="Felicitaciones ganaste la Galeraza!",
        reply_to_message_id=message_id,
    )


def _send_galerazas(
    db: Database,
    telegram: TelegramClient,
    chat_id: int,
    requester_user_id: str,
    reply_to_message_id: int | None,
) -> bool:
    scores = db.get_galeraza_scores(str(chat_id))
    lines = build_galeraza_lines(scores)
    page = render_galeraza_page(scores, page=1)
    content_json = json.dumps(
        {"header": "Galeraza!", "lines": lines},
        ensure_ascii=False,
    )
    try:
        result = telegram.send_message(
            chat_id=chat_id,
            text=page.text,
            reply_to_message_id=reply_to_message_id,
        )
        message_id = str(result.get("result", {}).get("message_id", ""))
        if page.total_pages > 1 and message_id:
            db.save_paginated_message_state(
                chat_id=str(chat_id),
                message_id=message_id,
                list_type="galeraza",
                requester_user_id=requester_user_id,
                content_json=content_json,
                unlocked=False,
                current_page=page.page,
            )
            telegram.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=page.text,
                reply_markup=build_keyboard(
                    message_id,
                    page.page,
                    page.total_pages,
                    unlocked=False,
                ),
            )
        return True
    except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
        logger.warning("No pude enviar ranking de Galeraza: %s", exc)
        return False


def _send_text_response(
    db: Database,
    telegram: TelegramClient,
    chat_id: int,
    text: str,
    requester_user_id: str,
    reply_to_message_id: int | None,
    list_type: str,
) -> None:
    lines = text.splitlines()
    header = lines[0] if lines else ""
    body_lines = lines[1:]
    page = render_page(header, body_lines, page=1)

    result = telegram.send_message(
        chat_id=chat_id,
        text=page.text,
        reply_to_message_id=reply_to_message_id,
    )
    message_id = str(result.get("result", {}).get("message_id", ""))
    if page.total_pages <= 1 or not message_id:
        return

    content_json = json.dumps(
        {"header": header, "lines": body_lines},
        ensure_ascii=False,
    )
    db.save_paginated_message_state(
        chat_id=str(chat_id),
        message_id=message_id,
        list_type=list_type,
        requester_user_id=requester_user_id,
        content_json=content_json,
        unlocked=False,
        current_page=page.page,
    )
    telegram.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=page.text,
        reply_markup=build_keyboard(
            message_id,
            page.page,
            page.total_pages,
            unlocked=False,
        ),
    )


def _handle_paginated_callback(
    callback_query: dict,
    db: Database,
    telegram: TelegramClient,
    dev_user_ids: frozenset[str],
    parsed: tuple[str, str, str | None],
) -> None:
    action, message_id, value = parsed
    user = callback_query.get("from", {})
    user_id = str(user.get("id"))
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    if chat_id is None:
        return

    state = db.get_paginated_message_state(str(chat_id), message_id)
    if state is None:
        return

    is_dev = user_id in dev_user_ids
    is_owner = user_id == state.requester_user_id
    can_page = state.unlocked or is_owner or is_dev
    can_delete = is_owner or is_dev

    if action == "unlock":
        if not is_owner or state.unlocked:
            return
        db.set_paginated_message_unlocked(str(chat_id), message_id, True)
        current_page = state.current_page
        _edit_paginated_message(db, telegram, chat_id, message_id, page=current_page, unlocked=True)
        return

    if action == "delete":
        if not can_delete:
            return
        try:
            telegram.delete_message(chat_id=chat_id, message_id=message_id)
        finally:
            db.delete_paginated_message_state(str(chat_id), message_id)
        return

    if action == "page":
        if not can_page or value is None:
            return
        try:
            target_page = int(value)
        except ValueError:
            return

        if target_page == state.current_page:
            return
        _edit_paginated_message(
            db,
            telegram,
            chat_id,
            message_id,
            page=target_page,
            unlocked=state.unlocked,
        )


def _edit_paginated_message(
    db: Database,
    telegram: TelegramClient,
    chat_id: int,
    message_id: str,
    page: int,
    unlocked: bool,
) -> None:
    state = db.get_paginated_message_state(str(chat_id), message_id)
    if state is None:
        return

    content = json.loads(state.content_json)
    rendered = render_page(content["header"], content["lines"], page=page)
    db.set_paginated_message_page(str(chat_id), message_id, rendered.page)
    telegram.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=rendered.text,
        reply_markup=build_keyboard(
            message_id,
            rendered.page,
            rendered.total_pages,
            unlocked=unlocked,
        ),
    )


def _register_chat_from_message(message: dict, db: Database) -> None:
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    if chat_id is None:
        return

    db.register_chat(
        chat_id=str(chat_id),
        chat_type=chat.get("type", "private"),
        title=chat.get("title"),
    )


def _handle_chat_migration(message: dict, db: Database) -> bool:
    old_chat_id = message.get("chat", {}).get("id")
    new_chat_id = message.get("migrate_to_chat_id")

    if old_chat_id is None or new_chat_id is None:
        return False

    db.migrate_chat_id(old_chat_id=str(old_chat_id), new_chat_id=str(new_chat_id))
    logger.info("Chat migrado de %s a %s.", old_chat_id, new_chat_id)
    return True


def _register_bot_added_event(message: dict, db: Database, bot_user_id: str) -> None:
    chat = message.get("chat", {})
    from_user = message.get("from", {})
    new_members = message.get("new_chat_members", [])
    chat_id = chat.get("id")
    added_by_user_id = from_user.get("id")

    if chat_id is None or added_by_user_id is None:
        return

    was_bot_added = any(str(member.get("id")) == bot_user_id for member in new_members)
    if not was_bot_added:
        return

    db.get_or_create_user(
        str(added_by_user_id),
        _display_name(from_user),
        from_user.get("username"),
    )
    db.register_chat(
        chat_id=str(chat_id),
        chat_type=chat.get("type", "private"),
        title=chat.get("title"),
        added_by_user_id=str(added_by_user_id),
    )


def _register_bot_removed_event(message: dict, db: Database, bot_user_id: str) -> None:
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    if chat_id is None:
        return

    left_member = message.get("left_chat_member")
    if isinstance(left_member, dict) and str(left_member.get("id")) == bot_user_id:
        db.mark_chat_inactive(str(chat_id), "left_chat_member")
        return

    new_status = message.get("new_chat_member", {})
    if not isinstance(new_status, dict):
        return

    user = new_status.get("user", {})
    status = new_status.get("status")
    if str(user.get("id")) == bot_user_id and status in {"left", "kicked"}:
        db.mark_chat_inactive(str(chat_id), status)


def _resolve_user_level(
    user_id: str,
    chat_id: int,
    chat_type: str,
    db: Database,
    telegram: TelegramClient,
    dev_user_ids: frozenset[str],
) -> UserLevel:
    if user_id in dev_user_ids:
        return UserLevel.DEV

    added_by_user_id = db.get_chat_added_by_user_id(str(chat_id))
    if added_by_user_id == user_id:
        return UserLevel.ADMIN

    if chat_type in {"group", "supergroup"} and _is_chat_admin(chat_id, user_id, telegram):
        return UserLevel.ADMIN

    return UserLevel.COMMON


def _is_chat_admin(chat_id: int, user_id: str, telegram: TelegramClient) -> bool:
    try:
        administrators = telegram.get_chat_administrators(chat_id)
    except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
        logger.warning("No pude leer admines del chat %s: %s", chat_id, exc)
        return False

    return any(str(admin.get("user", {}).get("id")) == user_id for admin in administrators)


def _send_unhandled_error_event(
    telegram: TelegramClient,
    log_chat_id: str | None,
    exc: BaseException,
) -> None:
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    if len(trace) > 3200:
        trace = trace[-3200:]

    _send_log_event(
        telegram,
        log_chat_id,
        f"Error no handleado:\n{trace}",
    )


def _send_log_event(telegram: TelegramClient, log_chat_id: str | None, text: str) -> None:
    if not log_chat_id:
        return

    try:
        telegram.send_message(chat_id=_parse_chat_id(log_chat_id), text=text)
    except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as exc:
        logger.warning("No pude enviar evento al canal de logging: %s", exc)


def _send_announcement(
    telegram: TelegramClient,
    announcements_chat_id: str | None,
    text: str,
) -> bool:
    if not announcements_chat_id:
        return False

    try:
        telegram.send_message(chat_id=_parse_chat_id(announcements_chat_id), text=text)
    except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as exc:
        logger.warning("No pude enviar novedad al canal de anuncios: %s", exc)
        return False

    return True


def _create_and_send_backup(
    db: Database,
    telegram: TelegramClient,
    chat_id: int,
    message_id: int | None,
) -> BackupResult:
    backup_path = db.create_backup(Path("backups"))
    size_bytes = backup_path.stat().st_size

    if size_bytes > TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES:
        return BackupResult(
            path=backup_path,
            size_bytes=size_bytes,
            max_size_bytes=TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES,
            sent=False,
        )

    telegram.send_document(
        chat_id=chat_id,
        document_path=backup_path,
        caption="Backup de la base de datos.",
        reply_to_message_id=message_id,
    )
    return BackupResult(
        path=backup_path,
        size_bytes=size_bytes,
        max_size_bytes=TELEGRAM_DOCUMENT_UPLOAD_LIMIT_BYTES,
        sent=True,
    )


def _send_debug_update(
    telegram: TelegramClient,
    chat_id: int,
    message_id: int | None,
    update: dict,
) -> bool:
    debug_json = json.dumps(update, ensure_ascii=False, indent=2, sort_keys=True)
    wrapped_json = f"```json\n{debug_json}\n```"

    try:
        if len(wrapped_json) <= TELEGRAM_MESSAGE_LIMIT_CHARS:
            telegram.send_message(
                chat_id=chat_id,
                text=wrapped_json,
                reply_to_message_id=message_id,
            )
            return True

        debug_dir = Path("debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_path = debug_dir / f"update-{message_id or int(time.time())}.json"
        debug_path.write_text(debug_json, encoding="utf-8")
        telegram.send_document(
            chat_id=chat_id,
            document_path=debug_path,
            caption="Update de debug.",
            reply_to_message_id=message_id,
        )
        return True
    except (HTTPError, URLError, TimeoutError, RuntimeError, OSError) as exc:
        logger.warning("No pude enviar update de debug: %s", exc)
        return False


def _leave_chat(db: Database, telegram: TelegramClient, chat_id: int) -> bool:
    try:
        telegram.leave_chat(chat_id)
    except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
        logger.warning("No pude salir del chat %s: %s", chat_id, exc)
        return False

    db.mark_chat_inactive(str(chat_id), "left_by_command")
    return True


def _parse_chat_id(raw_chat_id: str) -> int | str:
    if raw_chat_id.lstrip("-").isdigit():
        return int(raw_chat_id)
    return raw_chat_id


def _is_bot_removed_error(exc: RuntimeError) -> bool:
    message = str(exc).lower()
    markers = [
        "bot was blocked by the user",
        "bot was kicked",
        "bot is not a member",
        "chat not found",
        "forbidden",
    ]
    return any(marker in message for marker in markers)


def _today_key() -> str:
    try:
        now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    except Exception:
        now = datetime.now().astimezone()
    return now.date().isoformat()
