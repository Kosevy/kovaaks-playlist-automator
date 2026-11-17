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
from ui.overlay import SensOverlayWindow, HighscoreOverlayWindow, get_system_monitors
from ui.tabs import GeneratorTab, MonitorTab, SettingsTab


class KPAApp(ctk.CTk):
    """
    Interfaz gráfica principal de KovaaK's Playlist Automator & Live Tracker.
    Orquesta las pestañas modulares (GeneratorTab, MonitorTab, SettingsTab)
    y gestiona el ciclo de vida de los servicios del Core y Overlays Win32.
    """

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

        # Inicializar tarjeta de escenario activo si ya hay uno en el monitor
        if self.game_monitor.current_scenario:
            s_name = self.game_monitor.current_scenario
            s_info = self.benchmark_tracker.get_recommended_sens(s_name)
            sens_text = "N/A"
            if s_info:
                u_set = self.detector.load_user_settings()
                ingame_v = self.detector.cm360_to_ingame_sens(
                    s_info["cm360"],
                    u_set.get("sens_scale", "Marvel Rivals"),
                    u_set.get("dpi", 1600)
                )
                sens_text = f"{s_info['cm360']} cm/360 ({ingame_v} in-game)"
            self.monitor_tab.update_active_scenario(
                scenario_name=s_name,
                sens_text=sens_text,
                reps=self.game_monitor.current_reps,
                target_reps=5
            )

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

        tab_gen_frame = self.tabview.add(self._tab_key_gen)
        tab_mon_frame = self.tabview.add(self._tab_key_mon)
        tab_set_frame = self.tabview.add(self._tab_key_set)

        tab_gen_frame.grid_columnconfigure(0, weight=1)
        tab_gen_frame.grid_rowconfigure(0, weight=1)
        tab_mon_frame.grid_columnconfigure(0, weight=1)
        tab_mon_frame.grid_rowconfigure(0, weight=1)
        tab_set_frame.grid_columnconfigure(0, weight=1)
        tab_set_frame.grid_rowconfigure(0, weight=1)

        # 1. Pestaña Generador
        self.generator_tab = GeneratorTab(
            parent=tab_gen_frame,
            on_browse_clicked=self._on_browse_directory,
            on_generate_clicked=self._on_generate_clicked,
            on_open_folder_clicked=self._on_open_folder
        )
        self.generator_tab.grid(row=0, column=0, sticky="nsew")

        # 2. Pestaña Monitor
        self.monitor_tab = MonitorTab(
            parent=tab_mon_frame,
            on_toggle_monitor_clicked=self._on_toggle_monitor_clicked,
            on_sync_bench_clicked=self._on_sync_bench_clicked
        )
        self.monitor_tab.grid(row=0, column=0, sticky="nsew")

        # 3. Pestaña Ajustes
        self.settings_tab = SettingsTab(
            parent=tab_set_frame,
            monitor_names=self._get_monitor_display_names(),
            on_language_changed=self._on_settings_lang_changed,
            on_reset_pos_clicked=self._reset_overlay_position,
            on_test_sens_clicked=self._test_sens_overlay,
            on_test_highscore_clicked=self._test_highscore_overlay
        )
        self.settings_tab.grid(row=0, column=0, sticky="nsew")

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

    def _get_monitor_display_names(self) -> list[str]:
        mons = get_system_monitors()
        names = []
        for idx, m in enumerate(mons):
            prim = f" {t('settings.monitor_primary_suffix')}" if m["is_primary"] else ""
            names.append(f"Monitor {idx + 1}{prim} [{m['width']}x{m['height']}]")
        return names

    def _get_overlay_coords_or_none(self) -> Optional[tuple[int, int]]:
        if self.config_data.get("overlay_remember_drag", True):
            x = self.config_data.get("overlay_custom_x")
            y = self.config_data.get("overlay_custom_y")
            if x is not None and y is not None:
                return (int(x), int(y))
        return None

    def _compute_overlay_y_offset(self, other_overlay: Optional[ctk.CTkToplevel]) -> int:
        """
        Calcula el desplazamiento vertical necesario para apilar dos overlays simultáneos
        y evitar que se superpongan en la misma esquina de la pantalla.
        """
        if other_overlay and other_overlay.winfo_exists():
            return getattr(other_overlay, "height", 200) + 12
        return 0

    def _on_overlay_dragged(self, new_x: int, new_y: int):
        if self.config_data.get("overlay_remember_drag", True):
            self.config_data["overlay_custom_x"] = new_x
            self.config_data["overlay_custom_y"] = new_y
            try:
                self.config_manager.save_config(self.config_data)
            except Exception:
                pass

    def _reset_overlay_position(self):
        self.config_data["overlay_custom_x"] = None
        self.config_data["overlay_custom_y"] = None
        try:
            self.config_manager.save_config(self.config_data)
        except Exception:
            pass
        self.settings_tab.show_reset_confirmation(t("settings.pos_reset_done"))

    def _on_header_lang_changed(self, value: str):
        """Manejador cuando el usuario cambia el idioma desde el botón del encabezado."""
        new_lang = value.lower()
        if new_lang != get_i18n().language:
            self._save_current_values()
            get_i18n().set_language(new_lang)

    def _on_settings_lang_changed(self, value: str):
        """Manejador cuando el usuario cambia el idioma desde el menú de ajustes."""
        new_lang = "en" if "EN" in value else "es"
        if new_lang != get_i18n().language:
            self._save_current_values()
            get_i18n().set_language(new_lang)

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

        # Botón de selección de idioma en el encabezado
        current_lang = get_i18n().language
        self.btn_lang_toggle.set(current_lang.upper())

        # Pestañas
        self._update_tab_titles()
        self.generator_tab.retranslate()
        self.monitor_tab.retranslate(
            is_monitoring=self.game_monitor.is_monitoring,
            is_game_running=self.detector.is_game_running(),
            current_scenario=self.game_monitor.current_scenario
        )
        self.settings_tab.retranslate(
            saved_corner=self.config_data.get("overlay_corner", "top_right"),
            preferred_copy_format=self.config_data.get("preferred_copy_format", "cm360")
        )
        self.settings_tab.update_monitor_menu(
            self._get_monitor_display_names(),
            int(self.config_data.get("overlay_monitor", 0))
        )

    def _load_saved_values(self):
        """Carga los valores guardados en config.json en los campos de la UI."""
        self.generator_tab.load_values(
            steam=self.config_data.get("steam_input", ""),
            bench=self.config_data.get("benchmark_input", ""),
            dir_path=self.config_data.get("playlist_dir", ""),
            name=self.config_data.get("playlist_name", "improve-weaknesses")
        )
        self.settings_tab.load_values(self.config_data)
        self.generator_tab.append_log(t("generator.initial_banner"))

    def _save_current_values(self):
        """Guarda los valores actuales de los campos en config.json."""
        gen_vals = self.generator_tab.get_values()
        set_vals = self.settings_tab.get_values()

        self.config_data.update({
            "steam_input": gen_vals["steam"],
            "benchmark_input": gen_vals["benchmark"],
            "playlist_dir": gen_vals["dir"],
            "playlist_name": gen_vals["name"],
            "language": get_i18n().language,
            "auto_copy_sens": set_vals["auto_copy_sens"],
            "preferred_copy_format": set_vals["preferred_copy_format"],
            "notify_early_transition": set_vals["notify_early_transition"],
            "auto_close_overlay": set_vals["auto_close_overlay"],
            "auto_close_seconds": set_vals["auto_close_seconds"],
            "overlay_corner": set_vals["overlay_corner"],
            "overlay_monitor": set_vals["overlay_monitor"],
            "overlay_remember_drag": set_vals["overlay_remember_drag"],
            "monitor_enabled": self.game_monitor.is_monitoring
        })

        # Notificar al monitor del cambio de configuración
        self.game_monitor.set_notify_early_transition(self.config_data["notify_early_transition"])

        try:
            self.config_manager.save_config(self.config_data)
        except Exception as e:
            self.generator_tab.append_log(f"[ADVERTENCIA / WARNING] config.json: {e}\n")

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
                    self.after(0, lambda: self.monitor_tab.append_log(
                        t("monitor.preload_success", name=b_name, count=count)
                    ))
                except Exception as e:
                    self.after(0, lambda err=e: self.monitor_tab.append_log(
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
        gen_vals = self.generator_tab.get_values()
        current_dir = gen_vals["dir"]
        initial_dir = current_dir if os.path.isdir(current_dir) else os.path.expanduser("~")

        selected_dir = filedialog.askdirectory(
            parent=self,
            title=t("dialogs.browse_title"),
            initialdir=initial_dir
        )
        if selected_dir:
            normalized_path = os.path.normpath(selected_dir)
            self.generator_tab.set_dir(normalized_path)
            self._save_current_values()

    def _on_open_folder(self):
        gen_vals = self.generator_tab.get_values()
        current_dir = gen_vals["dir"]
        if current_dir and os.path.isdir(current_dir):
            try:
                os.startfile(current_dir)
            except Exception as e:
                messagebox.showerror(t("dialogs.folder_error_title"), t("dialogs.folder_error_msg", error=str(e)))
        else:
            messagebox.showwarning(t("dialogs.invalid_folder_title"), t("dialogs.invalid_folder_msg"))

    def _on_toggle_monitor_clicked(self):
        if self.game_monitor.is_monitoring:
            self.game_monitor.stop()
            self.monitor_tab.update_monitor_state(False)
            self.lbl_monitor_badge.configure(text=t("header.badge_paused"), text_color="#565F89")
        else:
            self.game_monitor.start()
            self.monitor_tab.update_monitor_state(True)
            self.lbl_monitor_badge.configure(text=t("header.badge_active"), text_color="#9ECE6A")

    def _on_sync_bench_clicked(self):
        self._save_current_values()
        gen_vals = self.generator_tab.get_values()
        bench_input = gen_vals["benchmark"]
        steam_input = gen_vals["steam"]

        if not bench_input or not steam_input:
            messagebox.showwarning(t("dialogs.sync_missing_data_title"), t("dialogs.sync_missing_data_msg"))
            return

        def sync_worker():
            try:
                self.after(0, lambda: self.monitor_tab.append_log(t("monitor.sync_start_log")))
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
                    self.monitor_tab.append_log(t("monitor.sync_done_log", count=count)),
                    messagebox.showinfo(t("dialogs.sync_success_title"), t("dialogs.sync_success_msg"))
                ))
            except Exception as e:
                self.after(0, lambda err=e: (
                    self.monitor_tab.append_log(t("monitor.sync_error_log", error=str(err))),
                    messagebox.showerror(t("dialogs.sync_error_title"), str(err))
                ))

        threading.Thread(target=sync_worker, daemon=True).start()

    # --- MANEJADORES DE EVENTOS DEL MONITOR (HILO SEGURO) ---

    def _on_game_process_change(self, is_running: bool):
        self.after(0, lambda: self.monitor_tab.update_game_status(is_running))

    def _on_monitor_status_change(self, is_running: bool, _message: str):
        def update():
            self.monitor_tab.update_monitor_state(is_running)
            badge_text = t("header.badge_active") if is_running else t("header.badge_paused")
            badge_color = "#9ECE6A" if is_running else "#565F89"
            self.lbl_monitor_badge.configure(text=badge_text, text_color=badge_color)
            msg = t("monitor.status_listening") if is_running else t("monitor.status_stopped")
            self.monitor_tab.append_log(f"{msg}\n")

        self.after(0, update)

    def _on_rep_completed_event(self, scenario: str, rep_number: int, score: float):
        def update():
            self.monitor_tab.update_rep_progress(rep_number, target=5)
            log_line = t("monitor.rep_log", rep=rep_number, target=5, scenario=scenario, score=f"{score:,.1f}")
            self.monitor_tab.append_log(log_line)

        self.after(0, update)

    def _on_scenario_transition_event(self, next_scenario: str, prev_scenario: str, reps_done: int, is_early: bool):
        def update():
            # Obtener datos de sensibilidad
            sens_info = self.benchmark_tracker.get_recommended_sens(next_scenario)
            user_settings = self.detector.load_user_settings()
            dpi = user_settings.get("dpi", 1600)
            scale_name = user_settings.get("sens_scale", "Marvel Rivals")

            cm360_val = sens_info["cm360"] if sens_info else 38.5
            ingame_sens = self.detector.cm360_to_ingame_sens(cm360_val, scale_name, dpi)

            sens_display_str = f"{cm360_val} cm/360 ({ingame_sens} in-game)"
            self.monitor_tab.update_active_scenario(
                scenario_name=next_scenario,
                sens_text=sens_display_str,
                reps=0,
                target_reps=5
            )

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
            self.monitor_tab.append_log(log_msg)

            # Desplegar Overlay flotante sin minimizar KovaaK's
            if self.active_sens_overlay and self.active_sens_overlay.winfo_exists():
                self.active_sens_overlay.close_overlay()

            monitor_idx = int(self.config_data.get("overlay_monitor", 0))
            custom_coords = self._get_overlay_coords_or_none()
            y_offset = self._compute_overlay_y_offset(self.active_highscore_overlay)

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
                monitor_index=monitor_idx,
                custom_coords=custom_coords,
                y_offset=y_offset,
                is_early=is_early,
                on_position_changed=self._on_overlay_dragged
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
            self.monitor_tab.append_log(log_msg)

            # Desplegar Overlay flotante de Highscore sin minimizar KovaaK's
            if self.active_highscore_overlay and self.active_highscore_overlay.winfo_exists():
                self.active_highscore_overlay.close_overlay()

            monitor_idx = int(self.config_data.get("overlay_monitor", 0))
            custom_coords = self._get_overlay_coords_or_none()
            y_offset = self._compute_overlay_y_offset(self.active_sens_overlay)

            self.active_highscore_overlay = HighscoreOverlayWindow(
                parent=self,
                result=result,
                auto_close=self.config_data.get("auto_close_overlay", False),
                auto_close_seconds=int(self.config_data.get("auto_close_seconds", 10)),
                corner=self.config_data.get("overlay_corner", "top_right"),
                monitor_index=monitor_idx,
                custom_coords=custom_coords,
                y_offset=y_offset,
                on_position_changed=self._on_overlay_dragged
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

        monitor_idx = int(self.config_data.get("overlay_monitor", 0))
        custom_coords = self._get_overlay_coords_or_none()
        y_offset = self._compute_overlay_y_offset(self.active_highscore_overlay)

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
            monitor_index=monitor_idx,
            custom_coords=custom_coords,
            y_offset=y_offset,
            is_early=False,
            on_position_changed=self._on_overlay_dragged
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

        monitor_idx = int(self.config_data.get("overlay_monitor", 0))
        custom_coords = self._get_overlay_coords_or_none()
        y_offset = self._compute_overlay_y_offset(self.active_sens_overlay)

        self.active_highscore_overlay = HighscoreOverlayWindow(
            parent=self,
            result=dummy_result,
            auto_close=self.config_data.get("auto_close_overlay", False),
            auto_close_seconds=int(self.config_data.get("auto_close_seconds", 10)),
            corner=self.config_data.get("overlay_corner", "top_right"),
            monitor_index=monitor_idx,
            custom_coords=custom_coords,
            y_offset=y_offset,
            on_position_changed=self._on_overlay_dragged
        )

    # --- GENERACIÓN DE PLAYLISTS ORIGINAL ---

    def _on_generate_clicked(self):
        if self.is_processing:
            return

        self._save_current_values()

        gen_vals = self.generator_tab.get_values()
        raw_steam = gen_vals["steam"]
        raw_bench = gen_vals["benchmark"]
        raw_dir = gen_vals["dir"]
        raw_name = gen_vals["name"]

        if not raw_bench:
            msg = t("dialogs.missing_bench_msg")
            self.generator_tab.append_log(f"[ERROR] {msg}\n\n")
            messagebox.showerror(t("dialogs.missing_bench_title"), msg)
            return

        if not raw_dir:
            msg = t("dialogs.missing_dir_msg")
            self.generator_tab.append_log(f"[ERROR] {msg}\n\n")
            messagebox.showerror(t("dialogs.missing_dir_title"), msg)
            return

        if not os.path.isdir(raw_dir):
            msg = t("dialogs.invalid_dir_msg", dir=raw_dir)
            self.generator_tab.append_log(f"[ERROR] {msg}\n\n")
            messagebox.showerror(t("dialogs.invalid_dir_title"), msg)
            return

        worker_thread = threading.Thread(
            target=self._worker_process,
            args=(raw_bench, raw_steam, raw_dir, raw_name),
            daemon=True
        )
        self.is_processing = True
        self.generator_tab.set_processing_state(True, t("generator.connecting_status"))
        worker_thread.start()

    def _worker_process(
        self,
        raw_bench: str,
        raw_steam: str,
        destination_dir: str,
        requested_name: str
    ):
        try:
            self.after(0, lambda: self.generator_tab.append_log(t("generator.log_analyzing_bench")))
            bench_info = self.benchmark_resolver.resolve_benchmark(raw_bench)
            benchmark_id = bench_info["benchmark_id"]

            bench_name = bench_info.get("benchmark_name")
            bench_diff = bench_info.get("difficulty")
            author = bench_info.get("author")

            if bench_name:
                diff_str = f" [{bench_diff}]" if bench_diff else ""
                self.after(0, lambda b=bench_name, d=diff_str, bid=benchmark_id: self.generator_tab.append_log(
                    t("generator.log_bench_identified", name=b, diff=d, id=bid)
                ))

            if not raw_steam and author:
                self.after(0, lambda a=author: self.generator_tab.append_log(
                    t("generator.log_resolving_steam", author=a)
                ))
                resolved_steam = self.benchmark_resolver.resolve_steam_vanity_or_id(author)
                if resolved_steam:
                    raw_steam = resolved_steam
                    self.after(0, lambda sid=resolved_steam, a=author: (
                        self.generator_tab.set_steam_id(sid),
                        self.generator_tab.append_log(t("generator.log_steam_detected", sid=sid, author=a)),
                        self._save_current_values()
                    ))

            steam_id = extract_steam_id(raw_steam)

            self.after(0, lambda: self.generator_tab.append_log(
                t("generator.log_fetching_progress", bid=benchmark_id, sid=steam_id)
            ))
            progress_data = self.api_client.fetch_player_progress(benchmark_id, steam_id)

            self.after(0, lambda: self.generator_tab.append_log(t("generator.log_fetching_sens")))
            sens_data = self.api_client.fetch_sensitivity_distributions(benchmark_id)

            # Cargar al BenchmarkTracker inmediatamente para habilitar el monitoreo
            self.benchmark_tracker.load_benchmark_data(
                benchmark_id=benchmark_id,
                steam_id=steam_id,
                progress_data=progress_data,
                sens_data=sens_data,
                benchmark_name=bench_name
            )

            self.after(0, lambda: self.generator_tab.append_log(t("generator.log_calculating")))
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
        self.is_processing = False
        self.generator_tab.set_processing_state(False, t("generator.success_status"))

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
        self.generator_tab.append_log("\n".join(out))

    def _on_error_callback(self, error_msg: str):
        self.is_processing = False
        self.generator_tab.set_processing_state(False, t("generator.error_status"))

        err_banner = [
            "\n❌ -------------------- ERROR --------------------",
            f"{error_msg}",
            "-------------------------------------------------\n"
        ]
        self.generator_tab.append_log("\n".join(err_banner))
        messagebox.showerror(t("dialogs.generate_error_title"), error_msg)
