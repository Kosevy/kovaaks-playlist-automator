import re
from typing import Optional, Dict, Any
from core.benchmark_resolver import BenchmarkResolver

_resolver = BenchmarkResolver()


def extract_steam_id(raw_input: str) -> str:
    r"""
    Extrae exactamente 17 dígitos numéricos consecutivos (\d{17}),
    ya sea ingresados directamente o dentro de una URL de Steam / EVXL.
    Lanza ValueError si no se encuentra un Steam ID de 17 dígitos.
    """
    if not raw_input:
        raise ValueError("El campo de Steam ID no puede estar vacío.")

    cleaned = raw_input.strip()
    match = re.search(r"(\d{17})", cleaned)
    if not match:
        raise ValueError(
            "Steam ID inválido: Se requieren exactamente 17 dígitos consecutivos "
            "(ej. 76561198444816419 o https://steamcommunity.com/profiles/76561198444816419)."
        )
    return match.group(1)


def extract_benchmark_info(raw_input: str) -> dict:
    """
    Resuelve la información completa del Benchmark a partir de texto plano,
    ID numérico o URLs de EVXL (ej. /u/{usuario}/{benchmark}/{dificultad}).
    Retorna dict con 'benchmark_id', 'benchmark_name', 'difficulty', 'author'.
    """
    return _resolver.resolve_benchmark(raw_input)


def extract_benchmark_id(raw_input: str) -> str:
    """
    Extrae el ID numérico de un Benchmark a partir de texto plano, ID directo
    o una URL de EVXL / KovaaK's.
    Lanza ValueError si no se encuentra o no se puede resolver.
    """
    info = extract_benchmark_info(raw_input)
    return info["benchmark_id"]
