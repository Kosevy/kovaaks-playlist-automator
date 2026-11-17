from typing import Optional, Callable, Dict
import customtkinter as ctk
from core.i18n import t


class GeneratorTab(ctk.CTkFrame):
    """
    Pestaña de Generación de Playlists de KPA.
    Contiene el formulario de entrada, botón de generación y la consola de resultados.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        on_browse_clicked: Optional[Callable[[], None]] = None,
        on_generate_clicked: Optional[Callable[[], None]] = None,
        on_open_folder_clicked: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.on_browse_clicked = on_browse_clicked
        self.on_generate_clicked = on_generate_clicked
        self.on_open_folder_clicked = on_open_folder_clicked

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_ui()

    def _build_ui(self):
        # 1. Formulario de Entrada
        form_frame = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color="#181926",
            border_width=1,
            border_color="#2A2E3D"
        )
        form_frame.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)

        # Steam ID
        self.steam_label = ctk.CTkLabel(form_frame, text=t("generator.steam_label"), font=ctk.CTkFont(weight="bold"))
        self.steam_label.grid(row=0, column=0, padx=(15, 10), pady=(12, 6), sticky="w")

        self.entry_steam = ctk.CTkEntry(
            form_frame,
            placeholder_text=t("generator.steam_placeholder")
        )
        self.entry_steam.grid(row=0, column=1, columnspan=2, padx=(0, 15), pady=(12, 6), sticky="ew")

        # Benchmark ID
        self.bench_label = ctk.CTkLabel(form_frame, text=t("generator.bench_label"), font=ctk.CTkFont(weight="bold"))
        self.bench_label.grid(row=1, column=0, padx=(15, 10), pady=6, sticky="w")

        self.entry_benchmark = ctk.CTkEntry(
            form_frame,
            placeholder_text=t("generator.bench_placeholder")
        )
        self.entry_benchmark.grid(row=1, column=1, columnspan=2, padx=(0, 15), pady=6, sticky="ew")

        # Directorio de Playlists Local
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
            command=self._handle_browse
        )
        self.btn_browse.grid(row=2, column=2, padx=(0, 15), pady=6, sticky="e")

        # Nombre de la Playlist
        self.name_label = ctk.CTkLabel(form_frame, text=t("generator.name_label"), font=ctk.CTkFont(weight="bold"))
        self.name_label.grid(row=3, column=0, padx=(15, 10), pady=(6, 12), sticky="w")

        self.entry_name = ctk.CTkEntry(
            form_frame,
            placeholder_text=t("generator.name_placeholder")
        )
        self.entry_name.grid(row=3, column=1, columnspan=2, padx=(0, 15), pady=(6, 12), sticky="ew")

        # 2. Fila de Acción
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=1, column=0, padx=10, pady=(6, 4), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.btn_generate = ctk.CTkButton(
            action_frame,
            text=t("generator.generate_btn"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self._handle_generate
        )
        self.btn_generate.grid(row=0, column=0, sticky="ew")

        self.lbl_status = ctk.CTkLabel(
            action_frame,
            text=t("generator.ready_status"),
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.lbl_status.grid(row=1, column=0, pady=(4, 0), sticky="w")

        # 3. Consola de Resultados
        output_frame = ctk.CTkFrame(
            self,
            corner_radius=10,
            fg_color="#181926",
            border_width=1,
            border_color="#2A2E3D"
        )
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
            command=self._handle_open_folder
        )
        self.btn_open_folder.grid(row=0, column=1, padx=(5, 5), sticky="e")

        self.btn_clear = ctk.CTkButton(
            top_output_bar,
            text=t("generator.clear_btn"),
            width=65,
            height=26,
            fg_color="#24283B",
            hover_color="#3B4261",
            command=self.clear_log
        )
        self.btn_clear.grid(row=0, column=2, sticky="e")

        self.textbox_output = ctk.CTkTextbox(
            output_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            corner_radius=8
        )
        self.textbox_output.grid(row=1, column=0, padx=12, pady=(4, 12), sticky="nsew")

    def _handle_browse(self):
        if self.on_browse_clicked:
            self.on_browse_clicked()

    def _handle_generate(self):
        if self.on_generate_clicked:
            self.on_generate_clicked()

    def _handle_open_folder(self):
        if self.on_open_folder_clicked:
            self.on_open_folder_clicked()

    def retranslate(self):
        """Actualiza todos los textos de la pestaña según el idioma activo."""
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

    def load_values(self, steam: str = "", bench: str = "", dir_path: str = "", name: str = ""):
        """Carga valores en los campos de entrada."""
        if steam:
            self.entry_steam.delete(0, "end")
            self.entry_steam.insert(0, steam)
        if bench:
            self.entry_benchmark.delete(0, "end")
            self.entry_benchmark.insert(0, bench)
        if dir_path:
            self.entry_dir.delete(0, "end")
            self.entry_dir.insert(0, dir_path)
        if name:
            self.entry_name.delete(0, "end")
            self.entry_name.insert(0, name)

    def get_values(self) -> Dict[str, str]:
        """Devuelve los valores actuales de los campos de entrada."""
        return {
            "steam": self.entry_steam.get().strip(),
            "benchmark": self.entry_benchmark.get().strip(),
            "dir": self.entry_dir.get().strip(),
            "name": self.entry_name.get().strip() or "improve-weaknesses"
        }

    def set_steam_id(self, steam_id: str):
        """Asigna un nuevo Steam ID en el campo de entrada."""
        self.entry_steam.delete(0, "end")
        self.entry_steam.insert(0, steam_id)

    def set_dir(self, dir_path: str):
        """Asigna un nuevo directorio en el campo de entrada."""
        self.entry_dir.delete(0, "end")
        self.entry_dir.insert(0, dir_path)

    def append_log(self, text: str):
        """Agrega texto a la consola de salida y desplaza al final."""
        self.textbox_output.insert("end", text)
        self.textbox_output.see("end")

    def clear_log(self):
        """Limpia el contenido de la consola de salida."""
        self.textbox_output.delete("1.0", "end")

    def set_processing_state(self, is_processing: bool, status_msg: str):
        """Actualiza el estado visual del botón de generación y etiqueta de estado."""
        if is_processing:
            self.btn_generate.configure(state="disabled", text=t("generator.generating_btn"))
            self.lbl_status.configure(text=status_msg, text_color="#3B8ED0")
        else:
            self.btn_generate.configure(state="normal", text=t("generator.generate_btn"))
            self.lbl_status.configure(text=status_msg, text_color="gray")
