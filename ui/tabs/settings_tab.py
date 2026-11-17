from typing import Optional, Callable, Dict, Any, List
import customtkinter as ctk
from core.i18n import t, get_i18n


class SettingsTab(ctk.CTkFrame):
    """
    Pestaña de Ajustes y Personalización de KPA.
    Gestiona las preferencias de idioma, copiado de sensibilidad,
    comportamiento de overlays (cierre, esquinas, monitores) y botones de prueba.
    Garantiza que get_values() siempre devuelva claves canónicas.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        monitor_names: Optional[List[str]] = None,
        on_language_changed: Optional[Callable[[str], None]] = None,
        on_reset_pos_clicked: Optional[Callable[[], None]] = None,
        on_test_sens_clicked: Optional[Callable[[], None]] = None,
        on_test_highscore_clicked: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.monitor_names = monitor_names or ["Monitor 1 [1920x1080]"]
        self.on_language_changed = on_language_changed
        self.on_reset_pos_clicked = on_reset_pos_clicked
        self.on_test_sens_clicked = on_test_sens_clicked
        self.on_test_highscore_clicked = on_test_highscore_clicked

        self.grid_columnconfigure(0, weight=1)

        self._build_ui()

    def _build_ui(self):
        # 1. Tarjeta Principal de Ajustes
        settings_frame = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color="#181926",
            border_width=1,
            border_color="#2A2E3D"
        )
        settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Selector de Idioma Formal
        self.lbl_lang = ctk.CTkLabel(
            settings_frame,
            text=t("settings.language_label"),
            font=ctk.CTkFont(weight="bold")
        )
        self.lbl_lang.grid(row=row, column=0, padx=(20, 10), pady=(15, 8), sticky="w")

        self.menu_language = ctk.CTkOptionMenu(
            settings_frame,
            values=["Español (ES)", "English (EN)"],
            command=self._handle_lang_changed
        )
        self.menu_language.grid(row=row, column=1, padx=(0, 20), pady=(15, 8), sticky="w")
        row += 1

        # Auto-copiar al portapapeles
        self.switch_auto_copy = ctk.CTkSwitch(
            settings_frame,
            text=t("settings.auto_copy_switch"),
            font=ctk.CTkFont(weight="bold")
        )
        self.switch_auto_copy.grid(row=row, column=0, columnspan=2, padx=20, pady=8, sticky="w")
        row += 1

        # Formato preferido al copiar
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

        # Notificar cambio anticipado
        self.switch_early_notify = ctk.CTkSwitch(
            settings_frame,
            text=t("settings.early_notify_switch"),
            font=ctk.CTkFont(weight="bold")
        )
        self.switch_early_notify.grid(row=row, column=0, columnspan=2, padx=20, pady=8, sticky="w")
        row += 1

        # Auto-cierre de overlays
        self.switch_auto_close = ctk.CTkSwitch(
            settings_frame,
            text=t("settings.auto_close_switch"),
            font=ctk.CTkFont(weight="bold"),
            command=self._on_auto_close_toggle
        )
        self.switch_auto_close.grid(row=row, column=0, columnspan=2, padx=20, pady=8, sticky="w")
        row += 1

        # Duración de auto-cierre
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

        # Selección de Pantalla / Monitor para Overlays
        self.lbl_monitor = ctk.CTkLabel(
            settings_frame,
            text=t("settings.monitor_select_label"),
            font=ctk.CTkFont(weight="bold")
        )
        self.lbl_monitor.grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")

        self.menu_monitor = ctk.CTkOptionMenu(
            settings_frame,
            values=self.monitor_names,
            width=220
        )
        self.menu_monitor.grid(row=row, column=1, padx=(0, 20), pady=8, sticky="w")
        row += 1

        # Esquina de posicionamiento
        self.lbl_corner = ctk.CTkLabel(
            settings_frame,
            text=t("settings.corner_label"),
            font=ctk.CTkFont(weight="bold")
        )
        self.lbl_corner.grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")

        self.menu_corner = ctk.CTkOptionMenu(
            settings_frame,
            values=[
                t("settings.corner_top_right"),
                t("settings.corner_top_left"),
                t("settings.corner_bottom_right"),
                t("settings.corner_bottom_left")
            ]
        )
        self.menu_corner.grid(row=row, column=1, padx=(0, 20), pady=8, sticky="w")
        row += 1

        # Recordar posición personalizada al arrastrar
        self.switch_remember_drag = ctk.CTkSwitch(
            settings_frame,
            text=t("settings.remember_drag_switch"),
            font=ctk.CTkFont(weight="bold")
        )
        self.switch_remember_drag.grid(row=row, column=0, columnspan=2, padx=20, pady=8, sticky="w")
        row += 1

        # Botón para restablecer posición personalizada
        reset_box = ctk.CTkFrame(settings_frame, fg_color="transparent")
        reset_box.grid(row=row, column=0, columnspan=2, padx=20, pady=6, sticky="w")

        self.btn_reset_pos = ctk.CTkButton(
            reset_box,
            text=t("settings.btn_reset_pos"),
            width=170,
            height=28,
            corner_radius=6,
            fg_color="#24283B",
            hover_color="#3B4261",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._handle_reset_pos
        )
        self.btn_reset_pos.pack(side="left", padx=(0, 12))

        self.lbl_reset_status = ctk.CTkLabel(
            reset_box,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#9ECE6A"
        )
        self.lbl_reset_status.pack(side="left")
        row += 1

        # Sugerencias y Tips de Display (better-ui)
        tips_frame = ctk.CTkFrame(
            settings_frame,
            corner_radius=8,
            fg_color="#1F2335",
            border_width=1,
            border_color="#292E42"
        )
        tips_frame.grid(row=row, column=0, columnspan=2, padx=20, pady=(10, 15), sticky="ew")

        self.lbl_drag_hint = ctk.CTkLabel(
            tips_frame,
            text=t("settings.drag_hint"),
            font=ctk.CTkFont(size=11),
            text_color="#7AA2F7",
            wraplength=680,
            justify="left"
        )
        self.lbl_drag_hint.pack(anchor="w", padx=12, pady=(8, 4))

        self.lbl_fullscreen_tip = ctk.CTkLabel(
            tips_frame,
            text=t("settings.fullscreen_tip"),
            font=ctk.CTkFont(size=11),
            text_color="#9AA5CE",
            wraplength=680,
            justify="left"
        )
        self.lbl_fullscreen_tip.pack(anchor="w", padx=12, pady=(0, 8))
        row += 1

        # 2. Tarjeta de Pruebas de Overlays
        test_frame = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color="#181926",
            border_width=1,
            border_color="#2A2E3D"
        )
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
            command=self._handle_test_sens
        )
        self.btn_test_sens.pack(side="left", padx=(0, 10))

        self.btn_test_high = ctk.CTkButton(
            btn_test_box,
            text=t("settings.test_high_btn"),
            height=34,
            corner_radius=6,
            fg_color="#24283B",
            hover_color="#3B4261",
            command=self._handle_test_highscore
        )
        self.btn_test_high.pack(side="left")

    def _on_auto_close_toggle(self):
        is_on = self.switch_auto_close.get() == 1
        self.entry_auto_close_sec.configure(state="normal" if is_on else "disabled")

    def _handle_lang_changed(self, value: str):
        if self.on_language_changed:
            self.on_language_changed(value)

    def _handle_reset_pos(self):
        if self.on_reset_pos_clicked:
            self.on_reset_pos_clicked()

    def _handle_test_sens(self):
        if self.on_test_sens_clicked:
            self.on_test_sens_clicked()

    def _handle_test_highscore(self):
        if self.on_test_highscore_clicked:
            self.on_test_highscore_clicked()

    def _get_canonical_corner(self) -> str:
        """Traduce la selección visual de la esquina a su clave canónica."""
        cur = self.menu_corner.get()
        if cur == t("settings.corner_top_left"):
            return "top_left"
        elif cur == t("settings.corner_bottom_right"):
            return "bottom_right"
        elif cur == t("settings.corner_bottom_left"):
            return "bottom_left"
        return "top_right"

    def _get_canonical_monitor_index(self) -> int:
        """Extrae el índice numérico 0-based del monitor seleccionado."""
        mon_str = self.menu_monitor.get()
        if "Monitor " in mon_str:
            try:
                idx = int(mon_str.split("Monitor ")[1].split(" ")[0]) - 1
                return max(0, idx)
            except Exception:
                return 0
        return 0

    def get_values(self) -> Dict[str, Any]:
        """
        Devuelve un diccionario con los valores de configuración canónicos
        (claves de esquina y formato estandarizadas, índice entero de monitor).
        """
        pref_fmt_key = "cm360" if self.segmented_copy_format.get() == t("settings.format_cm360") else "ingame"

        try:
            sec_val = int(self.entry_auto_close_sec.get().strip() or "8")
        except ValueError:
            sec_val = 8

        return {
            "auto_copy_sens": self.switch_auto_copy.get() == 1,
            "preferred_copy_format": pref_fmt_key,
            "notify_early_transition": self.switch_early_notify.get() == 1,
            "auto_close_overlay": self.switch_auto_close.get() == 1,
            "auto_close_seconds": sec_val,
            "overlay_corner": self._get_canonical_corner(),
            "overlay_monitor": self._get_canonical_monitor_index(),
            "overlay_remember_drag": self.switch_remember_drag.get() == 1,
        }

    def load_values(self, config_data: Dict[str, Any]):
        """Carga los valores de configuración en los widgets del formulario."""
        current_lang = get_i18n().language
        self.menu_language.set("English (EN)" if current_lang == "en" else "Español (ES)")

        auto_copy = config_data.get("auto_copy_sens", True)
        self.switch_auto_copy.select() if auto_copy else self.switch_auto_copy.deselect()

        pref_fmt = config_data.get("preferred_copy_format", "cm360")
        self.segmented_copy_format.set(t("settings.format_cm360") if pref_fmt == "cm360" else t("settings.format_ingame"))

        early_notify = config_data.get("notify_early_transition", True)
        self.switch_early_notify.select() if early_notify else self.switch_early_notify.deselect()

        auto_close = config_data.get("auto_close_overlay", False)
        if auto_close:
            self.switch_auto_close.select()
            self.entry_auto_close_sec.configure(state="normal")
        else:
            self.switch_auto_close.deselect()
            self.entry_auto_close_sec.configure(state="disabled")

        secs = str(config_data.get("auto_close_seconds", 8))
        self.entry_auto_close_sec.delete(0, "end")
        self.entry_auto_close_sec.insert(0, secs)

        saved_corner = config_data.get("overlay_corner", "top_right")
        self.update_corner_menu(saved_corner)

        saved_mon_idx = int(config_data.get("overlay_monitor", 0))
        self.update_monitor_menu(self.monitor_names, saved_mon_idx)

        rem_drag = config_data.get("overlay_remember_drag", True)
        self.switch_remember_drag.select() if rem_drag else self.switch_remember_drag.deselect()

    def update_corner_menu(self, corner_key: str):
        """Sincroniza la selección visual del menú de esquinas según la clave canónica."""
        mapping = {
            "top_right": t("settings.corner_top_right"),
            "top_left": t("settings.corner_top_left"),
            "bottom_right": t("settings.corner_bottom_right"),
            "bottom_left": t("settings.corner_bottom_left")
        }
        self.menu_corner.set(mapping.get(corner_key, t("settings.corner_top_right")))

    def update_monitor_menu(self, monitor_names: List[str], selected_idx: int = 0):
        """Actualiza la lista y selección del menú de monitores disponibles."""
        self.monitor_names = monitor_names
        self.menu_monitor.configure(values=monitor_names)
        if 0 <= selected_idx < len(monitor_names):
            self.menu_monitor.set(monitor_names[selected_idx])
        elif monitor_names:
            self.menu_monitor.set(monitor_names[0])

    def show_reset_confirmation(self, message: str):
        """Muestra una confirmación temporal de restablecimiento de coordenadas."""
        self.lbl_reset_status.configure(text=message, text_color="#9ECE6A")
        self.after(2000, lambda: self.lbl_reset_status.configure(text=""))

    def retranslate(self, saved_corner: str = "top_right", preferred_copy_format: str = "cm360"):
        """Actualiza todos los textos de la pestaña según el idioma activo."""
        self.lbl_lang.configure(text=t("settings.language_label"))
        current_lang = get_i18n().language
        self.menu_language.set("English (EN)" if current_lang == "en" else "Español (ES)")

        self.switch_auto_copy.configure(text=t("settings.auto_copy_switch"))
        self.lbl_format.configure(text=t("settings.copy_format_label"))
        self.segmented_copy_format.configure(values=[t("settings.format_cm360"), t("settings.format_ingame")])
        self.segmented_copy_format.set(t("settings.format_ingame") if preferred_copy_format == "ingame" else t("settings.format_cm360"))

        self.switch_early_notify.configure(text=t("settings.early_notify_switch"))
        self.switch_auto_close.configure(text=t("settings.auto_close_switch"))
        self.lbl_secs.configure(text=t("settings.auto_close_secs_label"))
        self.lbl_monitor.configure(text=t("settings.monitor_select_label"))

        self.lbl_corner.configure(text=t("settings.corner_label"))
        corner_opts = [
            t("settings.corner_top_right"),
            t("settings.corner_top_left"),
            t("settings.corner_bottom_right"),
            t("settings.corner_bottom_left")
        ]
        self.menu_corner.configure(values=corner_opts)
        self.update_corner_menu(saved_corner)

        self.switch_remember_drag.configure(text=t("settings.remember_drag_switch"))
        self.btn_reset_pos.configure(text=t("settings.btn_reset_pos"))
        self.lbl_drag_hint.configure(text=t("settings.drag_hint"))
        self.lbl_fullscreen_tip.configure(text=t("settings.fullscreen_tip"))

        self.lbl_test_title.configure(text=t("settings.test_section_title"))
        self.lbl_test_desc.configure(text=t("settings.test_section_desc"))
        self.btn_test_sens.configure(text=t("settings.test_sens_btn"))
        self.btn_test_high.configure(text=t("settings.test_high_btn"))
