-- Official vote totals per candidate, for elections that have already
-- happened (first use: the 2026-06-23 MD primary, from the MSBE results
-- CSVs). One row per candidate per party primary: cross-filed judges appear
-- on both the Democratic and Republican primary ballots and get separate
-- totals in each, so primary_party is part of the key (null for
-- nonpartisan contests such as Board of Education).
--
-- votes are for the contest's whole jurisdiction (reporting_unit), not just
-- the searched precinct -- that's what decides who won.

create table if not exists contest_results (
  result_id uuid primary key default gen_random_uuid(),
  contest_id uuid not null references contests (contest_id) on delete cascade,
  candidate_id uuid not null references candidates (candidate_id) on delete cascade,
  primary_party text,
  reporting_unit text not null,
  votes int not null check (votes >= 0),
  is_winner boolean not null default false,
  source_id uuid references sources (source_id)
);

create unique index if not exists contest_results_natural_key_idx
  on contest_results (candidate_id, coalesce(primary_party, ''));

create index if not exists contest_results_contest_id_idx on contest_results (contest_id);

alter table contest_results enable row level security;
-- No policies: only the service_role key (used by Edge Functions) can read/write.
