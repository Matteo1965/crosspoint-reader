#!/usr/bin/env python3
"""Source-level regression checks for the shared Picco/X4 Pro HU keyboard.

These structural checks do not claim to test display or touch hardware.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/activities/util/HungarianKeyboardLayout.h").read_text(encoding="utf-8")


def row(name):
    m = re.search(r"inline const fui::KeyboardKey " + re.escape(name) +
                  r"\[\]\s*=\s*\{(.*?)\};", SOURCE, re.S)
    if m is None:
        raise AssertionError(f"Missing row: {name}")
    return m.group(1)


def widths(name):
    """Collect fixed-width macros; ordinary HUK entries are two units."""
    text = row(name)
    calls = re.findall(r"\b(HUKS|HUKW|HUK)\(", text)
    widths = [int(n) for n in re.findall(r"\b(?:HUKS|HUKW)\([^\n]*?,\s*(\d+)\)", text)]
    assert len(widths) <= len(calls), name
    return len(calls) * 2 + sum(w - 2 for w in widths)


class HungarianKeyboardStructure(unittest.TestCase):
    def test_all_alphanumeric_and_control_rows_fit_22_units(self):
        for name in ("NUM_ROW", "ROW1", "ROW2", "ROW3",
                     "SHIFT_ROW1", "SHIFT_ROW2", "SHIFT_ROW3",
                     "BOTTOM", "BOTTOM_LANG", "SYMBOL_ROW2",
                     "SYMBOL_EXTRA_ROW", "SYMBOL_ROW3",
                     "SYMBOL2_ROW1", "SYMBOL2_ROW2",
                     "SYMBOL2_ROW3", "SYMBOL_BOTTOM"):
            with self.subTest(row=name):
                self.assertEqual(widths(name), 22)

    def test_hungarian_special_letters(self):
        for letter in ("á", "é", "ö", "ü", "Á", "É", "Ö", "Ü"):
            self.assertIn(f'"{letter}"', SOURCE)
        for letter in ("ő", "ű", "Ő", "Ű"):
            self.assertIn(f'return "{letter}"', SOURCE)

    def test_forward_delete_and_mode_controls(self):
        self.assertIn("FORWARD_DELETE_KEY", row("NUM_ROW"))
        self.assertIn('HUKS("fn"', row("BOTTOM"))
        self.assertIn('HUKS("fn"', row("SYMBOL_BOTTOM"))
        self.assertIn('HUKS("OK"', row("BOTTOM"))


if __name__ == "__main__":
    unittest.main()
