import os
import re
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse, unquote
import requests


CACHE_FILE = ".benchmarks_cache.json"
CACHE_TTL_SECONDS = 86400  # 24 horas

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Origin": "https://evxl.app",
    "Referer": "https://evxl.app/"
}


class BenchmarkResolver:
    """
    Resuelve identificadores y URLs de benchmarks de EVXL.
    Soporta:
      - IDs numéricos directos (ej. 2336)
      - URLs con parámetro benchmarkId (ej. ?benchmarkId=2336)
      - URLs amigables de EVXL:
        https://evxl.app/u/{usuario}/{benchmark_name}/{dificultad}?tab=charts
        https://evxl.app/benchmarks/{benchmark_name}/{dificultad}
    """

    def __init__(self, headers: Dict[str, str] = None, cache_path: str = CACHE_FILE):
        self.headers = headers or DEFAULT_HEADERS
        self.cache_path = cache_path
        self._benchmarks_catalog: Optional[List[Dict[str, Any]]] = None

    def resolve_benchmark(self, raw_input: str) -> Dict[str, Any]:
        """
        Analiza raw_input y devuelve un diccionario con:
          - benchmark_id: str (ID numérico de KovaaK's)
          - benchmark_name: Optional[str]
          - difficulty: Optional[str]
          - author: Optional[str]
        Lanza ValueError si no se puede resolver.
        """
        if not raw_input:
            raise ValueError("El campo de Benchmark no puede estar vacío.")

        cleaned = raw_input.strip()

        # 1. ¿Es un ID puramente numérico? (ej. "2336")
        if cleaned.isdigit():
            return {
                "benchmark_id": cleaned,
                "benchmark_name": None,
                "difficulty": None,
                "author": None
            }

        # 2. ¿Contiene el parámetro benchmarkId=XXXX o /benchmarks/XXXX (solo números)?
        match_param = re.search(r"benchmarkId=(\d+)", cleaned, re.IGNORECASE)
        if match_param:
            return {
                "benchmark_id": match_param.group(1),
                "benchmark_name": None,
                "difficulty": None,
                "author": None
            }

        match_bench_num = re.search(r"benchmarks?/(\d+)(?:[/?]|$)", cleaned, re.IGNORECASE)
        if match_bench_num:
            return {
                "benchmark_id": match_bench_num.group(1),
                "benchmark_name": None,
                "difficulty": None,
                "author": None
            }

        # 3. Analizar URL amigable de EVXL
        parsed_url = self._parse_evxl_url(cleaned)
        if not parsed_url:
            # Fallback a buscar cualquier secuencia de dígitos
            digits = re.search(r"\b(\d+)\b", cleaned)
            if digits:
                return {
                    "benchmark_id": digits.group(1),
                    "benchmark_name": None,
                    "difficulty": None,
                    "author": None
                }
            raise ValueError(
                f"No se pudo interpretar el Benchmark ingresado: '{cleaned}'. "
                "Asegúrate de ingresar un ID numérico o un enlace de EVXL válido "
                "(ej. https://evxl.app/u/crimstag/Viscose%20Benchmarks%20S2/Medium?tab=charts)."
            )

        author, bench_name, difficulty = parsed_url

        # 4. Buscar en el catálogo de EVXL
        catalog = self.get_benchmarks_catalog()
        bench_match = self._find_benchmark_in_catalog(catalog, bench_name)
        if not bench_match:
            raise ValueError(
                f"No se encontró el benchmark '{bench_name}' en el catálogo oficial de EVXL."
            )

        official_name = bench_match.get("benchmarkName", bench_name)
        difficulties = bench_match.get("difficulties", [])

        if not difficulties:
            raise ValueError(f"El benchmark '{official_name}' no tiene dificultades registradas.")

        # 5. Resolver dificultad
        chosen_diff = None
        chosen_id = None

        if difficulty:
            diff_clean = difficulty.strip().lower()
            for d in difficulties:
                d_name = d.get("difficultyName", "").strip()
                if d_name.lower() == diff_clean:
                    chosen_diff = d_name
                    chosen_id = str(d.get("kovaaksBenchmarkId"))
                    break

            if not chosen_id:
                available = [d.get("difficultyName") for d in difficulties]
                raise ValueError(
                    f"Dificultad '{difficulty}' no encontrada para '{official_name}'. "
                    f"Dificultades disponibles: {', '.join(available)}."
                )
        else:
            # Si no se especificó dificultad en la URL
            if len(difficulties) == 1:
                chosen_diff = difficulties[0].get("difficultyName")
                chosen_id = str(difficulties[0].get("kovaaksBenchmarkId"))
            else:
                available = [d.get("difficultyName") for d in difficulties]
                raise ValueError(
                    f"El benchmark '{official_name}' requiere especificar una dificultad. "
                    f"Dificultades disponibles: {', '.join(available)}. "
                    f"(Ejemplo: añade /{available[0]} al final del enlace)."
                )

        return {
            "benchmark_id": chosen_id,
            "benchmark_name": official_name,
            "difficulty": chosen_diff,
            "author": author
        }

    def _parse_evxl_url(self, url: str) -> Optional[Tuple[Optional[str], str, Optional[str]]]:
        """
        Extrae (author, benchmark_name, difficulty) de una URL de EVXL.
        Ejemplos:
          - https://evxl.app/u/crimstag/Viscose%20Benchmarks%20S2/Medium?tab=charts
            -> ('crimstag', 'Viscose Benchmarks S2', 'Medium')
          - https://evxl.app/benchmarks/Viscose%20Benchmarks%20S2/Medium
            -> (None, 'Viscose Benchmarks S2', 'Medium')
          - Viscose Benchmarks S2/Medium (texto plano)
            -> (None, 'Viscose Benchmarks S2', 'Medium')
        """
        if "://" in url:
            parsed = urlparse(url)
            path = unquote(parsed.path).strip("/")
        else:
            path = unquote(url).strip("/")

        segments = [s for s in path.split("/") if s]

        # Caso: /u/{author}/{benchmark_name}/{difficulty}/...
        if len(segments) >= 3 and segments[0].lower() == "u":
            author = segments[1]
            # Omitir si el tercer segmento es 'aimbeast'
            if segments[2].lower() == "aimbeast" and len(segments) >= 4:
                bench_name = segments[3]
                difficulty = segments[4] if len(segments) >= 5 else None
            else:
                bench_name = segments[2]
                difficulty = segments[3] if len(segments) >= 4 else None
            return (author, bench_name, difficulty)

        # Caso: /u/{author}/{benchmark_name}
        if len(segments) == 2 and segments[0].lower() == "u":
            return (segments[1], segments[2] if len(segments) > 2 else segments[1], None)

        # Caso: /benchmarks/{benchmark_name}/{difficulty}
        if len(segments) >= 2 and segments[0].lower() == "benchmarks":
            bench_name = segments[1]
            difficulty = segments[2] if len(segments) >= 3 else None
            return (None, bench_name, difficulty)

        # Caso texto plano con barra: "Nombre/Dificultad"
        if "/" in path and not path.startswith("http"):
            parts = path.split("/")
            return (None, parts[0].strip(), parts[1].strip() if len(parts) > 1 else None)

        return None

    def _find_benchmark_in_catalog(self, catalog: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
        """Busca un benchmark por nombre en el catálogo (coincidencia exacta o normalizada)."""
        name_clean = name.strip().lower()

        # 1. Coincidencia exacta insensible a mayúsculas
        for b in catalog:
            if b.get("benchmarkName", "").strip().lower() == name_clean:
                return b

        # 2. Coincidencia eliminando espacios adicionales o guiones
        norm_target = re.sub(r"[\s\-_]+", "", name_clean)
        for b in catalog:
            b_name = b.get("benchmarkName", "").strip().lower()
            if re.sub(r"[\s\-_]+", "", b_name) == norm_target:
                return b

        # 3. Coincidencia de prefijo o sufijo
        for b in catalog:
            b_name = b.get("benchmarkName", "").strip().lower()
            if name_clean in b_name or b_name in name_clean:
                return b

        return None

    def get_benchmarks_catalog(self) -> List[Dict[str, Any]]:
        """Obtiene el catálogo de benchmarks desde memoria, caché local o descargándolo de EVXL."""
        if self._benchmarks_catalog:
            return self._benchmarks_catalog

        # 1. Intentar cargar de caché local
        cached = self._load_cache()
        if cached:
            self._benchmarks_catalog = cached
            return self._benchmarks_catalog

        # 2. Descargar dinámicamente desde EVXL
        catalog = self._fetch_catalog_from_evxl()
        if catalog:
            self._benchmarks_catalog = catalog
            self._save_cache(catalog)
            return self._benchmarks_catalog

        raise RuntimeError("No se pudo obtener el catálogo de benchmarks de EVXL.")

    def _load_cache(self) -> Optional[List[Dict[str, Any]]]:
        if os.path.exists(self.cache_path):
            try:
                mtime = os.path.getmtime(self.cache_path)
                if time.time() - mtime < CACHE_TTL_SECONDS:
                    with open(self.cache_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list) and len(data) > 0:
                            return data
            except Exception:
                pass
        return None

    def _save_cache(self, catalog: List[Dict[str, Any]]) -> None:
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(catalog, f, ensure_ascii=False)
        except Exception:
            pass

    def _fetch_catalog_from_evxl(self) -> List[Dict[str, Any]]:
        """Descarga dinámicamente el catálogo de benchmarks analizando los bundles JS de EVXL."""
        try:
            # 1. Obtener app.[hash].js de la página principal
            html = requests.get("https://evxl.app", headers=self.headers, timeout=10).text
            app_js_match = re.search(r"/_app/immutable/entry/app\.([a-zA-Z0-9_-]+)\.js", html)
            if not app_js_match:
                raise ValueError("No se pudo encontrar entry/app.js en evxl.app.")

            app_js_url = "https://evxl.app" + app_js_match.group(0)
            app_js = requests.get(app_js_url, headers=self.headers, timeout=10).text

            # 2. Encontrar el nodo 3 (layout de usuario que importa el catálogo)
            node3_match = re.search(r"nodes/3\.([a-zA-Z0-9_-]+)\.js", app_js)
            if not node3_match:
                raise ValueError("No se pudo encontrar el nodo 3 en app.js.")

            node3_url = "https://evxl.app/_app/immutable/" + node3_match.group(0)
            node3_js = requests.get(node3_url, headers=self.headers, timeout=10).text

            # 3. Encontrar las importaciones de chunks en el nodo 3
            chunk_matches = re.findall(r"from\s*\"(\.\./chunks/[^\"]+)\"", node3_js)
            for cm in chunk_matches:
                chunk_path = cm.replace("../", "")
                chunk_url = f"https://evxl.app/_app/immutable/{chunk_path}"
                chunk_text = requests.get(chunk_url, headers=self.headers, timeout=10).text

                if "benchmarkName" in chunk_text and "kovaaksBenchmarkId" in chunk_text:
                    json_m = re.search(r"JSON\.parse\(`(\[.*?\])`\)", chunk_text, re.DOTALL)
                    if json_m:
                        raw_json = json_m.group(1).replace("\\`", "`").replace("\\${", "${")
                        benchmarks = json.loads(raw_json)
                        if isinstance(benchmarks, list) and len(benchmarks) > 0:
                            return benchmarks

            raise ValueError("No se encontró el catálogo de benchmarks en los chunks analizados.")
        except Exception as e:
            # Si falla la descarga dinámica y existe un caché previo (incluso vencido), usarlo
            if os.path.exists(self.cache_path):
                try:
                    with open(self.cache_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            raise RuntimeError(f"Error al descargar el catálogo de benchmarks de EVXL: {e}")

    def resolve_steam_vanity_or_id(self, identifier: str) -> Optional[str]:
        """
        Resuelve un identificador de usuario a su Steam ID64 de 17 dígitos.
        Si ya tiene 17 dígitos, lo retorna directamente.
        Si es un nombre de usuario / vanity (ej. 'crimstag'), consulta /api/steam de EVXL.
        """
        if not identifier:
            return None

        cleaned = identifier.strip()
        if re.fullmatch(r"\d{17}", cleaned):
            return cleaned

        try:
            res = requests.post(
                "https://evxl.app/api/steam",
                headers={"Content-Type": "application/json", "Referer": "https://evxl.app/", "Origin": "https://evxl.app"},
                json={"identifier": cleaned},
                timeout=8
            )
            if res.status_code == 200:
                data = res.json()
                steamid = data.get("steamid")
                if steamid and re.fullmatch(r"\d{17}", str(steamid)):
                    return str(steamid)
        except Exception:
            pass

        return None
