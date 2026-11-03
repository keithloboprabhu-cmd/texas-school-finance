# Lone Star Ledger: notes for Claude Code

Texas school finance atlas: Streamlit app over a Python -> pandas -> DuckDB -> SQL pipeline.
The full build spec lives in the owner's prompt; this file records the conventions.

## Hard rules
- **Never invent data, codes, IDs or findings.** Confirm every field name, PEIMS fund/function/object
  code and identifier against the downloaded file or its official data dictionary before using it.
  If something cannot be confirmed, mark it `unverified` in a code comment and on the Methodology page.
- Every number in the README or in the app comes from a query over the marts; show that query.
- The app never shows placeholder or sample numbers. If a mart is missing, the page says so
  (`ui.components.require_marts`).
- No paid APIs, no map tokens, no LLM calls at runtime, no network calls from the app.
- Never commit secrets or raw downloads (`data/raw/` and `data/processed/` are gitignored).
- CDNs are 6-digit zero-padded **strings**, never integers.

## Layout
- `app.py` + `pages/`: Streamlit app (top navigation). Reads only `data/marts/*.parquet`
  and `data/geo/*.geojson`.
- `ui/`: theme tokens (`theme.py`), CSS (`assets/app.css`), components, data access, SQL Lab guard.
- `pipeline/ingest/`: downloaders (shared `_http.py`: retries, User-Agent, cache, checksum log).
  `config/sources.yaml` is the registry of every source.
- `sql/{ref,staging,core,marts,saved}`: all SQL lives in files, never as large strings in Python.
- `config/`: `glossary.yaml` (all hover definitions), `events.yaml` (law-change markers; a marker
  needs a checked primary-source URL), `sources.yaml`.

## Commands
- Install: `pip install -r requirements-dev.txt` (app-only: `requirements.txt`)
- Pipeline: `make data` (`python -m pipeline.build`)
- App: `streamlit run app.py`
- Checks: `ruff check . && ruff format --check . && pytest -q`

## Adding a metric
1. Add its SQL to one mart in `sql/marts/`.
2. Add its label, unit, format and palette to `config/metrics.yaml`.
3. Add a test in `tests/test_marts.py` if it has a natural bound.
