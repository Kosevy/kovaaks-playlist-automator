import os
import json
import time
import threading
from typing import Optional, Callable, Dict, Any, Set, List

from core.kovaaks_detector import KovaaksDetector
from core.benchmark_tracker import BenchmarkTracker, HighscoreResult


class GameMonitor:
    """
    Monitor en tiempo real que observa la actividad de KovaaK's mediante
    la carpeta stats/, PlaylistOrder.json, PlaylistInProgress.json y el estado del proceso.
    """

    def __init__(
        self,
        detector: KovaaksDetector,
        benchmark_tracker: BenchmarkTracker,
        target_reps: int = 5,
        notify_early_transition: bool = True,
        on_scenario_transition: Optional[Callable[[str, str, int, bool], None]] = None,
        on_rep_completed: Optional[Callable[[str, int, float], None]] = None,
        on_highscore: Optional[Callable[[HighscoreResult], None]] = None,
        on_status_change: Optional[Callable[[bool, str], None]] = None,
        on_game_process_change: Optional[Callable[[bool], None]] = None,
    ):
        self.detector = detector
        self.tracker = benchmark_tracker
        self.target_reps = target_reps
        self.notify_early_transition = notify_early_transition

        self.on_scenario_transition = on_scenario_transition
        self.on_rep_completed = on_rep_completed
        self.on_highscore = on_highscore
        self.on_status_change = on_status_change
        self.on_game_process_change = on_game_process_change

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.is_monitoring = False

        # Estado de sesión
        self.current_scenario: Optional[str] = None
        self.current_reps: int = 0
        self.last_completed_scenario: Optional[str] = None
        self.current_playlist_index: Optional[int] = None

        # Seguimiento de archivos
        self._known_stats_files: Set[str] = set()
        self._last_playlist_order_mtime: float = 0.0
        self._last_process_check_time: float = 0.0
        self.is_game_running: bool = False

    def start(self) -> None:
        """Inicia el monitoreo en segundo plano."""
        if self.is_monitoring:
            return

        self._stop_event.clear()
        self.is_monitoring = True

        # Pre-cargar archivos existentes en stats para no procesar repeticiones antiguas
        stats_dir = self.detector.find_stats_dir()
        if stats_dir and os.path.isdir(stats_dir):
            try:
                for entry in os.scandir(stats_dir):
                    if entry.name.endswith(".csv"):
                        self._known_stats_files.add(entry.name)
            except Exception:
                pass

        # Inicializar estado inicial desde PlaylistOrder / PlaylistInProgress si KovaaK's ya está corriendo
        self._init_current_state()

        self._thread = threading.Thread(target=self._run_loop, name="KovaaksGameMonitor", daemon=True)
        self._thread.start()
        if self.on_status_change:
            self.on_status_change(True, "Monitor activo y escuchando eventos de KovaaK's...")

    def stop(self) -> None:
        """Detiene el hilo de monitoreo."""
        if not self.is_monitoring:
            return

        self._stop_event.set()
        self.is_monitoring = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        if self.on_status_change:
            self.on_status_change(False, "Monitor pausado.")

    def set_notify_early_transition(self, enabled: bool) -> None:
        """Configura si se debe notificar al cambiar de escenario antes de las repeticiones objetivo."""
        self.notify_early_transition = enabled

    def _init_current_state(self) -> None:
        """Detecta el escenario actual si KovaaK's ya está abierto con una playlist en progreso."""
        order_path = self.detector.find_playlist_order_path()
        in_prog_path = self.detector.find_playlist_in_progress_path()

        if order_path and in_prog_path and os.path.isfile(order_path) and os.path.isfile(in_prog_path):
            try:
                self._last_playlist_order_mtime = os.path.getmtime(order_path)
                with open(order_path, "r", encoding="utf-8") as f:
                    order_data = json.load(f)
                with open(in_prog_path, "r", encoding="utf-8") as f:
                    prog_data = json.load(f)

                curr_idx = order_data.get("currentScenarioIndex", 0)
                sc_list = prog_data.get("scenarioList", [])
                play_counts = order_data.get("playCounts", [])

                if 0 <= curr_idx < len(sc_list):
                    self.current_playlist_index = curr_idx
                    self.current_scenario = sc_list[curr_idx].get("scenario_name", "")
                    if curr_idx < len(play_counts):
                        self.current_reps = int(play_counts[curr_idx])
            except Exception:
                pass

    def _run_loop(self) -> None:
        """Bucle principal de seguimiento con bajo consumo de CPU."""
        stats_dir = self.detector.find_stats_dir()
        order_path = self.detector.find_playlist_order_path()
        in_prog_path = self.detector.find_playlist_in_progress_path()

        while not self._stop_event.is_set():
            # 1. Comprobar periódicamente si KovaaK's está en ejecución
            now = time.time()
            if now - self._last_process_check_time > 1.2:
                self._last_process_check_time = now
                running = self.detector.is_game_running()
                if running != self.is_game_running:
                    self.is_game_running = running
                    if self.on_game_process_change:
                        self.on_game_process_change(running)

            # 2. Comprobar cambio de escenario en playlist mediante PlaylistOrder.json
            if order_path and in_prog_path and os.path.isfile(order_path) and os.path.isfile(in_prog_path):
                try:
                    mtime = os.path.getmtime(order_path)
                    if mtime > self._last_playlist_order_mtime:
                        self._last_playlist_order_mtime = mtime
                        self._check_playlist_advance(order_path, in_prog_path)
                except Exception:
                    pass

            # 3. Comprobar nuevas finalizaciones de repetición en stats/*.csv
            if stats_dir and os.path.isdir(stats_dir):
                try:
                    new_entries: List[os.DirEntry] = []
                    for entry in os.scandir(stats_dir):
                        if entry.name.endswith(".csv") and entry.name not in self._known_stats_files:
                            new_entries.append(entry)

                    if new_entries:
                        # Ordenar por tiempo de modificación ascendente para procesar en orden
                        new_entries.sort(key=lambda e: e.stat().st_mtime)
                        for entry in new_entries:
                            self._known_stats_files.add(entry.name)
                            self._process_stats_csv(entry.path)
                except Exception:
                    pass
            else:
                # Reintentar encontrar stats_dir si no estaba disponible
                stats_dir = self.detector.find_stats_dir()

            time.sleep(0.25)

    def _check_playlist_advance(self, order_path: str, in_prog_path: str) -> None:
        """Detecta cuando el usuario pulsa Next o cambia de ejercicio en la playlist."""
        try:
            with open(order_path, "r", encoding="utf-8") as f:
                order_data = json.load(f)
            with open(in_prog_path, "r", encoding="utf-8") as f:
                prog_data = json.load(f)

            curr_idx = order_data.get("currentScenarioIndex", 0)
            sc_list = prog_data.get("scenarioList", [])

            if 0 <= curr_idx < len(sc_list):
                next_scenario = sc_list[curr_idx].get("scenario_name", "")
                if not next_scenario:
                    return

                if self.current_playlist_index is None:
                    self.current_playlist_index = curr_idx
                    if not self.current_scenario:
                        self.current_scenario = next_scenario
                        self.current_reps = 0
                    return

                if curr_idx != self.current_playlist_index:
                    self.current_playlist_index = curr_idx
                    self._handle_scenario_change(next_scenario)
        except Exception:
            pass

    def _handle_scenario_change(self, next_scenario: str) -> None:
        """Maneja el avance a un nuevo escenario (ej. pulsando Next en playlist)."""
        if not next_scenario:
            return

        if not self.current_scenario:
            self.current_scenario = next_scenario
            self.current_reps = 0
            return

        if self.current_scenario == next_scenario:
            return

        prev_scenario = self.current_scenario
        reps_done = self.current_reps
        is_early = reps_done < self.target_reps

        self.current_scenario = next_scenario
        self.current_reps = 0

        should_notify = (not is_early) or self.notify_early_transition
        if should_notify and self.on_scenario_transition:
            self.on_scenario_transition(next_scenario, prev_scenario, reps_done, is_early)

    def _handle_challenge_start(self, scenario: str) -> None:
        """Alias para inicio de escenario."""
        self._handle_scenario_change(scenario)

    def _process_stats_csv(self, file_path: str) -> None:
        """Extrae el escenario y puntaje del archivo CSV generado tras una repetición."""
        sc_name = ""
        score = 0.0

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("Scenario:,"):
                        sc_name = line.split("Scenario:,", 1)[1].strip()
                    elif line.startswith("Score:,"):
                        try:
                            score = float(line.split("Score:,", 1)[1].strip())
                        except ValueError:
                            pass
        except Exception:
            return

        if not sc_name:
            return

        self._handle_challenge_complete(sc_name, score)

    def _handle_challenge_complete(self, scenario: str, score: float) -> None:
        """Maneja la finalización de una repetición registrada por el juego."""
        if self.current_scenario and self.current_scenario != scenario:
            # Transición detectada vía CSV
            self._handle_scenario_change(scenario)
            self.current_reps = 1
        elif self.current_scenario == scenario:
            self.current_reps += 1
        else:
            self.current_scenario = scenario
            self.current_reps = 1

        self.last_completed_scenario = scenario

        # Notificar repetición completada
        if self.on_rep_completed:
            self.on_rep_completed(scenario, self.current_reps, score)

        # Verificar si es un nuevo Highscore en el benchmark
        if score > 0:
            highscore_result = self.tracker.check_score(scenario, score)
            if highscore_result and self.on_highscore:
                self.on_highscore(highscore_result)
