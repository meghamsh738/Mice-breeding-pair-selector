# Mice Breeding Pair Selector (React + FastAPI)

Modernized UI for the PyQt breeder tool with lab notebook neo-brutalist styling. Upload Excel/CSV colony sheets (multi-sheet supported by the backend), manage gene classes, enter desired genotype text, compute direct/indirect breeder pairs, and export results. A distinct example dataset is bundled.

## Project structure
- `src/` – React UI (Vite + TypeScript + Tailwind).
- `backend/` – FastAPI service (legacy gene logic + modern endpoints).
- `example_data/animals.csv` – Bundled breeder dataset for example mode.
- `tests/` – Playwright E2E covering the example flow.
- `screenshots/example_run.png` – Produced by E2E (Dec 28, 2025).
- Preview: open `screenshots/example_run.png` after running the E2E.

## Prerequisites
- Node 18+ and npm
- Python 3.10+

## Setup
```bash
npm install
pip install -r backend/requirements.txt
```

## Run (dev)
```bash
# API on :8002
npm run dev:back
# Frontend on :5174
npm run dev:front
```
Open http://localhost:5174, check **Use Example Data** (or upload CSV/XLSX), set a desired genotype (e.g., `cre +/- reporter +/+`), and click **Find Breeder Pairs**.

## Data format & quick AI helper
- Required columns (CSV/XLSX): `breeder_name, gender, strain, sheet, cre, reporter, flox1, flox2, age` (see `example_data/animals.csv`).
- If your colony sheet differs, reshape it first with an AI: [ChatGPT](https://chat.openai.com/), [Gemini](https://gemini.google.com/app), [Grok](https://grok.com/).
- Prompt: "Convert my table to CSV with headers: breeder_name, gender, strain, sheet, cre, reporter, flox1, flox2, age. Keep values, no invented data, output UTF-8 CSV text only."
- Save as `animals.csv`, then upload or paste. Visual helper: `screenshots/data-format-helper.svg`.

## Tests & screenshot
```bash
npx playwright install --with-deps chromium
npm run test:e2e
```
Generates `screenshots/example_run.png` after driving the example flow.

## Modern endpoints (used by the React UI)
- `POST /upload` – multipart Excel/CSV -> breeders + gene catalog
- `GET /genes` – current gene database
- `POST /genes/add` / `POST /genes/delete` – manage gene library
- `POST /find-pairs` – breeders[], desired_genotype{}, min_prob?, use_example?
- `POST /export-breeders` – Excel workbook with direct/indirect pairs
- `GET /health` – liveness

All endpoints accept `use_example: true` to operate entirely on `example_data/animals.csv` without user data.
