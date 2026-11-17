import unittest
from core.kovaaks_detector import KovaaksDetector


class TestKovaaksDetector(unittest.TestCase):

    def setUp(self):
        self.detector = KovaaksDetector()

    def test_default_yaw_increments(self):
        # Verificar factores conocidos
        mr_inc = self.detector.get_yaw_increment("Marvel Rivals")
        self.assertAlmostEqual(mr_inc, 0.0175, places=4)

        ow_inc = self.detector.get_yaw_increment("Overwatch")
        self.assertAlmostEqual(ow_inc, 0.0066, places=4)

        val_inc = self.detector.get_yaw_increment("Valorant")
        self.assertAlmostEqual(val_inc, 0.06996, places=5)

    def test_cm360_conversion_marvel_rivals(self):
        # 50.0 cm/360 @ 1600 DPI en Marvel Rivals -> ~0.65314
        sens = self.detector.cm360_to_ingame_sens(50.0, "Marvel Rivals", 1600)
        self.assertAlmostEqual(sens, 0.65314, places=4)

        # Conversión inversa
        cm = self.detector.ingame_sens_to_cm360(sens, "Marvel Rivals", 1600)
        self.assertAlmostEqual(cm, 50.0, delta=0.1)

    def test_cm360_conversion_overwatch(self):
        # 34.64 cm/360 @ 800 DPI en Overwatch -> 5.0
        sens = self.detector.cm360_to_ingame_sens(34.64, "Overwatch", 800)
        self.assertAlmostEqual(sens, 5.0, delta=0.05)

    def test_zero_or_negative_inputs(self):
        self.assertEqual(self.detector.cm360_to_ingame_sens(0, "Overwatch", 800), 0.0)
        self.assertEqual(self.detector.cm360_to_ingame_sens(34.0, "Overwatch", 0), 0.0)


if __name__ == "__main__":
    unittest.main()
