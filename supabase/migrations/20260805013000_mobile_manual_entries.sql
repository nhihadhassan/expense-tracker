-- Mobile manual expense and income entries. Hosted rows belong to the signed-in owner.

create table if not exists public.exp_manual_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  entry_type text not null check (entry_type in ('expense', 'income')),
  date date not null,
  amount numeric(12,2) not null check (amount > 0),
  name text not null check (char_length(btrim(name)) between 1 and 160),
  category text not null check (char_length(btrim(category)) between 1 and 80),
  account text not null default 'Manual',
  note text not null default '',
  currency text not null default 'CAD' check (char_length(currency) = 3),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists exp_manual_entries_user_date_idx
  on public.exp_manual_entries(user_id, date desc);

create or replace function public.exp_touch_manual_entry()
returns trigger language plpgsql security invoker set search_path = public as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists exp_manual_entries_touch_updated_at on public.exp_manual_entries;
create trigger exp_manual_entries_touch_updated_at
before update on public.exp_manual_entries
for each row execute function public.exp_touch_manual_entry();

alter table public.exp_manual_entries enable row level security;
drop policy if exists exp_manual_entries_owner on public.exp_manual_entries;
create policy exp_manual_entries_owner on public.exp_manual_entries
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

grant select, insert, update, delete on public.exp_manual_entries to authenticated;

-- Rename only the three unambiguous historical categories requested for the mobile catalog.
update public.exp_transactions set category = 'Eating out' where category = 'Food & Dining';
update public.exp_transactions set category = 'Food' where category = 'Groceries';
update public.exp_transactions set category = 'Health' where category = 'Health & Pharmacy';
update public.exp_rules set category = 'Eating out' where category = 'Food & Dining';
update public.exp_rules set category = 'Food' where category = 'Groceries';
update public.exp_rules set category = 'Health' where category = 'Health & Pharmacy';
update public.exp_subs set category = 'Eating out' where category = 'Food & Dining';
update public.exp_subs set category = 'Food' where category = 'Groceries';
update public.exp_subs set category = 'Health' where category = 'Health & Pharmacy';

insert into public.exp_budgets(category, monthly)
select 'Eating out', monthly from public.exp_budgets where category = 'Food & Dining'
on conflict (category) do nothing;
insert into public.exp_budgets(category, monthly)
select 'Food', monthly from public.exp_budgets where category = 'Groceries'
on conflict (category) do nothing;
insert into public.exp_budgets(category, monthly)
select 'Health', monthly from public.exp_budgets where category = 'Health & Pharmacy'
on conflict (category) do nothing;
delete from public.exp_budgets where category in ('Food & Dining', 'Groceries', 'Health & Pharmacy');
