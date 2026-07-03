# Data architecture

Last updated: 2026-07-02.

## Pipeline overview

```
Address → Geocoding (Census → ArcGIS fallback) → PostGIS overlay (rpc_district_lookup)
  → District stack (CD, SLDU, SLDL, county, place, unsd, precinct, delegate subdistrict, ward, ANC, SMD...)
  → precinct → ballot_style → contests → candidates / measures
  → Unified response: offices + measures + ballots + election events
```

Implemented as Supabase (Postgres + PostGIS) with two Edge Functions (`search`, `sample-ballot`).

## Table generations (two coexisting)

### Legacy tables (predate this work, never versioned in a migration until 2026-07-02)

- `cd119`, `sldu`, `sldl`, `county`, `place`, `unsd` — one table per layer type, columns `id`/`name`/`geom`, TIGER/Line data for all of MD+DC+VA
- `layer_metadata` — exists but is empty (0 rows), not actually used
- `cd119_raw`, `sldu_raw`, etc. — staging tables with all original TIGER attributes

These tables have backed the `rpc_district_lookup` function since before this project had migrations. **They were not touched or migrated** — they were only registered in `district_layers` (see below) so that `contests.district_layer_id` can reference `cd119`, `sldu`, etc.

### New tables (created 2026-07-02, migrations in `supabase/migrations/`)

- `district_layers` / `district_boundaries` — generic layer + geometry registry, used for every new non-TIGER layer (MD precincts, DC wards/ANC/SMD/SBOE, VA supervisor districts). `rpc_district_lookup` does a `UNION ALL` between the legacy tables and these new ones — see migration `20260702130000_fix_rpc_district_lookup_legacy_tables.sql`.
- `elections`, `deadlines` — elections and deadlines
- `precincts` — precinct as its own entity (separate from `district_boundaries`, designed to link with `ballot_styles`)
- `offices`, `contests`, `candidates` — abstract office vs. specific race vs. candidate, following the distinction recommended in the original research reports. `contests.verification_note` (added `20260702170000_contests_verification_note.sql`) flags a contest whose data conflicts across official sources instead of silently picking one — the frontend renders it as a visible warning; see [dmv-expansion-plan.md](dmv-expansion-plan.md) for the Board of Education example that prompted this.
- `ballot_styles`, `ballot_style_contests` — ballot style (by election + precinct + party) and which contests it contains
- `ballot_measures`, `ballot_style_measures` — questions/referendums (schema ready, no real data loaded yet)
- `polling_locations` — voting locations (schema ready, no data loaded yet)
- `sources` — provenance: every row loaded by a script has `source_url`, `fetched_at`/`effective_date`, for auditing

All new tables have RLS enabled **with no policies** — only the Edge Functions' `service_role key` can read/write. The anon key never accesses a table directly, only via `rpc_district_lookup` and the Edge Functions.

## Loader scripts (`scripts/`)

- `load_district_layers.py` — fetches 9 ArcGIS REST layers live (MD precincts/delegate subdistricts, DC wards/ANC/SMD/SBOE, VA Fairfax/Loudoun) and generates idempotent SQL (`ON CONFLICT DO UPDATE`) for `district_layers`/`district_boundaries`. Reusable — safe to re-run whenever a source publishes an update.
- `load_montgomery_primary_2026_bs_dem_125.py` — **not automatically reusable**. Contains the BS DEM 125 ballot's contests/candidates, manually transcribed from the MSBE certified PDF. Serves as a template/pattern for repeating the process on other ballot styles, not a generic pipeline.
- `load_md_2026_elections_calendar.py` — populates `elections`/`deadlines` (certified primary + scheduled general) from dates verified in [election-research-notes.md](election-research-notes.md).
- `load_montgomery_early_voting_2026_primary.py` — geocodes (Census, fallback ArcGIS) and loads Montgomery County's 14 official early voting centers (MSBE certified PDF) into `polling_locations`.
- `load_montgomery_primary_2026_bs_rep_125.py` — same pattern as the Democratic script, loads the Republican ballot (`BS REP 125`) for the same precinct. Reuses the same `contest_id` for the 10 offices that exist on both ballots (automatic merge, no schema change needed — `contests` is already party-agnostic). Also corrects (`UPDATE`) the `party` of the 5 already-loaded Circuit Court Judge candidates, from `'Democratic'` to `'Cross-filed'` (cross-filing: same candidates on both primary ballots).

## Edge Functions

- `supabase/functions/search` — address → geocode → `rpc_district_lookup` → memberships (every district containing the point)
- `supabase/functions/sample-ballot` — geocode + memberships +:
  - real `contests`/`measures`/`candidates` via PostgREST embedding (`precincts → ballot_styles → ballot_style_contests → contests → offices/district_layers/sources/candidates`), filtered by `include_downballot`
  - `polling_locations`: 5 nearest locations via RPC `rpc_nearby_polling_locations` (ordered by `ST_Distance`, can't be done with REST filters alone)
  - `election_events`: all `deadlines` + associated `elections`, via a simple PostgREST embed
  - `ballot_status`: `"loaded"` or `"not_available"` — never fabricates data when no ballot_style is loaded for the precinct

## Notable incident (2026-07-02)

The first `district_layers` migration recreated `rpc_district_lookup` pointing only at the new (empty) tables, briefly breaking district search in production because the legacy tables with real data (`cd119` etc.) weren't known about until inspected directly in the database. Fixed in the same session with a hotfix migration that does a `UNION ALL` between legacy and new. Lesson: **the production schema was never documented before this work** — hence the importance of keeping this `/docs` folder up to date.
