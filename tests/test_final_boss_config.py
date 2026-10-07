from pathlib import Path
import unittest
from unittest.mock import patch

from galerazo_bot.config import Settings, load_settings


BOSS_FILE_ID_FIELDS = (
    "telegram_hisopo_final_boss_phase_1_file_id",
    "telegram_hisopo_final_boss_phase_2_file_id",
    "telegram_hisopo_final_boss_phase_3_file_id",
    "telegram_hisopo_final_boss_phase_4_file_id",
    "telegram_hisopo_final_boss_defeated_file_id",
    "telegram_hisopo_final_boss_victorious_file_id",
)


class FinalBossConfigurationTests(unittest.TestCase):
    def test_manual_file_ids_load_independently_and_keep_each_phase_mapping(self):
        expected = {field: f"fixture-{index}" for index, field in enumerate(BOSS_FILE_ID_FIELDS, start=1)}
        with patch("galerazo_bot.config.load_dotenv"), patch.dict(
            "os.environ", {field.upper(): value for field, value in expected.items()}, clear=True
        ):
            settings = load_settings()
        self.assertEqual({field: getattr(settings, field) for field in BOSS_FILE_ID_FIELDS}, expected)

    def test_missing_empty_and_direct_settings_default_to_none(self):
        direct = Settings("fixture", frozenset(), None, None, Path("fixture.sqlite3"))
        self.assertTrue(all(getattr(direct, field) is None for field in BOSS_FILE_ID_FIELDS))
        for environment in ({}, {field.upper(): "" for field in BOSS_FILE_ID_FIELDS}):
            with self.subTest(environment=environment), patch("galerazo_bot.config.load_dotenv"), patch.dict(
                "os.environ", environment, clear=True
            ):
                settings = load_settings()
            self.assertTrue(all(getattr(settings, field) is None for field in BOSS_FILE_ID_FIELDS))

    def test_example_lists_all_six_manual_file_ids_once_and_without_values(self):
        lines = (Path(__file__).resolve().parent.parent / ".env.example").read_text(encoding="utf-8").splitlines()
        for field in BOSS_FILE_ID_FIELDS:
            self.assertEqual(lines.count(f"{field.upper()}="), 1)
