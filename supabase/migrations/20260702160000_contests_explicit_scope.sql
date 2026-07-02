-- scope (at_large vs district) was being inferred in the Edge Function from
-- whether contests.district_id was null. That's wrong whenever a contest
-- attaches a "containing" district for map/name purposes while still being
-- an at-large seat (e.g. County Council At-Large is geographically bounded
-- by the county, but is still an at-large office; County Council District 7
-- has no district geometry loaded at all, which made it look at-large).
-- scope must be an explicit, authoritative property of the contest, not an
-- inferred one.

alter table contests add column if not exists scope text check (scope in ('at_large', 'district'));

-- Backfill: default from the old (buggy) heuristic, then fix the one known
-- inversion (County Council At-Large) explicitly. Any future contest must
-- set scope explicitly at insert time -- see scripts/load_montgomery_primary_2026_bs_dem_125.py.
update contests set scope = case when district_id is null then 'at_large' else 'district' end where scope is null;
update contests set scope = 'at_large' where contest_label = 'County Council At-Large';
update contests set scope = 'district' where contest_label = 'County Council District 7';

alter table contests alter column scope set not null;
