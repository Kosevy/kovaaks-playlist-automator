import re
from typing import Optional


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


def extract_benchmark_id(raw_input: str) -> str:
    """
    Extrae el ID numérico de un Benchmark a partir de texto plano o de una URL
    (ej. https://evxl.app/benchmarks/2336 o parámetro benchmarkId=2336).
    Lanza ValueError si no se encuentra un ID numérico.
    """
    if not raw_input:
        raise ValueError("El campo de Benchmark ID no puede estar vacío.")

    cleaned = raw_input.strip()
    
    # 1. Intentar extraer de patrones de URL conocidos
    url_patterns = [
        r"benchmarks?/(\d+)",
        r"benchmarkId=(\d+)",
        r"bench/(\d+)"
    ]
    for pattern in url_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            return match.group(1)

    # 2. Si no es URL con ruta específica, buscar cualquier grupo de dígitos
    match = re.search(r"\b(\d+)\b", cleaned)
    if match:
        return match.group(1)

    raise ValueError(
        "Benchmark ID inválido: No se detectó un identificador numérico "
        "(ej. 2336 o https://evxl.app/benchmarks/2336)."
    )
