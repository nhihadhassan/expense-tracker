# Cloud / Hosted Features — Implementation Plans (for later)

These features can't be built in the current **local, zero-install, single-user** setup —
they need external services, API keys, a hosted server, and/or credentials. Each plan below
is detailed enough to execute when you decide to provide those. They're intentionally
**not built** so the app stays local and private by default.

The good news: the architecture is ready. `ingest.py` (parsing + analytics), `db.py` (SQLite),
and `server.py` (stdlib HTTP + JSON API) cleanly separate concerns, so these are additive.

---

## 1. Plaid (or Flinks) live bank sync

Replace manual file drops with automatic transaction pulls from your banks.

**What you must provide:** a Plaid account + API keys (`PLAID_CLIENT_ID`, `PLAID_SECRET`),
and you'd link each bank through Plaid Link (OAuth). In Canada, **Flinks** or **MX** are
common alternatives with better CA bank coverage — same shape of integration.

**Dependencies:** `plaid-python` (requires `pip`, so this breaks the no-install promise →
run in a venv or container). HTTPS is required for the OAuth redirect.

**Build outline:**
- **Link flow:** a `/link` page hosting Plaid Link → returns a `public_token` →
  `POST /api/plaid/exchange` swaps it for an `access_token`; store encrypted in a new
  `plaid_items(item_id, access_token_enc, institution, cursor)` table.
- **Sync:** `POST /api/plaid/sync` calls `/transactions/sync` (cursor-based) → map Plaid
  transactions to our record shape (`date, merchant=name, amount, raw, account`), run
  `ingest.resolve()` for categories, upsert via `db._insert_cards` (dedupe on Plaid
  `transaction_id` as `ref`). Add `account_type` from Plaid account subtype (credit/depository).
- **Schedule:** a cron/launchd job hitting `/api/plaid/sync` daily (the repo already has a
  scheduled-tasks pattern).
- **Chequing/income:** Plaid `depository` accounts feed the existing chequing/income views;
  reuse `classify_deposit()` on the transaction names.

**Security:** encrypt `access_token` at rest (e.g. `cryptography.fernet` + a key in the OS
keychain, not in the repo). Never store raw bank credentials (Plaid handles auth). **Never
initiate transfers** — read-only `transactions`/`accounts` scopes only.

**Effort:** ~1–2 days. **Risk:** medium (OAuth, secret handling, CA coverage).

---

## 2. Login + multi-device sync

Today everything is single-user and local (budgets/goals/income in `localStorage`, data in a
local SQLite). To use it from your phone + laptop with shared state, you need a hosted server
and accounts.

**What you must provide:** a host (Fly.io / Render / a small VPS) and a domain with HTTPS.

**Build outline:**
- **Host the backend:** containerize `server.py` (or port it to FastAPI for async + uvicorn).
  Move SQLite → **Postgres** (or Litestream-backed SQLite) for concurrent access.
- **Auth:** email magic-link or OAuth (Google). Add `users` table; scope every table with
  `user_id`. Sessions via signed cookies (`itsdangerous`) or JWT.
- **Sync the client-only state:** move `budgets`, `goals`, `income` out of `localStorage`
  into DB tables keyed by `user_id`, exposed via `/api/budgets|goals|income` (budgets/goals
  endpoints already exist server-side — just wire the dashboard to them when authed).
- **Per-user data isolation:** every `db.*` query filters by `user_id`.

**Security:** HTTPS only; httpOnly+SameSite cookies; rate-limit auth; encrypt the DB at rest;
a clear data-export/delete path (it's financial data).

**Effort:** ~3–5 days. **Risk:** medium-high (now responsible for hosting others' financial data).

---

## 3. Email / push alert notifications

Turn the existing in-app insights (budget overspend, new subscription, anomalies, upcoming
recurring charges) into proactive notifications.

**What you must provide:** an email API key (Resend / Postmark / SES) or a push service
(web-push VAPID keys, or Telegram/Slack webhook — simplest).

**Build outline:**
- **Alert engine:** a `compute_alerts(txns, budgets, recurring)` in `ingest.py` returning
  typed alerts (reuse `detect_anomalies`, `detect_recurring`, budget math from the dashboard).
  Persist to an `alerts(user_id, type, payload, created, sent)` table; dedupe so each fires once.
- **Delivery:** a scheduled job (daily / on-sync) renders unsent alerts to an email
  (Resend API) or posts to a Slack/Telegram webhook. Slack/Telegram is the lowest-friction
  (no domain/DKIM needed) — recommended first step.
- **Triggers:** budget crosses 90%/100%; a *new* recurring merchant appears; an anomaly above
  threshold; a recurring charge due in ≤3 days.
- **Preferences:** a `/settings` UI to choose channels + thresholds (stored per user).

**Security:** keys in env/secret store, never the repo; unsubscribe link; don't put full
account numbers or balances in notification bodies.

**Effort:** ~1 day for Slack/Telegram; +1 day for email with templates. **Risk:** low
(Slack/Telegram) → medium (email deliverability/DKIM).

---

## 4. (Optional) Vite + ECharts SPA rewrite — deferred, not recommended now

A modern single-page rebuild (componentized, ECharts for native cross-linking/sankey/brush).
**Why deferred:** it's a *tech refactor*, not a feature — the current single-file dashboard
already does cross-filtering, drill-down-style filtering, calendar heatmap, and all charts,
and it has the big advantage of **"double-click to open, no build step."** The JSON API
(`/api/*`) is already SPA-ready, so this can be done anytime without backend changes. Do it
only if you want a component library / mobile-first redesign — budget ~3–5 days.

---

## Suggested order if you pursue these
1. **Slack/Telegram alerts** (cheap, high value, no hosting).
2. **Plaid/Flinks sync** (kills manual file drops — the biggest convenience win).
3. **Host + login + sync** (only if you need multi-device).
4. **SPA** (only for a visual/mobile overhaul).
