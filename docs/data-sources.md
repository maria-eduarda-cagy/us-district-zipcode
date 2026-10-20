# Data source catalog

Last updated: 2026-10-20. "Loaded" = already in the Supabase database. "Available" = the source exists and has been mapped, but not loaded yet.

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
| Certified PDF — MD 2026 general, Montgomery County | `elections.maryland.gov/elections/2026/general_ballots/Montgomery.pdf` — 1542 pages, certified 2026-08-31, re-published 2026-09-03 (Question 3 language revised by court order) | **Loaded** for precinct 008-006 only: `BS 125` (pages 745-750), 19 contests + 3 statewide questions — `scripts/load_montgomery_general_2026_bs_125.py` |
| MSBE primary results CSVs | `elections.maryland.gov/elections/2026/election_data/` — `GP26_16*Results.csv` (Montgomery), `GP26_16Counc*Results.csv` (by council district), `GP26_CongressionalBreakDown*.csv`, `GP26_LegislativeBreakDown*.csv`. Last-Modified 2026-07-23 | **Loaded** into `contest_results` for every contest on precinct 008-006's primary ballots (106 rows), jurisdiction-wide totals — `scripts/load_montgomery_primary_2026_results.py` (fetches live; re-run to refresh) |
| Certified PDF — 2026 Early Voting Centers (MSBE) | `elections.maryland.gov/elections/2026/2026_Early_Voting_Centers-EN.pdf` — published 2026-04-23 | **Loaded**: 14 Montgomery County centers for the primary. For the general (`2026_Early_Voting_Centers-GG-EN.pdf`, 2026-08-03): **all 102 centers in all 24 MD counties** (Oct 22-29) — `scripts/load_md_early_voting_2026_general.py` parses the PDF, checks every county's count against the PDF's own totals table, and checks each geocoded point falls inside its county. `rpc_nearby_polling_locations` only returns locations in the address's county whose dates haven't passed |
| MSBE general drop boxes / ballot questions | `2026_General_Drop_Box_Locations.pdf`, `ballot_questions.html` | Mapped, not loaded (the 3 statewide questions are loaded from the ballot PDF itself) |
| Montgomery County Board of Elections (`mcg.montgomerycountymd.gov/elections`) | Personalized voter guide, precinct/district maps, online early voting map | Mapped, not used for loading yet |
| DC Board of Elections | Sample ballots by ward/party, calendar | Not researched in depth yet |
| Virginia Department of Elections | Candidates, polling/ballot lookup, redistricting GIS | Not researched in depth yet |
| Google Civic API | Elections, OCD divisions, contests | Not used — secondary cross-check source, never source of truth |

## Rules used in this project

1. **Official source > secondary aggregator.** Never use Vote.org/Ballotpedia/Google Civic as source of truth — only for cross-checking.
2. **Never fabricate data.** If the official source hasn't published yet (e.g. general election results before certification), the table stays empty, it does not get a placeholder. This already caused a real problem in this project (fictitious measures in the old `main.py`) and was fixed.
3. **Every loaded row has a traceable `source_url`** in the `sources` table, linked via `source_id` on rows in `elections`, `ballot_styles`, `contests`, `candidates`, `district_layers`, `district_boundaries`, `precincts`.
4. **Verify the official layer name before labeling it**, don't trust an inherited file name (this happened with MD precincts: the old file said "2022", the source had already updated to "2026").
5. **Freshness is visible.** `sample-ballot` returns `data_sources` (each with the document's `effective_date` and our `fetched_at`) and `data_last_updated`; the frontend shows "Data last updated" above the ballot. Loaders refresh `sources.fetched_at` on re-run.
