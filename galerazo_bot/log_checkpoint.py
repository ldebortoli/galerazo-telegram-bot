from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .logging_utils import redact_secrets


ERROR_PATTERN = re.compile(
    r"(^|\s)(ERROR|CRITICAL)(\s|:)|Traceback \(most recent call last\)|Conflict:|Exception:",
    re.IGNORECASE,
)
DEFAULT_LOG_PATH = Path("data/bot.log")
DEFAULT_CHECKPOINT_PATH = Path("data/bot-log-checkpoint.json")


@dataclass(frozen=True)
class CheckpointResult:
    new_text: str
    error_lines: tuple[str, ...]
    advanced: bool
    start_offset: int
    end_offset: int


def check_log(
    log_path: Path = DEFAULT_LOG_PATH,
    checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
    acknowledge: bool = False,
) -> CheckpointResult:
    if not log_path.exists():
        return CheckpointResult("", (), False, 0, 0)

    stat = log_path.stat()
    file_id = f"{stat.st_dev}:{stat.st_ino}"
    state = _load_checkpoint(checkpoint_path)
    start_offset = int(state.get("offset", 0))
    if state.get("file_id") != file_id or start_offset > stat.st_size:
        start_offset = 0

    with log_path.open("rb") as log_file:
        log_file.seek(start_offset)
        raw = log_file.read()
    new_text = raw.decode("utf-8", errors="replace")
    error_lines = tuple(line for line in new_text.splitlines() if ERROR_PATTERN.search(line))
    advanced = acknowledge or not error_lines
    if advanced:
        _save_checkpoint(checkpoint_path, file_id, stat.st_size)

    return CheckpointResult(
        new_text=new_text,
        error_lines=error_lines,
        advanced=advanced,
        start_offset=start_offset,
        end_offset=stat.st_size,
    )


def _load_checkpoint(checkpoint_path: Path) -> dict[str, object]:
    try:
        return json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return {}


def _save_checkpoint(checkpoint_path: Path, file_id: str, offset: int) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "file_id": file_id,
        "offset": offset,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    checkpoint_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Review only new Galerazo Bot log entries.")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--acknowledge", action="store_true")
    args = parser.parse_args()

    result = check_log(args.log, args.checkpoint, acknowledge=args.acknowledge)
    if not args.log.exists():
        print(f"Log not found: {args.log}")
        return 0
    if result.start_offset == result.end_offset:
        print("No new bot log entries.")
        return 0
    if result.error_lines and not args.acknowledge:
        print(f"Detected {len(result.error_lines)} error marker(s) in new bot log entries:")
        for line in result.error_lines[-30:]:
            print(redact_secrets(line))
        print("Checkpoint not advanced. Fix or investigate, then rerun with --acknowledge.")
        return 1

    action = "Acknowledged" if args.acknowledge else "Reviewed"
    print(f"{action} bot log bytes {result.start_offset}..{result.end_offset}; no pending error markers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
