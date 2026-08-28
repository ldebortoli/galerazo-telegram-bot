from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aiohttp import web

from galerazo_bot.database import Database
from galerazo_bot.mini_app import build_mini_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Vista previa local de la Mini App de Hisopos")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="galerazo-miniapp-") as directory:
        app = build_mini_app(
            db=Database(Path(directory) / "preview.sqlite3"),
            bot_token="preview-token",
            bot=None,
            public_url=f"http://{args.host}:{args.port}",
            preview_mode=True,
        )
        web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
