-- Versions the point-in-polygon infrastructure that previously only existed
-- as manual objects in the Supabase SQL editor (see README "Create
-- rpc_district_lookup in Supabase SQL Editor"). Shape matches the contract
-- already asserted by supabase/functions/search/index.test.ts and
-- supabase/functions/sample-ballot/index.test.ts: layer_id, layer_type,
-- district_id, district_name, source_url, geojson (text).

create extension if not exists postgis;
create extension if not exists pgcrypto;

create table if not exists district_layers (
  layer_id text primary key,
  layer_type text not null,
  name text not null,
  state text,
  jurisdiction text,
  tiger_year text,
  source_url text,
  created_at timestamptz not null default now()
);

create table if not exists district_boundaries (
  id uuid primary key default gen_random_uuid(),
  layer_id text not null references district_layers (layer_id) on delete cascade,
  district_id text,
  district_name text,
  geom geometry(MultiPolygon, 4326) not null,
  effective_from date not null default '1900-01-01',
  effective_to date,
  source_url text,
  source_id uuid,
  retrieved_at timestamptz not null default now()
);

create index if not exists district_boundaries_geom_idx
  on district_boundaries using gist (geom);

create index if not exists district_boundaries_layer_id_idx
  on district_boundaries (layer_id);

create unique index if not exists district_boundaries_layer_district_effective_idx
  on district_boundaries (layer_id, district_id, effective_from);

alter table district_layers enable row level security;
alter table district_boundaries enable row level security;
-- No policies: only the service_role key (used by Edge Functions) can read/write.
-- The anon key never queries these tables directly, only via rpc_district_lookup.

create or replace function rpc_district_lookup(lon double precision, lat double precision)
returns table (
  layer_id text,
  layer_type text,
  district_id text,
  district_name text,
  source_url text,
  geojson text
)
language sql
stable
as $$
  select
    b.layer_id,
    l.layer_type,
    b.district_id,
    b.district_name,
    coalesce(b.source_url, l.source_url) as source_url,
    st_asgeojson(b.geom) as geojson
  from district_boundaries b
  join district_layers l on l.layer_id = b.layer_id
  where st_intersects(b.geom, st_setsrid(st_makepoint(lon, lat), 4326))
    and b.effective_from <= current_date
    and (b.effective_to is null or b.effective_to >= current_date);
$$;
