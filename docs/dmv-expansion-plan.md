# Plan: from 1 address to the whole DMV

Last updated: 2026-07-02. See current scope in [mvp-scope.md](mvp-scope.md).

Two independent fronts: **geography** (where districts/precincts are) and **election data** (who's running, on which ballot). Geography is solvable with reusable scripts; election data today depends on manual PDF transcription due to the lack of a structured API.

## Front 1 — Geography (expanding `district_layers`/`district_boundaries`)

### Virginia: missing Arlington, Alexandria, Prince William, Falls Church, Fairfax City, Manassas, Manassas Park

Per-locality process:
1. Find the county/city's ArcGIS REST server (each publishes its own — there's no single statewide precinct service for VA, unlike MD)
2. Inspect `{MapServer}?f=json` to find the right `layer id` (election districts, precincts) and the **official layer name** (don't trust an old file name — this is exactly the bug we fixed on MD's precinct layer, which was labeled "2022" when the source had already renamed it "2026")
3. Add the entry to `LAYERS` in `scripts/load_district_layers.py` with the correct field mapper (each source uses different property names)
4. Run the script, review the generated SQL, apply in batches (large files hit Supabase's API 413 limit — split into ~1.5MB batches)

### Maryland and DC

Already fully covered in the loaded layers (precincts, delegate subdistricts, wards, ANC, SMD, SBOE). Maintenance = periodically re-run `load_district_layers.py` (already idempotent) and re-verify official layer names on each run, since agencies re-publish without notice.

### 3 districts identified with no geographic layer (2026-07-02 audit)

These offices already appear correctly on the ballot (the link is via `precinct → ballot_style`, not dependent on geometry), but don't show a district name/boundary on the map nor allow "Focus on Map":

| District | Source found | Status |
|---|---|---|
| Montgomery County Council (1-7) | `gis.montgomerycountymd.gov/arcgis/rest/services/elections/council_7_districts_maponly/MapServer/0` (found via the county's ArcGIS Online webmap item, `mcgov-gis.maps.arcgis.com`) | **Loaded** (2026-07-02) — geometry agrees with the certified ballot (Ashton = District 7 in both) |
| Montgomery Board of Education | `gis4.montgomerycountymd.gov/arcgis/rest/services/elections/board_of_ed/FeatureServer/0` | **Loaded** (2026-07-02), but **not linked to the affected contest** — see the data conflict below |
| Judicial Circuit 6 | No dedicated shapefile found | Low priority — Circuit 6 = all of Montgomery + Frederick, every Montgomery precinct already falls in it without needing its own layer |

Note: `gis.montgomerycountymd.gov` and `gis4.montgomerycountymd.gov` return HTTP 403 for Python's default `urllib` user agent (but allow curl's default) — `scripts/load_district_layers.py`'s `fetch_features` now sends `User-Agent: Mozilla/5.0` to work around this.

### Data conflict found: Board of Education District boundary vs. certified ballot (2026-07-02)

Loading the real Board of Education boundary layer surfaced a genuine, unresolved conflict for the Ashton precinct (008-006): the certified ballot PDF prints "Board of Education District 3" for this precinct, but **three independent official Montgomery County sources** all say District 5 instead:

1. The live ArcGIS boundary layer (point-in-polygon places Ashton inside District 5's polygon, nowhere near District 3's)
2. The county's own official PDF map, titled "2021 Board of Education District 3" (covers precinct groups 04/06/10/13, not group 08 which Ashton belongs to)
3. The county's own official crosswalk PDF, "2022 Montgomery County Precincts Within Board of Education Districts" (explicitly lists precinct group 08, including 08-06, under District 5)

This lines up with the earlier-found bug where the same "District 3" + same 5 candidates appeared across all 771 ballot styles in the county (see [mvp-scope.md](mvp-scope.md)) — but confirms it's likely a real anomaly in the certified ballot PDF's Board of Education section (or upstream of it), not just an artifact of the third-party extraction tool, since my own independent re-extraction of the actual PDF (twice, coordinate-based) shows the same "District 3" text.

**Resolution**: rather than silently trust either source, the `contests` row for "Board of Education District 3" now carries a `verification_note` (added via migration `20260702170000_contests_verification_note.sql`) and is **not linked** to the new boundary layer (`district_layer_id`/`district_id` left null). The frontend renders a visible "Data conflict — not verified" warning on that contest's card instead of silently picking a side. The candidates themselves (Sharon Creed, Brett DiResta, Andrew Frykman, Sally A. McCarthy, Cassandra "Cassi" Sung) were left as loaded, since it's the **district label**, not necessarily the candidate list, that's in question — that hasn't been independently confirmed either way.

## Front 2 — Real election data (ballot styles, contests, candidates)

This is the bottleneck. There's no structured public API for this in MD/DC/VA — only certified PDFs per county/jurisdiction.

### Repeatable process (what was done manually in task 3, for 1 precinct)

1. Find the jurisdiction's certified ballot PDF (e.g. `elections.maryland.gov/elections/<year>/primary_ballots/<County>.pdf`)
2. Download and extract text with `pdftotext -layout`
3. Locate the page for the ballot style of interest (search by precinct code)
4. Transcribe contests + candidates into a data structure (as in `scripts/load_montgomery_primary_2026_bs_dem_125.py`)
5. Generate and apply the SQL

### What needs to change to scale (not do it manually per precinct)

- **Coordinate-aware parser** (`pdfplumber`, reading each word's x/y position) instead of `pdftotext -layout`, which scrambles two-column layouts — this is why Central Committee and Board of Education were left out in task 3
- **Automate locating the ballot style by precinct within the PDF**, instead of manual grep by precinct code
- Montgomery County alone has **125+ Democratic ballot styles** (the "BS DEM 125" code indicates this) — each is a different combination of districts. Populating all of them requires running this parser for each one, not just hand-transcribing.
- Repeat for the Republican ballot (loaded as of 2026-07-02 for the test precinct, see [mvp-scope.md](mvp-scope.md)) and for the other 23 MD counties, DC (sample ballots by ward/party), and VA (per locality — each publishes separately, no single pattern)

### Recommended priority order (from the original research report)

1. Maryland + Montgomery County complete (most structured official sources, already the pilot)
2. Rest of Maryland (same pipeline, other counties)
3. DC (sample ballots by ward/party, vote centers instead of fixed polling place — slightly different modeling)
4. Virginia (more fragmented — each locality has its own source; full lookup is strongest only for state primary/general elections)

## Front 3 — Data not started yet

- **`polling_locations` — only partially loaded** (task 6): Montgomery County's 14 early voting centers (2026 primary), via the MSBE certified PDF. **Update (2026-07-02)**: found the structured source that was missing — Montgomery County has its own ArcGIS elections service (`gis3.montgomerycountymd.gov/arcgis/rest/services/elections`) with `polling_place` (election-day location **per precinct**, `District_P` field in "01-01" format already compatible with our `precinct_code`) and `drop_boxes`, neither loaded yet. This replaces the earlier assumption that no structured source existed. VA/Loudoun already has `loudoun_polling_places.geojson` available via `download_data.py`, never loaded. DC not researched yet.
- `ballot_measures` (questions/referendums) — schema ready, zero real data loaded
- November 2026 general election — blocked until the MSBE certifies it (see [election-research-notes.md](election-research-notes.md))

## Multi-party candidates completed for the test precinct (2026-07-02)

Loaded the full Republican ballot (`BS REP 125`, 13 contests) for precinct 008-006, merging automatically with the Democratic contests already loaded — no schema change needed, since `contests` was already party-agnostic. Also handled judicial cross-filing (5 Circuit Court judges appearing on both party ballots) with a dedicated `'Cross-filed'` party value. See [mvp-scope.md](mvp-scope.md) for details. Geographic layers (Montgomery County Council, Board of Education) and the remaining 770 ballot styles in the county are still pending, awaiting a scope decision.
