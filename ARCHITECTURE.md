# Expense Tracker architecture

## Canonical application

The generated dashboard at `/` remains the canonical application for this release. It owns the
complete accounts, statements, recurring-charge, forecasting, budgeting, analytics, import,
personalization, theme, authentication, and PWA workflows.

The React application at `/app/` is an incremental replacement, not a second source of truth.
It currently provides a focused overview, cash-flow explorer, activity list, simple analytics,
plans summary, and manual-entry composer. Links for capabilities that have not migrated return to
the canonical root application. `/legacy.html` is intentionally not produced.

React can replace the root only after these parity gates are met and tested with production-shaped
synthetic data:

1. Accounts, statements, net worth, recurring charges, forecasts, warnings, and full analytics.
2. Supabase-backed budgets, goals, subscriptions, rules, recategorization, and personalization.
3. Preview/map/commit/history for hosted statement imports.
4. Profile switching, theme, PWA, sign-out, and the established mobile and desktop flows.
5. Equivalent calculation tests, accessibility checks, and authenticated browser verification.

## Private data boundaries

- Hosted builds run `build_dashboard.py --hosted-only`; they never parse local statements or bake
  transactions into HTML.
- Owner data is loaded only after Supabase authentication and remains protected by database RLS.
- Read-only snapshots live in `exp_shared_profiles` and are visible only to their owner or an
  explicit member. Membership and all writes are service-managed.
- Shared payloads are fetched only when selected and remain in memory. There is no public `/data/`
  profile path, local-storage payload, or service-worker cache for financial APIs.
- `tools/privacy_check.py` blocks tracked financial exports, statement formats, likely secrets,
  payment-card numbers, and public profile JSON.

## Production build

`npm run build` generates the empty authenticated root, custom 404, crawler policy, PWA assets,
and the React `/app/` build. Recharts is loaded only when the cash-flow visualization is opened;
Supabase and icon code are split into stable vendor chunks. Production source maps are disabled.

Known React routes have explicit Vercel rewrites. Unknown root and `/app/*` routes fall through to
the branded `404.html` with an HTTP 404 response.
