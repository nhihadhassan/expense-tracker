# Hosted version (Vercel + Supabase Auth)

**Live URL:** https://expense-tracker-sooty-six-38.vercel.app
**Login:** email magic-link, restricted to **nhihad.hassan@gmail.com** only.

## Architecture
- **Vercel** (project `expense-tracker`, team nhihadhassan-2432) serves `web/index.html` — an
  auth-gated shell with **no data baked in** (`.vercelignore` keeps all statements/CSVs/PDFs/the
  local dashboard OFF Vercel).
- **Supabase** (project `rachel-tracker`, ref `zgafubhzhxikuknihmnu`, ca-central-1) holds the data
  in `exp_*` tables and does Auth. Every `exp_` table has **RLS** locking access to
  `auth.jwt() ->> 'email' = 'nhihad.hassan@gmail.com'`. Verified: anon reads return `[]`.
- The browser talks to Supabase directly via supabase-js (publishable key); RLS is the security.
- Dashboard layout preferences and dismissed warnings sync through
  `exp_dashboard_preferences` with owner-only RLS.
- Statement previews use authenticated Vercel Python Functions. Normalized rows are staged in
  `exp_imports`, committed with deterministic dedupe keys, then the staged payload is deleted.
  Raw statement files are never retained online.

## ⚠️ One setup step you must do (once)
The magic-link login needs the Vercel URL on Supabase's redirect allowlist. Until then, links
redirect to the project's default Site URL (rachel-tracker) instead of here.

1. Supabase dashboard → project **rachel-tracker** → **Authentication** → **URL Configuration**.
2. Under **Redirect URLs**, click **Add URL** and paste:
   ```
   https://expense-tracker-sooty-six-38.vercel.app/**
   ```
3. **Save.** (Leave the Site URL as-is — this is additive and won't affect the other apps.)

Then open the URL, enter `nhihad.hassan@gmail.com`, and tap the magic link in your email.

## Updating the hosted data
Open **Admin → Import statement**, preview the detected account and totals, then choose
**Import new rows**. The dashboard refreshes from Supabase without a redeploy. Supported inputs:

- Scotiabank EBCDIC PDF
- Tangerine credit-card or chequing PDF
- Amex CSV
- BMO CSV (image-only BMO PDFs are not supported)
- normalized Tangerine Markdown

The local bulk-refresh command remains available for rebuilding from every source file:
```
python3 push_supabase.py     # re-parses locally, refreshes the exp_* tables
```
Do not relax RLS for hosted imports. The Vercel Functions use the server-only
`SUPABASE_SECRET_KEY` after verifying the signed-in owner.

To change the frontend, edit the template in `build_dashboard.py`, run `python3 build_dashboard.py`
(regenerates `web/index.html`), then `npx vercel deploy --prod --yes`.

## Hosted import setup

The migration is tracked at
`supabase/migrations/20260701020000_dashboard_admin_imports.sql`, followed by the PostgREST
dedupe-constraint migration `20260701023000_import_dedupe_constraints.sql`. Vercel needs these encrypted
environment variables in Production and Preview:

```
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY
OWNER_EMAIL
```

Never place `SUPABASE_SECRET_KEY` in `build_dashboard.py`, `web/index.html`, or a committed env file.

## Hosted v1 scope
Charts, insights, recurring, chequing, income, spend-vs-pay, calendar, transactions, synchronized
dashboard personalization, warning dismissal, and preview-first statement imports. Budgets,
goals, subscriptions, and manually entered income remain per-device in localStorage. The rules
editor and inline recategorization remain local-only.
