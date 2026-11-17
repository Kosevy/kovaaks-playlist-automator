import os
import json
import tempfile
import unittest

from core.playlist_service import PlaylistService, sanitize_filename, resolve_unique_filepath
from core.benchmark_tracker import BenchmarkTracker, HighscoreResult
from core.kovaaks_detector import KovaaksDetector
from core.extractor import extract_steam_id


class TestCoreLogic(unittest.TestCase):
    """
    Suite de pruebas unitarias puras (sin llamadas de red ni dependencias externas de GUI)
    para la lógica central de KPA: sanitización de rutas, generación de playlists por debilidades,
    rastreador de récords/rangos, conversión matemática de sensibilidad y extracción de Steam ID.
    """

    def test_sanitize_and_unique_filepath(self):
        """1. Sanitización de nombres en Windows y resolución de nombres duplicados únicos."""
        # Sanitización de caracteres prohibidos (< > : " / \ | ? *)
        dirty_name = 'my:playlist/name*?test<foo>bar|baz.json'
        cleaned = sanitize_filename(dirty_name)
        self.assertNotIn(":", cleaned)
        self.assertNotIn("/", cleaned)
        self.assertNotIn("*", cleaned)
        self.assertNotIn("?", cleaned)
        self.assertNotIn("<", cleaned)
        self.assertNotIn(">", cleaned)
        self.assertNotIn("|", cleaned)

        # Fallbacks a nombre por defecto si queda vacío
        self.assertEqual(sanitize_filename(""), "improve-weaknesses")
        self.assertEqual(sanitize_filename("   ...  "), "improve-weaknesses")

        # Resolución de colisión de archivos únicos con directorio temporal
        with tempfile.TemporaryDirectory() as tmp_dir:
            path_0, name_0 = resolve_unique_filepath(tmp_dir, "benchmark_playlist")
            self.assertEqual(name_0, "benchmark_playlist")
            # Simular creación del archivo
            with open(path_0, "w", encoding="utf-8") as f:
                f.write("{}")

            # Segunda llamada debe retornar (1)
            path_1, name_1 = resolve_unique_filepath(tmp_dir, "benchmark_playlist")
            self.assertEqual(name_1, "benchmark_playlist (1)")
            with open(path_1, "w", encoding="utf-8") as f:
                f.write("{}")

            # Tercera llamada debe retornar (2)
            path_2, name_2 = resolve_unique_filepath(tmp_dir, "benchmark_playlist")
            self.assertEqual(name_2, "benchmark_playlist (2)")

    def test_playlist_generation_bottom_5_and_sens_fallback(self):
        """2. Selección de los 5 peores escenarios según puntaje continuo y fallback de sensibilidad."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Datos sintéticos con 7 escenarios y diferentes scores continuos
            progress_data = {
                "categories": {
                    "Clicking": {
                        "scenarios": {
                            "Scenario_Worst": {
                                "score": 100000,  # 1000.0
                                "scenario_rank": 0,
                                "rank_maxes": [5000.0, 10000.0]  # continuous = 0 + 1000/5000 = 0.20
                            },
                            "Scenario_2nd_Worst": {
                                "score": 200000,  # 2000.0
                                "scenario_rank": 0,
                                "rank_maxes": [5000.0, 10000.0]  # continuous = 0 + 2000/5000 = 0.40
                            },
                            "Scenario_3rd_Worst": {
                                "score": 300000,  # 3000.0
                                "scenario_rank": 0,
                                "rank_maxes": [5000.0, 10000.0]  # continuous = 0.60
                            },
                            "Scenario_4th_Worst": {
                                "score": 400000,  # 4000.0
                                "scenario_rank": 0,
                                "rank_maxes": [5000.0, 10000.0]  # continuous = 0.80
                            },
                        }
                    },
                    "Tracking": {
                        "scenarios": {
                            "Scenario_5th_Worst": {
                                "score": 600000,  # 6000.0
                                "scenario_rank": 1,
                                "rank_maxes": [5000.0, 10000.0]  # continuous = 1.0 + (6000-5000)/5000 = 1.20
                            },
                            "Scenario_Good": {
                                "score": 900000,  # 9000.0
                                "scenario_rank": 1,
                                "rank_maxes": [5000.0, 10000.0]  # continuous = 1.80
                            },
                            "Scenario_Best": {
                                "score": 1000000,  # 10000.0
                                "scenario_rank": 2,
                                "rank_maxes": [5000.0, 10000.0]  # continuous = 2.00
                            }
                        }
                    }
                }
            }

            # Sensibilidad con rangos para probar fallback en cascada:
            # Scenario_Worst tiene Fuchsia (máxima jerarquía)
            # Scenario_2nd_Worst tiene solo Indigo (debe hacer fallback a Indigo)
            # Scenario_3rd_Worst no tiene sens_data (debe resultar None)
            sens_data = {
                "Scenario_Worst": {
                    "Fuchsia": {"median": 34.5},
                    "Indigo": {"median": 38.0}
                },
                "Scenario_2nd_Worst": {
                    "Indigo": {"median": 42.0}
                }
            }

            service = PlaylistService()
            result = service.process_and_generate_playlist(
                progress_data=progress_data,
                sens_data=sens_data,
                destination_dir=tmp_dir,
                requested_name="weakness_test"
            )

            scenarios = result["scenarios"]
            # Debe contener exactamente 5 escenarios
            self.assertEqual(len(scenarios), 5)

            selected_names = [sc["name"] for sc in scenarios]
            # Deben ser los 5 peores
            self.assertIn("Scenario_Worst", selected_names)
            self.assertIn("Scenario_2nd_Worst", selected_names)
            self.assertIn("Scenario_3rd_Worst", selected_names)
            self.assertIn("Scenario_4th_Worst", selected_names)
            self.assertIn("Scenario_5th_Worst", selected_names)
            # Los 2 mejores NO deben estar incluidos
            self.assertNotIn("Scenario_Good", selected_names)
            self.assertNotIn("Scenario_Best", selected_names)

            # Validar fallback de sensibilidad
            sc_worst = next(sc for sc in scenarios if sc["name"] == "Scenario_Worst")
            self.assertEqual(sc_worst["sens_rank"], "Fuchsia")
            self.assertEqual(sc_worst["sens_value"], 34.5)

            sc_second = next(sc for sc in scenarios if sc["name"] == "Scenario_2nd_Worst")
            self.assertEqual(sc_second["sens_rank"], "Indigo")
            self.assertEqual(sc_second["sens_value"], 42.0)

            sc_third = next(sc for sc in scenarios if sc["name"] == "Scenario_3rd_Worst")
            self.assertIsNone(sc_third.get("sens_value"))

            # El archivo JSON debe haberse guardado exitosamente
            self.assertTrue(os.path.isfile(result["file_path"]))
            with open(result["file_path"], "r", encoding="utf-8") as f:
                saved_json = json.load(f)
                self.assertIn("scenarioList", saved_json)
                self.assertEqual(len(saved_json["scenarioList"]), 5)

    def test_benchmark_tracker_highscore_and_rankup(self):
        """3. Detección de Highscore, cálculo de deltas y transición de rango (rank up)."""
        tracker = BenchmarkTracker()
        progress_data = {
            "ranks": [
                {"name": "Bronze", "color": "#CD7F32"},
                {"name": "Silver", "color": "#C0C0C0"},
                {"name": "Gold", "color": "#FFD700"},
                {"name": "Platinum", "color": "#E5E4E2"}
            ],
            "overall_rank": 1,
            "benchmark_progress": 45.0,
            "categories": {
                "Static": {
                    "scenarios": {
                        "1w4t": {
                            "score": 80000,  # 800.0 (rango Silver actual)
                            "scenario_rank": 1,
                            "rank_maxes": [600.0, 900.0, 1200.0, 1500.0]
                        }
                    }
                }
            }
        }

        tracker.load_benchmark_data(
            benchmark_id="bench_123",
            steam_id="76561198000000000",
            progress_data=progress_data
        )

        # Caso A: Puntuación inferior o igual al récord actual -> No hay Highscore
        res_low = tracker.check_score("1w4t", 750.0)
        self.assertIsNone(res_low)

        res_equal = tracker.check_score("1w4t", 800.0)
        self.assertIsNone(res_equal)

        # Caso B: Nueva puntuación superior dentro del mismo rango (Silver)
        res_high = tracker.check_score("1w4t", 850.0)
        self.assertIsNotNone(res_high)
        self.assertIsInstance(res_high, HighscoreResult)
        self.assertEqual(res_high.old_score, 800.0)
        self.assertEqual(res_high.new_score, 850.0)
        self.assertEqual(res_high.delta_score, 50.0)
        self.assertFalse(res_high.rank_up)
        self.assertEqual(res_high.new_rank_name, "Silver")
        self.assertEqual(res_high.next_rank_name, "Gold")

        # Caso C: Nueva puntuación que supera el umbral de rango (Silver -> Gold >= 900.0)
        res_rankup = tracker.check_score("1w4t", 950.0)
        self.assertIsNotNone(res_rankup)
        self.assertTrue(res_rankup.rank_up)
        self.assertEqual(res_rankup.old_rank_name, "Silver")
        self.assertEqual(res_rankup.new_rank_name, "Gold")
        self.assertEqual(res_rankup.next_rank_name, "Platinum")

    def test_kovaaks_detector_sens_conversions(self):
        """4. Conversiones matemáticas de sensibilidad (cm/360 <-> in-game) y reciprocidad."""
        detector = KovaaksDetector()

        # Probar escala estándar Quake/Source (yaw increment = 0.022)
        test_cm360 = 38.5
        dpi = 1600
        scale = "Quake/Source"

        ingame = detector.cm360_to_ingame_sens(test_cm360, scale, dpi)
        self.assertGreater(ingame, 0.0)

        # Conversión inversa recíproca debe reconstruir el cm/360 original
        cm360_calc = detector.ingame_sens_to_cm360(ingame, scale, dpi)
        self.assertAlmostEqual(test_cm360, cm360_calc, delta=0.05)

        # Casos límite / valores inválidos
        self.assertEqual(detector.cm360_to_ingame_sens(0, scale, dpi), 0.0)
        self.assertEqual(detector.cm360_to_ingame_sens(-5.0, scale, dpi), 0.0)
        self.assertEqual(detector.cm360_to_ingame_sens(38.5, scale, 0), 0.0)
        self.assertEqual(detector.ingame_sens_to_cm360(0, scale, dpi), 0.0)

    def test_extract_steam_id(self):
        """5. Extracción robusta de Steam ID de 17 dígitos desde URL o texto plano."""
        valid_id = "76561198012345678"

        # Directo
        self.assertEqual(extract_steam_id(valid_id), valid_id)
        # Con espacios alrededor
        self.assertEqual(extract_steam_id(f"  {valid_id}  "), valid_id)
        # Desde URL de perfil de Steam
        url = f"https://steamcommunity.com/profiles/{valid_id}/"
        self.assertEqual(extract_steam_id(url), valid_id)

        # Entradas inválidas deben levantar ValueError
        with self.assertRaises(ValueError):
            extract_steam_id("")
        with self.assertRaises(ValueError):
            extract_steam_id("short12345")
        with self.assertRaises(ValueError):
            extract_steam_id("7656119801234567")  # 16 dígitos


if __name__ == "__main__":
    unittest.main()
