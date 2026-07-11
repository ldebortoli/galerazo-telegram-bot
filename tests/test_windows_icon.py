from __future__ import annotations

import struct
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICON_PATH = PROJECT_ROOT / "assets" / "galerazo-bot-icon.ico"


class WindowsIconTests(unittest.TestCase):
    def test_icon_contains_valid_native_sizes(self) -> None:
        data = ICON_PATH.read_bytes()
        reserved, image_type, count = struct.unpack_from("<HHH", data)

        self.assertEqual((reserved, image_type), (0, 1))
        self.assertGreaterEqual(count, 4)

        sizes: set[int] = set()
        for index in range(count):
            entry_offset = 6 + (16 * index)
            width, height, _, _, planes, bit_count, length, offset = struct.unpack_from(
                "<BBBBHHII", data, entry_offset
            )
            width = width or 256
            height = height or 256
            sizes.add(width)

            self.assertEqual(width, height)
            self.assertEqual(planes, 1)
            self.assertIn(bit_count, {1, 4, 8, 24, 32})
            self.assertGreater(length, 40)
            self.assertLessEqual(offset + length, len(data))
            self.assertEqual(struct.unpack_from("<I", data, offset)[0], 40)

        self.assertTrue({16, 20, 24, 32, 48, 256}.issubset(sizes))


if __name__ == "__main__":
    unittest.main()
