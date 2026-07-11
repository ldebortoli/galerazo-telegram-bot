from __future__ import annotations

import struct
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICON_PATH = PROJECT_ROOT / "assets" / "galerazo-bot-icon.ico"


class WindowsIconTests(unittest.TestCase):
    def test_icon_contains_transparent_32_bit_native_sizes(self) -> None:
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
            self.assertEqual(bit_count, 32)
            self.assertGreater(length, 40)
            self.assertLessEqual(offset + length, len(data))
            self.assertEqual(struct.unpack_from("<I", data, offset)[0], 40)

            dib_width, dib_height = struct.unpack_from("<ii", data, offset + 4)
            self.assertEqual(dib_width, width)
            self.assertEqual(dib_height, height * 2)

            pixels_offset = offset + 40
            alpha_values = data[pixels_offset + 3 : pixels_offset + (width * height * 4) : 4]
            self.assertEqual(min(alpha_values), 0)
            self.assertEqual(max(alpha_values), 255)

            visible_pixels = [
                (pixel_index % width, height - 1 - (pixel_index // width))
                for pixel_index, alpha in enumerate(alpha_values)
                if alpha > 8
            ]
            if width <= 64:
                visible_x = [x for x, _ in visible_pixels]
                visible_y = [y for _, y in visible_pixels]
                visible_width = max(visible_x) - min(visible_x) + 1
                visible_height = max(visible_y) - min(visible_y) + 1
                self.assertGreaterEqual(visible_width, int(width * 0.75))
                self.assertGreaterEqual(visible_height, int(height * 0.75))

            mask_offset = pixels_offset + (width * height * 4)
            mask_stride = ((width + 31) // 32) * 4
            for x, y in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
                pixel_offset = pixels_offset + (((height - 1 - y) * width + x) * 4)
                self.assertEqual(data[pixel_offset + 3], 0)
                mask_byte = data[mask_offset + ((height - 1 - y) * mask_stride) + (x // 8)]
                self.assertTrue(mask_byte & (0x80 >> (x % 8)))

        self.assertTrue({16, 20, 24, 32, 48, 256}.issubset(sizes))


if __name__ == "__main__":
    unittest.main()
