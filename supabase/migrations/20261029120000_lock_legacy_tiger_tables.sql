-- The legacy TIGER tables (created before this project's migrations) had RLS
-- disabled and full grants to anon/authenticated, so anyone with the public
-- anon key could INSERT/UPDATE/DELETE/TRUNCATE them through the REST API.
-- Edge Functions use the service role (bypasses RLS), so, like every other
-- table here, they get RLS with no policies. Grants are revoked too because
-- TRUNCATE ignores RLS.
do $$
declare
  t text;
begin
  foreach t in array array[
    'cd119', 'cd119_raw', 'sldu', 'sldu_raw', 'sldl', 'sldl_raw',
    'county', 'county_raw', 'place', 'place_raw', 'unsd', 'unsd_raw'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
  end loop;
end $$;

-- public.spatial_ref_sys (PostGIS's SRID catalog) stays as the advisor flags
-- it: it's owned by supabase_admin, so neither RLS nor its grants can be
-- changed from the postgres role (a revoke only warns).
