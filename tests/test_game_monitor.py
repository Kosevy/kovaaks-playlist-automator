import unittest
from core.kovaaks_detector import KovaaksDetector
from core.benchmark_tracker import BenchmarkTracker
from core.game_monitor import GameMonitor


class TestGameMonitor(unittest.TestCase):

    def setUp(self):
        self.detector = KovaaksDetector()
        self.tracker = BenchmarkTracker()
        self.events = []

        self.monitor = GameMonitor(
            detector=self.detector,
            benchmark_tracker=self.tracker,
            target_reps=5,
            notify_early_transition=True,
            on_scenario_transition=lambda next_s, prev_s, reps, early: self.events.append(
                {"event": "transition", "next": next_s, "prev": prev_s, "reps": reps, "early": early}
            ),
            on_rep_completed=lambda sc, rep, score: self.events.append(
                {"event": "rep", "scenario": sc, "rep": rep, "score": score}
            )
        )

    def test_reps_and_normal_transition(self):
        # Iniciar escenario A
        self.monitor._handle_challenge_start("Scenario A")
        self.assertEqual(self.monitor.current_scenario, "Scenario A")
        self.assertEqual(self.monitor.current_reps, 0)

        # 5 repeticiones de escenario A
        for rep in range(1, 6):
            self.monitor._handle_challenge_complete("Scenario A", 1000.0 * rep)
            self.assertEqual(self.monitor.current_reps, rep)

        # Ahora pasar a escenario B (tras 5 reps completadas)
        self.monitor._handle_challenge_start("Scenario B")

        # Verificar que el evento de transición no es temprano (is_early = False)
        transitions = [e for e in self.events if e["event"] == "transition"]
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0]["next"], "Scenario B")
        self.assertEqual(transitions[0]["prev"], "Scenario A")
        self.assertEqual(transitions[0]["reps"], 5)
        self.assertFalse(transitions[0]["early"])

        # Verificar que las repeticiones se resetearon para el escenario B
        self.assertEqual(self.monitor.current_scenario, "Scenario B")
        self.assertEqual(self.monitor.current_reps, 0)

    def test_early_transition_toggle(self):
        # Caso 1: notify_early_transition = True
        self.monitor._handle_challenge_start("Scenario 1")
        self.monitor._handle_challenge_complete("Scenario 1", 500.0)
        self.monitor._handle_challenge_complete("Scenario 1", 520.0)  # 2 reps
        self.monitor._handle_challenge_start("Scenario 2")

        transitions = [e for e in self.events if e["event"] == "transition"]
        self.assertEqual(len(transitions), 1)
        self.assertTrue(transitions[0]["early"])
        self.assertEqual(transitions[0]["reps"], 2)

        # Caso 2: notify_early_transition = False
        self.events.clear()
        self.monitor.set_notify_early_transition(False)
        self.monitor._handle_challenge_complete("Scenario 2", 600.0)  # 1 rep
        self.monitor._handle_challenge_start("Scenario 3")  # Cambio temprano con notificación desactivada

        transitions_disabled = [e for e in self.events if e["event"] == "transition"]
        self.assertEqual(len(transitions_disabled), 0)

    def test_process_stats_csv(self):
        import tempfile
        import os

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", encoding="utf-8") as f:
            f.write("Kills:,10\nScenario:,psalmTS Viscose Click\nScore:,115.5\nHoriz Sens:,2.5\n")
            temp_path = f.name

        try:
            self.monitor._process_stats_csv(temp_path)
            self.assertEqual(self.monitor.current_scenario, "psalmTS Viscose Click")
            self.assertEqual(self.monitor.current_reps, 1)

            rep_events = [e for e in self.events if e["event"] == "rep"]
            self.assertEqual(len(rep_events), 1)
            self.assertEqual(rep_events[0]["scenario"], "psalmTS Viscose Click")
            self.assertEqual(rep_events[0]["score"], 115.5)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_check_playlist_advance(self):
        import tempfile
        import json
        import os

        order_data = {"currentScenarioIndex": 0, "playCounts": [0, 0]}
        prog_data = {
            "scenarioList": [
                {"scenario_name": "Scenario Alpha"},
                {"scenario_name": "Scenario Beta"}
            ]
        }

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f1, \
             tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f2:
            json.dump(order_data, f1)
            json.dump(prog_data, f2)
            order_path = f1.name
            prog_path = f2.name

        try:
            # Primera inicialización: index 0
            self.monitor._check_playlist_advance(order_path, prog_path)
            self.assertEqual(self.monitor.current_scenario, "Scenario Alpha")
            self.assertEqual(len([e for e in self.events if e["event"] == "transition"]), 0)

            # Simulamos 5 repeticiones en Alpha
            for rep in range(1, 6):
                self.monitor._handle_challenge_complete("Scenario Alpha", 100.0)

            # Simulamos que KovaaK's avanzó al escenario Beta (index 1)
            order_data["currentScenarioIndex"] = 1
            with open(order_path, "w", encoding="utf-8") as f:
                json.dump(order_data, f)

            self.monitor._check_playlist_advance(order_path, prog_path)
            self.assertEqual(self.monitor.current_scenario, "Scenario Beta")
            transitions = [e for e in self.events if e["event"] == "transition"]
            self.assertEqual(len(transitions), 1)
            self.assertEqual(transitions[0]["next"], "Scenario Beta")
            self.assertEqual(transitions[0]["prev"], "Scenario Alpha")
            self.assertEqual(transitions[0]["reps"], 5)
            self.assertFalse(transitions[0]["early"])
        finally:
            if os.path.exists(order_path):
                os.remove(order_path)
            if os.path.exists(prog_path):
                os.remove(prog_path)


if __name__ == "__main__":
    unittest.main()
