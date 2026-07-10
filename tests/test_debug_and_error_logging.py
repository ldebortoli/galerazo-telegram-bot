import json
import unittest

from telegram import Update

from galerazo_bot.telegram_bot import _send_unhandled_error_event, _serialize_update


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send_message(self, **kwargs) -> None:
        self.messages.append(kwargs)


class DebugSerializationTests(unittest.IsolatedAsyncioTestCase):
    def test_serializes_ptb_update_as_indented_json(self) -> None:
        serialized = _serialize_update(Update(update_id=17))
        self.assertEqual(json.loads(serialized)["update_id"], 17)
        self.assertIn("\n", serialized)

    async def test_unhandled_error_log_includes_update_json(self) -> None:
        bot = FakeBot()
        await _send_unhandled_error_event(
            bot,
            "-100123",
            RuntimeError("failure"),
            Update(update_id=23),
        )

        self.assertEqual(len(bot.messages), 1)
        text = str(bot.messages[0]["text"])
        self.assertIn("Error no handleado", text)
        self.assertIn("Update JSON", text)
        self.assertIn('"update_id": 23', text)


if __name__ == "__main__":
    unittest.main()
