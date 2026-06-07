# 💸 Expense Tracker

A local-first, private expense dashboard built from Scotiabank Visa e-statement PDFs.
Everything runs on your machine — no accounts, no cloud, no data leaves your computer.

## Two ways to run it

### 1. Static dashboard (simplest — double-click)
```
python3 build_dashboard.py        # regenerates expense-dashboard.html from the PDFs
open expense-dashboard.html       # or just double-click it
```
Self-contained HTML with all data baked in. Charts via Chart.js (CDN). This is the
"just works" path.

### 2. Local backend (for the import pipeline + API)
```
python3 server.py                 # → http://localhost:8765/   (or double-click run-server.command)
```
On startup it prints every address it's reachable at (localhost, your Wi-Fi LAN IP, and your
Tailscale IP if installed). **To use it from your phone, see `TUNNEL_SETUP.md`** — a private
Tailscale tunnel keeps all data on your Mac while letting your phone reach the full live app.
Zero-dependency stdlib server (no `pip install`). On startup it **syncs every account**
(Scotiabank PDFs + Tangerine + Amex + BMO + chequing) into a SQLite DB via `db.sync_all()`
(idempotent), serves the dashboard **and** a JSON API, and lets you **upload new statement
PDFs**.

When the dashboard is opened **through the backend** (localhost:8765) it auto-detects the
API, fetches live data (all 4 cards + chequing), and shows the **rules editor**, inline
category dropdowns, and the **"⬆ Add statement"** upload — all reflecting your full data.
Opened as a plain file it transparently falls back to the baked-in data. Same HTML, two modes.

```
GET  /api/insights      bundle: summary + statements + recurring + anomalies + forecast + budgets + accounts
GET  /api/transactions  GET /api/summary  GET /api/recurring  GET /api/anomalies  GET /api/forecast
GET  /api/statements    GET /api/chequing    GET /api/budgets    POST /api/budgets {category, monthly}
GET  /api/rules         POST /api/rules {action:add|update|delete, ...}   categorization rules
POST /api/recategorize  {merchant, category}   reclassify a merchant (updates ALL its rules)
POST /api/ingest        multipart PDF upload → parse + dedupe + store
```

> Multi-account note: file-derived sources (Tangerine/Amex/BMO/chequing) re-sync on every
> startup; uploaded PDFs accumulate. Refs for CSV/markdown rows use `_seq_ref()` (full
> description + per-row sequence) so identical-looking rows don't collide on `UNIQUE(source,ref)`.

**Categorization rules engine (live mode):** a "🏷️ Categorization rules" panel lets you edit
the keyword→display→category rules that turn raw statement text into tidy data. Change a
category (in the rules panel *or* inline on any transaction row) and every matching
transaction is re-classified instantly — new rules take priority. Rules live in the SQLite
`rules` table (seeded from `ingest.MERCHANTS`); each transaction stores its exact 25-char
`field` so re-applying rules is precise.

## Files

| File | Role |
|------|------|
| `ingest.py` | **Shared core.** EBCDIC/zlib PDF extraction, FX-aware row parser, merchant→category map, and the smart-feature algorithms (recurring detection, anomalies, forecast). Used by both the CLI and the backend. |
| `build_dashboard.py` | CLI generator → `expense-dashboard.html` (imports `ingest`). |
| `expense-dashboard.html` | The dashboard (generated). |
| `db.py` | SQLite schema + loader (transactions, statements, rules, budgets, goals). |
| `server.py` | Stdlib HTTP backend: JSON API + PDF upload + static serving. |
| `test_recon.py` | Guards parsing correctness (reconciles to statement totals, FX, recurring, anomalies). |
| `favicon.svg` | App icon (purple bar-chart tile); also embedded inline in the dashboard `<head>` as a data-URI so the static file stays self-contained. |

Run the tests anytime: `python3 test_recon.py`

## How the data is parsed (the tricky part)

Scotiabank PDFs store text in **EBCDIC (cp037) fonts** inside FlateDecode streams, and the
machine has no PDF library — so `ingest.py` decodes the compressed streams directly. Notable
details: the permissive `stream...endstream` capture (to catch page-3 "continued" rows), the
fixed-width 25-char merchant field, and foreign-currency rows carrying two amounts
(`AMT 178.48 USD 248.09` → the posted **CAD** 248.09 is used). Totals reconcile exactly:
**$5,236.00** across the 3 sample statements.

## Feature status (roadmap = `~/.claude/plans/i-have-bank-and-velvet-kite.md`)

| Phase | Item | Status |
|-------|------|--------|
| Core | Monthly/category/weekly/merchant charts, budgets, spend-vs-payments, CSV export | ✅ Done |
| 3 | Recurring & subscription detection (+ next-charge, annualized) | ✅ Done |
| 3 | Projected spending (recurring + variable run-rate) | ✅ Done |
| 3 | Anomaly detection + auto-insights (plain-English callouts) | ✅ Done |
| 2 | Cross-filtering — click category/month/merchant/day → everything reacts; filter chips | ✅ Done |
| 4 | Calendar heatmap (daily intensity, click-to-filter) | ✅ Done |
| 4 | Savings goals tracker (progress bars, localStorage) | ✅ Done |
| 5 | Drag-and-drop PDF import (live mode) | ✅ Done |
| 5 | Income & net cash-flow + savings rate (goal ETAs) | ✅ Done |
| 5 | Multi-account: Scotiabank + Tangerine MC + Amex + chequing (adapters, account filter) | ✅ Done |
| 5 | Chequing net-worth/balance trend + classified income (payroll/gov't vs transfers) | ✅ Done |
| 5 | BMO Mastercard (CSV adapter) | ✅ Done |
| 1 | Shared `ingest` module + SQLite + JSON API + PDF-upload ingestion | ✅ Done |
| 1 | Reconciliation/regression tests (incl. DB sync) | ✅ Done |
| 5 | Editable categorization **rules engine** (DB-backed, UI to edit + inline recategorize) | ✅ Done |
| 1 | **Backend = all accounts** — `db.sync_all()` loads 4 cards + chequing; live mode = full data | ✅ Done |
| 2/4 | Vite + ECharts SPA (drillthrough, sankey, brushing) | 📋 Deferred — tech refactor, low payoff (see `CLOUD_ROADMAP.md`) |
| 6 | Auth, multi-device sync, Plaid live import, email/alert notifications | 📋 Planned for later — need external services/credentials (see `CLOUD_ROADMAP.md`) |

**Why some items are scaffolded vs. built:** multi-bank parsing needs real sample statements
from those banks to build and verify against; Plaid/auth/email need API keys and infra and
are security-sensitive. The foundation (shared parser, DB, API, rules table) is in place so
these are incremental additions rather than rewrites.

## Accounts

The dashboard spans multiple accounts via per-issuer adapters in `ingest.py`:
- **Scotiabank Visa** — EBCDIC PDF parser (`parse_dir`).
- **Tangerine Mastercard** — markdown-table parser (`parse_tangerine_cc`); purchases merge into
  the spending views, payments/credits excluded.
- **Amex** — year-end summary CSV parser (`parse_amex_csv`); Charges = spending, Credits
  excluded; falls back to Amex's own Sub-Category when a merchant keyword doesn't match.
- **Tangerine Chequing** — `parse_tangerine_chq`; powers the "Chequing & net worth" card
  (balance trend, money in/out) and the income estimate.

`ingest.load_all()` unifies them; each card transaction carries an `account` field, exposed as
an **account filter** in the dashboard. Combined card spend reconciles to **$38,306.97**
(Scotiabank $5,236.00 + Tangerine $18,389.62 + Amex $11,536.11 + BMO $3,145.24), ~98%
auto-categorized — fix the rest in the rules panel.

**Income classification:** chequing deposits are bucketed by `classify_deposit()` into
payroll/business, government, cheques, peer e-transfers, bank transfers, internal moves, and
interest. "Income" counts only payroll + government + cheques (≈ **$5,016/mo**), excluding peer
e-transfers and account-to-account transfers — a far more realistic figure than counting all
deposits. The chequing card shows the full deposit breakdown.

**BMO** — `parse_bmo_csv` (`BMO/*.csv`: Date,Description,Amount,Direction,AbsAmount). Direction
`out` = purchases, `in` = payments (excluded). Reconciles to **$3,145.24**. The original BMO
PDFs were image-only scans with no text layer; the CSV (user-exported/transcribed) is the
working source. Any future bank that gives a CSV can be added the same way.

Sources: `Tangerine/*.md` (normalized via `Tangerine/normalize_tangerine.py` from MarkItDown),
`amex/YearEndSummary*.csv`.

## Next steps

The local app is feature-complete. Remaining items are **cloud / hosted** features that need
external services & credentials — see **`CLOUD_ROADMAP.md`** for detailed implementation plans:
Plaid live bank sync, login + multi-device sync, and real email/push alerts. (An optional
Vite + ECharts SPA rewrite is also noted there — a tech refactor with low user-facing payoff.)
