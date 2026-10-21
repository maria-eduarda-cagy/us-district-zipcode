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
- `offices`, `contests`, `candidates` — abstract office vs. specific race vs. candidate, following the distinction recommended in the original research reports
- `ballot_styles`, `ballot_style_contests` — ballot style (by election + precinct + party) and which contests it contains
- `ballot_measures`, `ballot_style_measures` — questions/referendums (3 statewide questions loaded for the 2026 general)
- `contest_results` — official vote totals per candidate per party primary (migration `20261020120000`); jurisdiction-wide, not per precinct
- `polling_locations` — voting locations, with `county_fips` (early voting in MD is county-restricted): Montgomery's 14 primary centers + all 102 MD general centers
- `sources` — provenance: every row loaded by a script has `source_url`, `fetched_at`/`effective_date`, for auditing

All new tables have RLS enabled **with no policies** — only the Edge Functions' `service_role key` can read/write. The anon key never accesses a table directly, only via `rpc_district_lookup` and the Edge Functions.

## Loader scripts (`scripts/`)

- `load_district_layers.py` — fetches the ArcGIS REST layers live (MD precincts/delegate subdistricts, Montgomery council/BOE districts, DC wards/ANC/SMD/SBOE, VA Fairfax supervisor districts/precincts, Loudoun) and generates idempotent SQL (`ON CONFLICT DO UPDATE`) for `district_layers`/`district_boundaries`. Each layer mirrors its source: districts the source stops publishing are deleted. For `md_precincts_2026` it also rebuilds MD `precincts` (re-run `load_md_general_2026.py` afterwards if precinct codes changed) and derives the code of Garrett's and Kent's unsplit districts, which the state publishes without a VTD. Reusable — safe to re-run whenever a source publishes an update.
- `load_montgomery_primary_2026_bs_dem_125.py` — **not automatically reusable**. Contains the BS DEM 125 ballot's contests/candidates, manually transcribed from the MSBE certified PDF. Serves as a template/pattern for repeating the process on other ballot styles, not a generic pipeline.
- `load_md_2026_elections_calendar.py` — populates `elections`/`deadlines` (certified primary + scheduled general) from dates verified in [election-research-notes.md](election-research-notes.md).
- `load_montgomery_early_voting_2026_primary.py` — geocodes (Census, fallback ArcGIS) and loads Montgomery County's 14 official early voting centers (MSBE certified PDF) into `polling_locations`.
- `load_montgomery_primary_2026_bs_rep_125.py` — same pattern as the Democratic script, loads the Republican ballot (`BS REP 125`) for the same precinct. Reuses the same `contest_id` for the 10 offices that exist on both ballots (automatic merge, no schema change needed — `contests` is already party-agnostic). Also corrects (`UPDATE`) the `party` of the 5 already-loaded Circuit Court Judge candidates, from `'Democratic'` to `'Cross-filed'` (cross-filing: same candidates on both primary ballots).
- `md_general_ballot_parser.py` — parses an MSBE certified general ballot PDF (pdftohtml coordinates) into ballot styles: precinct, contests, candidates, parties, questions, as printed. Handles the per-county layout variations; validated against the hand transcription of Montgomery's BS 125 and against MSBE's official candidate lists.
- `load_md_general_2026.py` — the 2026 general ballot for every MD precinct (24 jurisdictions, 1,991 styles): downloads and parses the 24 PDFs, aborts unless the ballots agree with MSBE's official candidate lists, then rebuilds the MD general election's contests and ballot styles in one transaction. State/federal/legislative contests are shared across counties (congressional district taken from the official list); every other contest is scoped to its county; Cumberland's city contests to the city. Ballot precincts with no polygon in `md_precincts_2026` are reported and skipped (4 as of 2026-10-21: Anne Arundel 04-025, Calvert 03-002, Worcester 01-003/01-004). Replaced the hand-transcribed `load_montgomery_general_2026_bs_125.py`.
- `load_va_precincts.py` — Northern Virginia precincts (all localities but Fairfax County) from the Department of Elections' per-locality GIS files (one zipped shapefile per county/city, same schema statewide): `va_precincts_elect` layer (district_id = 11-digit precinct GEOID) mirrored into `precincts`. Replaced Loudoun's old county layer. Needs `ogr2ogr`.
- `va_general_2026.py` — what every Virginia ballot shares: the election, U.S. Senate and House contests, the 3 constitutional amendments with ELECT's explanations. Imported by the VA ballot loaders so all localities link to the same contest/measure rows.
- `load_va_localities_general_2026.py` — 2026 general ballots for Northern Virginia localities other than Fairfax County, configured per locality (sample ballot, styles, precinct assignment). Loaded so far: Alexandria, Prince William.
- `load_fairfax_general_2026.py` — the whole of Fairfax County, VA: creates the VA 2026 general election (+ election-day deadline), copies the `va_fairfax_precincts` layer into `precincts`, and links each precinct to one of 5 ballot styles (one per sample ballot PDF) using the precinct → congressional district list from the county's precinct descriptions. Split precincts (Pioneer, CD 11/8) and the 3 Herndon precincts (town ballot vs. "town exception" for voters outside town limits) get two styles each. The generated SQL asserts the style count.
- `load_montgomery_primary_2026_results.py` — fetches the MSBE primary results CSVs live and loads `contest_results`. Validates every candidate name against the two primary ballot loaders and aborts on any mismatch; the generated SQL ends with a row-count assertion. Reusable — re-run to refresh.

## Edge Functions

- `supabase/functions/search` — address → geocode → `rpc_district_lookup` → memberships (every district containing the point)
- `supabase/functions/sample-ballot` — geocode + memberships +:
  - the address's precinct: when neighboring localities' precinct layers overlap at a border, the precinct of the address's own county (precinct codes start with the county FIPS)
  - split precincts: when a precinct has several styles for the same election and party, keeps the one whose district contests all contain the address (most matches wins; best partial match if none is complete). County-scoped contests don't count; when styles still tie (no boundary layer tells them apart, e.g. Talbot's Board of Education districts), all of them are kept
  - `district_mismatches`: district contests on the selected ballot (with a real boundary layer — not county-scoped) whose district doesn't contain the address. Catches precinct polygons older than the ballot (e.g. Anne Arundel 04-025, created after the boundary data). The UI still shows the ballot, with a notice and a link to the state's official voter lookup
  - real `contests`/`measures`/`candidates` via PostgREST embedding (`precincts → ballot_styles → ballot_style_contests → contests → offices/district_layers/sources/candidates`), filtered by `include_downballot`
  - `polling_locations`: 5 nearest locations in the address's county, still in use (end date not passed), via RPC `rpc_nearby_polling_locations` (ordered by `ST_Distance`, can't be done with REST filters alone)
  - `election_events`: `deadlines` + associated `elections` for the address's state only, via a PostgREST embed
  - `coverage`: `ballot` / `districts_only` / `outside_coverage`, plus state and county (from the COUNTY membership); the UI explains why there's no ballot instead of showing an empty one
  - `ballot_status`: `"loaded"` or `"not_available"` — never fabricates data when no ballot_style is loaded for the precinct
  - each contest/measure carries its `election`, so the frontend groups the ballot by election (upcoming first, then past ones with results); candidates carry `results` (votes, % within their party primary, winner)
  - `data_sources` / `data_last_updated`: provenance and freshness of everything in the response, shown as "Data last updated" in the UI

## Notable incident (2026-07-02)

The first `district_layers` migration recreated `rpc_district_lookup` pointing only at the new (empty) tables, briefly breaking district search in production because the legacy tables with real data (`cd119` etc.) weren't known about until inspected directly in the database. Fixed in the same session with a hotfix migration that does a `UNION ALL` between legacy and new. Lesson: **the production schema was never documented before this work** — hence the importance of keeping this `/docs` folder up to date.
