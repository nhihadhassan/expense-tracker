-- Authenticated, read-only shared financial snapshots.
-- No profile or financial data is seeded by this migration.

create table if not exists public.exp_shared_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  slug text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
  display_name text not null check (char_length(btrim(display_name)) between 1 and 80),
  title text not null check (char_length(btrim(title)) between 1 and 120),
  schema_version integer not null default 1 check (schema_version = 1),
  payload jsonb not null default '{"transactions":[],"chequing":[],"payments":[],"statements":[],"manual_entries":[]}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint exp_shared_profiles_payload_object check (jsonb_typeof(payload) = 'object')
);

create table if not exists public.exp_shared_profile_members (
  profile_id uuid not null references public.exp_shared_profiles(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'viewer' check (role = 'viewer'),
  created_at timestamptz not null default now(),
  primary key (profile_id, user_id)
);

create index if not exists exp_shared_profiles_owner_idx
  on public.exp_shared_profiles(owner_user_id);
create index if not exists exp_shared_profile_members_user_idx
  on public.exp_shared_profile_members(user_id, profile_id);

create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

create or replace function private.exp_can_view_shared_profile(requested_profile_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.exp_shared_profiles profile
    left join public.exp_shared_profile_members member
      on member.profile_id = profile.id
      and member.user_id = (select auth.uid())
    where profile.id = requested_profile_id
      and (
        profile.owner_user_id = (select auth.uid())
        or member.user_id is not null
      )
  );
$$;

revoke all on function private.exp_can_view_shared_profile(uuid) from public, anon;
grant execute on function private.exp_can_view_shared_profile(uuid) to authenticated;

alter table public.exp_shared_profiles enable row level security;
alter table public.exp_shared_profile_members enable row level security;

drop policy if exists exp_shared_profiles_readers on public.exp_shared_profiles;
create policy exp_shared_profiles_readers
  on public.exp_shared_profiles
  for select
  to authenticated
  using (private.exp_can_view_shared_profile(id));

-- Membership rows are intentionally not client-readable. The helper above performs
-- the membership check without disclosing who else can see a profile.
revoke all on public.exp_shared_profiles from anon, authenticated;
revoke all on public.exp_shared_profile_members from anon, authenticated;
grant select on public.exp_shared_profiles to authenticated;

comment on table public.exp_shared_profiles is
  'Service-managed read-only financial snapshots visible only to owners and explicit viewers.';
comment on table public.exp_shared_profile_members is
  'Service-managed viewer allowlist; never exposed directly to browser clients.';
