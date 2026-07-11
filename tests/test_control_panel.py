from __future__ import annotations

import unittest
from unittest.mock import Mock

from galerazo_bot.control_panel import ControlPanel


class ControlPanelTests(unittest.TestCase):
    def test_closing_panel_stops_bot_before_destroying_window(self) -> None:
        calls: list[str] = []
        panel = Mock()
        panel.stop_bot.side_effect = lambda: calls.append("stop")
        panel.destroy.side_effect = lambda: calls.append("destroy")

        ControlPanel.close_panel(panel)

        self.assertEqual(calls, ["stop", "destroy"])


if __name__ == "__main__":
    unittest.main()
