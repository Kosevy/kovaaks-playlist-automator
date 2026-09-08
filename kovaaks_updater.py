import requests
import json
import os

STEAM_ID = "76561198444816419"
BENCHMARK_ID = "2336"
PROGRESS_URL = f"https://kovaaks.com/webapp-backend/benchmarks/player-progress-rank-benchmark?benchmarkId={BENCHMARK_ID}&steamId={STEAM_ID}&page=0&max=100"
SENS_URL = f"https://api.evxl.app/distributions/sensitivity?benchmarkId={BENCHMARK_ID}&groupBy=scenario"

# Ruta destino para tu cuenta de Steam
PLAYLIST_DIR = fr"C:\Users\admin\AppData\Local\FPSAimTrainer\Saved\SaveGames\{STEAM_ID}\Playlists"

# Mapeo de índices a nombres de rango según EVXL
RANK_NAMES = {
    0: "Unranked", 1: "Cinnabar", 2: "Vermillion", 3: "Saffron",
    4: "Celadon", 5: "Viridian", 6: "Cerulean", 7: "Lavender",
    8: "Indigo", 9: "Fuchsia"
}

def get_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://evxl.app",
        "Referer": "https://evxl.app/"
    }
    
    # El parámetro timeout evita que el script se cuelgue si el servidor no responde
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def generate_playlist():
    progress_data = get_data(PROGRESS_URL)
    sens_data = get_data(SENS_URL)

    scenarios_list = []

    # 1. Extraer puntajes y calcular porcentaje de progreso real
    categories = progress_data.get('categories', {})
    for cat_name, cat_data in categories.items():
        scenarios = cat_data.get('scenarios', {})
        for sc_name, sc_data in scenarios.items():
            
            score_raw = sc_data.get('score', 0)
            actual_score = score_raw / 100.0
            sc_rank = sc_data.get('scenario_rank', 0)
            rank_maxes = sc_data.get('rank_maxes', [])

            if not rank_maxes:
                continue

            prev_tier = 0 if sc_rank == 0 else rank_maxes[sc_rank - 1]
            next_tier = rank_maxes[sc_rank] if sc_rank < len(rank_maxes) else rank_maxes[-1]

            if next_tier - prev_tier == 0:
                pct = 0
            else:
                pct = (actual_score - prev_tier) / (next_tier - prev_tier)

            # Score continuo = Rango base + porcentaje hacia el siguiente rango
            continuous_score = sc_rank + pct

            scenarios_list.append({
                "name": sc_name,
                "continuous_score": continuous_score,
                "rank": sc_rank,
                "pct": round(pct * 100, 2)
            })

    # 2. Ordenar de menor a mayor y aislar los 5 peores
    scenarios_list.sort(key=lambda x: x['continuous_score'])
    bottom_5 = scenarios_list[:5]

    playlist_items = []
    print("--- 5 Escenarios a Practicar ---")

    # 3. Cruzar con la sensibilidad respectiva del rango y estructurar
    for sc in bottom_5:
        sc_name = sc["name"]
        sc_rank = sc["rank"]
        rank_name = RANK_NAMES.get(sc_rank, "Unranked")

        # Extraer mediana del rango actual
        sens_actual = None
        if sc_name in sens_data and rank_name in sens_data[sc_name]:
            sens_actual = sens_data[sc_name][rank_name].get("median")

        # Extraer mediana del rango Fuchsia
        sens_fuchsia = None
        if sc_name in sens_data and "Fuchsia" in sens_data[sc_name]:
            sens_fuchsia = sens_data[sc_name]["Fuchsia"].get("median")

        # Formateo de texto
        str_actual = f"{round(sens_actual, 1)} cm/360" if sens_actual else "N/A"
        str_fuchsia = f"{round(sens_fuchsia, 1)} cm/360" if sens_fuchsia else "N/A"

        print(f"Escenario: {sc_name}")
        print(f" > Rango actual ({rank_name}): {str_actual} | Rango objetivo (Fuchsia): {str_fuchsia}")

        playlist_items.append({
            "scenarioName": sc_name,
            "playCount": 5
        })

    # 4. Construir y guardar el archivo .json
    playlist_json = {
        "playlistName": "Auto_Weaknesses",
        "scenarioList": playlist_items,
        "isFavorite": False
    }

    os.makedirs(PLAYLIST_DIR, exist_ok=True)
    save_path = os.path.join(PLAYLIST_DIR, "Auto_Weaknesses.json")

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(playlist_json, f, indent=4)

    print(f"\nArchivo generado: {save_path}")

if __name__ == "__main__":
    generate_playlist()