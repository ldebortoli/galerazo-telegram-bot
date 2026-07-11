from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = PROJECT_ROOT / "data" / "integration-status.json"


def save_logging_status(ok: bool, detail: str) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "logging": {
            "ok": ok,
            "detail": detail,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_logging_status() -> dict[str, object] | None:
    try:
        payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        status = payload.get("logging")
        return status if isinstance(status, dict) else None
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
