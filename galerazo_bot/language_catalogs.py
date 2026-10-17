"""Local catalogs only. Acquisition never runs in the bot process."""
import json
from pathlib import Path

CATALOGS = json.loads(Path(__file__).with_name("language-catalogs.json").read_text(encoding="utf-8"))
LANGUAGE_OPTIONS = CATALOGS["options"]
LANGUAGE_NAMES = CATALOGS["names"]
