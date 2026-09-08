import requests
from typing import Dict, Any


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://evxl.app",
    "Referer": "https://evxl.app/"
}

DEFAULT_TIMEOUT = 15  # segundos


class KovaaksApiClient:
    """Handles HTTP communication with KovaaK's and EVXL backend endpoints."""

    def __init__(self, headers: Dict[str, str] = None, timeout: int = DEFAULT_TIMEOUT):
        self.headers = headers or DEFAULT_HEADERS
        self.timeout = timeout

    def fetch_player_progress(self, benchmark_id: str, steam_id: str) -> Dict[str, Any]:
        """
        Fetches player progress benchmark data.
        Endpoint: https://kovaaks.com/webapp-backend/benchmarks/player-progress-rank-benchmark
        """
        url = (
            f"https://kovaaks.com/webapp-backend/benchmarks/player-progress-rank-benchmark"
            f"?benchmarkId={benchmark_id}&steamId={steam_id}&page=0&max=100"
        )
        return self._get_json(url, context_name="Progreso del Jugador (KovaaK's)")

    def fetch_sensitivity_distributions(self, benchmark_id: str) -> Dict[str, Any]:
        """
        Fetches scenario sensitivity distributions for the benchmark.
        Endpoint: https://api.evxl.app/distributions/sensitivity
        """
        url = f"https://api.evxl.app/distributions/sensitivity?benchmarkId={benchmark_id}&groupBy=scenario"
        return self._get_json(url, context_name="Distribuciones de Sensibilidad (EVXL)")

    def _get_json(self, url: str, context_name: str) -> Dict[str, Any]:
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, (dict, list)):
                raise ValueError(f"Respuesta inesperada de {context_name}: no es un objeto JSON.")
            return data
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"Tiempo de espera agotado al consultar {context_name}. "
                "Verifica tu conexión a internet o el estado del servidor."
            )
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Error de conexión al consultar {context_name} (posible bloqueo o timeout 10060): {e}"
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else "desconocido"
            raise RuntimeError(
                f"Error HTTP {status_code} al consultar {context_name}. "
                "Verifica que el Benchmark ID y Steam ID existan."
            )
        except Exception as e:
            raise RuntimeError(f"Error inesperado al obtener {context_name}: {e}")

