from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from galerazo_bot.release_broadcast import validate_release_broadcast
from galerazo_bot.versioning import CURRENT_VERSION


TELEGRAM_MESSAGE_LIMIT_CHARS = 4096


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the curated Telegram release broadcast before publication."
    )
    parser.add_argument("--version", default=CURRENT_VERSION)
    parser.add_argument("--allow-draft", action="store_true")
    args = parser.parse_args()
    try:
        entry, maximum_length = validate_release_broadcast(
            args.version,
            TELEGRAM_MESSAGE_LIMIT_CHARS,
            require_approved=not args.allow_draft,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(
        f"Broadcast {entry.status} para v{entry.version}: "
        f"maximo formateado={maximum_length}/{TELEGRAM_MESSAGE_LIMIT_CHARS} caracteres."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
