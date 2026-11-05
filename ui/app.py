import os
import subprocess
import threading
from typing import Dict, Any, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.config import ConfigManager
from core.extractor import extract_steam_id, extract_benchmark_id, extract_benchmark_info
from core.benchmark_resolver import BenchmarkResolver
from core.api_client import KovaaksApiClient
from core.playlist_service import PlaylistService
from core.kovaaks_detector import KovaaksDetector
from core.benchmark_tracker import BenchmarkTracker, HighscoreResult
from core.game_monitor import GameMonitor
from core.i18n import t, get_i18n, detect_system_language
from ui.overlay import SensOverlayWindow, HighscoreOverlayWindow


class KPAApp(ctk.CTk):
    """Interfaz gráfica principal de KovaaK's Playlist Automator & Live Tracker."""

    def __init__(self):
        super().__init__()

        # 1. Configuración de Apariencia
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # 2. Servicios del Core
        self.config_manager = ConfigManager()
        self.config_data = self.config_manager.load_config()

        # Configurar idioma activo
        initial_lang = self.config_data.get("language") or detect_system_language()
        get_i18n().set_language(initial_lang)

        self.title(t("header.title"))
        self.geometry("820x760")
        self.minsize(740, 660)

        self.benchmark_resolver = BenchmarkResolver()
        self.api_client = KovaaksApiClient()
        self.playlist_service = PlaylistService()

        # Detector de KovaaK's y Rastreador de Benchmarks
        self.detector = KovaaksDetector(custom_playlist_dir=self.config_data.get("playlist_dir"))
        self.benchmark_tracker = BenchmarkTracker()

        # Overlays activos
        self.active_sens_overlay: Optional[SensOverlayWindow] = None
        self.active_highscore_overlay: Optional[HighscoreOverlayWindow] = None

        # Monitor de Juego en Vivo
        self.game_monitor = GameMonitor(
            detector=self.detector,
            benchmark_tracker=self.benchmark_tracker,
            target_reps=5,
            notify_early_transition=self.config_data.get("notify_early_transition", True),
            on_scenario_transition=self._on_scenario_transition_event,
            on_rep_completed=self._on_rep_completed_event,
            on_highscore=self._on_highscore_event,
            on_status_change=self._on_monitor_status_change,
            on_game_process_change=self._on_game_process_change
        )

        # Variable para controlar estado de ejecución
        self.is_processing = False

        # Registrar listener para cambio de idioma en caliente
        get_i18n().register_listener(self._retranslate_ui)

        # Protocolo de cierre para persistir valores y detener hilos
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 3. Construcción de la UI
        self._create_widgets()
        self._load_saved_values()

        # 4. Iniciar monitor si está habilitado en configuración
        if self.config_data.get("monitor_enabled", True):
            self.game_monitor.start()

        # 5. Carga inicial en segundo plano de datos del benchmark si ya están guardados
        self._initial_benchmark_preload()

    def _create_widgets(self):
        # Grid principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- ENCABEZADO SUPERIOR ---
        header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(12, 6), sticky="ew")

        top_title_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_title_row.pack(fill="x")

        self.title_label = ctk.CTkLabel(
            top_title_row,
            text=t("header.title"),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        self.title_label.pack(side="left")

        # Controles del lado derecho del encabezado: Insignia de monitor y Selector rápido de idioma
        top_right_box = ctk.CTkFrame(top_title_row, fg_color="transparent")
        top_right_box.pack(side="right")

        self.lbl_monitor_badge = ctk.CTkLabel(
            top_right_box,
            text=t("header.badge_inactive"),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#565F89"
        )
        self.lbl_monitor_badge.pack(side="left", padx=(0, 12))

        # Selector rápido de idioma tipo píldora [ ES | EN ]
        current_lang_upper = get_i18n().language.upper()
        self.btn_lang_toggle = ctk.CTkSegmentedButton(
            top_right_box,
            values=["ES", "EN"],
            width=75,
            height=26,
            corner_radius=6,
            command=self._on_header_lang_changed
        )
        self.btn_lang_toggle.set(current_lang_upper)
        self.btn_lang_toggle.pack(side="right")

        self.subtitle_label = ctk.CTkLabel(
            header_frame,
            text=t("header.subtitle"),
            font=ctk.CTkFont(size=12),
            text_color="#7982A9"
        )
        self.subtitle_label.pack(anchor="w", pady=(2, 0))

        # --- TABVIEW PRINCIPAL (better-ui: radius 12) ---
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.grid(row=1, column=0, padx=20, pady=(4, 15), sticky="nsew")

        # Nombres internos de pestañas (constantes como claves)
        self._tab_key_gen = "tab_generator"
        self._tab_key_mon = "tab_monitor"
        self._tab_key_set = "tab_settings"

        self.tab_generator = self.tabview.add(self._tab_key_gen)
        self.tab_monitor = self.tabview.add(self._tab_key_mon)
        self.tab_settings = self.tabview.add(self._tab_key_set)

        self._build_generator_tab()
        self._build_monitor_tab()
        self._build_settings_tab()

        # Configurar títulos iniciales de pestañas
        self._update_tab_titles()

    def _update_tab_titles(self):
        """Actualiza los títulos visibles de los botones del tabview según el idioma."""
        try:
            buttons = self.tabview._segmented_button._buttons_dict
            if self._tab_key_gen in buttons:
                buttons[self._tab_key_gen].configure(text=t("tabs.generator"))
            if self._tab_key_mon in buttons:
                buttons[self._tab_key_mon].configure(text=t("tabs.monitor"))
            if self._tab_key_set in buttons:
                buttons[self._tab_key_set].configure(text=t("tabs.settings"))
        except Exception:
            pass

    def _build_generator_tab(self):
        tab = self.tab_generator
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Formulario de Entrada
        form_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#181926", border_width=1, border_color="#2A2E3D")
        form_frame.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)

        # 1. Steam ID
        self.steam_label = ctk.CTkLabel(form_frame, text=t("generator.steam_label"), font=ctk.CTkFont(weight="bold"))
        self.steam_label.grid(row=0, column=0, padx=(15, 10), pady=(12, 6), sticky="w")

        self.entry_steam = ctk.CTkEntry(
            form_frame,
            placeholder_text=t("generator.steam_placeholder")
        )
        self.entry_steam.grid(row=0, column=1, columnspan=2, padx=(0, 15), pady=(12, 6), sticky="ew")

        # 2. Benchmark ID
        self.bench_label = ctk.CTkLabel(form_frame, text=t("generator.bench_label"), font=ctk.CTkFont(weight="bold"))
        self.bench_label.grid(row=1, column=0, padx=(15, 10), pady=6, sticky="w")

        self.entry_benchmark = ctk.CTkEntry(
            form_frame,
            placeholder_text=t("generator.bench_placeholder")
        )
        self.entry_benchmark.grid(row=1, column=1, columnspan=2, padx=(0, 15), pady=6, sticky="ew")

        # 3. Directorio de Playlists Local
        self.dir_label = ctk.CTkLabel(form_frame, text=t("generator.dir_label"), font=ctk.CTkFont(weight="bold"))
        self.dir_label.grid(row=2, column=0, padx=(15, 10), pady=6, sticky="w")

        self.entry_dir = ctk.CTkEntry(
            form_frame,
            placeholder_text=t("generator.dir_placeholder")
        )
        self.entry_dir.grid(row=2, column=1, padx=(0, 10), pady=6, sticky="ew")

        self.btn_browse = ctk.CTkButton(
            form_frame,
            text=t("generator.browse_btn"),
            width=90,
            command=self._on_browse_directory
        )
        self.btn_browse.grid(row=2, column=2, padx=(0, 15), pady=6, sticky="e")

        # 4. Nombre de la Playlist
        self.name_label = ctk.CTkLabel(form_frame, text=t("generator.name_label"), font=ctk.CTkFont(weight="bold"))
        self.name_label.grid(row=3, column=0, padx=(15, 10), pady=(6, 12), sticky="w")

        self.entry_name = ctk.CTkEntry(
            form_frame,
            placeholder_text=t("generator.name_placeholder")
        )
        self.entry_name.grid(row=3, column=1, columnspan=2, padx=(0, 15), pady=(6, 12), sticky="ew")

        # Fila de Acción
        action_frame = ctk.CTkFrame(tab, fg_color="transparent")
        action_frame.grid(row=1, column=0, padx=10, pady=(6, 4), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.btn_generate = ctk.CTkButton(
            action_frame,
            text=t("generator.generate_btn"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self._on_generate_clicked
        )
        self.btn_generate.grid(row=0, column=0, sticky="ew")

        self.lbl_status = ctk.CTkLabel(
            action_frame,
            text=t("generator.ready_status"),
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.lbl_status.grid(row=1, column=0, pady=(4, 0), sticky="w")

        # Consola de Resultados
        output_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#181926", border_width=1, border_color="#2A2E3D")
        output_frame.grid(row=2, column=0, padx=10, pady=(6, 10), sticky="nsew")
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(1, weight=1)

        top_output_bar = ctk.CTkFrame(output_frame, fg_color="transparent")
        top_output_bar.grid(row=0, column=0, padx=15, pady=(8, 4), sticky="ew")
        top_output_bar.grid_columnconfigure(0, weight=1)

        self.lbl_console = ctk.CTkLabel(
            top_output_bar,
            text=t("generator.console_title"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_console.grid(row=0, column=0, sticky="w")

        self.btn_open_folder = ctk.CTkButton(
            top_output_bar,
            text=t("generator.open_folder_btn"),
            width=95,
            height=26,
            fg_color="#24283B",
            hover_color="#3B4261",
            command=self._on_open_folder
        )
        self.btn_open_folder.grid(row=0, column=1, padx=(5, 5), sticky="e")

        self.btn_clear = ctk.CTkButton(
            top_output_bar,
            text=t("generator.clear_btn"),
            width=65,
            height=26,
            fg_color="#24283B",
            hover_color="#3B4261",
            command=self._clear_textbox
        )
        self.btn_clear.grid(row=0, column=2, sticky="e")

        self.textbox_output = ctk.CTkTextbox(
            output_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            corner_radius=8
        )
        self.textbox_output.grid(row=1, column=0, padx=12, pady=(4, 12), sticky="nsew")

    def _build_monitor_tab(self):
        tab = self.tab_monitor
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Tarjeta 1: Estado del Sistema en Tiempo Real
        status_card = ctk.CTkFrame(tab, corner_radius=10, fg_color="#181926", border_width=1, border_color="#2A2E3D")
        status_card.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        status_card.grid_columnconfigure(2, weight=1)

        game_is_up = self.detector.is_game_running()
        game_text = t("monitor.game_running") if game_is_up else t("monitor.game_not_found")
        game_color = "#9ECE6A" if game_is_up else "#565F89"
        self.lbl_game_status = ctk.CTkLabel(
            status_card,
            text=game_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=game_color
        )
        self.lbl_game_status.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.lbl_monitor_state = ctk.CTkLabel(
            status_card,
            text=t("monitor.state_active") if self.game_monitor.is_monitoring else t("monitor.state_paused"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#9ECE6A" if self.game_monitor.is_monitoring else "#565F89"
        )
        self.lbl_monitor_state.grid(row=0, column=1, padx=15, pady=10, sticky="w")

        # Botones de control del monitor
        btn_box = ctk.CTkFrame(status_card, fg_color="transparent")
        btn_box.grid(row=0, column=2, padx=15, pady=10, sticky="e")

        btn_toggle_text = t("monitor.btn_pause") if self.game_monitor.is_monitoring else t("monitor.btn_resume")
        self.btn_toggle_monitor = ctk.CTkButton(
            btn_box,
            text=btn_toggle_text,
            width=120,
            height=30,
            corner_radius=6,
            fg_color="#3B4261" if self.game_monitor.is_monitoring else "#3D59A1",
            hover_color="#565F89",
            command=self._on_toggle_monitor_clicked
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
            command=self._on_sync_bench_clicked
        )
        self.btn_sync_bench.pack(side="left", padx=4)

        # Tarjeta 2: Escenario y Sesión Activa
        session_card = ctk.CTkFrame(tab, corner_radius=10, fg_color="#181926", border_width=1, border_color="#2A2E3D")
        session_card.grid(row=1, column=0, padx=10, pady=4, sticky="ew")
        session_card.grid_columnconfigure(1, weight=1)

        self.lbl_s_title = ctk.CTkLabel(session_card, text=t("monitor.active_scenario_title"), font=ctk.CTkFont(weight="bold"))
        self.lbl_s_title.grid(row=0, column=0, padx=15, pady=(10, 4), sticky="w")

        init_sc = self.game_monitor.current_scenario or t("monitor.no_active_scenario")
        self.lbl_active_scenario = ctk.CTkLabel(
            session_card,
            text=init_sc,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#7AA2F7"
        )
        self.lbl_active_scenario.grid(row=0, column=1, padx=15, pady=(10, 4), sticky="w")

        self.lbl_r_title = ctk.CTkLabel(session_card, text=t("monitor.reps_title"), font=ctk.CTkFont(weight="bold"))
        self.lbl_r_title.grid(row=1, column=0, padx=15, pady=4, sticky="w")

        rep_box = ctk.CTkFrame(session_card, fg_color="transparent")
        rep_box.grid(row=1, column=1, padx=15, pady=4, sticky="ew")

        init_reps = self.game_monitor.current_reps
        self.lbl_active_reps = ctk.CTkLabel(
            rep_box,
            text=t("monitor.reps_count", current=init_reps, target=5),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FFFFFF"
        )
        self.lbl_active_reps.pack(side="left", padx=(0, 10))

        self.prog_reps = ctk.CTkProgressBar(rep_box, width=180, height=10, corner_radius=5)
        self.prog_reps.pack(side="left")
        self.prog_reps.set(min(1.0, init_reps / 5.0))

        self.lbl_sens_title = ctk.CTkLabel(session_card, text=t("monitor.sens_title"), font=ctk.CTkFont(weight="bold"))
        self.lbl_sens_title.grid(row=2, column=0, padx=15, pady=(4, 10), sticky="w")

        init_sens_text = "N/A"
        if self.game_monitor.current_scenario:
            s_info = self.benchmark_tracker.get_recommended_sens(self.game_monitor.current_scenario)
            if s_info:
                u_set = self.detector.load_user_settings()
                ingame_v = self.detector.cm360_to_ingame_sens(
                    s_info["cm360"],
                    u_set.get("sens_scale", "Marvel Rivals"),
                    u_set.get("dpi", 1600)
                )
                init_sens_text = f"{s_info['cm360']} cm/360 ({ingame_v} in-game)"

        self.lbl_active_sens = ctk.CTkLabel(
            session_card,
            text=init_sens_text,
            font=ctk.CTkFont(size=12),
            text_color="#9AA5CE"
        )
        self.lbl_active_sens.grid(row=2, column=1, padx=15, pady=(4, 10), sticky="w")

        # Tarjeta 3: Feed de Registro en Tiempo Real
        feed_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#181926", border_width=1, border_color="#2A2E3D")
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

    def _build_settings_tab(self):
        tab = self.tab_settings
        tab.grid_columnconfigure(0, weight=1)

        # Tarjeta de Ajustes
        settings_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#181926", border_width=1, border_color="#2A2E3D")
        settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # 0. Selector de Idioma Formal
        self.lbl_lang = ctk.CTkLabel(
            settings_frame,
            text=t("settings.language_label"),
            font=ctk.CTkFont(weight="bold")
        )
        self.lbl_lang.grid(row=row, column=0, padx=(20, 10), pady=(15, 8), sticky="w")

        self.menu_language = ctk.CTkOptionMenu(
            settings_frame,
            values=["Español (ES)", "English (EN)"],
            command=self._on_settings_lang_changed
        )
        self.menu_language.grid(row=row, column=1, padx=(0, 20), pady=(15, 8), sticky="w")
        row += 1

        # 1. Auto-copiar al portapapeles
        self.switch_auto_copy = ctk.CTkSwitch(
            settings_frame,
            text=t("settings.auto_copy_switch"),
            font=ctk.CTkFont(weight="bold")
        )
        self.switch_auto_copy.grid(row=row, column=0, columnspan=2, padx=20, pady=8, sticky="w")
        row += 1

        # 2. Formato preferido al copiar
        self.lbl_format = ctk.CTkLabel(
            settings_frame,
            text=t("settings.copy_format_label"),
            font=ctk.CTkFont(weight="bold")
        )
        self.lbl_format.grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")

        self.segmented_copy_format = ctk.CTkSegmentedButton(
            settings_frame,
            values=[t("settings.format_cm360"), t("settings.format_ingame")]
        )
        self.segmented_copy_format.grid(row=row, column=1, padx=(0, 20), pady=8, sticky="w")
        row += 1

        # 3. Notificar cambio anticipado
        self.switch_early_notify = ctk.CTkSwitch(
            settings_frame,
            text=t("settings.early_notify_switch"),
            font=ctk.CTkFont(weight="bold")
        )
        self.switch_early_notify.grid(row=row, column=0, columnspan=2, padx=20, pady=8, sticky="w")
        row += 1

        # 4. Auto-cierre de overlays
        self.switch_auto_close = ctk.CTkSwitch(
            settings_frame,
            text=t("settings.auto_close_switch"),
            font=ctk.CTkFont(weight="bold"),
            command=self._on_auto_close_toggle
        )
        self.switch_auto_close.grid(row=row, column=0, columnspan=2, padx=20, pady=8, sticky="w")
        row += 1

        # 5. Duración de auto-cierre
        self.lbl_secs = ctk.CTkLabel(
            settings_frame,
            text=t("settings.auto_close_secs_label"),
            font=ctk.CTkFont(weight="bold")
        )
        self.lbl_secs.grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")

        self.entry_auto_close_sec = ctk.CTkEntry(
            settings_frame,
            width=70,
            placeholder_text="8"
        )
        self.entry_auto_close_sec.grid(row=row, column=1, padx=(0, 20), pady=8, sticky="w")
        row += 1

        # 6. Esquina de posicionamiento
        self.lbl_corner = ctk.CTkLabel(
            settings_frame,
            text=t("settings.corner_label"),
            font=ctk.CTkFont(weight="bold")
        )
        self.lbl_corner.grid(row=row, column=0, padx=(20, 10), pady=(8, 15), sticky="w")

        self.menu_corner = ctk.CTkOptionMenu(
            settings_frame,
            values=[
                t("settings.corner_top_right"),
                t("settings.corner_top_left"),
                t("settings.corner_bottom_right"),
                t("settings.corner_bottom_left")
            ]
        )
        self.menu_corner.grid(row=row, column=1, padx=(0, 20), pady=(8, 15), sticky="w")
        row += 1

        # Tarjeta de Pruebas de Overlays
        test_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color="#181926", border_width=1, border_color="#2A2E3D")
        test_frame.grid(row=1, column=0, padx=10, pady=8, sticky="ew")

        self.lbl_test_title = ctk.CTkLabel(
            test_frame,
            text=t("settings.test_section_title"),
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_test_title.pack(anchor="w", padx=15, pady=(12, 4))

        self.lbl_test_desc = ctk.CTkLabel(
            test_frame,
            text=t("settings.test_section_desc"),
            font=ctk.CTkFont(size=11),
            text_color="#7982A9"
        )
        self.lbl_test_desc.pack(anchor="w", padx=15, pady=(0, 10))

        btn_test_box = ctk.CTkFrame(test_frame, fg_color="transparent")
        btn_test_box.pack(fill="x", padx=15, pady=(0, 14))

        self.btn_test_sens = ctk.CTkButton(
            btn_test_box,
            text=t("settings.test_sens_btn"),
            height=34,
            corner_radius=6,
            fg_color="#24283B",
            hover_color="#3B4261",
            command=self._test_sens_overlay
        )
        self.btn_test_sens.pack(side="left", padx=(0, 10))

        self.btn_test_high = ctk.CTkButton(
            btn_test_box,
            text=t("settings.test_high_btn"),
            height=34,
            corner_radius=6,
            fg_color="#24283B",
            hover_color="#3B4261",
            command=self._test_highscore_overlay
        )
        self.btn_test_high.pack(side="left")

    def _on_header_lang_changed(self, value: str):
        """Manejador cuando el usuario cambia el idioma desde el botón del encabezado."""
        new_lang = value.lower()
        if new_lang != get_i18n().language:
            get_i18n().set_language(new_lang)
            self._save_current_values()

    def _on_settings_lang_changed(self, value: str):
        """Manejador cuando el usuario cambia el idioma desde el menú de ajustes."""
        new_lang = "en" if "EN" in value else "es"
        if new_lang != get_i18n().language:
            get_i18n().set_language(new_lang)
            self._save_current_values()

    def _retranslate_ui(self):
        """Actualiza dinámicamente todos los elementos de la interfaz al idioma activo."""
        self.title(t("header.title"))

        # Encabezado
        self.title_label.configure(text=t("header.title"))
        self.subtitle_label.configure(text=t("header.subtitle"))

        # Estado del monitor en badge
        if self.game_monitor.is_monitoring:
            self.lbl_monitor_badge.configure(text=t("header.badge_active"))
        else:
            self.lbl_monitor_badge.configure(text=t("header.badge_paused"))

        # Botones de selección de idioma sincronizados
        current_lang = get_i18n().language
        self.btn_lang_toggle.set(current_lang.upper())
        self.menu_language.set("English (EN)" if current_lang == "en" else "Español (ES)")

        # Pestañas
        self._update_tab_titles()

        # Generador Tab
        self.steam_label.configure(text=t("generator.steam_label"))
        self.entry_steam.configure(placeholder_text=t("generator.steam_placeholder"))
        self.bench_label.configure(text=t("generator.bench_label"))
        self.entry_benchmark.configure(placeholder_text=t("generator.bench_placeholder"))
        self.dir_label.configure(text=t("generator.dir_label"))
        self.entry_dir.configure(placeholder_text=t("generator.dir_placeholder"))
        self.btn_browse.configure(text=t("generator.browse_btn"))
        self.name_label.configure(text=t("generator.name_label"))
        self.entry_name.configure(placeholder_text=t("generator.name_placeholder"))
        self.btn_generate.configure(text=t("generator.generate_btn"))
        self.lbl_console.configure(text=t("generator.console_title"))
        self.btn_open_folder.configure(text=t("generator.open_folder_btn"))
        self.btn_clear.configure(text=t("generator.clear_btn"))

        # Monitor Tab
        self.lbl_s_title.configure(text=t("monitor.active_scenario_title"))
        self.lbl_r_title.configure(text=t("monitor.reps_title"))
        self.lbl_sens_title.configure(text=t("monitor.sens_title"))
        self.lbl_feed.configure(text=t("monitor.feed_title"))
        self.btn_sync_bench.configure(text=t("monitor.btn_sync"))

        btn_toggle_text = t("monitor.btn_pause") if self.game_monitor.is_monitoring else t("monitor.btn_resume")
        self.btn_toggle_monitor.configure(text=btn_toggle_text)
        state_text = t("monitor.state_active") if self.game_monitor.is_monitoring else t("monitor.state_paused")
        self.lbl_monitor_state.configure(text=state_text)

        game_is_up = self.detector.is_game_running()
        game_text = t("monitor.game_running") if game_is_up else t("monitor.game_not_found")
        game_color = "#9ECE6A" if game_is_up else "#565F89"
        self.lbl_game_status.configure(text=game_text, text_color=game_color)

        if not self.game_monitor.current_scenario:
            self.lbl_active_scenario.configure(text=t("monitor.no_active_scenario"))
            self.lbl_active_reps.configure(text=t("monitor.reps_count", current=0, target=5))

        # Ajustes Tab
        self.lbl_lang.configure(text=t("settings.language_label"))
        self.switch_auto_copy.configure(text=t("settings.auto_copy_switch"))
        self.lbl_format.configure(text=t("settings.copy_format_label"))
        self.segmented_copy_format.configure(values=[t("settings.format_cm360"), t("settings.format_ingame")])

        # Preservar selección activa en segmented
        curr_fmt = "ingame" if self.config_data.get("preferred_copy_format") == "ingame" else "cm360"
        self.segmented_copy_format.set(t("settings.format_ingame") if curr_fmt == "ingame" else t("settings.format_cm360"))

        self.switch_early_notify.configure(text=t("settings.early_notify_switch"))
        self.switch_auto_close.configure(text=t("settings.auto_close_switch"))
        self.lbl_secs.configure(text=t("settings.auto_close_secs_label"))
        self.lbl_corner.configure(text=t("settings.corner_label"))

        corner_opts = [
            t("settings.corner_top_right"),
            t("settings.corner_top_left"),
            t("settings.corner_bottom_right"),
            t("settings.corner_bottom_left")
        ]
        self.menu_corner.configure(values=corner_opts)
        self._update_corner_menu_selection()

        self.lbl_test_title.configure(text=t("settings.test_section_title"))
        self.lbl_test_desc.configure(text=t("settings.test_section_desc"))
        self.btn_test_sens.configure(text=t("settings.test_sens_btn"))
        self.btn_test_high.configure(text=t("settings.test_high_btn"))

    def _update_corner_menu_selection(self):
        saved_corner = self.config_data.get("overlay_corner", "top_right")
        mapping = {
            "top_right": t("settings.corner_top_right"),
            "top_left": t("settings.corner_top_left"),
            "bottom_right": t("settings.corner_bottom_right"),
            "bottom_left": t("settings.corner_bottom_left")
        }
        self.menu_corner.set(mapping.get(saved_corner, t("settings.corner_top_right")))

    def _on_auto_close_toggle(self):
        is_on = self.switch_auto_close.get() == 1
        self.entry_auto_close_sec.configure(state="normal" if is_on else "disabled")

    def _load_saved_values(self):
        """Carga los valores guardados en config.json en los campos de la UI."""
        steam_val = self.config_data.get("steam_input", "")
        bench_val = self.config_data.get("benchmark_input", "")
        dir_val = self.config_data.get("playlist_dir", "")
        name_val = self.config_data.get("playlist_name", "improve-weaknesses")

        if steam_val:
            self.entry_steam.insert(0, steam_val)
        if bench_val:
            self.entry_benchmark.insert(0, bench_val)
        if dir_val:
            self.entry_dir.insert(0, dir_val)
        if name_val:
            self.entry_name.insert(0, name_val)

        # Ajustes
        auto_copy = self.config_data.get("auto_copy_sens", True)
        self.switch_auto_copy.select() if auto_copy else self.switch_auto_copy.deselect()

        pref_fmt = self.config_data.get("preferred_copy_format", "cm360")
        self.segmented_copy_format.set(t("settings.format_cm360") if pref_fmt == "cm360" else t("settings.format_ingame"))

        early_notify = self.config_data.get("notify_early_transition", True)
        self.switch_early_notify.select() if early_notify else self.switch_early_notify.deselect()

        auto_close = self.config_data.get("auto_close_overlay", False)
        if auto_close:
            self.switch_auto_close.select()
            self.entry_auto_close_sec.configure(state="normal")
        else:
            self.switch_auto_close.deselect()
            self.entry_auto_close_sec.configure(state="disabled")

        secs = str(self.config_data.get("auto_close_seconds", 8))
        self.entry_auto_close_sec.delete(0, "end")
        self.entry_auto_close_sec.insert(0, secs)

        self._update_corner_menu_selection()

        self._append_text(t("generator.initial_banner"))

    def _save_current_values(self):
        """Guarda los valores actuales de los campos en config.json."""
        current_corner_text = self.menu_corner.get()
        corner_key = "top_right"
        if current_corner_text == t("settings.corner_top_left"):
            corner_key = "top_left"
        elif current_corner_text == t("settings.corner_bottom_right"):
            corner_key = "bottom_right"
        elif current_corner_text == t("settings.corner_bottom_left"):
            corner_key = "bottom_left"

        pref_fmt_key = "cm360" if self.segmented_copy_format.get() == t("settings.format_cm360") else "ingame"

        try:
            sec_val = int(self.entry_auto_close_sec.get().strip() or "8")
        except ValueError:
            sec_val = 8

        self.config_data.update({
            "steam_input": self.entry_steam.get().strip(),
            "benchmark_input": self.entry_benchmark.get().strip(),
            "playlist_dir": self.entry_dir.get().strip(),
            "playlist_name": self.entry_name.get().strip() or "improve-weaknesses",
            "language": get_i18n().language,
            "auto_copy_sens": self.switch_auto_copy.get() == 1,
            "preferred_copy_format": pref_fmt_key,
            "notify_early_transition": self.switch_early_notify.get() == 1,
            "auto_close_overlay": self.switch_auto_close.get() == 1,
            "auto_close_seconds": sec_val,
            "overlay_corner": corner_key,
            "monitor_enabled": self.game_monitor.is_monitoring
        })

        # Notificar al monitor del cambio de configuración
        self.game_monitor.set_notify_early_transition(self.config_data["notify_early_transition"])

        try:
            self.config_manager.save_config(self.config_data)
        except Exception as e:
            self._append_text(f"[ADVERTENCIA / WARNING] config.json: {e}\n")

    def _initial_benchmark_preload(self):
        """Pre-carga los datos del benchmark en segundo plano si ya hay credenciales en config."""
        bench_input = self.config_data.get("benchmark_input", "").strip()
        steam_input = self.config_data.get("steam_input", "").strip()

        if bench_input and steam_input:
            def bg_load():
                try:
                    bench_info = self.benchmark_resolver.resolve_benchmark(bench_input)
                    b_id = bench_info["benchmark_id"]
                    s_id = extract_steam_id(steam_input)
                    prog = self.api_client.fetch_player_progress(b_id, s_id)
                    sens = self.api_client.fetch_sensitivity_distributions(b_id)
                    self.benchmark_tracker.load_benchmark_data(
                        benchmark_id=b_id,
                        steam_id=s_id,
                        progress_data=prog,
                        sens_data=sens,
                        benchmark_name=bench_info.get("benchmark_name")
                    )
                    b_name = bench_info.get("benchmark_name", b_id)
                    count = len(self.benchmark_tracker.scenarios)
                    self.after(0, lambda: self._append_monitor_log(
                        t("monitor.preload_success", name=b_name, count=count)
                    ))
                except Exception as e:
                    self.after(0, lambda err=e: self._append_monitor_log(
                        t("monitor.preload_fail", error=str(err))
                    ))

            threading.Thread(target=bg_load, daemon=True).start()

    def _on_closing(self):
        """Manejador del evento de cierre de ventana para persistir datos y detener hilos."""
        self._save_current_values()
        if self.game_monitor:
            self.game_monitor.stop()
        if self.active_sens_overlay and self.active_sens_overlay.winfo_exists():
            self.active_sens_overlay.close_overlay()
        if self.active_highscore_overlay and self.active_highscore_overlay.winfo_exists():
            self.active_highscore_overlay.close_overlay()
        self.destroy()

    def _on_browse_directory(self):
        current_dir = self.entry_dir.get().strip()
        initial_dir = current_dir if os.path.isdir(current_dir) else os.path.expanduser("~")

        selected_dir = filedialog.askdirectory(
            parent=self,
            title=t("dialogs.browse_title"),
            initialdir=initial_dir
        )
        if selected_dir:
            normalized_path = os.path.normpath(selected_dir)
            self.entry_dir.delete(0, "end")
            self.entry_dir.insert(0, normalized_path)
            self._save_current_values()

    def _on_open_folder(self):
        current_dir = self.entry_dir.get().strip()
        if current_dir and os.path.isdir(current_dir):
            try:
                os.startfile(current_dir)
            except Exception as e:
                messagebox.showerror(t("dialogs.folder_error_title"), t("dialogs.folder_error_msg", error=str(e)))
        else:
            messagebox.showwarning(t("dialogs.invalid_folder_title"), t("dialogs.invalid_folder_msg"))

    def _clear_textbox(self):
        self.textbox_output.delete("1.0", "end")

    def _append_text(self, text: str):
        self.textbox_output.insert("end", text)
        self.textbox_output.see("end")

    def _append_monitor_log(self, text: str):
        if hasattr(self, "textbox_monitor_log"):
            self.textbox_monitor_log.insert("end", text)
            self.textbox_monitor_log.see("end")

    def _update_ui_state(self, is_processing: bool, status_msg: str):
        self.is_processing = is_processing
        if is_processing:
            self.btn_generate.configure(state="disabled", text=t("generator.generating_btn"))
            self.lbl_status.configure(text=status_msg, text_color="#3B8ED0")
        else:
            self.btn_generate.configure(state="normal", text=t("generator.generate_btn"))
            self.lbl_status.configure(text=status_msg, text_color="gray")

    def _on_toggle_monitor_clicked(self):
        if self.game_monitor.is_monitoring:
            self.game_monitor.stop()
            self.btn_toggle_monitor.configure(text=t("monitor.btn_resume"), fg_color="#3D59A1")
        else:
            self.game_monitor.start()
            self.btn_toggle_monitor.configure(text=t("monitor.btn_pause"), fg_color="#3B4261")

    def _on_sync_bench_clicked(self):
        self._save_current_values()
        bench_input = self.entry_benchmark.get().strip()
        steam_input = self.entry_steam.get().strip()

        if not bench_input or not steam_input:
            messagebox.showwarning(t("dialogs.sync_missing_data_title"), t("dialogs.sync_missing_data_msg"))
            return

        def sync_worker():
            try:
                self.after(0, lambda: self._append_monitor_log(t("monitor.sync_start_log")))
                bench_info = self.benchmark_resolver.resolve_benchmark(bench_input)
                b_id = bench_info["benchmark_id"]
                s_id = extract_steam_id(steam_input)

                prog = self.api_client.fetch_player_progress(b_id, s_id)
                sens = self.api_client.fetch_sensitivity_distributions(b_id)
                self.benchmark_tracker.load_benchmark_data(
                    benchmark_id=b_id,
                    steam_id=s_id,
                    progress_data=prog,
                    sens_data=sens,
                    benchmark_name=bench_info.get("benchmark_name")
                )
                count = len(self.benchmark_tracker.scenarios)
                self.after(0, lambda: (
                    self._append_monitor_log(t("monitor.sync_done_log", count=count)),
                    messagebox.showinfo(t("dialogs.sync_success_title"), t("dialogs.sync_success_msg"))
                ))
            except Exception as e:
                self.after(0, lambda err=e: (
                    self._append_monitor_log(t("monitor.sync_error_log", error=str(err))),
                    messagebox.showerror(t("dialogs.sync_error_title"), str(err))
                ))

        threading.Thread(target=sync_worker, daemon=True).start()

    # --- MANEJADORES DE EVENTOS DEL MONITOR (HILO SEGURO) ---

    def _on_game_process_change(self, is_running: bool):
        def update():
            game_text = t("monitor.game_running") if is_running else t("monitor.game_not_found")
            game_color = "#9ECE6A" if is_running else "#565F89"
            self.lbl_game_status.configure(text=game_text, text_color=game_color)
        self.after(0, update)

    def _on_monitor_status_change(self, is_running: bool, _message: str):
        def update():
            state_text = t("monitor.state_active") if is_running else t("monitor.state_paused")
            state_color = "#9ECE6A" if is_running else "#565F89"
            badge_text = t("header.badge_active") if is_running else t("header.badge_paused")
            badge_color = "#9ECE6A" if is_running else "#565F89"

            self.lbl_monitor_state.configure(text=state_text, text_color=state_color)
            self.lbl_monitor_badge.configure(text=badge_text, text_color=badge_color)
            msg = t("monitor.status_listening") if is_running else t("monitor.status_stopped")
            self._append_monitor_log(f"{msg}\n")

        self.after(0, update)

    def _on_rep_completed_event(self, scenario: str, rep_number: int, score: float):
        def update():
            self.lbl_active_scenario.configure(text=scenario)
            self.lbl_active_reps.configure(text=t("monitor.reps_count", current=rep_number, target=5))
            self.prog_reps.set(min(1.0, rep_number / 5.0))
            log_line = t("monitor.rep_log", rep=rep_number, target=5, scenario=scenario, score=f"{score:,.1f}")
            self._append_monitor_log(log_line)

        self.after(0, update)

    def _on_scenario_transition_event(self, next_scenario: str, prev_scenario: str, reps_done: int, is_early: bool):
        def update():
            self.lbl_active_scenario.configure(text=next_scenario)
            self.lbl_active_reps.configure(text=t("monitor.reps_count", current=0, target=5))
            self.prog_reps.set(0.0)

            # Obtener datos de sensibilidad
            sens_info = self.benchmark_tracker.get_recommended_sens(next_scenario)
            user_settings = self.detector.load_user_settings()
            dpi = user_settings.get("dpi", 1600)
            scale_name = user_settings.get("sens_scale", "Marvel Rivals")

            cm360_val = sens_info["cm360"] if sens_info else 38.5
            ingame_sens = self.detector.cm360_to_ingame_sens(cm360_val, scale_name, dpi)

            sens_display_str = f"{cm360_val} cm/360 ({ingame_sens} in-game)"
            self.lbl_active_sens.configure(text=sens_display_str)

            # Copiado automático al portapapeles si está habilitado
            pref_fmt = self.config_data.get("preferred_copy_format", "cm360")
            auto_copied = False
            if self.config_data.get("auto_copy_sens", True):
                text_to_copy = str(ingame_sens) if pref_fmt == "ingame" else str(cm360_val)
                try:
                    self.clipboard_clear()
                    self.clipboard_append(text_to_copy)
                    self.update()
                    auto_copied = True
                except Exception:
                    pass

            log_msg = t(
                "monitor.transition_log",
                prev=prev_scenario,
                reps=reps_done,
                next=next_scenario,
                sens=f"{cm360_val} cm/360"
            )
            self._append_monitor_log(log_msg)

            # Desplegar Overlay flotante sin minimizar KovaaK's
            if self.active_sens_overlay and self.active_sens_overlay.winfo_exists():
                self.active_sens_overlay.close_overlay()

            self.active_sens_overlay = SensOverlayWindow(
                parent=self,
                scenario_name=next_scenario,
                cm360_val=cm360_val,
                ingame_sens_val=ingame_sens,
                scale_name=scale_name,
                dpi=dpi,
                auto_copied=auto_copied,
                preferred_copy_format=pref_fmt,
                auto_close=self.config_data.get("auto_close_overlay", False),
                auto_close_seconds=int(self.config_data.get("auto_close_seconds", 8)),
                corner=self.config_data.get("overlay_corner", "top_right"),
                is_early=is_early
            )

        self.after(0, update)

    def _on_highscore_event(self, result: HighscoreResult):
        def update():
            log_msg = t(
                "monitor.highscore_log",
                scenario=result.scenario_name,
                old_score=f"{result.old_score:,.1f}",
                new_score=f"{result.new_score:,.1f}",
                delta=f"{result.delta_score:,.1f}",
                rank=result.new_rank_name,
                pct=result.pct_to_next_rank
            )
            self._append_monitor_log(log_msg)

            # Desplegar Overlay flotante de Highscore sin minimizar KovaaK's
            if self.active_highscore_overlay and self.active_highscore_overlay.winfo_exists():
                self.active_highscore_overlay.close_overlay()

            self.active_highscore_overlay = HighscoreOverlayWindow(
                parent=self,
                result=result,
                auto_close=self.config_data.get("auto_close_overlay", False),
                auto_close_seconds=int(self.config_data.get("auto_close_seconds", 10)),
                corner=self.config_data.get("overlay_corner", "top_right")
            )

        self.after(0, update)

    # --- PRUEBAS INTERACTIVAS DE OVERLAYS ---

    def _test_sens_overlay(self):
        user_settings = self.detector.load_user_settings()
        scale = user_settings.get("sens_scale", "Marvel Rivals")
        dpi = user_settings.get("dpi", 1600)
        ingame = self.detector.cm360_to_ingame_sens(38.5, scale, dpi)

        if self.active_sens_overlay and self.active_sens_overlay.winfo_exists():
            self.active_sens_overlay.close_overlay()

        self.active_sens_overlay = SensOverlayWindow(
            parent=self,
            scenario_name="Smoothsphere Viscose (Test)",
            cm360_val=38.5,
            ingame_sens_val=ingame,
            scale_name=scale,
            dpi=dpi,
            auto_copied=True,
            preferred_copy_format=self.config_data.get("preferred_copy_format", "cm360"),
            auto_close=self.config_data.get("auto_close_overlay", False),
            auto_close_seconds=int(self.config_data.get("auto_close_seconds", 8)),
            corner=self.config_data.get("overlay_corner", "top_right"),
            is_early=False
        )

    def _test_highscore_overlay(self):
        dummy_result = HighscoreResult(
            scenario_name="Smoothsphere Viscose (Test)",
            old_score=11481.0,
            new_score=11850.0,
            delta_score=369.0,
            old_rank_idx=5,
            new_rank_idx=5,
            old_rank_name="Viridian",
            new_rank_name="Viridian",
            current_rank_color="#368b5c",
            next_rank_name="Cerulean",
            next_rank_color="#02A4D3",
            rank_up=False,
            pct_to_next_rank=76.5,
            points_to_next_rank=200.0,
            rank_maxes=[6000, 7700, 8900, 10100, 11200, 12050, 12800, 13700, 14400],
            ranks_list=[
                {"name": "Cinnabar", "color": "#A71112"},
                {"name": "Vermillion", "color": "#F85939"},
                {"name": "Saffron", "color": "#F1C338"},
                {"name": "Celadon", "color": "#9CFF91"},
                {"name": "Viridian", "color": "#368b5c"},
                {"name": "Cerulean", "color": "#02A4D3"},
                {"name": "Lavender", "color": "#C2C2FF"},
                {"name": "Indigo", "color": "#5C3896"},
                {"name": "Fuchsia", "color": "#C74375"},
            ],
            old_continuous_score=5.33,
            new_continuous_score=5.76,
            overall_progress_pct=64.2,
            category_name="Arm"
        )

        if self.active_highscore_overlay and self.active_highscore_overlay.winfo_exists():
            self.active_highscore_overlay.close_overlay()

        self.active_highscore_overlay = HighscoreOverlayWindow(
            parent=self,
            result=dummy_result,
            auto_close=self.config_data.get("auto_close_overlay", False),
            auto_close_seconds=int(self.config_data.get("auto_close_seconds", 10)),
            corner=self.config_data.get("overlay_corner", "top_right")
        )

    # --- GENERACIÓN DE PLAYLISTS ORIGINAL ---

    def _on_generate_clicked(self):
        if self.is_processing:
            return

        self._save_current_values()

        raw_steam = self.entry_steam.get().strip()
        raw_bench = self.entry_benchmark.get().strip()
        raw_dir = self.entry_dir.get().strip()
        raw_name = self.entry_name.get().strip() or "improve-weaknesses"

        if not raw_bench:
            msg = t("dialogs.missing_bench_msg")
            self._append_text(f"[ERROR] {msg}\n\n")
            messagebox.showerror(t("dialogs.missing_bench_title"), msg)
            return

        if not raw_dir:
            msg = t("dialogs.missing_dir_msg")
            self._append_text(f"[ERROR] {msg}\n\n")
            messagebox.showerror(t("dialogs.missing_dir_title"), msg)
            return

        if not os.path.isdir(raw_dir):
            msg = t("dialogs.invalid_dir_msg", dir=raw_dir)
            self._append_text(f"[ERROR] {msg}\n\n")
            messagebox.showerror(t("dialogs.invalid_dir_title"), msg)
            return

        worker_thread = threading.Thread(
            target=self._worker_process,
            args=(raw_bench, raw_steam, raw_dir, raw_name),
            daemon=True
        )
        self._update_ui_state(True, t("generator.connecting_status"))
        worker_thread.start()

    def _worker_process(
        self,
        raw_bench: str,
        raw_steam: str,
        destination_dir: str,
        requested_name: str
    ):
        try:
            self.after(0, lambda: self._append_text(t("generator.log_analyzing_bench")))
            bench_info = self.benchmark_resolver.resolve_benchmark(raw_bench)
            benchmark_id = bench_info["benchmark_id"]

            bench_name = bench_info.get("benchmark_name")
            bench_diff = bench_info.get("difficulty")
            author = bench_info.get("author")

            if bench_name:
                diff_str = f" [{bench_diff}]" if bench_diff else ""
                self.after(0, lambda b=bench_name, d=diff_str, bid=benchmark_id: self._append_text(
                    t("generator.log_bench_identified", name=b, diff=d, id=bid)
                ))

            if not raw_steam and author:
                self.after(0, lambda a=author: self._append_text(
                    t("generator.log_resolving_steam", author=a)
                ))
                resolved_steam = self.benchmark_resolver.resolve_steam_vanity_or_id(author)
                if resolved_steam:
                    raw_steam = resolved_steam
                    self.after(0, lambda sid=resolved_steam, a=author: (
                        self.entry_steam.delete(0, "end"),
                        self.entry_steam.insert(0, sid),
                        self._append_text(t("generator.log_steam_detected", sid=sid, author=a)),
                        self._save_current_values()
                    ))

            steam_id = extract_steam_id(raw_steam)

            self.after(0, lambda: self._append_text(
                t("generator.log_fetching_progress", bid=benchmark_id, sid=steam_id)
            ))
            progress_data = self.api_client.fetch_player_progress(benchmark_id, steam_id)

            self.after(0, lambda: self._append_text(t("generator.log_fetching_sens")))
            sens_data = self.api_client.fetch_sensitivity_distributions(benchmark_id)

            # Cargar al BenchmarkTracker inmediatamente para habilitar el monitoreo
            self.benchmark_tracker.load_benchmark_data(
                benchmark_id=benchmark_id,
                steam_id=steam_id,
                progress_data=progress_data,
                sens_data=sens_data,
                benchmark_name=bench_name
            )

            self.after(0, lambda: self._append_text(t("generator.log_calculating")))
            result = self.playlist_service.process_and_generate_playlist(
                progress_data=progress_data,
                sens_data=sens_data,
                destination_dir=destination_dir,
                requested_name=requested_name
            )

            self.after(0, lambda: self._on_success_callback(result, bench_info))

        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._on_error_callback(error_msg))

    def _on_success_callback(self, result: Dict[str, Any], bench_info: Dict[str, Any]):
        self._update_ui_state(False, t("generator.success_status"))

        scenarios = result["scenarios"]
        file_path = result["file_path"]
        pl_name = result["playlist_name"]

        bench_display = bench_info.get("benchmark_name")
        if bench_display:
            if bench_info.get("difficulty"):
                bench_display = f"{bench_display} [{bench_info['difficulty']}] (ID: {bench_info['benchmark_id']})"
            else:
                bench_display = f"{bench_display} (ID: {bench_info['benchmark_id']})"
        else:
            bench_display = f"ID: {bench_info['benchmark_id']}"

        out = []
        out.append("\n==========================================================")
        out.append(f"  {t('generator.summary_title')}")
        out.append("==========================================================")
        out.append(t("generator.summary_benchmark", bench=bench_display))
        out.append(t("generator.summary_file", file=file_path))
        out.append(t("generator.summary_name", name=pl_name))
        out.append(t("generator.summary_count", count=len(scenarios)))
        out.append("----------------------------------------------------------")
        out.append(f"  {t('generator.summary_header')}")
        out.append("----------------------------------------------------------")

        for idx, sc in enumerate(scenarios, start=1):
            rank_label = sc["sens_rank"] if sc.get("sens_rank") else "Fuchsia"
            sens_text = f"{sc['sens_value']} cm/360" if sc.get("sens_value") is not None else "N/A"
            out.append(t("generator.summary_scenario_name", idx=idx, name=sc['name']))
            out.append(t("generator.summary_scenario_sens", rank=rank_label, sens=sens_text))
            out.append(t("generator.summary_scenario_score", score=sc['continuous_score']))
            out.append("")

        out.append("==========================================================\n")
        self._append_text("\n".join(out))

    def _on_error_callback(self, error_msg: str):
        self._update_ui_state(False, t("generator.error_status"))

        err_banner = [
            "\n❌ -------------------- ERROR --------------------",
            f"{error_msg}",
            "-------------------------------------------------\n"
        ]
        self._append_text("\n".join(err_banner))
        messagebox.showerror(t("dialogs.generate_error_title"), error_msg)
