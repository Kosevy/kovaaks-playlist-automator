import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.extractor import extract_steam_id, extract_benchmark_id
from core.playlist_service import sanitize_filename, resolve_unique_filepath, PlaylistService


class TestExtractor(unittest.TestCase):
    def test_extract_steam_id_direct(self):
        self.assertEqual(extract_steam_id("76561198444816419"), "76561198444816419")

    def test_extract_steam_id_url(self):
        url = "https://steamcommunity.com/profiles/76561198444816419/"
        self.assertEqual(extract_steam_id(url), "76561198444816419")

    def test_extract_steam_id_invalid(self):
        with self.assertRaises(ValueError):
            extract_steam_id("12345")  # Menos de 17 dígitos
        with self.assertRaises(ValueError):
            extract_steam_id("")

    def test_extract_benchmark_id_direct(self):
        self.assertEqual(extract_benchmark_id("2336"), "2336")

    def test_extract_benchmark_id_url(self):
        self.assertEqual(extract_benchmark_id("https://evxl.app/benchmarks/2336"), "2336")
        self.assertEqual(extract_benchmark_id("https://kovaaks.com/webapp?benchmarkId=2336"), "2336")

    def test_extract_benchmark_id_invalid(self):
        with self.assertRaises(ValueError):
            extract_benchmark_id("no_id_here")


class TestPlaylistService(unittest.TestCase):
    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename('invalid:name*test?'), "invalidnametest")
        self.assertEqual(sanitize_filename(''), "improve-weaknesses")
        self.assertEqual(sanitize_filename('  test_playlist.  '), "test_playlist")

    def test_sensitivity_fallback(self):
        # Escenario donde Fuchsia no existe pero Indigo sí
        progress_data = {
            "categories": {
                "Tracking": {
                    "scenarios": {
                        "Test Scenario 1": {
                            "score": 1000000,
                            "scenario_rank": 3,
                            "rank_maxes": [5000, 8000, 9000, 11000, 13000]
                        }
                    }
                }
            }
        }
        # Solo Indigo disponible, Fuchsia ausente
        sens_data = {
            "Test Scenario 1": {
                "Indigo": {"median": 35.45}
            }
        }

        import tempfile
        service = PlaylistService()
        with tempfile.TemporaryDirectory() as td:
            res = service.process_and_generate_playlist(
                progress_data, sens_data, td, "fallback_test"
            )
            sc = res["scenarios"][0]
            self.assertEqual(sc["sens_rank"], "Indigo")
            self.assertEqual(sc["sens_value"], 35.5)
            self.assertEqual(sc["sens_display"], "35.5 cm/360 (Indigo)")


if __name__ == "__main__":
    unittest.main()

