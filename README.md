# KPA - KovaaK's Playlist Automator

Aplicación de escritorio en Python con **CustomTkinter** que automatiza la extracción de estadísticas de la plataforma [evxl.app](https://evxl.app) y el backend de KovaaK's para generar listas de reproducción (`.json`) con los 5 escenarios donde el jugador tiene mayor margen de mejora en un benchmark específico.

---

## Características

- **Interfaz Moderna y Oscura**: Diseñada con CustomTkinter en modo oscuro nativo.
- **Persistencia de Configuración**: Guarda automáticamente en `config.json` tus credenciales e información de rutas al reiniciar la app o cambiar de valores.
- **Extracción Inteligente por Regex**:
  - **Steam ID**: Extrae exactamente 17 dígitos consecutivos (`\d{17}`) a partir de texto directo o URLs de Steam (`steamcommunity.com/profiles/7656...`).
  - **Benchmark ID**: Extrae el ID numérico de enlaces de EVXL / KovaaK's o entrada numérica.
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
│   ├── config.py             # Manejo de persistencia y config.json
│   ├── extractor.py          # Regex para Steam ID y Benchmark ID
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

## Instalación y Uso

### 1. Activar entorno virtual e instalar dependencias

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Ejecutar la aplicación

```powershell
python main.py
```

---

## Pruebas

Para ejecutar las pruebas unitarias:
```powershell
python -m unittest discover tests
```

