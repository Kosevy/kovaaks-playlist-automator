import unittest
from ui.overlay import get_system_monitors, calculate_corner_position


class TestOverlay(unittest.TestCase):

    def test_get_system_monitors(self):
        monitors = get_system_monitors()
        self.assertIsInstance(monitors, list)
        self.assertGreater(len(monitors), 0)
        first = monitors[0]
        self.assertTrue(first["is_primary"])
        self.assertIn("width", first)
        self.assertIn("height", first)
        self.assertIn("left", first)
        self.assertIn("top", first)

    def test_calculate_corner_position_default(self):
        x, y = calculate_corner_position(monitor_index=0, width=380, height=195, corner="top_right")
        monitors = get_system_monitors()
        prim = monitors[0]
        expected_x = prim["left"] + prim["width"] - 380 - 24
        expected_y = prim["top"] + 32
        self.assertEqual(x, expected_x)
        self.assertEqual(y, expected_y)

    def test_calculate_corner_position_custom_coords(self):
        custom = (123, 456)
        x, y = calculate_corner_position(monitor_index=0, width=380, height=195, custom_coords=custom)
        self.assertEqual((x, y), custom)

    def test_calculate_corner_positions_all_corners(self):
        monitors = get_system_monitors()
        m = monitors[0]
        corners = ["top_left", "top_right", "bottom_left", "bottom_right"]
        for c in corners:
            x, y = calculate_corner_position(monitor_index=0, width=300, height=150, corner=c)
            self.assertIsInstance(x, int)
            self.assertIsInstance(y, int)


if __name__ == "__main__":
    unittest.main()
