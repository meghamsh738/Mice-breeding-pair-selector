# Suite Integration (Easylab Suite)

This folder contains the integration contract for bundling this repo into the `easylab-suite` desktop launcher.

## What the suite expects
- Front-end build output at `.app-dist/web/` (Vite, file:// safe via `base: "./"`).
- FastAPI backend at `backend/main.py` (bundled into the suite under `apps/breeding/backend`).
- Optional example dataset at `example_data/` (bundled into the suite under `apps/breeding/example_data`).

## Writable state
This backend persists a gene catalog (`gene_database.json`). In the suite, the launcher injects `EASYLAB_DATA_PATH`
so the file is written under `Documents/Easylab/...` (not inside the app’s read-only resources directory).

## Module metadata
See `suite/module.json`.
