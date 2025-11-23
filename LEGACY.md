# Breeder Pair Selector — Legacy Desktop (PyQt)

This file documents the original PyQt desktop app (`python main.py`). The modern React + FastAPI app is documented in `README.md`.

## Quick start (legacy)

```bash
python main.py
```

Requires Python 3 and PyQt5. Installs: `pip install -r requirements.txt` (if present) or `pip install pyqt5 pandas openpyxl`.

## Features (legacy)

- Load breeder Excel/CSV (multi-sheet) with age filtering and colored-row exclusions.
- Manage gene/class pairs via an embedded gene database.
- Desired-genotype parsing and breeder pair suggestion.
- Export results and annotate Excel with pair tags.
- Log viewer and mice detail viewer.

## Notes

- Logging writes to `~/.local/state/mice-breeding-logs` (per recent hardening).
- UI is not actively developed; new work should target the modern web app.

