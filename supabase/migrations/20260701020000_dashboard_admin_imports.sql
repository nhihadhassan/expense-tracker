-- Dashboard personalization and staged statement imports.
-- Run once in the rachel-tracker Supabase SQL editor before enabling hosted imports.

create table if not exists public.exp_dashboard_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  version integer not null default 1,
  layout jsonb not null default '{}'::jsonb,
  dismissed_warnings jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.exp_dashboard_preferences enable row level security;
drop policy if exists "owner reads dashboard preferences" on public.exp_dashboard_preferences;
drop policy if exists "owner writes dashboard preferences" on public.exp_dashboard_preferences;
create policy "owner reads dashboard preferences"
  on public.exp_dashboard_preferences for select
  using (auth.uid() = user_id);
create policy "owner writes dashboard preferences"
  on public.exp_dashboard_preferences for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create table if not exists public.exp_imports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  file_name text not null,
  file_hash text not null,
  institution text not null,
  account text not null,
  status text not null check (status in ('preview','committing','committed','cancelled','failed','expired')),
  summary jsonb not null default '{}'::jsonb,
  staged_payload jsonb,
  error text,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '24 hours'),
  committed_at timestamptz
);

create index if not exists exp_imports_user_created_idx
  on public.exp_imports(user_id, created_at desc);
create unique index if not exists exp_imports_committed_file_idx
  on public.exp_imports(user_id, file_hash) where status = 'committed';

alter table public.exp_imports enable row level security;
drop policy if exists "owner reads imports" on public.exp_imports;
create policy "owner reads imports"
  on public.exp_imports for select
  using (auth.uid() = user_id);

alter table public.exp_transactions add column if not exists dedupe_key text;
alter table public.exp_payments add column if not exists dedupe_key text;
alter table public.exp_chequing add column if not exists dedupe_key text;

create extension if not exists pgcrypto;

with ranked as (
  select id, row_number() over (
    partition by account, date, coalesce(raw, merchant), round(amount::numeric, 2)
    order by id
  ) - 1 as occurrence
  from public.exp_transactions
)
update public.exp_transactions t
set dedupe_key = encode(extensions.digest(convert_to(concat_ws('|', 'transaction', t.account, t.date,
  coalesce(t.raw, t.merchant), round(t.amount::numeric, 2)::text, ranked.occurrence::text), 'UTF8'), 'sha256'), 'hex')
from ranked where ranked.id = t.id and t.dedupe_key is null;

with ranked as (
  select id, row_number() over (
    partition by account, date, round(amount::numeric, 2)
    order by id
  ) - 1 as occurrence
  from public.exp_payments
)
update public.exp_payments p
set dedupe_key = encode(extensions.digest(convert_to(concat_ws('|', 'payment', p.account, p.date, '',
  round(p.amount::numeric, 2)::text, ranked.occurrence::text), 'UTF8'), 'sha256'), 'hex')
from ranked where ranked.id = p.id and p.dedupe_key is null;

with ranked as (
  select id, row_number() over (
    partition by account, date, descr, round(amount::numeric, 2), balance
    order by id
  ) - 1 as occurrence
  from public.exp_chequing
)
update public.exp_chequing c
set dedupe_key = encode(extensions.digest(convert_to(concat_ws('|', 'chequing', c.account, c.date, c.descr,
  round(c.amount::numeric, 2)::text, coalesce(round(c.balance::numeric, 2)::text, ''),
  ranked.occurrence::text), 'UTF8'), 'sha256'), 'hex')
from ranked where ranked.id = c.id and c.dedupe_key is null;

create unique index if not exists exp_transactions_dedupe_idx
  on public.exp_transactions(dedupe_key) where dedupe_key is not null;
create unique index if not exists exp_payments_dedupe_idx
  on public.exp_payments(dedupe_key) where dedupe_key is not null;
create unique index if not exists exp_chequing_dedupe_idx
  on public.exp_chequing(dedupe_key) where dedupe_key is not null;

-- Existing IDs remain unchanged; only deterministic import fingerprints are added.
