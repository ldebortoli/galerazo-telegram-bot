from __future__ import annotations

import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ControlPanelTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
