import json
import os
import re
from typing import Dict, Any, List, Tuple

# Ranks en orden de jerarquía descendente para fallback de sensibilidad
RANK_FALLBACK_ORDER = [
    "Fuchsia",
    "Indigo",
    "Lavender",
    "Cerulean",
    "Viridian",
    "Celadon",
    "Saffron",
    "Vermillion",
    "Cinnabar"
]


def sanitize_filename(filename: str, default: str = "improve-weaknesses") -> str:
    r"""
    Sanitiza el nombre del archivo eliminando caracteres reservados de Windows
    (< > : " / \ | ? *) y caracteres de control.
    Si el resultado queda vacío, retorna el nombre por defecto.
    """
    if not filename:
        return default

    # Eliminar caracteres no permitidos en sistemas de archivos Windows
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename).strip()
    # Windows no permite nombres que terminen en punto o espacio
    cleaned = cleaned.rstrip(". ")

    return cleaned if cleaned else default


def resolve_unique_filepath(directory: str, base_name: str) -> Tuple[str, str]:
    """
    Determina una ruta de archivo única dentro de directory.
    Si base_name.json ya existe, añade (1), (2), etc.
    Retorna (ruta_completa, nombre_final_sin_extension).
    """
    candidate_name = base_name
    candidate_path = os.path.join(directory, f"{candidate_name}.json")
    counter = 1

    while os.path.exists(candidate_path):
        candidate_name = f"{base_name} ({counter})"
        candidate_path = os.path.join(directory, f"{candidate_name}.json")
        counter += 1

    return candidate_path, candidate_name


class PlaylistService:
    """Processes benchmark & sensitivity data and generates KovaaK's playlists."""

    def process_and_generate_playlist(
        self,
        progress_data: Dict[str, Any],
        sens_data: Dict[str, Any],
        destination_dir: str,
        requested_name: str = "improve-weaknesses"
    ) -> Dict[str, Any]:
        """
        Calcula puntajes continuos, selecciona los 5 peores escenarios,
        cruza con la sensibilidad Fuchsia (o rango previo si no existe),
        y guarda el archivo JSON de la playlist en destination_dir.
        """
        if not destination_dir or not os.path.isdir(destination_dir):
            raise ValueError(
                f"El directorio de destino no existe o no es válido: '{destination_dir}'. "
                "Por favor selecciona una carpeta existente con el botón 'Explorar'."
            )

        # 1. Extraer puntajes y calcular puntaje continuo
        scenarios_list = []
        categories = progress_data.get("categories", {})
        if not categories:
            raise ValueError(
                "La respuesta del servidor no contiene categorías de benchmark válidas. "
                "Verifica el Benchmark ID y Steam ID."
            )

        for cat_name, cat_data in categories.items():
            scenarios = cat_data.get("scenarios", {})
            for sc_name, sc_data in scenarios.items():
                score_raw = sc_data.get("score", 0)
                actual_score = score_raw / 100.0
                sc_rank = sc_data.get("scenario_rank", 0)
                rank_maxes = sc_data.get("rank_maxes", [])

                if not rank_maxes:
                    continue

                score_min_rango = 0 if sc_rank == 0 else rank_maxes[sc_rank - 1]
                score_max_rango = rank_maxes[sc_rank] if sc_rank < len(rank_maxes) else rank_maxes[-1]

                delta = score_max_rango - score_min_rango
                if delta == 0:
                    pct = 0.0
                else:
                    pct = (actual_score - score_min_rango) / delta

                # Puntaje continuo = Rango base + porcentaje hacia el siguiente rango
                continuous_score = sc_rank + pct

                scenarios_list.append({
                    "name": sc_name,
                    "continuous_score": continuous_score,
                    "rank": sc_rank,
                    "pct": pct
                })

        if not scenarios_list:
            raise ValueError("No se encontraron escenarios con información de rangos en este benchmark.")

        # 2. Ordenar de forma ascendente por puntaje continuo y aislar los 5 peores
        scenarios_list.sort(key=lambda x: x["continuous_score"])
        bottom_5 = scenarios_list[:5]

        # 3. Cruzar con datos de sensibilidad con fallback en cascada
        processed_scenarios = []
        scenario_playlist_items = []

        for item in bottom_5:
            sc_name = item["name"]
            sens_entry = sens_data.get(sc_name, {})

            chosen_sens_val = None
            chosen_rank = None

            # Buscar desde Fuchsia hacia abajo
            for rank_candidate in RANK_FALLBACK_ORDER:
                if rank_candidate in sens_entry and isinstance(sens_entry[rank_candidate], dict):
                    median_val = sens_entry[rank_candidate].get("median")
                    if median_val is not None:
                        chosen_sens_val = round(float(median_val), 1)
                        chosen_rank = rank_candidate
                        break

            if chosen_sens_val is not None:
                sens_display_str = f"{chosen_sens_val} cm/360 ({chosen_rank})"
            else:
                sens_display_str = "N/A"

            processed_scenarios.append({
                "name": sc_name,
                "continuous_score": round(item["continuous_score"], 3),
                "rank_index": item["rank"],
                "sens_display": sens_display_str,
                "sens_value": chosen_sens_val,
                "sens_rank": chosen_rank
            })

            scenario_playlist_items.append({
                "scenarioName": sc_name,
                "playCount": 5
            })

        # 4. Sanitizar nombre y resolver colisión de archivos
        sanitized_base = sanitize_filename(requested_name, default="improve-weaknesses")
        save_path, final_playlist_name = resolve_unique_filepath(destination_dir, sanitized_base)

        # 5. Construir estructura JSON nativa de KovaaK's
        playlist_json = {
            "playlistName": final_playlist_name,
            "scenarioList": scenario_playlist_items,
            "isFavorite": False
        }

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(playlist_json, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Error al escribir el archivo de playlist en disco: {e}")

        return {
            "file_path": save_path,
            "playlist_name": final_playlist_name,
            "scenarios": processed_scenarios
        }
