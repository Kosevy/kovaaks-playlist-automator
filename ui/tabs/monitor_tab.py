from typing import Optional, Callable
import customtkinter as ctk
from core.i18n import t


class MonitorTab(ctk.CTkFrame):
    """
    Pestaña de Monitoreo en Vivo de KPA.
    Muestra el estado de ejecución de KovaaK's, estado del monitor,
    tarjeta de sesión activa (escenario, repeticiones, sensibilidad recomendada)
    y el feed de actividad en tiempo real.
    Totalmente desacoplada de KovaaksDetector y BenchmarkTracker.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        on_toggle_monitor_clicked: Optional[Callable[[], None]] = None,
        on_sync_bench_clicked: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.on_toggle_monitor_clicked = on_toggle_monitor_clicked
        self.on_sync_bench_clicked = on_sync_bench_clicked

        self._current_reps = 0
        self._target_reps = 5
        self._current_scenario_name: Optional[str] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_ui()

    def _build_ui(self):
        # 1. Tarjeta: Estado del Sistema en Tiempo Real
        status_card = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color="#181926",
            border_width=1,
            border_color="#2A2E3D"
        )
        status_card.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        status_card.grid_columnconfigure(2, weight=1)

        self.lbl_game_status = ctk.CTkLabel(
            status_card,
            text=t("monitor.game_not_found"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#565F89"
        )
        self.lbl_game_status.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.lbl_monitor_state = ctk.CTkLabel(
            status_card,
            text=t("monitor.state_active"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#9ECE6A"
        )
        self.lbl_monitor_state.grid(row=0, column=1, padx=15, pady=10, sticky="w")

        # Botones de control del monitor
        btn_box = ctk.CTkFrame(status_card, fg_color="transparent")
        btn_box.grid(row=0, column=2, padx=15, pady=10, sticky="e")

        self.btn_toggle_monitor = ctk.CTkButton(
            btn_box,
            text=t("monitor.btn_pause"),
            width=120,
            height=30,
            corner_radius=6,
            fg_color="#3B4261",
            hover_color="#565F89",
            command=self._handle_toggle_monitor
        )
        self.btn_toggle_monitor.pack(side="left", padx=4)

        self.btn_sync_bench = ctk.CTkButton(
            btn_box,
            text=t("monitor.btn_sync"),
            width=130,
            height=30,
            corner_radius=6,
            fg_color="#24283B",
            hover_color="#3B4261",
            command=self._handle_sync_bench
        )
        self.btn_sync_bench.pack(side="left", padx=4)

        # 2. Tarjeta: Escenario y Sesión Activa
        session_card = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color="#181926",
            border_width=1,
            border_color="#2A2E3D"
        )
        session_card.grid(row=1, column=0, padx=10, pady=4, sticky="ew")
        session_card.grid_columnconfigure(1, weight=1)

        self.lbl_s_title = ctk.CTkLabel(session_card, text=t("monitor.active_scenario_title"), font=ctk.CTkFont(weight="bold"))
        self.lbl_s_title.grid(row=0, column=0, padx=15, pady=(10, 4), sticky="w")

        self.lbl_active_scenario = ctk.CTkLabel(
            session_card,
            text=t("monitor.no_active_scenario"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#7AA2F7"
        )
        self.lbl_active_scenario.grid(row=0, column=1, padx=15, pady=(10, 4), sticky="w")

        self.lbl_r_title = ctk.CTkLabel(session_card, text=t("monitor.reps_title"), font=ctk.CTkFont(weight="bold"))
        self.lbl_r_title.grid(row=1, column=0, padx=15, pady=4, sticky="w")

        rep_box = ctk.CTkFrame(session_card, fg_color="transparent")
        rep_box.grid(row=1, column=1, padx=15, pady=4, sticky="ew")

        self.lbl_active_reps = ctk.CTkLabel(
            rep_box,
            text=t("monitor.reps_count", current=0, target=5),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FFFFFF"
        )
        self.lbl_active_reps.pack(side="left", padx=(0, 10))

        self.prog_reps = ctk.CTkProgressBar(rep_box, width=180, height=10, corner_radius=5)
        self.prog_reps.pack(side="left")
        self.prog_reps.set(0.0)

        self.lbl_sens_title = ctk.CTkLabel(session_card, text=t("monitor.sens_title"), font=ctk.CTkFont(weight="bold"))
        self.lbl_sens_title.grid(row=2, column=0, padx=15, pady=(4, 10), sticky="w")

        self.lbl_active_sens = ctk.CTkLabel(
            session_card,
            text="N/A",
            font=ctk.CTkFont(size=12),
            text_color="#9AA5CE"
        )
        self.lbl_active_sens.grid(row=2, column=1, padx=15, pady=(4, 10), sticky="w")

        # 3. Tarjeta: Feed de Registro en Tiempo Real
        feed_frame = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color="#181926",
            border_width=1,
            border_color="#2A2E3D"
        )
        feed_frame.grid(row=2, column=0, padx=10, pady=(6, 10), sticky="nsew")
        feed_frame.grid_columnconfigure(0, weight=1)
        feed_frame.grid_rowconfigure(1, weight=1)

        self.lbl_feed = ctk.CTkLabel(
            feed_frame,
            text=t("monitor.feed_title"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_feed.grid(row=0, column=0, padx=15, pady=(8, 4), sticky="w")

        self.textbox_monitor_log = ctk.CTkTextbox(
            feed_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            corner_radius=8
        )
        self.textbox_monitor_log.grid(row=1, column=0, padx=12, pady=(4, 12), sticky="nsew")

    def _handle_toggle_monitor(self):
        if self.on_toggle_monitor_clicked:
            self.on_toggle_monitor_clicked()

    def _handle_sync_bench(self):
        if self.on_sync_bench_clicked:
            self.on_sync_bench_clicked()

    def retranslate(self, is_monitoring: bool, is_game_running: bool, current_scenario: Optional[str] = None):
        """Actualiza todos los textos de la pestaña según el idioma activo."""
        self.lbl_s_title.configure(text=t("monitor.active_scenario_title"))
        self.lbl_r_title.configure(text=t("monitor.reps_title"))
        self.lbl_sens_title.configure(text=t("monitor.sens_title"))
        self.lbl_feed.configure(text=t("monitor.feed_title"))
        self.btn_sync_bench.configure(text=t("monitor.btn_sync"))

        btn_toggle_text = t("monitor.btn_pause") if is_monitoring else t("monitor.btn_resume")
        self.btn_toggle_monitor.configure(text=btn_toggle_text)

        state_text = t("monitor.state_active") if is_monitoring else t("monitor.state_paused")
        state_color = "#9ECE6A" if is_monitoring else "#565F89"
        self.lbl_monitor_state.configure(text=state_text, text_color=state_color)

        game_text = t("monitor.game_running") if is_game_running else t("monitor.game_not_found")
        game_color = "#9ECE6A" if is_game_running else "#565F89"
        self.lbl_game_status.configure(text=game_text, text_color=game_color)

        if not current_scenario:
            self.lbl_active_scenario.configure(text=t("monitor.no_active_scenario"))
            self.lbl_active_reps.configure(text=t("monitor.reps_count", current=self._current_reps, target=self._target_reps))
        else:
            self.lbl_active_reps.configure(text=t("monitor.reps_count", current=self._current_reps, target=self._target_reps))

    def update_game_status(self, is_running: bool):
        """Actualiza el indicador visual del proceso KovaaK's."""
        game_text = t("monitor.game_running") if is_running else t("monitor.game_not_found")
        game_color = "#9ECE6A" if is_running else "#565F89"
        self.lbl_game_status.configure(text=game_text, text_color=game_color)

    def update_monitor_state(self, is_monitoring: bool):
        """Actualiza el indicador visual de estado y botón de toggle del monitor."""
        state_text = t("monitor.state_active") if is_monitoring else t("monitor.state_paused")
        state_color = "#9ECE6A" if is_monitoring else "#565F89"
        btn_text = t("monitor.btn_pause") if is_monitoring else t("monitor.btn_resume")
        btn_color = "#3B4261" if is_monitoring else "#3D59A1"

        self.lbl_monitor_state.configure(text=state_text, text_color=state_color)
        self.btn_toggle_monitor.configure(text=btn_text, fg_color=btn_color)

    def update_rep_progress(self, rep_number: int, target: int = 5):
        """Actualiza la barra y contador de repeticiones de la sesión activa."""
        self._current_reps = rep_number
        self._target_reps = target
        self.lbl_active_reps.configure(text=t("monitor.reps_count", current=rep_number, target=target))
        self.prog_reps.set(min(1.0, rep_number / float(target)))

    def update_active_scenario(
        self,
        scenario_name: Optional[str],
        sens_text: Optional[str] = None,
        reps: int = 0,
        target_reps: int = 5
    ):
        """Actualiza la información de la tarjeta de sesión activa."""
        self._current_scenario_name = scenario_name
        self._current_reps = reps
        self._target_reps = target_reps

        if scenario_name:
            self.lbl_active_scenario.configure(text=scenario_name)
        else:
            self.lbl_active_scenario.configure(text=t("monitor.no_active_scenario"))

        if sens_text is not None:
            self.lbl_active_sens.configure(text=sens_text)

        self.lbl_active_reps.configure(text=t("monitor.reps_count", current=reps, target=target_reps))
        self.prog_reps.set(min(1.0, reps / float(target_reps)) if target_reps > 0 else 0.0)

    def append_log(self, text: str):
        """Agrega texto al feed de eventos del monitor y desplaza al final."""
        self.textbox_monitor_log.insert("end", text)
        self.textbox_monitor_log.see("end")
