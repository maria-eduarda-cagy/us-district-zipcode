# Data source catalog

Last updated: 2026-07-02. "Loaded" = already in the Supabase database. "Available" = the source exists and has been mapped, but not loaded yet.

## Geography / districts

| Source | Coverage | Status | Base URL |
|---|---|---|---|
| Census TIGER/Line | CD, SLDU, SLDL, county, place, unsd — MD+DC+VA | Loaded (legacy, predates this work) | `www2.census.gov/geo/tiger/` |
| Maryland iMAP — MD_ElectionBoundaries | MD precincts (official name: "Maryland Precincts 2026"), delegate subdistricts ("Maryland Legislative Districts 2022") | Loaded | `mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer` |
| DC GIS — Administrative_Other_Boundaries | Wards ("Ward - 2022"), ANC ("Advisory Neighborhood Commission - 2023"), SMD ("Single Member District - 2023") | Loaded | `maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer` |
| DC GIS — Education | SBOE districts | Loaded | `maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Education_WebMercator/MapServer` |
| Fairfax County GIS | Supervisor districts | Loaded | `fairfaxcounty.gov/idrisi/rest/services/Jade/Electoral/MapServer` |
| Loudoun County GIS | Election districts, precincts, polling places (polling places only mapped, not loaded) | Partial (precincts/districts loaded; polling places not) | `logis.loudoun.gov/gis/rest/services/COL/ElectionDistricts/MapServer` |
| Arlington, Alexandria, Prince William, Falls Church, Fairfax City, Manassas, Manassas Park (VA) | — | **Not mapped yet** — each likely publishes its own GIS, needs individual URL discovery | — |

## Calendar and ballots

| Source | What it has | Status |
|---|---|---|
| Maryland State Board of Elections (`elections.maryland.gov`) | Official calendar, candidates, certified ballots as PDF per county | Used for date research ([election-research-notes.md](election-research-notes.md)) and for the Montgomery ballot ([mvp-scope.md](mvp-scope.md)) |
| Certified PDF — MD 2026 primary, Montgomery County | `elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf` — 1542 pages, certified 2026-04-14 | Partially extracted (1 of ~125+ Democratic ballot styles in the county) |
| Certified PDF — 2026 Early Voting Centers (MSBE) | `elections.maryland.gov/elections/2026/2026_Early_Voting_Centers-EN.pdf` — published 2026-04-23 | **Loaded**: 14 Montgomery County centers (geocoded and in `polling_locations`) |
| Montgomery County Board of Elections (`mcg.montgomerycountymd.gov/elections`) | Personalized voter guide, precinct/district maps, online early voting map | Mapped, not used for loading yet |
| DC Board of Elections | Sample ballots by ward/party, calendar | Not researched in depth yet |
| Virginia Department of Elections | Candidates, polling/ballot lookup, redistricting GIS | Not researched in depth yet |
| Google Civic API | Elections, OCD divisions, contests | Not used — secondary cross-check source, never source of truth |

## Rules used in this project

1. **Official source > secondary aggregator.** Never use Vote.org/Ballotpedia/Google Civic as source of truth — only for cross-checking.
2. **Never fabricate data.** If the official source hasn't published yet (e.g. the 2026 general ballot), the table stays empty, it does not get a placeholder. This already caused a real problem in this project (fictitious measures in the old `main.py`) and was fixed.
3. **Every loaded row has a traceable `source_url`** in the `sources` table, linked via `source_id` on rows in `elections`, `ballot_styles`, `contests`, `candidates`, `district_layers`, `district_boundaries`, `precincts`.
4. **Verify the official layer name before labeling it**, don't trust an inherited file name (this happened with MD precincts: the old file said "2022", the source had already updated to "2026").
