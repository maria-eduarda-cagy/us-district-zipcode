-- Early voting in MD is county-restricted (you vote at a center in your own
-- county), but rpc_nearby_polling_locations returned the nearest centers of
-- any county -- a DC or Fairfax address got Montgomery centers. Store each
-- location's county (5-digit FIPS, same as the legacy county.id) and let the
-- RPC filter by it. sample-ballot passes the address's COUNTY membership.

alter table polling_locations add column if not exists county_fips text;

-- Every location loaded before this migration is a Montgomery County early
-- voting center (primary + general).
update polling_locations set county_fips = '24031' where county_fips is null;

alter table polling_locations alter column county_fips set not null;

create index if not exists polling_locations_county_fips_idx on polling_locations (county_fips);

drop function if exists rpc_nearby_polling_locations(double precision, double precision, int);

create function rpc_nearby_polling_locations(
  lon double precision,
  lat double precision,
  max_results int default 10,
  county_fips text default null
)
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
    and (rpc_nearby_polling_locations.county_fips is null or p.county_fips = rpc_nearby_polling_locations.county_fips)
  order by p.geom::geography <-> st_setsrid(st_makepoint(lon, lat), 4326)::geography
  limit max_results;
$$;
