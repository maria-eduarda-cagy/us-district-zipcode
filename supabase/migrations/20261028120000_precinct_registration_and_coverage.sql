-- Registered voters per official precinct (first use: MSBE's
-- GP26_State_Precinct_Reference.xlsx), so ballot coverage can be measured in
-- voters instead of precinct polygons. precinct_code uses the same format as
-- precincts.precinct_code (county FIPS + "ED-PCT"). The list is the election
-- authority's, not ours: a precinct here with no row in precincts is one the
-- boundary layer doesn't have yet.

create table if not exists precinct_registration (
  state text not null,
  county_fips text not null,
  precinct_code text not null,
  registered_voters int not null check (registered_voters >= 0),
  source_id uuid references sources (source_id),
  primary key (state, precinct_code)
);

alter table precinct_registration enable row level security;
-- No policies: only the service_role key (used by Edge Functions) can read/write.

-- Ballot coverage of each general election, in registered voters:
--   own_ballot:   the precinct has a polygon and its own certified ballot,
--                 and its styles can be told apart by address
--   tied_ballots: split precinct whose styles differ only by contests with no
--                 boundary layer (the app shows every possible ballot)
--   no_polygon:   the precinct isn't in the boundary layer; its voters land
--                 in another polygon (inferred or neighbor ballot, flagged)
--   no_ballot:    the precinct has a polygon but no ballot loaded
-- Two styles of a precinct are tied when they share the same set of contests
-- that sample-ballot can match by address (scope = district, with a non-county
-- boundary layer) -- the same rule selectBallotStyles uses.
create or replace view ballot_coverage with (security_invoker = true) as
with general_elections as (
  select election_id, state from elections where election_type = 'general'
),
style_keys as (
  select bs.election_id, bs.precinct_id, bs.ballot_style_id,
    coalesce(string_agg(c.contest_id::text, ',' order by c.contest_id)
      filter (where c.scope = 'district' and dl.layer_type <> 'COUNTY' and c.district_id is not null), '') as match_key
  from ballot_styles bs
  join general_elections g on g.election_id = bs.election_id
  left join ballot_style_contests x on x.ballot_style_id = bs.ballot_style_id
  left join contests c on c.contest_id = x.contest_id
  left join district_layers dl on dl.layer_id = c.district_layer_id
  group by bs.election_id, bs.precinct_id, bs.ballot_style_id
),
precinct_status as (
  select election_id, precinct_id, max(n) > 1 as tied
  from (select *, count(*) over (partition by election_id, precinct_id, match_key) as n from style_keys) s
  group by election_id, precinct_id
),
classified as (
  select g.election_id, r.state, r.registered_voters, r.source_id,
    case
      when p.precinct_id is null then 'no_polygon'
      when s.precinct_id is null then 'no_ballot'
      when s.tied then 'tied_ballots'
      else 'own_ballot'
    end as status
  from precinct_registration r
  join general_elections g on g.state = r.state
  left join precincts p on p.state = r.state and p.precinct_code = r.precinct_code and p.effective_to is null
  left join precinct_status s on s.election_id = g.election_id and s.precinct_id = p.precinct_id
)
select c.election_id, c.state,
  sum(registered_voters)::int as registered_voters,
  coalesce(sum(registered_voters) filter (where status = 'own_ballot'), 0)::int as voters_own_ballot,
  coalesce(sum(registered_voters) filter (where status = 'tied_ballots'), 0)::int as voters_tied_ballots,
  coalesce(sum(registered_voters) filter (where status = 'no_polygon'), 0)::int as voters_no_polygon,
  coalesce(sum(registered_voters) filter (where status = 'no_ballot'), 0)::int as voters_no_ballot,
  count(*)::int as precincts,
  count(*) filter (where status = 'own_ballot')::int as precincts_own_ballot,
  min(src.source_url) as registration_source_url,
  min(src.effective_date) as registration_as_of
from classified c
left join sources src on src.source_id = c.source_id
group by c.election_id, c.state;
