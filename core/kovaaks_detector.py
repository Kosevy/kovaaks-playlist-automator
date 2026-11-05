import os
import json
import re
from typing import Dict, Any, Optional, Tuple


# Factores de incremento por defecto (grados por conteo / yaw increment) para escalas comunes
DEFAULT_YAW_INCREMENTS = {
    "Quake/Source": 0.022,
    "Apex Legends": 0.022,
    "Counter-Strike": 0.022,
    "Overwatch": 0.0066,
    "Valorant": 0.06996,
    "Fortnite": 0.005555,
    "Marvel Rivals": 0.0175,
    "Rainbow Six Siege": 0.00572,
}


class KovaaksDetector:
    """Detecta las rutas de instalación, logs, estadísticas y configuraciones de KovaaK's."""

    def __init__(self, custom_playlist_dir: Optional[str] = None):
        self.custom_playlist_dir = custom_playlist_dir
        self._cached_install_dir: Optional[str] = None
        self._cached_stats_dir: Optional[str] = None
        self._cached_log_path: Optional[str] = None
        self._cached_user_settings_path: Optional[str] = None
        self._cached_fov_sens_path: Optional[str] = None
        self._cached_playlist_in_prog_path: Optional[str] = None
        self._cached_playlist_order_path: Optional[str] = None
        self._yaw_increments: Dict[str, float] = dict(DEFAULT_YAW_INCREMENTS)

    def find_install_dir(self) -> Optional[str]:
        """Localiza el directorio de instalación de KovaaK's."""
        if self._cached_install_dir and os.path.isdir(self._cached_install_dir):
            return self._cached_install_dir

        candidates = []
        if self.custom_playlist_dir:
            # Si el usuario especificó la carpeta Playlists, subir hasta FPSAimTrainer
            curr = os.path.abspath(self.custom_playlist_dir)
            while curr and os.path.splitdrive(curr)[1] not in ("\\", "/"):
                if os.path.basename(curr).lower() == "fpsaimtrainer":
                    candidates.append(curr)
                    break
                curr = os.path.dirname(curr)

        # Rutas comunes por defecto de Steam
        candidates.extend([
            r"C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer",
            r"C:\Program Files\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer",
            r"D:\SteamLibrary\steamapps\common\FPSAimTrainer\FPSAimTrainer",
            r"E:\SteamLibrary\steamapps\common\FPSAimTrainer\FPSAimTrainer",
        ])

        for path in candidates:
            if os.path.isdir(path):
                self._cached_install_dir = path
                return path

        return None

    def find_stats_dir(self) -> Optional[str]:
        """Localiza el directorio stats donde KovaaK's almacena los CSV de cada sesión."""
        if self._cached_stats_dir and os.path.isdir(self._cached_stats_dir):
            return self._cached_stats_dir

        install_dir = self.find_install_dir()
        if install_dir:
            stats_path = os.path.join(install_dir, "stats")
            if os.path.isdir(stats_path):
                self._cached_stats_dir = stats_path
                return stats_path

        return None

    def find_log_path(self) -> Optional[str]:
        """Localiza el archivo de log activo de Unreal Engine (FPSAimTrainer.log)."""
        if self._cached_log_path and os.path.isfile(self._cached_log_path):
            return self._cached_log_path

        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = os.path.join(local_app_data, "FPSAimTrainer", "Saved", "Logs", "FPSAimTrainer.log")
            if os.path.isfile(candidate):
                self._cached_log_path = candidate
                return candidate

        return None

    def find_user_settings_path(self) -> Optional[str]:
        """Localiza PrimaryUserSettings.json de KovaaK's."""
        if self._cached_user_settings_path and os.path.isfile(self._cached_user_settings_path):
            return self._cached_user_settings_path

        install_dir = self.find_install_dir()
        if install_dir:
            candidate = os.path.join(install_dir, "Saved", "SaveGames", "PrimaryUserSettings.json")
            if os.path.isfile(candidate):
                self._cached_user_settings_path = candidate
                return candidate

        return None

    def find_fov_sens_config_path(self) -> Optional[str]:
        """Localiza FovSensConfig.json con las fórmulas exactas del juego."""
        if self._cached_fov_sens_path and os.path.isfile(self._cached_fov_sens_path):
            return self._cached_fov_sens_path

        install_dir = self.find_install_dir()
        if install_dir:
            candidate = os.path.join(install_dir, "Saved", "SaveGames", "FovSensConfig.json")
            if os.path.isfile(candidate):
                self._cached_fov_sens_path = candidate
                return candidate

        return None

    def find_playlist_in_progress_path(self) -> Optional[str]:
        """Localiza PlaylistInProgress.json con la lista activa de escenarios."""
        if self._cached_playlist_in_prog_path and os.path.isfile(self._cached_playlist_in_prog_path):
            return self._cached_playlist_in_prog_path

        install_dir = self.find_install_dir()
        if install_dir:
            candidate = os.path.join(install_dir, "Saved", "SaveGames", "PlaylistInProgress.json")
            if os.path.isfile(candidate):
                self._cached_playlist_in_prog_path = candidate
                return candidate

        return None

    def find_playlist_order_path(self) -> Optional[str]:
        """Localiza PlaylistOrder.json con el índice del escenario actual en la playlist."""
        if self._cached_playlist_order_path and os.path.isfile(self._cached_playlist_order_path):
            return self._cached_playlist_order_path

        install_dir = self.find_install_dir()
        if install_dir:
            candidate = os.path.join(install_dir, "Saved", "SaveGames", "PlaylistOrder.json")
            if os.path.isfile(candidate):
                self._cached_playlist_order_path = candidate
                return candidate

        return None

    def is_game_running(self) -> bool:
        """Determina de forma ultrarrápida si el proceso de KovaaK's está en ejecución."""
        try:
            import ctypes
            from ctypes import wintypes

            TH32CS_SNAPPROCESS = 0x00000002

            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ('dwSize', wintypes.DWORD),
                    ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.POINTER(wintypes.ULONG)),
                    ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', wintypes.LONG),
                    ('dwFlags', wintypes.DWORD),
                    ('szExeFile', ctypes.c_char * 260)
                ]

            kernel32 = ctypes.windll.kernel32
            hSnapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
            if hSnapshot == -1:
                return False

            pe32 = PROCESSENTRY32()
            pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
            success = kernel32.Process32First(hSnapshot, ctypes.byref(pe32))
            found = False
            while success:
                name = pe32.szExeFile.decode('utf-8', errors='ignore').lower()
                if 'fpsaimtrainer' in name:
                    found = True
                    break
                success = kernel32.Process32Next(hSnapshot, ctypes.byref(pe32))
            kernel32.CloseHandle(hSnapshot)
            return found
        except Exception:
            return False

    def load_user_settings(self) -> Dict[str, Any]:
        """Lee PrimaryUserSettings.json para extraer DPI, Escala y Sens actual."""
        settings_path = self.find_user_settings_path()
        result = {
            "dpi": 1600,
            "sens_scale": "Marvel Rivals",
            "x_sens": 0.65314,
            "y_sens": 0.65314,
            "is_loaded": False,
        }
        if not settings_path or not os.path.isfile(settings_path):
            return result

        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            int_settings = data.get("integerSettings", {})
            string_settings = data.get("stringSettings", {})
            float_settings = data.get("floatSettings", {})

            if "EIntegerSettingId::DPI" in int_settings:
                result["dpi"] = int(int_settings["EIntegerSettingId::DPI"])

            if "EStringSettingId::SensScaleString" in string_settings:
                result["sens_scale"] = str(string_settings["EStringSettingId::SensScaleString"])

            if "EFloatSettingId::XSens" in float_settings:
                result["x_sens"] = float(float_settings["EFloatSettingId::XSens"])
            if "EFloatSettingId::YSens" in float_settings:
                result["y_sens"] = float(float_settings["EFloatSettingId::YSens"])

            result["is_loaded"] = True
        except Exception:
            pass

        return result

    def get_yaw_increment(self, scale_name: str) -> float:
        """Obtiene el incremento yaw para la escala dada, leyendo FovSensConfig.json si está disponible."""
        if scale_name in self._yaw_increments:
            return self._yaw_increments[scale_name]

        # Intentar cargar desde FovSensConfig.json
        cfg_path = self.find_fov_sens_config_path()
        if cfg_path and os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    configs = json.load(f)
                    for item in configs:
                        if item.get("ScaleName") == scale_name:
                            sens_data = item.get("Sens", {})
                            formula = sens_data.get("IncrementFormula", "")
                            # ej: "Sens * 0.0175"
                            match = re.search(r"Sens\s*\*\s*([0-9.]+)", formula)
                            if match:
                                inc = float(match.group(1))
                                self._yaw_increments[scale_name] = inc
                                return inc
            except Exception:
                pass

        # Fallback a Quake/Source si no se reconoce
        return DEFAULT_YAW_INCREMENTS.get("Quake/Source", 0.022)

    def cm360_to_ingame_sens(self, cm360: float, scale_name: str, dpi: int) -> float:
        """
        Convierte una sensibilidad en cm/360 a la escala del juego activo.
        Fórmula: Sens = (360 * 2.54) / (cm360 * yaw_increment * DPI)
        """
        if cm360 <= 0 or dpi <= 0:
            return 0.0

        yaw_inc = self.get_yaw_increment(scale_name)
        if yaw_inc <= 0:
            return 0.0

        # 360 pulgadas * 2.54 = 914.4
        sens = 914.4 / (cm360 * yaw_inc * dpi)
        return round(sens, 5)

    def ingame_sens_to_cm360(self, sens: float, scale_name: str, dpi: int) -> float:
        """
        Convierte una sensibilidad in-game a cm/360.
        Fórmula: cm360 = (360 * 2.54) / (sens * yaw_increment * DPI)
        """
        if sens <= 0 or dpi <= 0:
            return 0.0

        yaw_inc = self.get_yaw_increment(scale_name)
        if yaw_inc <= 0:
            return 0.0

        cm360 = 914.4 / (sens * yaw_inc * dpi)
        return round(cm360, 2)
