import os
import ctypes
from ctypes import wintypes
import tkinter as tk
from typing import Optional, Dict, Any, List, Callable
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
GA_ROOT = 2


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.c_ulong),
        ("szDevice", ctypes.c_wchar * 32),
    ]


def get_system_monitors() -> List[Dict[str, Any]]:
    """
    Detecta y devuelve todos los monitores conectados al sistema mediante la API de Win32.
    El monitor primario siempre ocupa el índice 0, seguido de los monitores secundarios ordenados.
    """
    monitors: List[Dict[str, Any]] = []
    try:
        user32 = ctypes.windll.user32

        def enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(MONITORINFOEXW)
            if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                m = info.rcMonitor
                w = info.rcWork
                is_prim = bool(info.dwFlags & 1)  # MONITORINFOF_PRIMARY = 1
                monitors.append({
                    "handle": hMonitor,
                    "is_primary": is_prim,
                    "left": int(m.left),
                    "top": int(m.top),
                    "right": int(m.right),
                    "bottom": int(m.bottom),
                    "width": int(m.right - m.left),
                    "height": int(m.bottom - m.top),
                    "work_left": int(w.left),
                    "work_top": int(w.top),
                    "work_right": int(w.right),
                    "work_bottom": int(w.bottom),
                    "device": str(info.szDevice),
                })
            return 1

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(RECT),
            ctypes.c_long,
        )
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(enum_proc), 0)
        # Ordenar: primero monitor primario, luego por coordenada left
        monitors.sort(key=lambda item: (not item["is_primary"], item["left"]))
    except Exception:
        pass

    if not monitors:
        # Fallback seguro en entornos sin soporte Win32
        monitors = [{
            "handle": None,
            "is_primary": True,
            "left": 0,
            "top": 0,
            "right": 1920,
            "bottom": 1080,
            "width": 1920,
            "height": 1080,
            "work_left": 0,
            "work_top": 0,
            "work_right": 1920,
            "work_bottom": 1080,
            "device": "DISPLAY1"
        }]

    for idx, mon in enumerate(monitors):
        mon["index"] = idx

    return monitors


def calculate_corner_position(
    monitor_index: int = 0,
    width: int = 380,
    height: int = 195,
    corner: str = "top_right",
    custom_coords: Optional[tuple[int, int]] = None,
    y_offset: int = 0
) -> tuple[int, int]:
    """
    Calcula las coordenadas X, Y según el monitor y la esquina deseada,
    aplicando un desplazamiento vertical (y_offset) para apilar múltiples overlays.
    """
    monitors = get_system_monitors()
    idx = max(0, min(len(monitors) - 1, monitor_index))
    m = monitors[idx]

    if custom_coords is not None:
        cx, cy = custom_coords
        if y_offset > 0:
            if cy + height + y_offset > m["bottom"] - 20:
                y = max(m["top"] + 10, cy - y_offset)
            else:
                y = cy + y_offset
            return cx, y
        return cx, cy

    m_left = m["left"]
    m_top = m["top"]
    m_w = m["width"]
    m_h = m["height"]

    margin_x = 24
    margin_y = 32

    if corner == "top_left":
        x = m_left + margin_x
        y = m_top + margin_y + y_offset
    elif corner == "bottom_left":
        x = m_left + margin_x
        y = m_top + m_h - height - margin_y - 48 - y_offset
    elif corner == "bottom_right":
        x = m_left + m_w - width - margin_x
        y = m_top + m_h - height - margin_y - 48 - y_offset
    else:  # top_right por defecto
        x = m_left + m_w - width - margin_x
        y = m_top + margin_y + y_offset

    return x, y


def apply_win32_overlay_styles(window: ctk.CTkToplevel, x: int, y: int, width: int, height: int):
    """
    Aplica estilos Win32 para garantizar que la ventana flote por encima de juegos (HWND_TOPMOST)
    y no robe el foco de entrada del ratón ni del teclado (WS_EX_NOACTIVATE).
    """
    try:
        window.attributes("-topmost", True)
    except Exception:
        pass

    try:
        window.update_idletasks()
        user32 = ctypes.windll.user32
        inner_hwnd = window.winfo_id()
        os_hwnd = user32.GetAncestor(inner_hwnd, GA_ROOT)
        if not os_hwnd:
            os_hwnd = user32.GetParent(inner_hwnd) or inner_hwnd

        current_style = user32.GetWindowLongW(os_hwnd, GWL_EXSTYLE)
        new_style = current_style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        user32.SetWindowLongW(os_hwnd, GWL_EXSTYLE, new_style)

        user32.SetWindowPos(
            os_hwnd,
            HWND_TOPMOST,
            int(x),
            int(y),
            int(width),
            int(height),
            SWP_NOACTIVATE | SWP_SHOWWINDOW
        )
    except Exception:
        try:
            window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    try:
        window.lift()
    except Exception:
        pass


class BaseOverlayWindow(ctk.CTkToplevel):
    """
    Clase base para ventanas flotantes (HUD overlays) no intrusivas en KovaaK's.
    Centraliza estilos Win32, libre arrastre con ratón, mantenimiento de capas topmost,
    detección de hover y ciclo de vida de cuenta regresiva de auto-cierre.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        width: int,
        height: int,
        auto_close: bool = False,
        auto_close_seconds: int = 8,
        corner: str = "top_right",
        monitor_index: int = 0,
        custom_coords: Optional[tuple[int, int]] = None,
        y_offset: int = 0,
        on_position_changed: Optional[Callable[[int, int], None]] = None
    ):
        super().__init__(parent)

        self.width = width
        self.height = height
        self.auto_close = auto_close
        self.auto_close_seconds = auto_close_seconds
        self.remaining_seconds = float(auto_close_seconds)
        self.is_hovered = False
        self.on_position_changed = on_position_changed

        self._timer_id: Optional[str] = None
        self._topmost_timer_id: Optional[str] = None
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Configuración base de ventana
        self.overrideredirect(True)
        self.configure(fg_color="#13141F")

        # Geometría con soporte para y_offset
        pos_x, pos_y = calculate_corner_position(
            monitor_index=monitor_index,
            width=width,
            height=height,
            corner=corner,
            custom_coords=custom_coords,
            y_offset=y_offset
        )
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        # Marco exterior común (better-ui: radius 12, dark tokyo night)
        self.outer_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color="#181926",
            border_width=1,
            border_color="#2E334A"
        )
        self.outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Aplicar estilos Win32
        apply_win32_overlay_styles(self, pos_x, pos_y, width, height)

        # Eventos para pausar auto-cierre con hover
        self.bind("<Enter>", self._on_mouse_enter)
        self.bind("<Leave>", self._on_mouse_leave)

        # Hacer arrastrable la ventana desde el borde exterior
        self._make_draggable(self)
        self._make_draggable(self.outer_frame)

        # Subclases construyen sus widgets específicos
        self._build_ui()

        if self.auto_close:
            self._start_countdown()

        self._keep_topmost()

    def _make_draggable(self, widget: tk.Misc):
        """Asocia eventos del ratón para arrastrar el overlay desde cualquier borde o cabecera."""
        try:
            widget.configure(cursor="size_all")
        except Exception:
            pass
        widget.bind("<Button-1>", self._on_drag_start, add="+")
        widget.bind("<B1-Motion>", self._on_drag_motion, add="+")
        widget.bind("<ButtonRelease-1>", self._on_drag_end, add="+")

    def _on_drag_start(self, event):
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _on_drag_motion(self, event):
        new_x = event.x_root - self._drag_start_x
        new_y = event.y_root - self._drag_start_y
        self.geometry(f"+{new_x}+{new_y}")

    def _on_drag_end(self, event):
        cur_x = self.winfo_x()
        cur_y = self.winfo_y()
        apply_win32_overlay_styles(self, cur_x, cur_y, self.winfo_width(), self.winfo_height())
        if self.on_position_changed:
            self.on_position_changed(cur_x, cur_y)

    def _keep_topmost(self):
        """Mantiene la ventana en la capa HWND_TOPMOST en caso de cambios de foco en KovaaK's."""
        if not self.winfo_exists():
            return
        try:
            self.attributes("-topmost", True)
            self.lift()
            user32 = ctypes.windll.user32
            os_hwnd = user32.GetAncestor(self.winfo_id(), GA_ROOT)
            if os_hwnd:
                user32.SetWindowPos(
                    os_hwnd,
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                )
        except Exception:
            pass
        self._topmost_timer_id = self.after(1500, self._keep_topmost)

    def _build_top_bar(
        self,
        badge_text: str,
        badge_color: str,
        badge_size: int = 10
    ) -> tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkButton]:
        """Crea la fila superior común con grip de arrastre, badge y botón de cierre."""
        top_bar = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=14, pady=(10, 4))
        self._make_draggable(top_bar)

        lbl_grip = ctk.CTkLabel(
            top_bar,
            text="⋮⋮",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#414868"
        )
        lbl_grip.pack(side="left", padx=(0, 6))
        self._make_draggable(lbl_grip)

        lbl_badge = ctk.CTkLabel(
            top_bar,
            text=badge_text,
            font=ctk.CTkFont(size=badge_size, weight="bold"),
            text_color=badge_color
        )
        lbl_badge.pack(side="left")
        self._make_draggable(lbl_badge)

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
            cursor="hand2",
            command=self.close_overlay
        )
        btn_close.pack(side="right")

        return top_bar, lbl_badge, btn_close

    def _build_countdown_footer(self) -> Optional[ctk.CTkLabel]:
        """Crea el label inferior de cuenta regresiva si el auto-cierre está activo."""
        if self.auto_close:
            lbl = ctk.CTkLabel(
                self.outer_frame,
                text=t("overlays.auto_close_countdown", secs=int(self.remaining_seconds)),
                font=ctk.CTkFont(size=10),
                text_color="#565F89"
            )
            lbl.pack(side="bottom", pady=(0, 4))
            self._make_draggable(lbl)
            self.lbl_countdown = lbl
            return lbl
        return None

    def _build_ui(self):
        """Método abstracto que deben implementar las subclases."""
        raise NotImplementedError

    def _on_mouse_enter(self, _event):
        self.is_hovered = True
        if self.auto_close and self.winfo_exists() and hasattr(self, "lbl_countdown") and self.lbl_countdown.winfo_exists():
            self.lbl_countdown.configure(text=t("overlays.auto_close_paused"), text_color="#7AA2F7")

    def _on_mouse_leave(self, _event):
        self.is_hovered = False
        # Restaurar inmediatamente el texto de cuenta regresiva sin esperar al siguiente tick
        if self.auto_close and self.winfo_exists() and hasattr(self, "lbl_countdown") and self.lbl_countdown.winfo_exists():
            self.lbl_countdown.configure(
                text=t("overlays.auto_close_countdown", secs=max(0, int(self.remaining_seconds))),
                text_color="#565F89"
            )

    def _start_countdown(self):
        def tick():
            if not self.winfo_exists():
                return
            if not self.is_hovered:
                self.remaining_seconds -= 1.0
                if hasattr(self, "lbl_countdown") and self.lbl_countdown.winfo_exists():
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
        """Cancela timers pendientes de forma segura y destruye la ventana."""
        if self._timer_id:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        if self._topmost_timer_id:
            try:
                self.after_cancel(self._topmost_timer_id)
            except Exception:
                pass
            self._topmost_timer_id = None

        if self.winfo_exists():
            self.destroy()


class SensOverlayWindow(BaseOverlayWindow):
    """
    Ventana emergente que muestra la sensibilidad recomendada al pasar de escenario,
    diseñada bajo la guía de better-ui, arrastrable con el ratón y garantizando
    no minimizar ni robar foco al juego.
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
        monitor_index: int = 0,
        custom_coords: Optional[tuple[int, int]] = None,
        y_offset: int = 0,
        is_early: bool = False,
        on_position_changed: Optional[Callable[[int, int], None]] = None
    ):
        # Asignar atributos ANTES de super().__init__ porque invoca _build_ui()
        self.scenario_name = scenario_name
        self.cm360_val = cm360_val
        self.ingame_sens_val = ingame_sens_val
        self.scale_name = scale_name or "Juego"
        self.dpi = dpi or 1600
        self.auto_copied = auto_copied
        self.preferred_copy_format = preferred_copy_format
        self.is_early = is_early

        super().__init__(
            parent=parent,
            width=380,
            height=195,
            auto_close=auto_close,
            auto_close_seconds=auto_close_seconds,
            corner=corner,
            monitor_index=monitor_index,
            custom_coords=custom_coords,
            y_offset=y_offset,
            on_position_changed=on_position_changed
        )

    def _build_ui(self):
        # Barra superior reutilizable
        badge_text = t("overlays.sens_badge_next") if not self.is_early else t("overlays.sens_badge_early")
        badge_color = "#3D59A1" if not self.is_early else "#9D7CD8"
        self._build_top_bar(badge_text, badge_color, badge_size=10)

        # Nombre del escenario
        lbl_scenario = ctk.CTkLabel(
            self.outer_frame,
            text=self.scenario_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF",
            anchor="w"
        )
        lbl_scenario.pack(fill="x", padx=14, pady=(0, 6))
        self._make_draggable(lbl_scenario)

        # Tarjeta interna de sensibilidad (better-ui: outer radius 12, inner card 8)
        sens_card = ctk.CTkFrame(
            self.outer_frame,
            corner_radius=8,
            fg_color="#1F2335",
            border_width=1,
            border_color="#292E42"
        )
        sens_card.pack(fill="x", padx=14, pady=2)
        self._make_draggable(sens_card)

        # Despliegue de cm/360 y sens in-game
        cm_text = f"{self.cm360_val} cm/360"
        lbl_sens_cm = ctk.CTkLabel(
            sens_card,
            text=cm_text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#7AA2F7"
        )
        lbl_sens_cm.pack(side="left", padx=(12, 8), pady=8)
        self._make_draggable(lbl_sens_cm)

        if self.ingame_sens_val is not None:
            ingame_text = f"{self.ingame_sens_val} ({self.scale_name} @ {self.dpi} DPI)"
            lbl_sens_ingame = ctk.CTkLabel(
                sens_card,
                text=ingame_text,
                font=ctk.CTkFont(size=11),
                text_color="#9AA5CE"
            )
            lbl_sens_ingame.pack(side="right", padx=(8, 12), pady=8)
            self._make_draggable(lbl_sens_ingame)

        # Fila de acciones y estado
        action_bar = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        action_bar.pack(fill="x", padx=14, pady=(8, 8))
        self._make_draggable(action_bar)

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
        self._make_draggable(self.lbl_status)

        # Botón para copiar manualmente (sin arrastre para responder al clic)
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
            cursor="hand2",
            command=self.copy_to_clipboard
        )
        self.btn_copy.pack(side="right")

        # Footer con cuenta regresiva si aplica
        self._build_countdown_footer()

    def copy_to_clipboard(self):
        """Copia el valor seleccionado al portapapeles y ofrece retroalimentación visual segura."""
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

        # Micro-interacción: cambio de texto y color con reversión segura ante cierre anticipado
        self.btn_copy.configure(text=t("overlays.copied_btn"), fg_color="#9ECE6A", text_color="#1A1B26")
        self.lbl_status.configure(text=t("overlays.copy_status_done", text=text_to_copy), text_color="#9ECE6A")

        def reset_button():
            if self.winfo_exists() and hasattr(self, "btn_copy") and self.btn_copy.winfo_exists():
                self.btn_copy.configure(
                    text=t("overlays.copy_btn"),
                    fg_color="#3B4261",
                    text_color="#FFFFFF"
                )

        self.after(1800, reset_button)


class HighscoreOverlayWindow(BaseOverlayWindow):
    """
    Ventana emergente no intrusiva que muestra la barra de progreso multicromática de EVXL
    y métricas actualizadas tras alcanzar un nuevo récord personal, arrastrable libremente
    y con protección anti-ocultamiento y canvas responsivo ante DPI.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        result: HighscoreResult,
        auto_close: bool = False,
        auto_close_seconds: int = 10,
        corner: str = "top_right",
        monitor_index: int = 0,
        custom_coords: Optional[tuple[int, int]] = None,
        y_offset: int = 0,
        on_position_changed: Optional[Callable[[int, int], None]] = None
    ):
        # Asignar atributos ANTES de super().__init__ porque invoca _build_ui()
        self.result = result

        super().__init__(
            parent=parent,
            width=420,
            height=275,
            auto_close=auto_close,
            auto_close_seconds=auto_close_seconds,
            corner=corner,
            monitor_index=monitor_index,
            custom_coords=custom_coords,
            y_offset=y_offset,
            on_position_changed=on_position_changed
        )

    def _build_ui(self):
        # Barra superior reutilizable
        title_text = t("overlays.highscore_title") if not self.result.rank_up else t("overlays.rankup_title")
        title_color = "#E0AF68" if not self.result.rank_up else "#BB9AF7"
        self._build_top_bar(title_text, title_color, badge_size=11)

        # Nombre del escenario
        lbl_scenario = ctk.CTkLabel(
            self.outer_frame,
            text=self.result.scenario_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF",
            anchor="w"
        )
        lbl_scenario.pack(fill="x", padx=14, pady=(0, 6))
        self._make_draggable(lbl_scenario)

        # Tarjeta de comparación de puntajes
        score_card = ctk.CTkFrame(
            self.outer_frame,
            corner_radius=8,
            fg_color="#1F2335",
            border_width=1,
            border_color="#292E42"
        )
        score_card.pack(fill="x", padx=14, pady=2)
        self._make_draggable(score_card)

        score_text = f"{self.result.old_score:,.1f}  ➔  {self.result.new_score:,.1f}"
        lbl_score_flow = ctk.CTkLabel(
            score_card,
            text=score_text,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#C0CAF5"
        )
        lbl_score_flow.pack(side="left", padx=12, pady=6)
        self._make_draggable(lbl_score_flow)

        delta_text = t("overlays.delta_points", delta=f"{self.result.delta_score:,.1f}")
        lbl_delta = ctk.CTkLabel(
            score_card,
            text=delta_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#9ECE6A"
        )
        lbl_delta.pack(side="right", padx=12, pady=6)
        self._make_draggable(lbl_delta)

        # BARRA DE BENCHMARK MULTICROMÁTICA DE EVXL
        bar_container = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        bar_container.pack(fill="x", padx=14, pady=(10, 4))
        self._make_draggable(bar_container)

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
        self._make_draggable(lbl_bar_header)

        # Canvas para renderizar la barra multicromática con redibujado responsivo ante Configure
        self.canvas_bar = tk.Canvas(
            bar_container,
            height=16,
            bg="#1F2335",
            highlightthickness=0
        )
        self.canvas_bar.pack(fill="x")
        self._make_draggable(self.canvas_bar)

        self.canvas_bar.bind("<Configure>", lambda e: self._render_multitier_bar(self.canvas_bar, e.width, e.height))

        # Fila de métricas inferiores: Puntos restantes y progreso global del benchmark
        bottom_metrics = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        bottom_metrics.pack(fill="x", padx=14, pady=(8, 4))
        self._make_draggable(bottom_metrics)

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
        self._make_draggable(lbl_remaining)

        lbl_overall = ctk.CTkLabel(
            bottom_metrics,
            text=t("overlays.overall_progress", pct=self.result.overall_progress_pct),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#7AA2F7"
        )
        lbl_overall.pack(side="right")
        self._make_draggable(lbl_overall)

        # Footer con cuenta regresiva si aplica
        self._build_countdown_footer()

    def _render_multitier_bar(self, canvas: tk.Canvas, width: int, height: int):
        """Renderiza los segmentos de color correspondientes a los rangos del benchmark de forma limpia y responsiva."""
        if width <= 1 or height <= 1:
            return

        canvas.delete("all")

        rank_maxes = self.result.rank_maxes
        if not rank_maxes:
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
        for i, threshold in enumerate(rank_maxes):
            seg_x = int(((threshold - min_score) / score_span) * width)
            color = ranks_palette[i % len(ranks_palette)]
            canvas.create_rectangle(prev_x, 0, seg_x, height, fill=color, outline="")
            prev_x = seg_x

        if prev_x < width:
            canvas.create_rectangle(prev_x, 0, width, height, fill=ranks_palette[-1], outline="")

        # Marcador luminoso en la posición del nuevo puntaje
        cur_x = int(((self.result.new_score - min_score) / score_span) * width)
        cur_x = max(2, min(width - 3, cur_x))

        # Aguja blanca con sombra
        canvas.create_rectangle(cur_x - 2, 0, cur_x + 2, height, fill="#FFFFFF", outline="#000000")
