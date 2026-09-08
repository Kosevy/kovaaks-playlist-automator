# KPA - KovaaK's Playlist Automator

Desktop application in Python with CustomTkinter that automates the extraction of statistics from the [evxl.app](https://evxl.app) platform and KovaaK's backend to generate playlist files (`.json`) with the 5 scenarios where the player has the greatest room for improvement in a specific benchmark.

---

## Features

- Modern Dark Interface: Designed with CustomTkinter in native dark mode.
- Configuration Persistence: Automatically saves your credentials and path information in `config.json` when the app restarts or values change.
- Intelligent Extraction Using Regex:
  - Steam ID: Extracts exactly 17 consecutive digits (`\d{17}`) from plain text or Steam URLs (`steamcommunity.com/profiles/7656...`).
  - Benchmark ID: Extracts the numeric ID from EVXL / KovaaK's links or numeric input.
- Path Detection and Browse Dialog:
  - Looks for Steam's default path (`C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\Saved\SaveGames\Playlists`) or lets you choose any folder through a native Windows file browser.
- Continuous Score Calculation:
  $$\text{Continuous Score} = \text{Base Range} + \frac{\text{Current Score} - \text{Minimum Score}}{\text{Maximum Score} - \text{Minimum Score}}$$
- Recommended Sensitivity with Dynamic Fallback:
  - Extracts the median sensitivity from the Fuchsia range.
  - If there are not enough data points in Fuchsia, it falls back in cascade (Indigo → Lavender → Cerulean → ...), indicating the source range in the interface.
- Native KovaaK's Structure (5 repetitions):
  - Generates the JSON file in KovaaK's native format (`playCount: 5`).
  - Sanitizes disallowed Windows characters (`< > : " / \ | ? *`).
  - Automatically handles collisions just like Windows Explorer (`name (1).json`, `name (2).json`).
- Asynchronous Execution Without Freezing:
  - HTTP requests in the background with full error handling (timeouts, HTTP errors, 10060, invalid paths).

---

## Project Structure

```text
KPA/
├── core/
│   ├── __init__.py
│   ├── api_client.py         # HTTP client with custom headers
│   ├── config.py             # Configuration persistence and config.json handling
│   ├── extractor.py          # Regex for Steam ID and Benchmark ID
│   └── playlist_service.py   # Score calculation, fallback logic, and JSON generation
├── ui/
│   ├── __init__.py
│   └── app.py                # Main CustomTkinter window and threading
├── tests/
│   ├── test_pipeline.py      # Integration test with real endpoints
│   └── test_unit.py          # Unit tests for extractor and logic
├── requirements.txt
├── main.py                   # Entry point
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