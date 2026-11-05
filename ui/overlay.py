import os
import ctypes
from ctypes import wintypes
import tkinter as tk
from typing import Optional, Dict, Any, List
import customtkinter as ctk

from core.benchmark_tracker import HighscoreResult
from core.i18n import t

# Constantes Win32
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001


def apply_win32_overlay_styles(window: ctk.CTkToplevel, x: int, y: int, width: int, height: int):
    """
    Aplica los estilos extendidos de Win32 para asegurar que la ventana flote
    por encima de KovaaK's (TOPMOST) y NUNCA le robe el foco de entrada ni lo minimice (NOACTIVATE).
    """
    try:
        window.update_idletasks()
        hwnd = window.winfo_id()
        user32 = ctypes.windll.user32

        # 1. Obtener y actualizar estilos extendidos
        current_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        new_style = current_style | WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

        # 2. Posicionar sin activar foco
        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            int(x),
            int(y),
            int(width),
            int(height),
            SWP_NOACTIVATE | SWP_SHOWWINDOW
        )
    except Exception:
        # Fallback en caso de que la llamada Win32 no esté disponible
        window.attributes("-topmost", True)
        window.geometry(f"{width}x{height}+{x}+{y}")


def calculate_corner_position(root: tk.Misc, width: int, height: int, corner: str = "top_right") -> tuple[int, int]:
    """Calcula las coordenadas X, Y según la esquina de la pantalla deseada."""
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    margin_x = 24
    margin_y = 32

    if corner == "top_left":
        return margin_x, margin_y
    elif corner == "bottom_left":
        return margin_x, screen_h - height - margin_y - 48
    elif corner == "bottom_right":
        return screen_w - width - margin_x, screen_h - height - margin_y - 48
    else:  # top_right por defecto
        return screen_w - width - margin_x, margin_y


class SensOverlayWindow(ctk.CTkToplevel):
    """
    Ventana emergente que muestra la sensibilidad recomendada al pasar de escenario,
    diseñada bajo la guía de better-ui y garantizando no minimizar el juego.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        scenario_name: str,
        cm360_val: float,
        ingame_sens_val: Optional[float] = None,
        scale_name: Optional[str] = None,
        dpi: Optional[int] = None,
        auto_copied: bool = True,
        preferred_copy_format: str = "cm360",
        auto_close: bool = False,
        auto_close_seconds: int = 8,
        corner: str = "top_right",
        is_early: bool = False
    ):
        super().__init__(parent)

        self.scenario_name = scenario_name
        self.cm360_val = cm360_val
        self.ingame_sens_val = ingame_sens_val
        self.scale_name = scale_name or "Juego"
        self.dpi = dpi or 1600
        self.auto_copied = auto_copied
        self.preferred_copy_format = preferred_copy_format
        self.auto_close = auto_close
        self.auto_close_seconds = auto_close_seconds
        self.is_early = is_early

        self.remaining_seconds = float(auto_close_seconds)
        self.is_hovered = False
        self._timer_id = None

        # Configuración de ventana
        self.overrideredirect(True)
        self.configure(fg_color="#13141F")

        # Dimensiones y posicionamiento
        w, h = 380, 195
        pos_x, pos_y = calculate_corner_position(self, w, h, corner)
        self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")

        self._build_ui()
        apply_win32_overlay_styles(self, pos_x, pos_y, w, h)

        # Eventos para pausar auto-cierre si el ratón está encima
        self.bind("<Enter>", self._on_mouse_enter)
        self.bind("<Leave>", self._on_mouse_leave)

        if self.auto_close:
            self._start_countdown()

    def _build_ui(self):
        # Marco exterior con radio 12 y borde sutil
        self.outer_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color="#181926",
            border_width=1,
            border_color="#2E334A"
        )
        self.outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Fila superior: Título e ícono de cierre
        top_bar = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=14, pady=(10, 4))

        badge_text = t("overlays.sens_badge_next") if not self.is_early else t("overlays.sens_badge_early")
        badge_color = "#3D59A1" if not self.is_early else "#9D7CD8"
        lbl_badge = ctk.CTkLabel(
            top_bar,
            text=badge_text,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=badge_color
        )
        lbl_badge.pack(side="left")

        btn_close = ctk.CTkButton(
            top_bar,
            text="✕",
            width=24,
            height=24,
            corner_radius=6,
            fg_color="#24283B",
            hover_color="#414868",
            text_color="#C0CAF5",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.close_overlay
        )
        btn_close.pack(side="right")

        # Nombre del escenario
        lbl_scenario = ctk.CTkLabel(
            self.outer_frame,
            text=self.scenario_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF",
            anchor="w"
        )
        lbl_scenario.pack(fill="x", padx=14, pady=(0, 6))

        # Tarjeta interna de sensibilidad (better-ui: outer radius 12, inner card 8)
        sens_card = ctk.CTkFrame(
            self.outer_frame,
            corner_radius=8,
            fg_color="#1F2335",
            border_width=1,
            border_color="#292E42"
        )
        sens_card.pack(fill="x", padx=14, pady=2)

        # Despliegue de cm/360 y sens in-game
        cm_text = f"{self.cm360_val} cm/360"
        lbl_sens_cm = ctk.CTkLabel(
            sens_card,
            text=cm_text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#7AA2F7"
        )
        lbl_sens_cm.pack(side="left", padx=(12, 8), pady=8)

        if self.ingame_sens_val is not None:
            ingame_text = f"{self.ingame_sens_val} ({self.scale_name} @ {self.dpi} DPI)"
            lbl_sens_ingame = ctk.CTkLabel(
                sens_card,
                text=ingame_text,
                font=ctk.CTkFont(size=11),
                text_color="#9AA5CE"
            )
            lbl_sens_ingame.pack(side="right", padx=(8, 12), pady=8)

        # Fila de acciones y estado
        action_bar = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        action_bar.pack(fill="x", padx=14, pady=(8, 8))

        # Estado de copiado
        status_text = t("overlays.copy_status_copied") if self.auto_copied else t("overlays.copy_status_ready")
        status_color = "#9ECE6A" if self.auto_copied else "#565F89"
        self.lbl_status = ctk.CTkLabel(
            action_bar,
            text=status_text,
            font=ctk.CTkFont(size=11),
            text_color=status_color
        )
        self.lbl_status.pack(side="left")

        # Botón para copiar manualmente
        self.btn_copy = ctk.CTkButton(
            action_bar,
            text=t("overlays.copy_btn"),
            width=85,
            height=28,
            corner_radius=6,
            fg_color="#3B4261",
            hover_color="#7AA2F7",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.copy_to_clipboard
        )
        self.btn_copy.pack(side="right")

        # Indicador de cuenta regresiva (si auto-cierre está activo)
        if self.auto_close:
            self.lbl_countdown = ctk.CTkLabel(
                self.outer_frame,
                text=t("overlays.auto_close_countdown", secs=int(self.remaining_seconds)),
                font=ctk.CTkFont(size=10),
                text_color="#565F89"
            )
            self.lbl_countdown.pack(side="bottom", pady=(0, 4))

    def copy_to_clipboard(self):
        """Copia el valor seleccionado al portapapeles y ofrece retroalimentación visual."""
        if self.preferred_copy_format == "ingame" and self.ingame_sens_val is not None:
            text_to_copy = str(self.ingame_sens_val)
        else:
            text_to_copy = str(self.cm360_val)

        try:
            self.clipboard_clear()
            self.clipboard_append(text_to_copy)
            self.update()
        except Exception:
            pass

        # Micro-interacción: cambio de texto y color con reversión suave
        self.btn_copy.configure(text=t("overlays.copied_btn"), fg_color="#9ECE6A", text_color="#1A1B26")
        self.lbl_status.configure(text=t("overlays.copy_status_done", text=text_to_copy), text_color="#9ECE6A")
        self.after(1800, lambda: self.btn_copy.configure(
            text=t("overlays.copy_btn"),
            fg_color="#3B4261",
            text_color="#FFFFFF"
        ))

    def _on_mouse_enter(self, _event):
        self.is_hovered = True
        if self.auto_close and hasattr(self, "lbl_countdown"):
            self.lbl_countdown.configure(text=t("overlays.auto_close_paused"), text_color="#7AA2F7")

    def _on_mouse_leave(self, _event):
        self.is_hovered = False

    def _start_countdown(self):
        def tick():
            if not self.is_hovered:
                self.remaining_seconds -= 1.0
                if hasattr(self, "lbl_countdown"):
                    self.lbl_countdown.configure(
                        text=t("overlays.auto_close_countdown", secs=max(0, int(self.remaining_seconds))),
                        text_color="#565F89"
                    )
                if self.remaining_seconds <= 0:
                    self.close_overlay()
                    return

            self._timer_id = self.after(1000, tick)

        self._timer_id = self.after(1000, tick)

    def close_overlay(self):
        if self._timer_id:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
        self.destroy()


class HighscoreOverlayWindow(ctk.CTkToplevel):
    """
    Ventana emergente no intrusiva que muestra la barra de progreso multicromática de EVXL
    y métricas actualizadas tras alcanzar un nuevo récord personal.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        result: HighscoreResult,
        auto_close: bool = False,
        auto_close_seconds: int = 10,
        corner: str = "top_right"
    ):
        super().__init__(parent)
        self.result = result
        self.auto_close = auto_close
        self.auto_close_seconds = auto_close_seconds
        self.remaining_seconds = float(auto_close_seconds)
        self.is_hovered = False
        self._timer_id = None

        self.overrideredirect(True)
        self.configure(fg_color="#13141F")

        # Dimensiones y posición
        w, h = 420, 275
        pos_x, pos_y = calculate_corner_position(self, w, h, corner)
        self.geometry(f"{w}x{h}+{pos_x}+{pos_y}")

        self._build_ui()
        apply_win32_overlay_styles(self, pos_x, pos_y, w, h)

        self.bind("<Enter>", self._on_mouse_enter)
        self.bind("<Leave>", self._on_mouse_leave)

        if self.auto_close:
            self._start_countdown()

    def _build_ui(self):
        outer_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color="#181926",
            border_width=1,
            border_color="#2E334A"
        )
        outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Fila superior: Badge de Highscore y botón cerrar
        top_bar = ctk.CTkFrame(outer_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=14, pady=(10, 4))

        title_text = t("overlays.highscore_title") if not self.result.rank_up else t("overlays.rankup_title")
        title_color = "#E0AF68" if not self.result.rank_up else "#BB9AF7"
        lbl_badge = ctk.CTkLabel(
            top_bar,
            text=title_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=title_color
        )
        lbl_badge.pack(side="left")

        btn_close = ctk.CTkButton(
            top_bar,
            text="✕",
            width=24,
            height=24,
            corner_radius=6,
            fg_color="#24283B",
            hover_color="#414868",
            text_color="#C0CAF5",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.close_overlay
        )
        btn_close.pack(side="right")

        # Nombre del escenario
        lbl_scenario = ctk.CTkLabel(
            outer_frame,
            text=self.result.scenario_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF",
            anchor="w"
        )
        lbl_scenario.pack(fill="x", padx=14, pady=(0, 6))

        # Tarjeta de comparación de puntajes
        score_card = ctk.CTkFrame(
            outer_frame,
            corner_radius=8,
            fg_color="#1F2335",
            border_width=1,
            border_color="#292E42"
        )
        score_card.pack(fill="x", padx=14, pady=2)

        score_text = f"{self.result.old_score:,.1f}  ➔  {self.result.new_score:,.1f}"
        lbl_score_flow = ctk.CTkLabel(
            score_card,
            text=score_text,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#C0CAF5"
        )
        lbl_score_flow.pack(side="left", padx=12, pady=6)

        delta_text = t("overlays.delta_points", delta=f"{self.result.delta_score:,.1f}")
        lbl_delta = ctk.CTkLabel(
            score_card,
            text=delta_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#9ECE6A"
        )
        lbl_delta.pack(side="right", padx=12, pady=6)

        # BARRA DE BENCHMARK MULTICROMÁTICA DE EVXL
        bar_container = ctk.CTkFrame(outer_frame, fg_color="transparent")
        bar_container.pack(fill="x", padx=14, pady=(10, 4))

        lbl_bar_header = ctk.CTkLabel(
            bar_container,
            text=t(
                "overlays.bar_header",
                rank=self.result.new_rank_name,
                pct=self.result.pct_to_next_rank,
                next_rank=self.result.next_rank_name
            ),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.result.current_rank_color,
            anchor="w"
        )
        lbl_bar_header.pack(fill="x", pady=(0, 4))

        # Canvas para renderizar la barra multicromática con bordes y aguja
        canvas_h = 16
        canvas_w = 388
        self.canvas_bar = tk.Canvas(
            bar_container,
            width=canvas_w,
            height=canvas_h,
            bg="#1F2335",
            highlightthickness=0
        )
        self.canvas_bar.pack(fill="x")
        self._render_multitier_bar(self.canvas_bar, canvas_w, canvas_h)

        # Fila de métricas inferiores: Puntos restantes y progreso global del benchmark
        bottom_metrics = ctk.CTkFrame(outer_frame, fg_color="transparent")
        bottom_metrics.pack(fill="x", padx=14, pady=(8, 4))

        if self.result.points_to_next_rank > 0:
            rem_text = t(
                "overlays.points_remaining",
                points=f"{self.result.points_to_next_rank:,.1f}",
                next_rank=self.result.next_rank_name
            )
        else:
            rem_text = t("overlays.max_rank_completed")

        lbl_remaining = ctk.CTkLabel(
            bottom_metrics,
            text=rem_text,
            font=ctk.CTkFont(size=11),
            text_color="#9AA5CE"
        )
        lbl_remaining.pack(side="left")

        lbl_overall = ctk.CTkLabel(
            bottom_metrics,
            text=t("overlays.overall_progress", pct=self.result.overall_progress_pct),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#7AA2F7"
        )
        lbl_overall.pack(side="right")

        # Auto-cierre
        if self.auto_close:
            self.lbl_countdown = ctk.CTkLabel(
                outer_frame,
                text=t("overlays.auto_close_countdown", secs=int(self.remaining_seconds)),
                font=ctk.CTkFont(size=10),
                text_color="#565F89"
            )
            self.lbl_countdown.pack(side="bottom", pady=(0, 4))

    def _render_multitier_bar(self, canvas: tk.Canvas, width: int, height: int):
        """Renderiza los segmentos de color correspondientes a los rangos del benchmark."""
        rank_maxes = self.result.rank_maxes
        if not rank_maxes:
            # Barra genérica si no hay umbrales
            canvas.create_rectangle(0, 0, width, height, fill="#3B4261", outline="")
            return

        min_score = 0
        max_score = rank_maxes[-1] * 1.05  # Margen superior
        score_span = max_score - min_score

        # Paleta oficial o predeterminada
        ranks_palette = [r.get("color", "#7AA2F7") for r in self.result.ranks_list if "color" in r]
        if not ranks_palette:
            ranks_palette = [
                "#CBD9E6", "#CAB148", "#2FCFC2", "#B9F2FF",
                "#EC44CA", "#FFD700", "#7900FF", "#FF2262", "#C74375"
            ]

        # Dibujar segmentos
        prev_x = 0
        prev_threshold = 0
        for i, threshold in enumerate(rank_maxes):
            seg_x = int(((threshold - min_score) / score_span) * width)
            color = ranks_palette[i % len(ranks_palette)]
            # Segmento atenuado de fondo
            canvas.create_rectangle(prev_x, 0, seg_x, height, fill=color, outline="")
            prev_x = seg_x
            prev_threshold = threshold

        # Último segmento
        if prev_x < width:
            canvas.create_rectangle(prev_x, 0, width, height, fill=ranks_palette[-1], outline="")

        # Marcador luminoso en la posición del nuevo puntaje
        cur_x = int(((self.result.new_score - min_score) / score_span) * width)
        cur_x = max(2, min(width - 3, cur_x))

        # Aguja blanca con sombra
        canvas.create_rectangle(cur_x - 2, 0, cur_x + 2, height, fill="#FFFFFF", outline="#000000")

    def _on_mouse_enter(self, _event):
        self.is_hovered = True
        if self.auto_close and hasattr(self, "lbl_countdown"):
            self.lbl_countdown.configure(text="Auto-cierre en pausa", text_color="#7AA2F7")

    def _on_mouse_leave(self, _event):
        self.is_hovered = False

    def _start_countdown(self):
        def tick():
            if not self.is_hovered:
                self.remaining_seconds -= 1.0
                if hasattr(self, "lbl_countdown"):
                    self.lbl_countdown.configure(
                        text=f"Auto-cierre en {max(0, int(self.remaining_seconds))}s",
                        text_color="#565F89"
                    )
                if self.remaining_seconds <= 0:
                    self.close_overlay()
                    return

            self._timer_id = self.after(1000, tick)

        self._timer_id = self.after(1000, tick)

    def close_overlay(self):
        if self._timer_id:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
        self.destroy()
