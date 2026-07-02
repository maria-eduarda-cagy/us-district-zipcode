-- Hotfix: the previous migration (20260702120000) replaced rpc_district_lookup
-- with a version that only reads from the new, empty district_boundaries
-- table. Production actually stores district data in per-layer legacy tables
-- (cd119, sldu, sldl, county, place, unsd — each with id/name/geom, populated
-- with real TIGER data) plus a layer_metadata table for source_url lookup.
-- This restores lookups against the real legacy tables and additionally
-- unions in district_boundaries so future layers (DC wards/ANC/SMD, VA
-- supervisor districts, MD precincts) can be loaded there without another
-- rewrite of this function.

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
  with pt as (
    select st_setsrid(st_makepoint(lon, lat), 4326) as geom
  ),
  legacy as (
    select 'cd119' as layer_id, 'CD' as layer_type, c.id as district_id, c.name as district_name, c.geom
    from cd119 c, pt where st_intersects(c.geom, pt.geom)
    union all
    select 'sldu', 'SLDU', c.id, c.name, c.geom
    from sldu c, pt where st_intersects(c.geom, pt.geom)
    union all
    select 'sldl', 'SLDL', c.id, c.name, c.geom
    from sldl c, pt where st_intersects(c.geom, pt.geom)
    union all
    select 'county', 'COUNTY', c.id, c.name, c.geom
    from county c, pt where st_intersects(c.geom, pt.geom)
    union all
    select 'place', 'PLACE', c.id, c.name, c.geom
    from place c, pt where st_intersects(c.geom, pt.geom)
    union all
    select 'unsd', 'UNSD', c.id, c.name, c.geom
    from unsd c, pt where st_intersects(c.geom, pt.geom)
  )
  select
    legacy.layer_id,
    legacy.layer_type,
    legacy.district_id,
    legacy.district_name,
    lm.source_url,
    st_asgeojson(legacy.geom) as geojson
  from legacy
  left join layer_metadata lm on lm.layer_id = legacy.layer_id
  union all
  select
    b.layer_id,
    l.layer_type,
    b.district_id,
    b.district_name,
    coalesce(b.source_url, l.source_url) as source_url,
    st_asgeojson(b.geom) as geojson
  from district_boundaries b
  join district_layers l on l.layer_id = b.layer_id
  join pt on st_intersects(b.geom, pt.geom)
  where b.effective_from <= current_date
    and (b.effective_to is null or b.effective_to >= current_date);
$$;
