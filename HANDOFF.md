# Expense Tracker Handoff

## Current state

This is a local-first personal finance dashboard for Scotiabank, Tangerine, Amex, and BMO data, with a hosted Vercel/Supabase shell.

- Working branch: `main`
- Latest local commit: `5877f25` (`Continue treasury roadmap phases`)
- GitHub: <https://github.com/nhihadhassan/expense-tracker>
- Production: <https://expense-tracker-sooty-six-38.vercel.app>
- Last deployment status: Ready
- The current checkout was clean before creating this handoff file.

`codex/treasury-analytics` is already merged into `main` by fast-forward. This continuation is
committed locally and is ready to publish; production deployment is tracked separately.

## What was just implemented

The fifth `Analytics` page is wired into the same date, account, category, merchant, month, and day filters used by the rest of the dashboard.

### Monthly variance and budget plan

Located in the `varianceCard` panel and rendered by `renderAnalytics()` in `build_dashboard.py`.

- Shows the latest selected month by category.
- Shows observed spend and normalized full-month spend.
- Partial-month normalization uses the loaded data coverage date and the number of observed calendar days.
- Compares normalized category spend with the prior three calendar months, including zero-spend months.
- Shows signed dollar and percentage variance.
- Compares normalized spend with the monthly budget target and shows the signed budget gap.

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
- `test_analytics.py`: deterministic fixtures for partial-month normalization, uncertainty spread,
  and budget-gap math.
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
python3 test_analytics.py
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

## Phase 2 — RLS-safe refresh

`push_supabase.py` accepts `SUPABASE_SECRET_KEY` from the environment. Use:

```bash
SUPABASE_SECRET_KEY=sb_secret_... python3 push_supabase.py
```

The secret is never embedded in the hosted bundle or committed files.

## Phase 3 — Hosted ingestion

Phone-friendly statement ingestion is already present through the authenticated Vercel Python
functions under `api/import/`. Preview, dedupe, commit, and import history are backed by
`exp_imports`; the parser remains Python so no EBCDIC logic is ported to Deno.

## Phase 4 — In-app budget alerts, tab a11y, light theme, net worth

- Insights now emits a budget-overspend alert per category: latest month in the current view vs
  its budget target, prorated by observed days when the month is partial. Skips categories with
  no target or with a gap under both 5% and $25 (avoids noise on tiny targets).
- Page tabs (`#pagetabs` and the sidebar) have `role="tab"`/`aria-selected`/`aria-label`, kept in
  sync by `showTab()`; the sidebar's `<a>` links use `aria-current` instead.
- A `[data-theme="light"]` toggle already existed (`#themeToggle`, `THEME_KEY`) from an earlier
  pass on this branch — do not add a second, competing `@media (prefers-color-scheme: light)`
  block; a first attempt at this did exactly that and silently fought the manual toggle whenever
  the OS preference and the toggle disagreed. Fixed by deleting the media query and merging only
  the genuinely uncovered contrast bugs into the existing selector: the hero card's translucent
  gradient (fine on a dark page, muddy on light — light mode gets an opaque one), several
  hardcoded `color:#fff` labels on translucent cards (`.scard h3`, `.ring .ring-pct`, `.fun-card`,
  `.mh-cell`) that the original pass missed, and `--danger`/`--warning`/`--success`, which the
  original pass never overrode — the dark-theme values are pale tones meant for a dark panel and
  read as low-contrast text on white.
- Real PNG app icons: `apple-touch-icon.png` (180px) plus `icon-192.png`/`icon-512.png` in
  `manifest.webmanifest`, rasterized from `favicon.svg` via macOS `qlmanage` (no extra tooling
  installed). Not marked `purpose: maskable` — the source art bleeds to the canvas edges with no
  safe-zone padding, so an adaptive-icon mask would clip it.
- Net worth (`networth` panel, Analytics tab, `renderNetWorth()`): chequing balance (asset, full
  history) minus Scotiabank's statement balance (the only liability with a real, verified number).
  Amex/BMO/Tangerine Mastercard are CSV imports with no statement balance in the data, so their
  debt is never estimated or guessed — the KPI row says "N of M card accounts tracked" and the
  table prints "not tracked" for any month without a matching statement, rather than silently
  omitting the gap. This was flagged in the prior handoff as blocked on "card-balance coverage
  for every account"; the fix was to stop waiting for full coverage and show a correctly-labeled
  partial number instead.

## Remaining phases

1. Extend net-worth coverage if/when Amex, BMO, or Tangerine ever expose a real statement
   balance (they don't today — CSV exports have no such field).
2. Add outbound budget/anomaly alerts only after an email or messaging provider and credentials are chosen.
3. Keep the projection copy explicit that the uncertainty band is historical-spend spread, not a probabilistic guarantee.

## Important assumptions

- Income is `effectiveIncome()`: manually entered monthly income takes priority, otherwise classified chequing income is used.
- Chequing income excludes internal transfers and peer transfers according to the existing classification logic.
- Card transactions represent spending; payments and credits are handled separately by the existing spend-vs-payments panel.
- Empty filtered states are valid and should remain non-throwing.
- GitHub and Vercel production are separate verification targets; confirm both after every future
  change before handoff.
