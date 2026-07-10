# Expense Tracker Handoff

## Current state

This is a local-first personal finance dashboard for Scotiabank, Tangerine, Amex, and BMO data, with a hosted Vercel/Supabase shell.

- Working branch: `main`
- Base commit before Phase 1: `a139bf0` (`Add agent handoff notes`)
- GitHub: <https://github.com/nhihadhassan/expense-tracker>
- Production: <https://expense-tracker-sooty-six-38.vercel.app>
- Last deployment status: Ready
- The current checkout was clean before creating this handoff file.

`codex/treasury-analytics` is already merged into `main` by fast-forward. The Phase 1 changes
below are ready in the local working tree and have not been pushed or deployed yet.

## What was just implemented

The fifth `Analytics` page is wired into the same date, account, category, merchant, month, and day filters used by the rest of the dashboard.

### Monthly variance

Located in the `varianceCard` panel and rendered by `renderAnalytics()` in `build_dashboard.py`.

- Shows the latest selected month by category.
- Shows observed spend and normalized full-month spend.
- Partial-month normalization uses the loaded data coverage date and the number of observed calendar days.
- Compares normalized category spend with the prior three calendar months, including zero-spend months.
- Shows signed dollar and percentage variance.

### Category trends

Located in the `trendsCard` panel.

- Shows monthly lines for the top six categories in the selected range.
- Uses normalized monthly values so a partial latest month does not visually collapse the trend.
- Trend badges are linear-regression slopes in dollars per month.
- The table also shows latest normalized spend, trailing three-month average, and latest change.

### Cash-flow projection

Located in the `projectionCard` panel.

- Projects six months after the latest loaded transaction month.
- Detected recurring charges come from `RECURRING`, which is derived from actual transaction patterns.
- Variable run rate is based on the prior three normalized monthly periods after recurring merchants are removed.
- Historical-spend standard deviation across the trailing six periods produces the monthly uncertainty spread.
- Net cash flow is income minus projected spend.
- When chequing data is loaded, the chart projects the ending chequing balance and shades the low/high balance range.
- If active filters match no history, the panel renders a clear empty state instead of throwing.

## Source files and edit rules

- `build_dashboard.py`: source of truth for the generated dashboard template, CSS, HTML, and browser JavaScript.
- `web/index.html`: tracked hosted build output. Regenerate it after changing `build_dashboard.py`.
- `expense-dashboard.html`: local generated dashboard. It is ignored and should not be treated as the hosted source.
- `ingest.py`: shared transaction parsing, categorization, recurring detection, and data loading.
- `server.py`: local backend on port `8765`.
- `db.py`: SQLite schema and sync helpers.
- `test_recon.py`: parser and reconciliation regression checks.
- `HOSTING.md`: Vercel, Supabase Auth, RLS, and hosted import notes.

The normal frontend workflow is:

```bash
python3 build_dashboard.py
python3 -m py_compile build_dashboard.py ingest.py server.py
```

Do not edit `web/index.html` alone. Make the template change in `build_dashboard.py`, then regenerate.

## Local verification

Run the local backend:

```bash
python3 server.py
```

Open <http://localhost:8765/>. The browser verification used the Analytics tab and confirmed:

- No console errors.
- No error overlay.
- 10 variance category rows.
- 6 trend badges.
- 6 projection rows.
- 390px mobile viewport with no body-width overflow.
- A no-match category filter renders `No filtered history for projection.` without a runtime error.

Useful checks:

```bash
python3 test_recon.py
git diff --check
npx --yes agent-browser open http://localhost:8765/#tab-analytics
```

## Deployment workflow

The repo is linked to the Vercel project `expense-tracker`.

```bash
python3 build_dashboard.py
npx --yes vercel@50.28.0 deploy --prod --yes
```

The global `vercel` command was not installed in this environment, so use the `npx` form unless the CLI is installed later.

Inspect a deployment with:

```bash
npx --yes vercel@50.28.0 inspect <deployment-url>
```

The hosted app is auth-gated and does not bake local financial data into `web/index.html`. Supabase owns hosted data and RLS. Follow `HOSTING.md` before changing auth, imports, or environment variables. Never commit `SUPABASE_SECRET_KEY`.

## Phase 1 — Personal state sync

The hosted dashboard now loads and debounced-writes income, goals, manual subscriptions,
dismissed recurring detections, and budget targets through the existing owner-only `exp_*`
tables. localStorage remains the local/offline cache. `personal_state_initialized` prevents an
empty but intentional remote state from being mistaken for a first login.

The source of truth for this behavior is the shared template in `build_dashboard.py`; regenerate
`web/index.html` after editing it.

## Recommended next steps

1. Add `SUPABASE_SECRET_KEY` support to `push_supabase.py` so local statement refreshes do not require temporarily relaxing RLS.
2. If changing the analytics formulas, add a small deterministic fixture or browser assertion for partial-month normalization and uncertainty-band values.
3. Consider phone uploads through a Vercel Python function when Mac-based statement refresh becomes the larger annoyance.
4. Keep the projection copy explicit that the uncertainty band is historical-spend spread, not a probabilistic guarantee.

## Important assumptions

- Income is `effectiveIncome()`: manually entered monthly income takes priority, otherwise classified chequing income is used.
- Chequing income excludes internal transfers and peer transfers according to the existing classification logic.
- Card transactions represent spending; payments and credits are handled separately by the existing spend-vs-payments panel.
- Empty filtered states are valid and should remain non-throwing.
- The production deployment still needs to be confirmed after the Phase 1 build is published.
