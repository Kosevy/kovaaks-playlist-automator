import os
import locale
import ctypes
from typing import Dict, Any, Callable, List, Optional


def detect_system_language() -> str:
    """
    Detecta el idioma predeterminado del sistema operativo Windows.
    Retorna 'es' si el idioma principal es español, de lo contrario 'en'.
    """
    try:
        # Intento 1: Windows API para idioma de interfaz de usuario
        windll = ctypes.windll.kernel32
        lang_id = windll.GetUserDefaultUILanguage()
        primary_lang = lang_id & 0x3FF
        if primary_lang == 0x0A:  # LANG_SPANISH
            return "es"
    except Exception:
        pass

    try:
        # Intento 2: locale de Python
        loc = locale.getdefaultlocale()[0]
        if loc and loc.lower().startswith("es"):
            return "es"
    except Exception:
        pass

    return "en"


TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "es": {
        "header": {
            "title": "KPA • KovaaK's Playlist Automator",
            "subtitle": "Optimización de debilidades • Monitoreo de sensibilidad en vivo • Overlays de Highscores EVXL",
            "badge_inactive": "● Monitor: Inactivo",
            "badge_active": "● Monitor: Activo",
            "badge_paused": "● Monitor: Pausado",
        },
        "tabs": {
            "generator": "⚡ Generador de Playlists",
            "monitor": "📡 Monitor en Vivo",
            "settings": "⚙ Ajustes y Overlays",
        },
        "generator": {
            "steam_label": "Steam ID o URL:",
            "steam_placeholder": "ej. 76561198000000000 o https://steamcommunity.com/profiles/76561198000000000",
            "bench_label": "Benchmark ID o URL:",
            "bench_placeholder": "ej. 2336 o https://evxl.app/benchmarks/2336",
            "dir_label": "Directorio Playlists:",
            "dir_placeholder": "Ruta a la carpeta Playlists de KovaaK's (deja vacío para explorar)",
            "browse_btn": "Explorar...",
            "name_label": "Nombre Playlist:",
            "name_placeholder": "improve-weaknesses",
            "generate_btn": "⚡ Generar Playlist de Debilidades",
            "generating_btn": "⏳ Procesando...",
            "ready_status": "Listo para procesar.",
            "connecting_status": "Resolviendo benchmark y conectando...",
            "success_status": "Playlist generada con éxito.",
            "error_status": "Ocurrió un error en la ejecución.",
            "console_title": "Consola de Resultados",
            "open_folder_btn": "Abrir Carpeta",
            "clear_btn": "Limpiar",
            "initial_banner": (
                "==========================================================\n"
                "  KPA - KovaaK's Playlist Automator & Live Tracker\n"
                "==========================================================\n"
                "• Configuración cargada desde config.json\n"
                "• Monitoreo en segundo plano listo para detectar repeticiones y highscores.\n\n"
            ),
            "log_analyzing_bench": "► Analizando identificador o URL del Benchmark...\n",
            "log_bench_identified": "✔ Benchmark identificado: {name}{diff} (ID: {id})\n",
            "log_resolving_steam": "► Intentando resolver Steam ID para el usuario '{author}' desde la URL...\n",
            "log_steam_detected": "✔ Steam ID detectado automáticamente: {sid} ({author})\n",
            "log_fetching_progress": "► Obteniendo progreso del jugador (Benchmark ID: {bid}, Steam ID: {sid})...\n",
            "log_fetching_sens": "► Obteniendo distribuciones de sensibilidad de EVXL...\n",
            "log_calculating": "► Calculando debilidades y estructurando playlist...\n",
            "summary_title": "✔ PLAYLIST GENERADA EXITOSAMENTE",
            "summary_benchmark": "Benchmark        : {bench}",
            "summary_file": "Archivo guardado : {file}",
            "summary_name": "Nombre playlist  : {name}",
            "summary_count": "Escenarios       : {count} (5 repeticiones cada uno)",
            "summary_header": "5 ESCENARIOS PROCESADOS (MAYOR MARGEN DE MEJORA):",
            "summary_scenario_name": "{idx}. Nombre del Escenario: {name}",
            "summary_scenario_sens": "   Sensibilidad Recomendada ({rank}): {sens}",
            "summary_scenario_score": "   Puntaje Continuo: {score}",
        },
        "monitor": {
            "game_detecting": "KovaaK's: Detectando...",
            "game_running": "● KovaaK's: En ejecución",
            "game_not_found": "○ KovaaK's: No detectado",
            "state_active": "Estado: Activo",
            "state_paused": "Estado: Pausado",
            "btn_pause": "⏸ Pausar Monitor",
            "btn_resume": "▶ Iniciar Monitor",
            "btn_sync": "🔄 Sincronizar EVXL",
            "active_scenario_title": "Escenario en Juego:",
            "no_active_scenario": "Ningún escenario activo (esperando KovaaK's)",
            "reps_title": "Progreso de Repeticiones:",
            "reps_count": "{current} / {target} repeticiones",
            "sens_title": "Sens Recomendada:",
            "feed_title": "Registro de Eventos en Tiempo Real (KovaaK's)",
            "rep_log": "► [Rep {rep}/{target}] {scenario} finalizado con {score} pts\n",
            "transition_log": "🔄 Cambio de escenario: {prev} ({reps} reps) ➔ {next} | Sens: {sens}\n",
            "highscore_log": (
                "🎉 [NUEVO HIGHSCORE] {scenario}: {old_score} ➔ {new_score} (+{delta} pts) "
                "| Rango: {rank} ({pct}%)\n"
            ),
            "sync_start_log": "► Sincronizando datos con EVXL y KovaaK's...\n",
            "sync_done_log": "✔ Benchmark sincronizado: {count} escenarios listos.\n",
            "sync_error_log": "❌ Error al sincronizar: {error}\n",
            "preload_success": "✔ Benchmark precargado: {name} ({count} escenarios en seguimiento)\n",
            "preload_fail": "[INFO] Benchmark no precargado automáticamente ({error}). Se cargará al sincronizar o generar playlist.\n",
            "status_listening": "Monitor activo y escuchando eventos de KovaaK's...",
            "status_stopped": "Monitor pausado.",
        },
        "settings": {
            "auto_copy_switch": "Copiar automáticamente la sensibilidad al portapapeles al cambiar de ejercicio",
            "copy_format_label": "Formato preferido al copiar:",
            "format_cm360": "cm/360",
            "format_ingame": "Escala In-Game",
            "early_notify_switch": "Notificar sensibilidad también si se cambia de escenario antes de las 5 repeticiones",
            "auto_close_switch": "Cerrar ventanas emergentes automáticamente tras un tiempo de espera",
            "auto_close_secs_label": "Segundos antes de cerrar automáticamente:",
            "corner_label": "Posición del overlay en pantalla:",
            "corner_top_right": "Superior Derecha",
            "corner_top_left": "Superior Izquierda",
            "corner_bottom_right": "Inferior Derecha",
            "corner_bottom_left": "Inferior Izquierda",
            "monitor_select_label": "Pantalla / Monitor para Overlays:",
            "monitor_primary_suffix": "(Principal)",
            "remember_drag_switch": "Recordar posición personalizada al arrastrar con el ratón",
            "btn_reset_pos": "↺ Restablecer Posición",
            "pos_reset_done": "Posición restablecida a la esquina",
            "drag_hint": "💡 Puedes arrastrar los overlays con el ratón desde sus bordes o cabecera para reubicarlos libremente.",
            "fullscreen_tip": "💡 Tip: Si KovaaK's se ejecuta en Pantalla Completa Exclusiva, selecciona el Monitor Secundario. Para verlos encima del juego en el monitor principal, usa Modo Ventana sin Bordes (Borderless) en KovaaK's.",
            "language_label": "Idioma / Language:",
            "test_section_title": "Pruebas de Superposición (Overlays)",
            "test_section_desc": "Prueba los overlays flotantes sobre cualquier ventana para comprobar su apariencia y comportamiento.",
            "test_sens_btn": "🧪 Probar Overlay de Sensibilidad",
            "test_high_btn": "🧪 Probar Overlay de Highscore",
        },
        "overlays": {
            "drag_grip_tooltip": "Arrastrar para mover",
            "sens_badge_next": "⚡ PRÓXIMO ESCENARIO",
            "sens_badge_early": "🔄 CAMBIO DE ESCENARIO",
            "copy_btn": "📋 Copiar",
            "copied_btn": "✔ ¡Copiado!",
            "copy_status_copied": "✔ Copiado al portapapeles",
            "copy_status_ready": "Listo para copiar",
            "copy_status_done": "✔ '{text}' copiado",
            "auto_close_countdown": "Auto-cierre en {secs}s",
            "auto_close_paused": "Auto-cierre en pausa",
            "highscore_title": "🎉 ¡NUEVO HIGHSCORE!",
            "rankup_title": "🏆 ¡ASCENSO DE RANGO & HIGHSCORE!",
            "delta_points": "+{delta} pts",
            "bar_header": "Rango: {rank}  •  {pct}% hacia {next_rank}",
            "points_remaining": "Faltan {points} pts para {next_rank}",
            "max_rank_completed": "¡Rango máximo completado!",
            "overall_progress": "Progreso Benchmark: {pct}%",
        },
        "dialogs": {
            "missing_bench_title": "Benchmark Faltante",
            "missing_bench_msg": "El campo de Benchmark ID o URL no puede estar vacío.",
            "missing_dir_title": "Directorio Faltante",
            "missing_dir_msg": "El directorio de Playlists no puede estar vacío. Usa el botón 'Explorar' para seleccionarlo.",
            "invalid_dir_title": "Directorio Inválido",
            "invalid_dir_msg": "El directorio seleccionado no existe en el sistema:\n{dir}",
            "browse_title": "Seleccionar Directorio de Playlists de KovaaK's",
            "folder_error_title": "Error",
            "folder_error_msg": "No se pudo abrir la carpeta:\n{error}",
            "invalid_folder_title": "Carpeta no válida",
            "invalid_folder_msg": "El directorio especificado no existe o está vacío.",
            "sync_missing_data_title": "Datos Faltantes",
            "sync_missing_data_msg": "Ingresa tu Steam ID y Benchmark ID en la pestaña Generador.",
            "sync_success_title": "Sincronización Exitosa",
            "sync_success_msg": "Benchmark sincronizado correctamente con EVXL.",
            "sync_error_title": "Error de Sincronización",
            "generate_error_title": "Error al Generar Playlist",
        }
    },
    "en": {
        "header": {
            "title": "KPA • KovaaK's Playlist Automator",
            "subtitle": "Weakness optimization • Live sensitivity monitor • EVXL Highscore overlays",
            "badge_inactive": "● Monitor: Inactive",
            "badge_active": "● Monitor: Active",
            "badge_paused": "● Monitor: Paused",
        },
        "tabs": {
            "generator": "⚡ Playlist Generator",
            "monitor": "📡 Live Monitor",
            "settings": "⚙ Settings & Overlays",
        },
        "generator": {
            "steam_label": "Steam ID or URL:",
            "steam_placeholder": "e.g. 76561198000000000 or https://steamcommunity.com/profiles/76561198000000000",
            "bench_label": "Benchmark ID or URL:",
            "bench_placeholder": "e.g. 2336 or https://evxl.app/benchmarks/2336",
            "dir_label": "Playlists Directory:",
            "dir_placeholder": "Path to KovaaK's Playlists folder (leave empty to browse)",
            "browse_btn": "Browse...",
            "name_label": "Playlist Name:",
            "name_placeholder": "improve-weaknesses",
            "generate_btn": "⚡ Generate Weakness Playlist",
            "generating_btn": "⏳ Processing...",
            "ready_status": "Ready to process.",
            "connecting_status": "Resolving benchmark and connecting...",
            "success_status": "Playlist generated successfully.",
            "error_status": "An error occurred during execution.",
            "console_title": "Results Console",
            "open_folder_btn": "Open Folder",
            "clear_btn": "Clear",
            "initial_banner": (
                "==========================================================\n"
                "  KPA - KovaaK's Playlist Automator & Live Tracker\n"
                "==========================================================\n"
                "• Configuration loaded from config.json\n"
                "• Background monitoring ready to track repetitions and high scores.\n\n"
            ),
            "log_analyzing_bench": "► Analyzing Benchmark identifier or URL...\n",
            "log_bench_identified": "✔ Benchmark identified: {name}{diff} (ID: {id})\n",
            "log_resolving_steam": "► Attempting to resolve Steam ID for user '{author}' from URL...\n",
            "log_steam_detected": "✔ Steam ID automatically detected: {sid} ({author})\n",
            "log_fetching_progress": "► Fetching player progress (Benchmark ID: {bid}, Steam ID: {sid})...\n",
            "log_fetching_sens": "► Fetching sensitivity distributions from EVXL...\n",
            "log_calculating": "► Calculating weaknesses and structuring playlist...\n",
            "summary_title": "✔ PLAYLIST GENERATED SUCCESSFULLY",
            "summary_benchmark": "Benchmark        : {bench}",
            "summary_file": "Saved file       : {file}",
            "summary_name": "Playlist name    : {name}",
            "summary_count": "Scenarios        : {count} (5 repetitions each)",
            "summary_header": "5 PROCESSED SCENARIOS (HIGHEST ROOM FOR IMPROVEMENT):",
            "summary_scenario_name": "{idx}. Scenario Name: {name}",
            "summary_scenario_sens": "   Recommended Sensitivity ({rank}): {sens}",
            "summary_scenario_score": "   Continuous Score: {score}",
        },
        "monitor": {
            "game_detecting": "KovaaK's: Detecting...",
            "game_running": "● KovaaK's: Running",
            "game_not_found": "○ KovaaK's: Not detected",
            "state_active": "Status: Active",
            "state_paused": "Status: Paused",
            "btn_pause": "⏸ Pause Monitor",
            "btn_resume": "▶ Start Monitor",
            "btn_sync": "🔄 Sync EVXL",
            "active_scenario_title": "Current Scenario:",
            "no_active_scenario": "No active scenario (waiting for KovaaK's)",
            "reps_title": "Repetition Progress:",
            "reps_count": "{current} / {target} repetitions",
            "sens_title": "Recommended Sens:",
            "feed_title": "Real-Time Event Feed (KovaaK's)",
            "rep_log": "► [Rep {rep}/{target}] {scenario} completed with {score} pts\n",
            "transition_log": "🔄 Scenario transition: {prev} ({reps} reps) ➔ {next} | Sens: {sens}\n",
            "highscore_log": (
                "🎉 [NEW HIGHSCORE] {scenario}: {old_score} ➔ {new_score} (+{delta} pts) "
                "| Rank: {rank} ({pct}%)\n"
            ),
            "sync_start_log": "► Synchronizing data with EVXL and KovaaK's...\n",
            "sync_done_log": "✔ Benchmark synchronized: {count} scenarios ready.\n",
            "sync_error_log": "❌ Sync error: {error}\n",
            "preload_success": "✔ Benchmark preloaded: {name} ({count} scenarios tracked)\n",
            "preload_fail": "[INFO] Benchmark not preloaded automatically ({error}). It will load on sync or playlist generation.\n",
            "status_listening": "Monitor active and listening to KovaaK's events...",
            "status_stopped": "Monitor paused.",
        },
        "settings": {
            "auto_copy_switch": "Automatically copy sensitivity to clipboard on scenario switch",
            "copy_format_label": "Preferred copy format:",
            "format_cm360": "cm/360",
            "format_ingame": "In-Game Scale",
            "early_notify_switch": "Notify sensitivity even if scenario changes before 5 repetitions",
            "auto_close_switch": "Automatically close popup overlays after a timeout",
            "auto_close_secs_label": "Seconds before closing automatically:",
            "corner_label": "Overlay screen position:",
            "corner_top_right": "Top Right",
            "corner_top_left": "Top Left",
            "corner_bottom_right": "Bottom Right",
            "corner_bottom_left": "Bottom Left",
            "monitor_select_label": "Screen / Monitor for Overlays:",
            "monitor_primary_suffix": "(Primary)",
            "remember_drag_switch": "Remember custom position when dragging with mouse",
            "btn_reset_pos": "↺ Reset Position",
            "pos_reset_done": "Position reset to corner",
            "drag_hint": "💡 You can drag overlays with your mouse from their borders or header to freely reposition them.",
            "fullscreen_tip": "💡 Tip: If KovaaK's runs in Exclusive Fullscreen, select the Secondary Monitor. To display them directly over the game on the primary monitor, set KovaaK's to Borderless Windowed mode.",
            "language_label": "Language / Idioma:",
            "test_section_title": "Overlay Tests",
            "test_section_desc": "Test floating overlays over any window to check their appearance and behavior.",
            "test_sens_btn": "🧪 Test Sensitivity Overlay",
            "test_high_btn": "🧪 Test Highscore Overlay",
        },
        "overlays": {
            "drag_grip_tooltip": "Drag to move",
            "sens_badge_next": "⚡ NEXT SCENARIO",
            "sens_badge_early": "🔄 SCENARIO SWITCH",
            "copy_btn": "📋 Copy",
            "copied_btn": "✔ Copied!",
            "copy_status_copied": "✔ Copied to clipboard",
            "copy_status_ready": "Ready to copy",
            "copy_status_done": "✔ '{text}' copied",
            "auto_close_countdown": "Auto-closing in {secs}s",
            "auto_close_paused": "Auto-close paused",
            "highscore_title": "🎉 NEW HIGHSCORE!",
            "rankup_title": "🏆 RANK UP & HIGHSCORE!",
            "delta_points": "+{delta} pts",
            "bar_header": "Rank: {rank}  •  {pct}% towards {next_rank}",
            "points_remaining": "{points} pts remaining for {next_rank}",
            "max_rank_completed": "Maximum rank achieved!",
            "overall_progress": "Benchmark Progress: {pct}%",
        },
        "dialogs": {
            "missing_bench_title": "Missing Benchmark",
            "missing_bench_msg": "Benchmark ID or URL cannot be empty.",
            "missing_dir_title": "Missing Directory",
            "missing_dir_msg": "Playlists directory cannot be empty. Use 'Browse' to select one.",
            "invalid_dir_title": "Invalid Directory",
            "invalid_dir_msg": "Selected directory does not exist on your system:\n{dir}",
            "browse_title": "Select KovaaK's Playlists Directory",
            "folder_error_title": "Error",
            "folder_error_msg": "Could not open directory:\n{error}",
            "invalid_folder_title": "Invalid Folder",
            "invalid_folder_msg": "Specified directory does not exist or is empty.",
            "sync_missing_data_title": "Missing Data",
            "sync_missing_data_msg": "Enter your Steam ID and Benchmark ID in the Generator tab.",
            "sync_success_title": "Sync Successful",
            "sync_success_msg": "Benchmark successfully synchronized with EVXL.",
            "sync_error_title": "Synchronization Error",
            "generate_error_title": "Error Generating Playlist",
        }
    }
}


class I18nManager:
    """Gestor singleton de internacionalización."""

    _instance: Optional["I18nManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._language = "es"
            cls._instance._listeners: List[Callable[[], None]] = []
        return cls._instance

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, lang: str) -> None:
        """Establece el idioma ('es' o 'en') y notifica a los suscriptores."""
        normalized = lang.lower().strip()
        if normalized not in ("es", "en"):
            normalized = "es"

        if normalized != self._language:
            self._language = normalized
            self._notify_listeners()

    def register_listener(self, callback: Callable[[], None]) -> None:
        """Registra un observador para ser notificado al cambiar de idioma."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[], None]) -> None:
        """Elimina un observador registrado."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:
                pass

    def translate(self, key_path: str, **kwargs) -> str:
        """
        Busca una clave en el catálogo del idioma actual usando notación con puntos.
        Ej: t("header.title") o t("overlays.delta_points", delta=369.0)
        """
        parts = key_path.split(".")
        val = self._lookup(self._language, parts)

        # Fallback al otro idioma si no se encuentra
        if val is None:
            fallback_lang = "en" if self._language == "es" else "es"
            val = self._lookup(fallback_lang, parts)

        if val is None:
            return key_path  # Retornar la clave como último recurso

        if kwargs and isinstance(val, str):
            try:
                return val.format(**kwargs)
            except Exception:
                return val

        return str(val)

    def _lookup(self, lang: str, parts: List[str]) -> Any:
        curr = TRANSLATIONS.get(lang, {})
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                return None
        return curr


_i18n_manager = I18nManager()


def get_i18n() -> I18nManager:
    """Retorna la instancia del gestor i18n."""
    return _i18n_manager


def t(key_path: str, **kwargs) -> str:
    """Función helper global para traducir cadenas."""
    return _i18n_manager.translate(key_path, **kwargs)
