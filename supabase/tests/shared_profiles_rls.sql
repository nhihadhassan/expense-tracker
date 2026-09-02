-- Run against an isolated local/test Supabase database after migrations.
-- This transaction creates synthetic users and rolls every row back.
begin;

insert into auth.users (id, email)
values
  ('00000000-0000-4000-8000-000000000001', 'snapshot-owner@example.invalid'),
  ('00000000-0000-4000-8000-000000000002', 'snapshot-viewer@example.invalid'),
  ('00000000-0000-4000-8000-000000000003', 'snapshot-stranger@example.invalid');

insert into public.exp_shared_profiles (id, owner_user_id, slug, display_name, title)
values (
  '10000000-0000-4000-8000-000000000001',
  '00000000-0000-4000-8000-000000000001',
  'synthetic-snapshot',
  'Synthetic snapshot',
  'Expense Tracker'
);

insert into public.exp_shared_profile_members (profile_id, user_id)
values (
  '10000000-0000-4000-8000-000000000001',
  '00000000-0000-4000-8000-000000000002'
);

do $$
begin
  if has_table_privilege('anon', 'public.exp_shared_profiles', 'select') then
    raise exception 'anon must not have profile access';
  end if;
  if has_table_privilege('authenticated', 'public.exp_shared_profiles', 'insert') then
    raise exception 'authenticated clients must not write profiles';
  end if;
  if has_table_privilege('authenticated', 'public.exp_shared_profile_members', 'select') then
    raise exception 'membership rows must not be client-readable';
  end if;
end $$;

set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000001', true);
do $$ declare visible integer; begin
  select count(*) into visible from public.exp_shared_profiles;
  if visible <> 1 then raise exception 'owner should see one snapshot'; end if;
end $$;

select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000002', true);
do $$ declare visible integer; begin
  select count(*) into visible from public.exp_shared_profiles;
  if visible <> 1 then raise exception 'viewer should see one snapshot'; end if;
end $$;

select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000003', true);
do $$ declare visible integer; begin
  select count(*) into visible from public.exp_shared_profiles;
  if visible <> 0 then raise exception 'non-member must see no snapshots'; end if;
end $$;

reset role;
rollback;
