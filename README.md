# KPA - KovaaK's Playlist Automator

Desktop application in Python with CustomTkinter that automates the extraction of statistics from the [evxl.app](https://evxl.app) platform and KovaaK's backend to generate playlist files (`.json`) with the 5 scenarios where the player has the greatest room for improvement in a specific benchmark.

---

## Features

- Modern Dark Interface: Designed with CustomTkinter in native dark mode.
- **Persistencia de Configuración**: Guarda automáticamente en `config.json` tus credenciales e información de rutas al reiniciar la app o cambiar de valores.
- **Resolución Avanzada de Benchmarks y URLs de EVXL**:
  - **URLs amigables de EVXL**: Soporta links con la estructura completa:
    `https://evxl.app/u/{usuario}/{benchmark}/{dificultad}?tab=charts` (ej. `https://evxl.app/u/crimstag/Viscose%20Benchmarks%20S2/Medium?tab=charts`).
    Resuelve dinámicamente el nombre del benchmark y dificultad contra el catálogo oficial de EVXL (129+ benchmarks).
  - **Autodetección de Steam ID**: Si el campo de Steam ID está vacío y la URL de EVXL contiene un usuario (`/u/{usuario}/...`), la aplicación detecta y resuelve automáticamente su Steam ID64.
  - **Formatos alternativos**: Acepta también URLs directas con `benchmarkId=XXXX`, rutas de benchmark (`/benchmarks/{nombre}/{dificultad}`) o IDs numéricos directos (ej. `2336`).
- **Extracción Inteligente por Regex**:
  - **Steam ID**: Extrae exactamente 17 dígitos consecutivos (`\d{17}`) a partir de texto directo o URLs de Steam (`steamcommunity.com/profiles/7656...`).
- **Detección de Rutas y Diálogo de Exploración**:
  - Busca la ruta predeterminada de Steam (`C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Playlists`) o permite seleccionar cualquier carpeta mediante un explorador nativo de Windows.
- **Cálculo de Puntaje Continuo**:
  $$\text{Puntaje Continuo} = \text{Rango Base} + \frac{\text{Score Actual} - \text{Score Mínimo}}{\text{Score Máximo} - \text{Score Mínimo}}$$
- **Sensibilidad Recomendada con Fallback Dinámico**:
  - Extrae la mediana de sensibilidad del rango **Fuchsia**.
  - Si no existen datos suficientes en Fuchsia, realiza un fallback en cascada (Indigo → Lavender → Cerulean → ...), indicando el rango origen en la interfaz.
- **Estructura Nativa de KovaaK's (5 repeticiones)**:
  - Genera el archivo JSON con formato nativo de KovaaK's (`playCount: 5`).
  - Sanitiza caracteres no permitidos en Windows (`< > : " / \ | ? *`).
  - Manejo automático de colisiones idéntico a Windows Explorer (`nombre (1).json`, `nombre (2).json`).
- **Ejecución Asíncrona sin Congelamiento**:
  - Peticiones HTTP en segundo plano con control de errores completo (timeouts, HTTP errors, 10060, rutas inválidas).

---

## Estructura del Proyecto

```text
KPA/
├── core/
│   ├── __init__.py
│   ├── api_client.py         # Cliente HTTP con headers personalizados
│   ├── benchmark_resolver.py # Resolutor dinámico de catálogo EVXL y URLs
│   ├── config.py             # Manejo de persistencia y config.json
│   ├── extractor.py          # Extractor Regex y parseo de entradas
│   └── playlist_service.py   # Lógica de cálculo, fallback y generación JSON
├── ui/
│   ├── __init__.py
│   └── app.py                # Ventana principal CustomTkinter y threading
├── tests/
│   ├── test_pipeline.py      # Test de integración con endpoints reales
│   └── test_unit.py          # Pruebas unitarias de extractor y lógica
├── requirements.txt
├── main.py                   # Punto de entrada
└── README.md
```

---

## Installation and Usage

### 1. Activate the virtual environment and install dependencies

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the application

```powershell
python main.py
```

---

## Tests

To run the unit tests:

```powershell
python -m unittest discover tests
```