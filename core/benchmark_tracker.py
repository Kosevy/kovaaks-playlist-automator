from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from core.playlist_service import RANK_FALLBACK_ORDER


@dataclass
class HighscoreResult:
    scenario_name: str
    old_score: float
    new_score: float
    delta_score: float
    old_rank_idx: int
    new_rank_idx: int
    old_rank_name: str
    new_rank_name: str
    current_rank_color: str
    next_rank_name: str
    next_rank_color: str
    rank_up: bool
    pct_to_next_rank: float
    points_to_next_rank: float
    rank_maxes: List[float]
    ranks_list: List[Dict[str, Any]]
    old_continuous_score: float
    new_continuous_score: float
    overall_progress_pct: float
    category_name: str


class BenchmarkTracker:
    """Rastrea el progreso del jugador en el benchmark activo y evalúa nuevos récords."""

    def __init__(self):
        self.benchmark_id: Optional[str] = None
        self.steam_id: Optional[str] = None
        self.benchmark_name: Optional[str] = None
        self.ranks: List[Dict[str, Any]] = []
        self.scenarios: Dict[str, Dict[str, Any]] = {}
        self.overall_rank: int = 0
        self.benchmark_progress: float = 0.0

    def load_benchmark_data(
        self,
        benchmark_id: str,
        steam_id: str,
        progress_data: Dict[str, Any],
        sens_data: Optional[Dict[str, Any]] = None,
        benchmark_name: Optional[str] = None
    ) -> None:
        """Carga y estructura los datos del benchmark del jugador."""
        self.benchmark_id = benchmark_id
        self.steam_id = steam_id
        self.benchmark_name = benchmark_name or f"Benchmark {benchmark_id}"
        self.ranks = progress_data.get("ranks", [])
        self.overall_rank = progress_data.get("overall_rank", 0)
        self.benchmark_progress = float(progress_data.get("benchmark_progress", 0.0))
        self.scenarios.clear()

        sens_data = sens_data or {}
        categories = progress_data.get("categories", {})

        for cat_name, cat_data in categories.items():
            scenarios = cat_data.get("scenarios", {})
            for sc_name, sc_data in scenarios.items():
                raw_score = sc_data.get("score", 0)
                score = raw_score / 100.0
                sc_rank = sc_data.get("scenario_rank", 0)
                rank_maxes = [float(x) for x in sc_data.get("rank_maxes", [])]

                # Resolver sensibilidad recomendada con fallback en cascada
                chosen_sens = None
                chosen_rank = None
                sens_entry = sens_data.get(sc_name, {})
                for candidate in RANK_FALLBACK_ORDER:
                    if candidate in sens_entry and isinstance(sens_entry[candidate], dict):
                        med = sens_entry[candidate].get("median")
                        if med is not None:
                            chosen_sens = round(float(med), 1)
                            chosen_rank = candidate
                            break

                # Calcular continuous score actual
                prev_tier = 0.0 if sc_rank == 0 else (rank_maxes[sc_rank - 1] if sc_rank - 1 < len(rank_maxes) else 0.0)
                next_tier = rank_maxes[sc_rank] if sc_rank < len(rank_maxes) else (rank_maxes[-1] if rank_maxes else score)
                delta = next_tier - prev_tier
                pct = ((score - prev_tier) / delta) if delta > 0 else 0.0
                continuous = sc_rank + pct

                self.scenarios[sc_name] = {
                    "name": sc_name,
                    "high_score": score,
                    "rank_idx": sc_rank,
                    "rank_maxes": rank_maxes,
                    "category": cat_name,
                    "continuous_score": continuous,
                    "recommended_sens": chosen_sens,
                    "recommended_rank": chosen_rank
                }

    def get_rank_info(self, rank_idx: int) -> Dict[str, Any]:
        """Retorna nombre y color para un índice de rango."""
        if 0 <= rank_idx < len(self.ranks):
            return self.ranks[rank_idx]
        return {"name": f"Rank {rank_idx}", "color": "#7AA2F7", "icon": ""}

    def get_recommended_sens(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene la sensibilidad recomendada para un escenario."""
        sc = self.find_scenario(scenario_name)
        if sc and sc.get("recommended_sens") is not None:
            return {
                "cm360": sc["recommended_sens"],
                "rank_name": sc.get("recommended_rank", "Fuchsia")
            }
        return None

    def find_scenario(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        """Busca un escenario por coincidencia exacta o normalizada."""
        if scenario_name in self.scenarios:
            return self.scenarios[scenario_name]

        # Búsqueda insensible a mayúsculas y espacios
        cleaned_target = scenario_name.strip().lower()
        for name, data in self.scenarios.items():
            if name.strip().lower() == cleaned_target:
                return data

        return None

    def check_score(self, scenario_name: str, score: float) -> Optional[HighscoreResult]:
        """
        Evalúa si el puntaje reportado es un nuevo récord para el escenario en el benchmark.
        Si es récord, actualiza el estado interno y retorna los detalles calculados.
        """
        sc = self.find_scenario(scenario_name)
        if not sc:
            return None

        old_score = sc["high_score"]
        if score <= old_score:
            return None

        # ¡NUEVO HIGHSCORE!
        delta_score = round(score - old_score, 2)
        old_rank_idx = sc["rank_idx"]
        rank_maxes = sc["rank_maxes"]

        # Calcular nuevo rango
        new_rank_idx = 0
        for i, threshold in enumerate(rank_maxes):
            if score >= threshold:
                new_rank_idx = i + 1
            else:
                break

        rank_up = new_rank_idx > old_rank_idx

        # Calcular umbrales de rango actual y siguiente
        if not rank_maxes:
            prev_tier_threshold = 0.0
            next_tier_threshold = score
            pct_to_next = 100.0
            points_to_next = 0.0
        else:
            if new_rank_idx == 0:
                prev_tier_threshold = 0.0
                next_tier_threshold = rank_maxes[0]
            elif new_rank_idx <= len(rank_maxes):
                prev_tier_threshold = rank_maxes[new_rank_idx - 1]
                if new_rank_idx < len(rank_maxes):
                    next_tier_threshold = rank_maxes[new_rank_idx]
                else:
                    next_tier_threshold = rank_maxes[-1]
            else:
                prev_tier_threshold = rank_maxes[-1]
                next_tier_threshold = rank_maxes[-1]

            tier_span = next_tier_threshold - prev_tier_threshold
            if tier_span > 0:
                pct_to_next = min(100.0, max(0.0, ((score - prev_tier_threshold) / tier_span) * 100.0))
                points_to_next = max(0.0, next_tier_threshold - score)
            else:
                pct_to_next = 100.0
                points_to_next = 0.0

        old_continuous = sc["continuous_score"]
        new_continuous = new_rank_idx + (pct_to_next / 100.0 if pct_to_next < 100.0 else 1.0)

        # Actualizar datos del escenario
        sc["high_score"] = score
        sc["rank_idx"] = new_rank_idx
        sc["continuous_score"] = new_continuous

        # Recalcular progreso general del benchmark (promedio continuo de todos los escenarios)
        total_continuous = sum(item["continuous_score"] for item in self.scenarios.values())
        max_possible = len(self.scenarios) * (len(self.ranks) - 1 if self.ranks else 9)
        overall_progress_pct = round((total_continuous / max_possible * 100.0) if max_possible > 0 else 0.0, 1)

        old_rank_info = self.get_rank_info(old_rank_idx)
        new_rank_info = self.get_rank_info(new_rank_idx)
        next_rank_info = self.get_rank_info(min(new_rank_idx + 1, len(self.ranks) - 1))

        return HighscoreResult(
            scenario_name=sc["name"],
            old_score=old_score,
            new_score=score,
            delta_score=delta_score,
            old_rank_idx=old_rank_idx,
            new_rank_idx=new_rank_idx,
            old_rank_name=old_rank_info.get("name", f"Rank {old_rank_idx}"),
            new_rank_name=new_rank_info.get("name", f"Rank {new_rank_idx}"),
            current_rank_color=new_rank_info.get("color", "#7AA2F7"),
            next_rank_name=next_rank_info.get("name", "Max Rank"),
            next_rank_color=next_rank_info.get("color", "#F7768E"),
            rank_up=rank_up,
            pct_to_next_rank=round(pct_to_next, 1),
            points_to_next_rank=round(points_to_next, 1),
            rank_maxes=rank_maxes,
            ranks_list=self.ranks,
            old_continuous_score=round(old_continuous, 3),
            new_continuous_score=round(new_continuous, 3),
            overall_progress_pct=overall_progress_pct,
            category_name=sc["category"]
        )
