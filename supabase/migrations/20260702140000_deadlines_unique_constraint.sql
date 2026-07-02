-- deadlines had no unique constraint, so "on conflict do nothing" in loader
-- scripts would silently insert duplicates on re-run instead of being
-- idempotent. One deadline_type per election is the natural key.

create unique index if not exists deadlines_election_type_idx
  on deadlines (election_id, deadline_type);
