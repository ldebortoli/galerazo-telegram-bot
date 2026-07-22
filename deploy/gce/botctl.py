#!/usr/bin/env python3
"""Contrato local y acotado para observar/moderar Galerazo desde la VM.

El script usa solamente la biblioteca estándar, nunca imprime secretos y está
pensado para ejecutarse como root por IAP. Las escrituras disponibles están
reducidas a moderación explícita y detención del servicio de Compose.
"""

from __future__ import annotations

import base64
from contextlib import closing
from datetime import UTC, datetime
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
from typing import Any
from urllib import parse, request


DATABASE_PATH = Path(os.environ.get("GALERAZO_DATABASE_PATH", "/srv/galerazo/data/galerazo.sqlite3"))
ENV_PATH = Path(os.environ.get("GALERAZO_ENV_PATH", "/etc/galerazo/bot.env"))
COMPOSE_PATH = Path(os.environ.get("GALERAZO_COMPOSE_PATH", "/opt/galerazo/compose.yaml"))
IMAGE_ENV_PATH = Path(os.environ.get("GALERAZO_IMAGE_ENV_PATH", "/opt/galerazo/image.env"))
COMPOSE_DIRECTORY = COMPOSE_PATH.parent
BOT_CONTROL_ACTOR = "bot-control-center"
TOKEN_PATTERN = re.compile(r"\b\d{6,14}:[A-Za-z0-9_-]{20,}\b")
MEDIA_TYPES = {"photo", "video", "animation", "audio", "voice", "document", "video_note", "sticker"}
MODERATION_ACTIONS = {"delete-trigger", "block-user", "delete-and-block"}


def _run(args: list[str], *, timeout: int = 15, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, check=check, text=True, timeout=timeout)


def _compose_args(*args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-directory",
        str(COMPOSE_DIRECTORY),
        "--env-file",
        str(IMAGE_ENV_PATH),
        "-f",
        str(COMPOSE_PATH),
        *args,
    ]


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.is_file():
        return values
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _telegram_json(method: str, token: str, fields: dict[str, str] | None = None) -> dict[str, Any]:
    body = parse.urlencode(fields or {}).encode("utf-8")
    api_request = request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=body,
        method="POST",
    )
    with request.urlopen(api_request, timeout=8) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError(f"Telegram rechazó {method}.")
    return result


def _token() -> str:
    token = _read_env().get("TELEGRAM_BOT_TOKEN", "")
    if not token or token == "replace-me":
        raise RuntimeError("TELEGRAM_BOT_TOKEN no está configurado.")
    return token


def _connect(*, readonly: bool) -> sqlite3.Connection:
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"No existe la base SQLite en {DATABASE_PATH}.")
    if readonly:
        connection = sqlite3.connect(f"file:{DATABASE_PATH.as_posix()}?mode=ro", uri=True, timeout=5)
    else:
        connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _container_id() -> str | None:
    if not COMPOSE_PATH.is_file():
        return None
    result = _run(_compose_args("ps", "-aq", "bot"), check=False)
    value = result.stdout.strip()
    return value.splitlines()[-1] if value else None


def _safe_log_lines(text: str, limit: int = 80) -> list[str]:
    clean: list[str] = []
    for raw_line in text.splitlines()[-limit:]:
        line = TOKEN_PATTERN.sub("[TELEGRAM_TOKEN_OCULTO]", raw_line).strip()
        if line:
            clean.append(line[:1000])
    return clean


def _parse_docker_stats(container_id: str) -> dict[str, Any]:
    result = _run(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}", container_id],
        timeout=10,
        check=False,
    )
    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        payload = {}
    return {
        "cpuPercent": payload.get("CPUPerc"),
        "memoryUsage": payload.get("MemUsage"),
        "memoryPercent": payload.get("MemPerc"),
    }


def _recent_restarts(container_id: str) -> int:
    result = _run(
        [
            "docker",
            "events",
            "--since",
            "15m",
            "--until",
            datetime.now(UTC).isoformat(),
            "--filter",
            f"container={container_id}",
            "--filter",
            "event=restart",
            "--format",
            "{{json .}}",
        ],
        timeout=8,
        check=False,
    )
    return len([line for line in result.stdout.splitlines() if line.strip()])


def runtime_status() -> dict[str, Any]:
    disk = shutil.disk_usage("/")
    result: dict[str, Any] = {
        "observedAt": datetime.now(UTC).isoformat(),
        "vm": {"status": "running"},
        "container": {
            "exists": False,
            "status": "not-created",
            "running": False,
            "health": "unavailable",
            "restartCount": 0,
            "recentRestarts": 0,
            "restartLoop": False,
            "image": None,
            "startedAt": None,
        },
        "telegram": {"connected": False, "username": None, "error": None},
        "resources": {
            "cpuPercent": None,
            "memoryUsage": None,
            "memoryPercent": None,
            "diskUsedBytes": disk.used,
            "diskTotalBytes": disk.total,
            "diskPercent": round((disk.used / disk.total) * 100, 1) if disk.total else None,
        },
        "database": {
            "available": DATABASE_PATH.is_file(),
            "bytes": DATABASE_PATH.stat().st_size if DATABASE_PATH.is_file() else None,
        },
        "logs": [],
        "errors": [],
        "alerts": [],
    }

    container_id = _container_id()
    if container_id:
        inspect_result = _run(["docker", "inspect", container_id], check=False)
        try:
            inspection = json.loads(inspect_result.stdout)[0]
        except (IndexError, KeyError, TypeError, json.JSONDecodeError):
            inspection = {}
        state = inspection.get("State") or {}
        status = str(state.get("Status") or "unknown")
        health = str((state.get("Health") or {}).get("Status") or "unavailable")
        recent_restarts = _recent_restarts(container_id)
        restart_count = int(inspection.get("RestartCount") or 0)
        restart_loop = status == "restarting" or recent_restarts >= 3
        result["container"] = {
            "exists": True,
            "status": status,
            "running": bool(state.get("Running")),
            "health": health,
            "restartCount": restart_count,
            "recentRestarts": recent_restarts,
            "restartLoop": restart_loop,
            "image": (inspection.get("Config") or {}).get("Image"),
            "startedAt": state.get("StartedAt"),
        }
        if result["container"]["running"]:
            result["resources"].update(_parse_docker_stats(container_id))
        logs_result = _run(["docker", "logs", "--tail", "80", "--timestamps", container_id], timeout=10, check=False)
        lines = _safe_log_lines(f"{logs_result.stdout}\n{logs_result.stderr}")
        result["logs"] = lines
        error_pattern = re.compile(r"error|exception|traceback|timed?\s*out|failed|fatal", re.IGNORECASE)
        result["errors"] = [line for line in lines if error_pattern.search(line)][-12:]
        if restart_loop:
            result["alerts"].append("El contenedor está en un posible bucle de reinicios.")
        if health == "unhealthy":
            result["alerts"].append("El healthcheck del contenedor informa unhealthy.")
        if status not in {"running", "created"}:
            result["alerts"].append(f"El contenedor está {status}.")
    else:
        result["alerts"].append("No existe un contenedor de Galerazo administrado por Compose.")

    try:
        telegram = _telegram_json("getMe", _token()).get("result") or {}
        result["telegram"] = {
            "connected": True,
            "username": telegram.get("username"),
            "error": None,
        }
    except Exception as exc:  # La salida nunca incluye el token.
        result["telegram"]["error"] = TOKEN_PATTERN.sub("[TELEGRAM_TOKEN_OCULTO]", str(exc))[:300]
        result["alerts"].append("No se pudo comprobar la conectividad con Telegram.")
    return result


def _encode_trigger_id(chat_id: str, trigger_name: str) -> str:
    raw = json.dumps({"chatId": chat_id, "name": trigger_name}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_trigger_id(value: str) -> tuple[str, str]:
    if not value or len(value) > 2048 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Identificador de trigger inválido.")
    padded = value + "=" * (-len(value) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Identificador de trigger inválido.") from exc
    if not isinstance(payload, dict) or not all(isinstance(payload.get(key), str) for key in ("chatId", "name")):
        raise ValueError("Identificador de trigger inválido.")
    return payload["chatId"], payload["name"]


def _file_metadata(file_id: str, media_type: str) -> tuple[str, str, str]:
    fallback_mime = {
        "photo": "image/jpeg",
        "video": "video/mp4",
        "animation": "video/mp4",
        "audio": "audio/mpeg",
        "voice": "audio/ogg",
        "video_note": "video/mp4",
        "sticker": "image/webp",
    }.get(media_type, "application/octet-stream")
    fallback_name = f"trigger-{media_type}{mimetypes.guess_extension(fallback_mime) or '.bin'}"
    try:
        remote = (_telegram_json("getFile", _token(), {"file_id": file_id}).get("result") or {}).get("file_path")
        if not isinstance(remote, str) or not remote:
            raise RuntimeError("Telegram no devolvió file_path.")
        name = Path(remote).name or fallback_name
        mime = mimetypes.guess_type(name)[0] or ("application/x-tgsticker" if name.endswith(".tgs") else fallback_mime)
        return name, mime, remote
    except Exception:
        return fallback_name, fallback_mime, ""


def _media_kind(media_type: str, mime_type: str) -> str:
    if media_type == "sticker":
        return "sticker"
    if mime_type.startswith("image/") or media_type == "photo":
        return "image"
    if mime_type.startswith("video/") or media_type in {"video", "animation", "video_note"}:
        return "video"
    if mime_type.startswith("audio/") or media_type in {"audio", "voice"}:
        return "audio"
    return "file"


def list_triggers() -> dict[str, Any]:
    with closing(_connect(readonly=True)) as connection:
        rows = connection.execute(
            """
            SELECT
                t.chat_id,
                t.trigger_name,
                t.display_name,
                t.text,
                t.media_type,
                t.file_id,
                t.caption,
                t.payload_json,
                t.created_by_user_id,
                t.created_at,
                u.display_name AS creator_display_name,
                u.username AS creator_username,
                c.title AS chat_title,
                c.chat_type,
                COALESCE(ccs.enabled, 1) AS enabled,
                CASE WHEN bu.user_id IS NULL THEN 0 ELSE 1 END AS creator_blocked
            FROM triggers AS t
            LEFT JOIN users AS u ON u.user_id = t.created_by_user_id
            LEFT JOIN chats AS c ON c.chat_id = t.chat_id
            LEFT JOIN chat_command_settings AS ccs
              ON ccs.chat_id = t.chat_id AND ccs.command_group = 'triggers'
            LEFT JOIN blocked_users AS bu ON bu.user_id = t.created_by_user_id
            ORDER BY lower(COALESCE(c.title, t.chat_id)), lower(t.display_name)
            """
        ).fetchall()

    triggers: list[dict[str, Any]] = []
    for row in rows:
        response_text = row["text"] or row["caption"] or (f"Contenido {row['media_type']}" if row["media_type"] else "Sin texto")
        item: dict[str, Any] = {
            "id": _encode_trigger_id(row["chat_id"], row["trigger_name"]),
            "name": row["display_name"],
            "phrase": row["display_name"],
            "response": response_text,
            "enabled": bool(row["enabled"]),
            "createdAt": row["created_at"],
            "createdBy": {
                "id": row["created_by_user_id"],
                "displayName": row["creator_display_name"] or f"Usuario {row['created_by_user_id']}",
                "username": row["creator_username"],
                "blocked": bool(row["creator_blocked"]),
            },
            "chat": {
                "id": row["chat_id"],
                "title": row["chat_title"] or f"Chat {row['chat_id']}",
                "platform": "telegram",
            },
        }
        if row["media_type"] in MEDIA_TYPES and row["file_id"]:
            filename, mime_type, _ = _file_metadata(row["file_id"], row["media_type"])
            item["media"] = {
                "kind": _media_kind(row["media_type"], mime_type),
                "filename": filename,
                "mimeType": mime_type,
                "source": "remote",
            }
        triggers.append(item)
    return {"observedAt": datetime.now(UTC).isoformat(), "triggers": triggers}


def fetch_media(trigger_id: str, output_path: Path) -> dict[str, Any]:
    chat_id, trigger_name = _decode_trigger_id(trigger_id)
    with closing(_connect(readonly=True)) as connection:
        row = connection.execute(
            "SELECT media_type, file_id FROM triggers WHERE chat_id = ? AND trigger_name = ?",
            (chat_id, trigger_name),
        ).fetchone()
    if row is None or row["media_type"] not in MEDIA_TYPES or not row["file_id"]:
        raise FileNotFoundError("El trigger no tiene multimedia descargable.")
    filename, mime_type, remote_path = _file_metadata(row["file_id"], row["media_type"])
    if not remote_path:
        remote_path = (_telegram_json("getFile", _token(), {"file_id": row["file_id"]}).get("result") or {}).get("file_path")
    if not isinstance(remote_path, str) or not remote_path:
        raise RuntimeError("Telegram no devolvió la ruta del archivo.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    media_url = f"https://api.telegram.org/file/bot{_token()}/{parse.quote(remote_path, safe='/')}"
    with request.urlopen(media_url, timeout=30) as response, output_path.open("wb") as target:
        shutil.copyfileobj(response, target)
        header_type = response.headers.get_content_type()
    if output_path.stat().st_size > 25 * 1024 * 1024:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("El archivo supera el límite de 25 MB del visor.")
    return {
        "filename": filename,
        "mimeType": header_type if header_type != "application/octet-stream" else mime_type,
        "bytes": output_path.stat().st_size,
    }


def moderate_trigger(trigger_id: str, action: str) -> dict[str, Any]:
    if action not in MODERATION_ACTIONS:
        raise ValueError("Acción de moderación inválida.")
    chat_id, trigger_name = _decode_trigger_id(trigger_id)
    delete = action in {"delete-trigger", "delete-and-block"}
    block = action in {"block-user", "delete-and-block"}
    with closing(_connect(readonly=False)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT t.display_name, t.created_by_user_id, u.display_name, u.username, c.title
            FROM triggers AS t
            LEFT JOIN users AS u ON u.user_id = t.created_by_user_id
            LEFT JOIN chats AS c ON c.chat_id = t.chat_id
            WHERE t.chat_id = ? AND t.trigger_name = ?
            """,
            (chat_id, trigger_name),
        ).fetchone()
        if row is None:
            raise FileNotFoundError("El trigger ya no existe.")
        if block:
            connection.execute(
                "INSERT OR IGNORE INTO users (user_id, display_name) VALUES (?, ?)",
                (BOT_CONTROL_ACTOR, "Bot Control Center"),
            )
            connection.execute(
                """
                INSERT INTO blocked_users (user_id, blocked_by_user_id)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    blocked_by_user_id = excluded.blocked_by_user_id,
                    blocked_at = CURRENT_TIMESTAMP
                """,
                (row["created_by_user_id"], BOT_CONTROL_ACTOR),
            )
        deleted = False
        if delete:
            deleted = connection.execute(
                "DELETE FROM triggers WHERE chat_id = ? AND trigger_name = ?",
                (chat_id, trigger_name),
            ).rowcount > 0
        connection.commit()

    actor = f"@{row['username']}" if row["username"] else (row["display_name"] or f"usuario {row['created_by_user_id']}")
    if action == "delete-trigger":
        warning = f"⚠️ Moderación: se eliminó el trigger «{row['display_name']}», agregado por {actor}."
    elif action == "block-user":
        warning = f"⚠️ Moderación: {actor} fue bloqueado en el bot por uso abusivo de triggers."
    else:
        warning = f"⚠️ Moderación: se eliminó el trigger «{row['display_name']}» y {actor} fue bloqueado en el bot."
    announcement_sent = False
    errors: list[str] = []
    try:
        _telegram_json("sendMessage", _token(), {"chat_id": chat_id, "text": warning})
        announcement_sent = True
    except Exception as exc:
        errors.append(TOKEN_PATTERN.sub("[TELEGRAM_TOKEN_OCULTO]", str(exc))[:300])
    return {
        "triggerDeleted": deleted,
        "userBlocked": block,
        "announcementSent": announcement_sent,
        "errors": errors,
    }


def stop_service() -> dict[str, Any]:
    if not COMPOSE_PATH.is_file():
        raise FileNotFoundError("No existe el Compose desplegado.")
    _run(_compose_args("stop", "bot"), timeout=60)
    return {
        "stopped": True,
        "message": "Contenedor detenido sin borrar base, imagen ni configuración.",
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        action = arguments.pop(0)
        if action == "status" and not arguments:
            payload = runtime_status()
        elif action == "triggers" and not arguments:
            payload = list_triggers()
        elif action == "media" and len(arguments) == 2:
            payload = fetch_media(arguments[0], Path(arguments[1]))
        elif action == "moderate" and len(arguments) == 2:
            payload = moderate_trigger(arguments[0], arguments[1])
        elif action == "stop" and not arguments:
            payload = stop_service()
        else:
            raise ValueError("Uso: botctl.py status|triggers|media|moderate|stop")
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"error": TOKEN_PATTERN.sub("[TELEGRAM_TOKEN_OCULTO]", str(exc))[:500]}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
