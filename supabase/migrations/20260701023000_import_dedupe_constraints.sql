-- PostgREST on_conflict requires named unique constraints, not partial indexes.
-- PostgreSQL unique constraints already allow multiple NULL values.

drop index if exists public.exp_transactions_dedupe_idx;
drop index if exists public.exp_payments_dedupe_idx;
drop index if exists public.exp_chequing_dedupe_idx;

alter table public.exp_transactions
  drop constraint if exists exp_transactions_dedupe_key_key,
  add constraint exp_transactions_dedupe_key_key unique (dedupe_key);

alter table public.exp_payments
  drop constraint if exists exp_payments_dedupe_key_key,
  add constraint exp_payments_dedupe_key_key unique (dedupe_key);

alter table public.exp_chequing
  drop constraint if exists exp_chequing_dedupe_key_key,
  add constraint exp_chequing_dedupe_key_key unique (dedupe_key);
