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
Re-run the parser + push after adding statements, then redeploy is **not** needed (data lives in
Supabase, the frontend is static):
```
python3 push_supabase.py     # re-parses locally, refreshes the exp_* tables
```
Note: `push_supabase.py` needs RLS temporarily relaxed (it uses the anon key). Ask Claude to run
the relax → push → re-lock sequence, or add a service-role key to the script.

To change the frontend, edit the template in `build_dashboard.py`, run `python3 build_dashboard.py`
(regenerates `web/index.html`), then `npx vercel deploy --prod --yes`.

## Hosted v1 scope
Read-only of all data (charts, insights, recurring, chequing, income, spend-vs-pay, calendar,
table). Budgets/goals/subscriptions/income are still per-device (localStorage). The rules editor,
inline recategorize, and PDF upload are hidden online (those stay on the local app). Moving the
editable bits + ingestion into Supabase is the natural v2.
