import unittest
from core.benchmark_tracker import BenchmarkTracker


class TestBenchmarkTracker(unittest.TestCase):

    def setUp(self):
        self.tracker = BenchmarkTracker()
        self.mock_progress = {
            "overall_rank": 5,
            "benchmark_progress": 250000.0,
            "ranks": [
                {"name": "No Rank", "color": "#ffffff"},
                {"name": "Cinnabar", "color": "#A71112"},
                {"name": "Vermillion", "color": "#F85939"},
                {"name": "Saffron", "color": "#F1C338"},
                {"name": "Celadon", "color": "#9CFF91"},
                {"name": "Viridian", "color": "#368b5c"},
                {"name": "Cerulean", "color": "#02A4D3"},
                {"name": "Lavender", "color": "#C2C2FF"},
                {"name": "Indigo", "color": "#5C3896"},
                {"name": "Fuchsia", "color": "#C74375"}
            ],
            "categories": {
                "Tracking": {
                    "scenarios": {
                        "Smooth Tracking Medium": {
                            "score": 1000000,  # 10000.0 pts
                            "scenario_rank": 3,
                            "rank_maxes": [6000, 7500, 9000, 10500, 12000, 13500]
                        }
                    }
                }
            }
        }
        self.mock_sens = {
            "Smooth Tracking Medium": {
                "Fuchsia": {"median": 34.5},
                "Indigo": {"median": 36.0}
            }
        }
        self.tracker.load_benchmark_data("mock_bench", "mock_steam", self.mock_progress, self.mock_sens)

    def test_load_benchmark_scenarios(self):
        sc = self.tracker.find_scenario("Smooth Tracking Medium")
        self.assertIsNotNone(sc)
        self.assertEqual(sc["high_score"], 10000.0)
        self.assertEqual(sc["rank_idx"], 3)
        self.assertEqual(sc["recommended_sens"], 34.5)

    def test_check_score_no_highscore(self):
        # Puntaje igual o menor no debe ser considerado highscore
        res_lower = self.tracker.check_score("Smooth Tracking Medium", 9500.0)
        self.assertIsNone(res_lower)

        res_equal = self.tracker.check_score("Smooth Tracking Medium", 10000.0)
        self.assertIsNone(res_equal)

    def test_check_score_new_highscore(self):
        # 10250.0 pts (supera 10000.0, pero no sube de rango, sigue en rank 3 < 10500)
        res = self.tracker.check_score("Smooth Tracking Medium", 10250.0)
        self.assertIsNotNone(res)
        self.assertEqual(res.delta_score, 250.0)
        self.assertEqual(res.new_score, 10250.0)
        self.assertFalse(res.rank_up)
        # Rango 3 umbral es 9000 a 10500 (span = 1500). (10250 - 9000)/1500 = 1250/1500 = 83.33%
        self.assertAlmostEqual(res.pct_to_next_rank, 83.3, places=1)
        self.assertEqual(res.points_to_next_rank, 250.0)

    def test_check_score_rank_up(self):
        # 10600.0 pts supera 10500 (sube de rank 3 a rank 4)
        res = self.tracker.check_score("Smooth Tracking Medium", 10600.0)
        self.assertIsNotNone(res)
        self.assertTrue(res.rank_up)
        self.assertEqual(res.new_rank_idx, 4)
        self.assertEqual(res.new_rank_name, "Celadon")


if __name__ == "__main__":
    unittest.main()
