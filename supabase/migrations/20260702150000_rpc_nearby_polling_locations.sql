-- polling_locations has no county/precinct column (early voting centers in
-- MD are open county-wide, not precinct-restricted), so the natural query
-- is "nearest N to this point" rather than an exact-match filter. PostgREST
-- can't express ST_Distance ordering through query params, hence this RPC,
-- mirroring the rpc_district_lookup pattern.

create or replace function rpc_nearby_polling_locations(lon double precision, lat double precision, max_results int default 10)
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
  distance_meters double precision
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
    ) as distance_meters
  from polling_locations p
  join elections e on e.election_id = p.election_id
  where p.geom is not null
  order by p.geom::geography <-> st_setsrid(st_makepoint(lon, lat), 4326)::geography
  limit max_results;
$$;
