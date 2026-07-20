from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ControlPanelTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "requires the native Windows Tk layout")
    def test_logging_status_label_is_not_vertically_clipped(self) -> None:
        from galerazo_bot.control_panel import ControlPanel

        panel = ControlPanel()
        try:
            panel.withdraw()
            panel.geometry("680x700")
            panel.notebook.select(panel.config_tab)
            panel.update_idletasks()

            self.assertGreaterEqual(
                panel.logging_status_label.winfo_height(),
                panel.logging_status_label.winfo_reqheight(),
            )
        finally:
            panel.destroy()

    def test_closing_panel_stops_bot_before_destroying_window(self) -> None:
        module = ast.parse(
            (PROJECT_ROOT / "galerazo_bot" / "control_panel.py").read_text(encoding="utf-8")
        )
        control_panel = next(
            node
            for node in module.body
            if isinstance(node, ast.ClassDef) and node.name == "ControlPanel"
        )
        close_panel = next(
            node
            for node in control_panel.body
            if isinstance(node, ast.FunctionDef) and node.name == "close_panel"
        )
        calls = [
            statement.value.func.attr
            for statement in close_panel.body
            if isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Attribute)
        ]

        self.assertEqual(calls, ["stop_bot", "destroy"])

    def test_openai_key_is_a_secret_configuration_field(self) -> None:
        from galerazo_bot.control_panel import FIELDS

        self.assertIn(
            ("OPENAI_API_KEY", "Clave de moderacion OpenAI", True),
            FIELDS,
        )


if __name__ == "__main__":
    unittest.main()
