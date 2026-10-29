-- Two changes to rpc_nearby_polling_locations, both needed once the 2026
-- general's early voting centers were loaded next to the primary's (same 14
-- buildings, different dates):
--   1. only return locations still in use (end_date, or election day when
--      there's no end_date, is today or later) -- otherwise every center
--      showed up twice, once with June's dates.
--   2. return each row's source, so sample-ballot can include it in
--      data_sources / data_last_updated.
-- The return type changes, so the function has to be dropped first.

drop function if exists rpc_nearby_polling_locations(double precision, double precision, int);

create function rpc_nearby_polling_locations(lon double precision, lat double precision, max_results int default 10)
returns table (
  location_id uuid,
  election_id uuid,
  election_name text,
  election_date date,
  location_type text,
  name text,
  address jsonb,
  hours text,
  start_date date,
  end_date date,
  distance_meters double precision,
  source_type text,
  source_url text,
  source_effective_date date,
  source_fetched_at timestamptz
)
language sql
stable
as $$
  select
    p.location_id,
    p.election_id,
    e.name as election_name,
    e.election_date,
    p.location_type,
    p.name,
    p.address,
    p.hours,
    p.start_date,
    p.end_date,
    st_distance(
      p.geom::geography,
      st_setsrid(st_makepoint(lon, lat), 4326)::geography
    ) as distance_meters,
    s.source_type,
    s.source_url,
    s.effective_date as source_effective_date,
    s.fetched_at as source_fetched_at
  from polling_locations p
  join elections e on e.election_id = p.election_id
  left join sources s on s.source_id = p.source_id
  where p.geom is not null
    and coalesce(p.end_date, e.election_date) >= current_date
  order by p.geom::geography <-> st_setsrid(st_makepoint(lon, lat), 4326)::geography
  limit max_results;
$$;
