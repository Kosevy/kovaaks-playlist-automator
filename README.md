# KPA - KovaaK's Playlist Automator

A desktop application built in Python with **CustomTkinter** that automates stats extraction from the [evxl.app](https://evxl.app) platform and KovaaK's backend. It analyzes your benchmark performance and generates native KovaaK's playlist files (`.json`) containing the 5 scenarios where you have the highest potential for improvement.

---

## Features

- **Modern Dark UI**: Clean desktop interface styled with CustomTkinter in default dark mode.
- **Persistent Configuration**: Automatically saves your credentials, preferences, and paths to `config.json` so you don't have to re-enter them on restart.
- **Advanced Benchmark & EVXL URL Resolution**:
  - **Full EVXL URL Support**: Compatible with standard user benchmark URLs:  
    `https://evxl.app/u/{user}/{benchmark_name}/{difficulty}?tab=charts`.
  - **Dynamic Catalog Discovery**: Analyzes EVXL's application bundles dynamically to query against the complete official catalog (129+ benchmarks) without requiring manual maintenance.
  - **Smart In-Memory & Local Cache**: Cached locally (24h TTL) to deliver sub-millisecond lookups on repeated executions.
  - **Automatic Steam ID Detection**: If the Steam ID input is left blank and an EVXL user URL is provided, the application resolves the user's Steam64 ID via EVXL's Steam profile API (`/api/steam`) and auto-fills the field.
  - **Alternative Formats**: Also supports direct URLs with `benchmarkId=XXXX`, `/benchmarks/{name}/{difficulty}`, or numeric IDs (e.g., `2336`).
- **Precise Regex Parsing**:
  - **Steam ID**: Accurately extracts exactly 17 consecutive digits (`\d{17}`) from raw text or Steam community profile links.
- **Path Auto-Detection & Explorer Dialog**:
  - Automatically detects Steam's default playlists directory (`C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Playlists`) or lets you select any custom path using a native Windows folder browser.
- **Continuous Score Algorithm**:
  $$\text{Continuous Score} = \text{Base Rank} + \frac{\text{Current Score} - \text{Minimum Score}}{\text{Maximum Score} - \text{Minimum Score}}$$
- **Recommended Sensitivity with Cascade Fallback**:
  - Extracts the median sensitivity for the target **Fuchsia** tier.
  - If Fuchsia lacks sufficient player data for a scenario, it automatically falls back in descending order (Indigo → Lavender → Cerulean → ...), indicating the source rank in the results output.
- **Native KovaaK's Playlist Structure (5 Play Count)**:
  - Outputs standard KovaaK's JSON playlists (`playCount: 5`).
  - Sanitizes invalid Windows filesystem characters (`< > : " / \ | ? *`).
  - Automatically resolves name collisions identical to Windows File Explorer (`name (1).json`, `name (2).json`).
- **Live KovaaK's Game Monitor**:
  - Automatically listens to real-time session logs (`FPSAimTrainer.log`) and stats without hogging CPU (<0.05%).
  - Tracks scenario repetitions (0/5) and notifies scenario changes.
  - Supports configurable triggers: notify on 5 reps completed or on early scenario transitions.
- **Non-Intrusive Win32 HUD Overlays (No-Minimize Guarantee)**:
  - Custom floating HUDs utilizing `WS_EX_TOPMOST` and `WS_EX_NOACTIVATE` via Win32 API.
  - Windows stay pinned on top without stealing focus or minimizing fullscreen/borderless games.
  - Styled with modern dark theme following **better-ui** guidelines (concentric radii, high contrast, smooth copy micro-interactions).
- **Exact Sensitivity Conversion & Clipboard Auto-Copy**:
  - Automatically reads the player's active DPI and Game Sens Scale (`Marvel Rivals`, `Overwatch`, `Valorant`, `Apex/Source`, `Fortnite`) directly from KovaaK's configuration (`PrimaryUserSettings.json` and `FovSensConfig.json`).
  - Converts recommended `cm/360` to in-game values with zero guesswork.
  - Automatically copies the recommended sensitivity to the Windows clipboard upon scenario switch.
- **Real-Time Highscore & Multi-Tier EVXL Benchmark Bar**:
  - Compares every completed run against your baseline benchmark scores.
  - Displays a celebration overlay with the multi-tier segmented progress bar using official EVXL rank colors (*Cinnabar* to *Fuchsia*).
  - Shows score gain ($+\Delta\text{ pts}$), distance to next rank, and updated overall benchmark completion percentage without opening a web browser.
- **Full Internationalization (i18n - Spanish & English)**:
  - Complete bilingual support for both Spanish (`es`) and English (`en`) covering all UI tabs, input fields, buttons, log feeds, dialogs, and floating overlays.
  - Automatic Windows OS system language detection on first run.
  - Live in-app hot-switching via 1-click header pill `[ ES | EN ]` and Settings dropdown without requiring app restart.
  - Preserves standard decimal point notation (`11,481.0`) across both languages.
- **Asynchronous Execution**:
  - Background threading (`threading.Thread`) prevents the UI from freezing during network requests, with comprehensive error handling (timeouts, HTTP errors, 10060, invalid directories).

---

## Project Structure

```text
KPA/
├── core/
│   ├── __init__.py
│   ├── api_client.py         # HTTP client with required headers and error handling
│   ├── benchmark_resolver.py # Dynamic EVXL catalog resolver and URL parser
│   ├── benchmark_tracker.py  # Benchmark baselines, continuous scores & highscore logic
│   ├── config.py             # Configuration persistence and config.json management
│   ├── extractor.py          # Regex extractors and input parsing
│   ├── game_monitor.py       # Real-time KovaaK's session and log monitor
│   ├── kovaaks_detector.py   # Install directory discovery, user settings & sens converter
│   └── playlist_service.py   # Continuous score computation, fallback logic & JSON generation
├── ui/
│   ├── __init__.py
│   ├── app.py                # Main Tabbed CustomTkinter UI (Generator, Monitor, Settings)
│   └── overlay.py            # Non-intrusive Win32 Topmost & No-Activate Overlays
├── tests/
│   ├── test_benchmark_tracker.py # Unit tests for benchmark progress and highscore evaluation
│   ├── test_game_monitor.py      # Unit tests for log parsing and transition triggers
│   ├── test_kovaaks_detector.py  # Unit tests for paths, DPI, and sensitivity math
│   ├── test_pipeline.py          # End-to-end integration test with live endpoints
│   └── test_unit.py              # Unit tests for extractors, sanitizer, and resolvers
├── requirements.txt
├── main.py                   # Application entry point
└── README.md
```
│   ├── test_pipeline.py      # End-to-end integration test with live endpoints
│   └── test_unit.py          # Unit tests for extractors, sanitizer, and resolvers
├── requirements.txt
├── main.py                   # Application entry point
└── README.md
```

---

## Installation and Usage

### 1. Set Up Virtual Environment & Dependencies

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the Application

```powershell
python main.py
```

---

## Tests

To run the automated unit test suite:

```powershell
python -m unittest discover tests
```

To run the live pipeline integration test:

```powershell
python tests/test_pipeline.py
```