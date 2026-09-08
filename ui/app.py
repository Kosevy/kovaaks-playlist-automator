import os
import subprocess
import threading
from typing import Dict, Any, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.config import ConfigManager
from core.extractor import extract_steam_id, extract_benchmark_id
from core.api_client import KovaaksApiClient
from core.playlist_service import PlaylistService


class KPAApp(ctk.CTk):
    """Interfaz gráfica principal de KovaaK's Playlist Automator."""

    def __init__(self):
        super().__init__()

        # 1. Configuración de Apariencia
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("KPA - KovaaK's Playlist Automator")
        self.geometry("780x740")
        self.minsize(700, 620)

        # 2. Servicios del Core
        self.config_manager = ConfigManager()
        self.config_data = self.config_manager.load_config()
        self.api_client = KovaaksApiClient()
        self.playlist_service = PlaylistService()

        # Variable para controlar estado de ejecución
        self.is_processing = False

        # Protocolo de cierre para persistir valores
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 3. Construcción de la UI
        self._create_widgets()
        self._load_saved_values()

    def _create_widgets(self):
        # Configuración del Grid principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- ENCABEZADO ---
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text="KovaaK's Playlist Automator",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Automatización de estadísticas de evxl.app y generador de playlists por debilidades",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle_label.pack(anchor="w")

        # --- FORMULARIO DE ENTRADA ---
        form_frame = ctk.CTkFrame(self, corner_radius=10)
        form_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)

        # 1. Steam ID
        steam_label = ctk.CTkLabel(form_frame, text="Steam ID o URL:", font=ctk.CTkFont(weight="bold"))
        steam_label.grid(row=0, column=0, padx=(15, 10), pady=(12, 6), sticky="w")

        self.entry_steam = ctk.CTkEntry(
            form_frame,
            placeholder_text="ej. 76561198444816419 o https://steamcommunity.com/profiles/76561198444816419"
        )
        self.entry_steam.grid(row=0, column=1, columnspan=2, padx=(0, 15), pady=(12, 6), sticky="ew")

        # 2. Benchmark ID
        bench_label = ctk.CTkLabel(form_frame, text="Benchmark ID o URL:", font=ctk.CTkFont(weight="bold"))
        bench_label.grid(row=1, column=0, padx=(15, 10), pady=6, sticky="w")

        self.entry_benchmark = ctk.CTkEntry(
            form_frame,
            placeholder_text="ej. 2336 o https://evxl.app/benchmarks/2336"
        )
        self.entry_benchmark.grid(row=1, column=1, columnspan=2, padx=(0, 15), pady=6, sticky="ew")

        # 3. Directorio de Playlists Local
        dir_label = ctk.CTkLabel(form_frame, text="Directorio Playlists:", font=ctk.CTkFont(weight="bold"))
        dir_label.grid(row=2, column=0, padx=(15, 10), pady=6, sticky="w")

        self.entry_dir = ctk.CTkEntry(
            form_frame,
            placeholder_text="Ruta a la carpeta Playlists de KovaaK's (deja vacío para explorar)"
        )
        self.entry_dir.grid(row=2, column=1, padx=(0, 10), pady=6, sticky="ew")

        self.btn_browse = ctk.CTkButton(
            form_frame,
            text="Explorar...",
            width=95,
            command=self._on_browse_directory
        )
        self.btn_browse.grid(row=2, column=2, padx=(0, 15), pady=6, sticky="e")

        # 4. Nombre de la Playlist
        name_label = ctk.CTkLabel(form_frame, text="Nombre Playlist:", font=ctk.CTkFont(weight="bold"))
        name_label.grid(row=3, column=0, padx=(15, 10), pady=(6, 12), sticky="w")

        self.entry_name = ctk.CTkEntry(
            form_frame,
            placeholder_text="improve-weaknesses"
        )
        self.entry_name.grid(row=3, column=1, columnspan=2, padx=(0, 15), pady=(6, 12), sticky="ew")

        # --- SECCIÓN DE ACCIONES ---
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.btn_generate = ctk.CTkButton(
            action_frame,
            text="⚡ Generar Playlist",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=42,
            command=self._on_generate_clicked
        )
        self.btn_generate.grid(row=0, column=0, sticky="ew")

        self.lbl_status = ctk.CTkLabel(
            action_frame,
            text="Listo para procesar.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.lbl_status.grid(row=1, column=0, pady=(4, 0), sticky="w")

        # --- ÁREA DE RESULTADOS (TEXTBOX) ---
        output_frame = ctk.CTkFrame(self, corner_radius=10)
        output_frame.grid(row=3, column=0, padx=20, pady=(10, 15), sticky="nsew")
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(1, weight=1)

        top_output_bar = ctk.CTkFrame(output_frame, fg_color="transparent")
        top_output_bar.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
        top_output_bar.grid_columnconfigure(0, weight=1)

        lbl_console = ctk.CTkLabel(
            top_output_bar,
            text="Consola de Resultados y Salida",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        lbl_console.grid(row=0, column=0, sticky="w")

        self.btn_open_folder = ctk.CTkButton(
            top_output_bar,
            text="Abrir Carpeta",
            width=100,
            height=26,
            fg_color="#333333",
            hover_color="#444444",
            command=self._on_open_folder
        )
        self.btn_open_folder.grid(row=0, column=1, padx=(5, 5), sticky="e")

        self.btn_clear = ctk.CTkButton(
            top_output_bar,
            text="Limpiar",
            width=70,
            height=26,
            fg_color="#333333",
            hover_color="#444444",
            command=self._clear_textbox
        )
        self.btn_clear.grid(row=0, column=2, sticky="e")

        self.textbox_output = ctk.CTkTextbox(
            output_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            corner_radius=8
        )
        self.textbox_output.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="nsew")

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

        self._append_text(
            "==========================================================\n"
            "  KPA - KovaaK's Playlist Automator Inicializado\n"
            "==========================================================\n"
            "• Configuración cargada desde config.json\n"
            "• Ingresa tus datos o revisa los campos y presiona 'Generar Playlist'.\n\n"
        )

    def _save_current_values(self):
        """Guarda los valores actuales de los campos en config.json."""
        self.config_data = {
            "steam_input": self.entry_steam.get().strip(),
            "benchmark_input": self.entry_benchmark.get().strip(),
            "playlist_dir": self.entry_dir.get().strip(),
            "playlist_name": self.entry_name.get().strip() or "improve-weaknesses"
        }
        try:
            self.config_manager.save_config(self.config_data)
        except Exception as e:
            self._append_text(f"[ADVERTENCIA] No se pudo guardar config.json: {e}\n")

    def _on_closing(self):
        """Manejador del evento de cierre de ventana para persistir datos."""
        self._save_current_values()
        self.destroy()

    def _on_browse_directory(self):
        """Abre un cuadro de diálogo para seleccionar la carpeta de Playlists."""
        current_dir = self.entry_dir.get().strip()
        initial_dir = current_dir if os.path.isdir(current_dir) else os.path.expanduser("~")

        selected_dir = filedialog.askdirectory(
            parent=self,
            title="Seleccionar Directorio de Playlists de KovaaK's",
            initialdir=initial_dir
        )
        if selected_dir:
            # Normalizar ruta a estilo Windows
            normalized_path = os.path.normpath(selected_dir)
            self.entry_dir.delete(0, "end")
            self.entry_dir.insert(0, normalized_path)
            self._save_current_values()

    def _on_open_folder(self):
        """Abre el explorador de archivos en la carpeta de Playlists seleccionada."""
        current_dir = self.entry_dir.get().strip()
        if current_dir and os.path.isdir(current_dir):
            try:
                os.startfile(current_dir)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{e}")
        else:
            messagebox.showwarning("Carpeta no válida", "El directorio especificado no existe o está vacío.")

    def _clear_textbox(self):
        """Limpia el contenido del área de texto."""
        self.textbox_output.delete("1.0", "end")

    def _append_text(self, text: str):
        """Inserta texto en la consola de forma segura."""
        self.textbox_output.insert("end", text)
        self.textbox_output.see("end")

    def _update_ui_state(self, is_processing: bool, status_msg: str):
        """Habilita o deshabilita los controles de la UI según el estado del hilo."""
        self.is_processing = is_processing
        if is_processing:
            self.btn_generate.configure(state="disabled", text="⏳ Procesando...")
            self.lbl_status.configure(text=status_msg, text_color="#3B8ED0")
        else:
            self.btn_generate.configure(state="normal", text="⚡ Generar Playlist")
            self.lbl_status.configure(text=status_msg, text_color="gray")

    def _on_generate_clicked(self):
        """Inicia el proceso de generación en un hilo en segundo plano."""
        if self.is_processing:
            return

        # Guardar valores inmediatamente
        self._save_current_values()

        raw_steam = self.entry_steam.get().strip()
        raw_bench = self.entry_benchmark.get().strip()
        raw_dir = self.entry_dir.get().strip()
        raw_name = self.entry_name.get().strip() or "improve-weaknesses"

        # Validaciones preliminares
        try:
            steam_id = extract_steam_id(raw_steam)
            benchmark_id = extract_benchmark_id(raw_bench)
        except ValueError as e:
            self._append_text(f"[ERROR DE VALIDACIÓN] {e}\n\n")
            messagebox.showerror("Dato Inválido", str(e))
            return

        if not raw_dir:
            msg = "El directorio de Playlists no puede estar vacío. Usa el botón 'Explorar' para seleccionarlo."
            self._append_text(f"[ERROR DE VALIDACIÓN] {msg}\n\n")
            messagebox.showerror("Directorio Faltante", msg)
            return

        if not os.path.isdir(raw_dir):
            msg = f"El directorio seleccionado no existe en el sistema:\n{raw_dir}"
            self._append_text(f"[ERROR DE RUTA] {msg}\n\n")
            messagebox.showerror("Directorio Inválido", msg)
            return

        # Ejecutar en segundo plano para no congelar la UI
        worker_thread = threading.Thread(
            target=self._worker_process,
            args=(benchmark_id, steam_id, raw_dir, raw_name),
            daemon=True
        )
        self._update_ui_state(True, "Conectando con KovaaK's y EVXL...")
        worker_thread.start()

    def _worker_process(
        self,
        benchmark_id: str,
        steam_id: str,
        destination_dir: str,
        requested_name: str
    ):
        """Hilo secundario que realiza las peticiones HTTP y cálculos."""
        try:
            # 1. Petición de progreso
            self.after(0, lambda: self._append_text(
                f"► Obteniendo progreso del jugador (Benchmark ID: {benchmark_id}, Steam ID: {steam_id})...\n"
            ))
            progress_data = self.api_client.fetch_player_progress(benchmark_id, steam_id)

            # 2. Petición de sensibilidades
            self.after(0, lambda: self._append_text("► Obteniendo distribuciones de sensibilidad de EVXL...\n"))
            sens_data = self.api_client.fetch_sensitivity_distributions(benchmark_id)

            # 3. Procesar y generar archivo de playlist
            self.after(0, lambda: self._append_text("► Calculando debilidades y estructurando playlist...\n"))
            result = self.playlist_service.process_and_generate_playlist(
                progress_data=progress_data,
                sens_data=sens_data,
                destination_dir=destination_dir,
                requested_name=requested_name
            )

            # 4. Mostrar resultados exitosos en la UI
            self.after(0, lambda: self._on_success_callback(result))

        except Exception as e:
            # Captura y muestra de cualquier excepción (conexión, timeouts, filesystem, etc.)
            error_msg = str(e)
            self.after(0, lambda: self._on_error_callback(error_msg))

    def _on_success_callback(self, result: Dict[str, Any]):
        """Actualiza la UI tras una ejecución exitosa."""
        self._update_ui_state(False, "Playlist generada con éxito.")

        scenarios = result["scenarios"]
        file_path = result["file_path"]
        pl_name = result["playlist_name"]

        out = []
        out.append("\n==========================================================")
        out.append("  ✔ PLAYLIST GENERADA EXITOSAMENTE")
        out.append("==========================================================")
        out.append(f"Archivo guardado : {file_path}")
        out.append(f"Nombre playlist  : {pl_name}")
        out.append(f"Escenarios       : {len(scenarios)} (5 repeticiones cada uno)")
        out.append("----------------------------------------------------------")
        out.append("  5 ESCENARIOS PROCESADOS (MAYOR MARGEN DE MEJORA):")
        out.append("----------------------------------------------------------")

        for idx, sc in enumerate(scenarios, start=1):
            rank_label = sc["sens_rank"] if sc.get("sens_rank") else "Fuchsia"
            sens_text = f"{sc['sens_value']} cm/360" if sc.get("sens_value") is not None else "N/A"
            out.append(f"{idx}. Nombre del Escenario: {sc['name']}")
            out.append(f"   Sensibilidad Recomendada ({rank_label}): {sens_text}")
            out.append(f"   Puntaje Continuo: {sc['continuous_score']}")
            out.append("")

        out.append("==========================================================\n")
        self._append_text("\n".join(out))

    def _on_error_callback(self, error_msg: str):
        """Actualiza la UI en caso de error durante la ejecución."""
        self._update_ui_state(False, "Ocurrió un error en la ejecución.")

        err_banner = [
            "\n❌ -------------------- ERROR ENCONTRADO --------------------",
            f"{error_msg}",
            "-----------------------------------------------------------\n"
        ]
        self._append_text("\n".join(err_banner))
        messagebox.showerror("Error al Generar Playlist", error_msg)
