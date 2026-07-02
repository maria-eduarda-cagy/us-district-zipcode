-- Core schema for real elections/ballots/contests/candidates/measures/polling
-- locations, replacing the static office-name mapping in
-- supabase/functions/sample-ballot/index.ts (buildContests) and the fake
-- placeholder measures in main.py (get_measures_for_jurisdiction).

create table if not exists sources (
  source_id uuid primary key default gen_random_uuid(),
  source_url text not null,
  source_type text not null,
  fetched_at timestamptz not null default now(),
  effective_date date,
  document_hash text,
  confidence numeric,
  manual_review_flag boolean not null default false,
  notes text
);

create table if not exists elections (
  election_id uuid primary key default gen_random_uuid(),
  name text not null,
  election_type text not null check (election_type in ('primary', 'general', 'special', 'municipal', 'referendum')),
  election_date date not null,
  state text not null,
  jurisdiction_scope text not null check (jurisdiction_scope in ('federal', 'state', 'county', 'city', 'district')),
  party_scope text,
  is_special boolean not null default false,
  status text not null default 'scheduled' check (status in ('scheduled', 'in_progress', 'certified', 'archived')),
  source_id uuid references sources (source_id)
);

create unique index if not exists elections_natural_key_idx
  on elections (state, election_date, election_type, coalesce(party_scope, ''));

create table if not exists deadlines (
  deadline_id uuid primary key default gen_random_uuid(),
  election_id uuid not null references elections (election_id) on delete cascade,
  deadline_type text not null,
  deadline_at timestamptz not null,
  source_id uuid references sources (source_id),
  notes text
);

create table if not exists precincts (
  precinct_id uuid primary key default gen_random_uuid(),
  precinct_code text not null,
  precinct_name text,
  county_fips text not null,
  state text not null,
  geom geometry(MultiPolygon, 4326),
  effective_from date not null default '1900-01-01',
  effective_to date,
  source_id uuid references sources (source_id),
  unique (state, county_fips, precinct_code, effective_from)
);

create index if not exists precincts_geom_idx on precincts using gist (geom);

create table if not exists offices (
  office_id uuid primary key default gen_random_uuid(),
  name text not null,
  level text not null check (level in ('Federal', 'State', 'Local')),
  description text,
  unique (name, level)
);

create table if not exists ballot_styles (
  ballot_style_id uuid primary key default gen_random_uuid(),
  election_id uuid not null references elections (election_id) on delete cascade,
  precinct_id uuid not null references precincts (precinct_id) on delete cascade,
  party text,
  style_code text not null,
  language text[] not null default array['en'],
  sample_ballot_url text,
  certification_date date,
  source_id uuid references sources (source_id),
  unique (election_id, precinct_id, style_code)
);

create table if not exists contests (
  contest_id uuid primary key default gen_random_uuid(),
  election_id uuid not null references elections (election_id) on delete cascade,
  office_id uuid not null references offices (office_id),
  district_layer_id text references district_layers (layer_id),
  district_id text,
  contest_label text not null,
  vote_for int not null default 1,
  nonpartisan boolean not null default false,
  retention boolean not null default false,
  write_in_allowed boolean not null default false,
  order_on_ballot int,
  source_id uuid references sources (source_id)
);

create unique index if not exists contests_natural_key_idx
  on contests (election_id, office_id, coalesce(district_id, ''), contest_label);

create table if not exists ballot_style_contests (
  ballot_style_id uuid not null references ballot_styles (ballot_style_id) on delete cascade,
  contest_id uuid not null references contests (contest_id) on delete cascade,
  primary key (ballot_style_id, contest_id)
);

create table if not exists candidates (
  candidate_id uuid primary key default gen_random_uuid(),
  contest_id uuid not null references contests (contest_id) on delete cascade,
  name text not null,
  ballot_name text,
  party text,
  running_mate text,
  incumbent boolean not null default false,
  unopposed boolean not null default false,
  withdrawn boolean not null default false,
  ballot_order int,
  source_id uuid references sources (source_id)
);

create table if not exists ballot_measures (
  measure_id uuid primary key default gen_random_uuid(),
  election_id uuid not null references elections (election_id) on delete cascade,
  district_layer_id text references district_layers (layer_id),
  district_id text,
  jurisdiction_scope text not null check (jurisdiction_scope in ('federal', 'state', 'county', 'city', 'district')),
  title text not null,
  question_text text,
  impact_yes text,
  impact_no text,
  order_on_ballot int,
  source_id uuid references sources (source_id)
);

create table if not exists ballot_style_measures (
  ballot_style_id uuid not null references ballot_styles (ballot_style_id) on delete cascade,
  measure_id uuid not null references ballot_measures (measure_id) on delete cascade,
  primary key (ballot_style_id, measure_id)
);

create table if not exists polling_locations (
  location_id uuid primary key default gen_random_uuid(),
  election_id uuid not null references elections (election_id) on delete cascade,
  location_type text not null check (location_type in ('election_day', 'early_vote', 'dropbox', 'vote_center')),
  name text not null,
  address jsonb,
  geom geometry(Point, 4326),
  hours text,
  start_date date,
  end_date date,
  is_accessible boolean,
  source_id uuid references sources (source_id)
);

create index if not exists polling_locations_geom_idx on polling_locations using gist (geom);
create index if not exists polling_locations_election_id_idx on polling_locations (election_id);

alter table sources enable row level security;
alter table elections enable row level security;
alter table deadlines enable row level security;
alter table precincts enable row level security;
alter table offices enable row level security;
alter table ballot_styles enable row level security;
alter table contests enable row level security;
alter table ballot_style_contests enable row level security;
alter table candidates enable row level security;
alter table ballot_measures enable row level security;
alter table ballot_style_measures enable row level security;
alter table polling_locations enable row level security;
-- No policies: only the service_role key (used by Edge Functions) can read/write.
