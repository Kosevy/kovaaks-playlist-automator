import json
import os
from typing import Dict, Any

DEFAULT_STEAM_PLAYLIST_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Playlists"

CONFIG_FILE_NAME = "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "steam_input": "",
    "benchmark_input": "",
    "playlist_dir": DEFAULT_STEAM_PLAYLIST_PATH if os.path.isdir(DEFAULT_STEAM_PLAYLIST_PATH) else "",
    "playlist_name": "improve-weaknesses"
}


class ConfigManager:
    """Manages application configuration loading and persistence."""

    def __init__(self, config_path: str = CONFIG_FILE_NAME):
        self.config_path = config_path

    def load_config(self) -> Dict[str, Any]:
        """Loads configuration from config.json. Falls back to defaults if not found or corrupted."""
        config = DEFAULT_CONFIG.copy()
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        config.update(data)
            except Exception:
                # If reading fails, keep defaults
                pass
        return config

    def save_config(self, config_data: Dict[str, Any]) -> None:
        """Saves configuration data into config.json."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            # Handle potential filesystem write errors
            raise IOError(f"Error al guardar {self.config_path}: {e}")

