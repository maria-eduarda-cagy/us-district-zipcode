# Roadmap and decisions

Last updated: 2026-10-29. This is the project's current direction; update it whenever a decision is made. Versão em português: [roadmap.pt-BR.md](roadmap.pt-BR.md).

## Direction

1. **Finish Maryland** — close the coverage gaps below.
2. **Automate Maryland updates (test state)** — each loader fetches the new source and runs on its own when the source changes. Comes before any other state.
3. **Finish the DMV** — every federal candidate for DC and Virginia through the map-point method, replicating Maryland's logic.
4. **Public API** — see [public-api-plan.md](public-api-plan.md). Starts only after the DMV is complete.

## Where we are (2026-10-21)

| Area | 2026 general ballot | Notes |
|---|---|---|
| Maryland (24 jurisdictions) | **Loaded**: 1,975 of 2,040 precincts from their own ballots + 13 inferred (1,988) | The 52 without a ballot: 34 MSBE "ghost" precincts (no voters) and 18 polygons of precincts that no longer exist where the ballot can't be inferred (below). Primary + results only for Montgomery precinct 008-006 |
| Fairfax County, VA | **Loaded**: all 266 precincts | Herndon town races, split precinct Pioneer, official measure explanations |
| Alexandria, VA | **Loaded**: all 32 precincts | One ballot for the city: U.S. Senate, House 8th, 3 amendments |
| Prince William, VA | **Loaded**: all 103 precincts | House 7th/10th (Colgan split), House of Delegates District 20 special (5 precincts), 4 towns (Dumfries, Haymarket, Occoquan, Quantico) |
| Rest of Northern Virginia | Precincts loaded (ELECT GIS), ballots not yet | Arlington, Fairfax City, Manassas, Manassas Park, Loudoun: sites block automated access — sample ballots must be downloaded by hand. Falls Church: no sample ballot file found |
| DC | Not loaded | Ward/ANC/SMD/SBOE layers loaded; sample ballot source not confirmed (dcboe.org blocks automated access) |

## Next steps

### 1. Finish Maryland
- ~~Howard~~ **fixed 2026-10-21**: the state layer was reloaded (Howard 118 → 67 precincts, matching the ballots).
- ~~Garrett, Kent~~ **fixed 2026-10-21**: their 17 unsplit election districts were in the layer without a VTD; codes are now derived (see decision log).
- **Polygon/ballot consistency check (2026-10-21)**: for every MD precinct with a ballot, a point inside its polygon falls in the ballot's congressional, senate, delegate and city districts — except Baltimore County 09-008 (59% 42B / 41% 42A in the 2022 delegate layer; the certified ballot says 42B for the whole precinct) and an expected Cumberland split precinct.
- **Paused 2026-10-29** (affects about 400 people, already shows a warning; the step 2 automation fixes it when the state updates its layer). **Stale polygons** — the state layer is built from county files of 2025, older than some 2026 precinct changes:
  - **Anne Arundel 04-025** (new precinct, no polygon anywhere — the county's own layer also predates it): its voters fall into a neighbor's polygon whose ballot has a **different congressional/senate district**. Mitigated 2026-10-21: `sample-ballot` now flags such ballots (`district_mismatches`) and the UI points to the official voter lookup. A real fix still needs the precinct's polygon.
  - **31 polygons of precincts that no longer exist** (not on MSBE's 2026 precinct list, which matches the ballots: 1,979 precincts + 34 ghosts). **13 now get an inferred ballot** (2026-10-21): Calvert 03-007/03-008 (Dunkirk, Chesapeake Beach — the largest gap; Calvert's new 03-002 has no polygon), Montgomery 05-024/06-018, St. Mary's 02-005/03-007 and 7 in Baltimore City. **18 stay without a ballot** because the inference is ambiguous or impossible: Dorchester 01-002/01-003, Washington 03-005/24-002, St. Mary's 06-005, Baltimore City 11-008/11-009, Carroll 04-008/05-007, Frederick 07-006/20-002/20-003/21-005/21-006/23-003/23-004/26-003 (some are Frederick's 6 ghosts), Montgomery 04-043. A real fix needs current county precinct layers (Calvert's GIS server didn't answer; Anne Arundel's and Montgomery's are as old as the state's).
  - **Worcester 01-003/01-004** (no polygon): harmless, all four 01-00x ballots are identical.
- **Paused 2026-10-29** (no public layer; the map-point method has the same limit). **Talbot**: 5 split precincts differ only by Board of Education district; with no boundary layer, all possible styles are shown.
- **Coverage in voters (2026-10-28)**, live in the `ballot_coverage` view and shown in the app, out of MSBE's 4,287,334 registered voters in 1,978 precincts: **99.45%** get their own precinct's polygon and certified ballot; **0.43%** (Talbot's 5 split precincts) see every possible ballot; **0.12%** are in precincts with no polygon (Calvert 03-002: 4,134, inferred ballot; Worcester 01-003/004: 870, identical ballots; Anne Arundel 04-025: 73, neighbor's ballot flagged). The 18 polygons with no ballot hold about **333 residents** (Census 2020 blocks), 0.005% of Maryland; the 13 inferred polygons about 10,071. This is coverage, not accuracy: stale precinct shapes can still misplace an address near a boundary, which only the ground-truth check measures.
- **Paused 2026-10-29** (the manual Frederick and Montgomery downloads are deferred). **County precinct layers searched (2026-10-28)**: the state layer's only 2026 update was Howard (already loaded); every other county file in it dates from 2025. Washington County's own layer (edited 2026-05-07) still lists 03-005 and 24-002 as current, so they are likely zero-voter precincts, not obsolete ones. Anne Arundel publishes 2026 voter counts but no new polygons; Carroll's, Calvert's and Dorchester's layers date from 2022-2023; Talbot has no public Board of Education district layer. Not reachable from here and left for a manual download: Frederick's 2026 precinct layer and map, Montgomery Planning's precinct layer (2026-01-26). With ~333 residents at stake, no further search is planned unless one of those downloads changes the picture.
- **Apply OCD-IDs to every MD district (next, 2026-10-29):** congressional (`cd`), state Senate (`sldu`), delegates (`sldl`, including subdistricts such as 42B), counties and places. Store them next to the Census GEOID and validate each code against the official list ([opencivicdata/ocd-division-ids](https://github.com/opencivicdata/ocd-division-ids)), checking the subdistrict format there. The `search` and `sample-ballot` functions start returning each district's OCD-ID. MD is the test: the same generation rule applies to the other states.
- **Ground-truth check (next, expanded 2026-10-29)**: compare a sample of real MD addresses against an official source independent of our layers (MSBE's voter list or the state's official district lookups), prioritizing addresses near district boundaries, and publish the hit rate **for both methods**: by map point (the default path) and by precinct (the extra layer).

### 2. Automate Maryland updates (test state)

Maryland is the test state: the logic built here is what gets replicated in the other states. That's why this comes before expanding.

**a) Adjust the loaders to pick up new or updated sources**

- `load_md_general_2026.py`: today it only downloads a PDF if it isn't cached, so it never sees a corrected ballot. Compare the site's `Last-Modified`/`ETag` (or a hash) with the local file and re-download when it changes.
- Move hard-coded values (year-based URLs, dates, election IDs, effective dates) out of the code into a per-election configuration. Effective dates should come from the source's `Last-Modified`.
- `load_md_2026_elections_calendar.py`: the dates were typed by hand. It stays manual, but the calendar page is now watched (hash) to flag changes.

**b) File check as the trigger, per loader**

- A manifest links each source to the loader that consumes it: iMAP precinct layer → `load_district_layers.py`; ballot PDFs → `load_md_general_2026.py`; precinct reference spreadsheet → `load_md_precinct_registration.py`; early voting PDF → `load_md_early_voting_2026_general.py`.
- For each source, store the last signature seen (`Last-Modified`, `ETag` or hash; for ArcGIS services, the edit date when exposed).
- When a signature changes, run **only that source's loader**, not all of them.
- Loader dependencies live in the manifest: if the precinct layer changes, run `load_md_general_2026.py` next (ballot styles depend on precinct codes).

**c) Scheduling**

- A scheduled GitHub Actions job (the project already uses it for CI): daily near elections, weekly otherwise.
- If a loader's validation fails, it aborts without writing anything (as it already does) and opens an alert (issue).

**Definition of done:** a new state is added with only a new configuration (sources and loaders), without rewriting the check and scheduling logic.

### 3. Finish the DMV
**Goal redefined 2026-10-29:** every federal candidate for DC and Virginia through the map-point method (both states' districts are already loaded). Precinct ballots become an extra layer.

- **Paused 2026-10-29** (precinct ballots are now an extra layer; for federal, the map-point method already covers all of Virginia). Virginia localities beyond Fairfax and Alexandria: precincts are loaded for all of them; ballots need each locality's sample ballots. The 5 blocked sites (Arlington, Fairfax City, Manassas, Manassas Park, Loudoun) need the PDFs downloaded in a browser; Falls Church has no sample ballot file.
- **Kept** (doesn't depend on precincts). Virginia calendar: only election day is loaded (registration and early voting deadlines missing).
- **Paused 2026-10-29** (federally, DC only votes for President and Delegate; the map-point method handles it). DC: confirm the sample ballot source.

### 4. Public API
See [public-api-plan.md](public-api-plan.md).

## Prerequisites for integrating with Voting Buddy

The integration is the second stage. **Before joining them, both systems must use the same district codes.** Today Strapi's District model only has `name` and `state` (free text), which can't be matched reliably.

1. **The same district code on both sides: OCD-ID.** E.g., `ocd-division/country:us/state:md/cd:8`. A new `ocdId` field on Strapi's District model; this project returns OCD-IDs. OCD-IDs cover federal, state and local in a single format.
2. **The district's election cycle.** OCD-IDs don't change with redistricting (`cd:8` stays `cd:8` under the new map). Each candidate must be linked to the district of their election (e.g., `cycle: 2026` or `congress: 120`).
3. **Standardized offices.** A closed list of offices with their level (the app already has the "President" vs "U.S. President" case). For federal candidates, also store the FEC ID to avoid duplicates.
4. **A contract between the systems.** This project takes an address and returns the list of OCD-IDs, the method (map point or precinct) and the confidence. Voting Buddy looks up candidates whose `district.ocdId` is in the list.
5. **An allow-list for the candidate pipeline.** The AI pipeline that collects and scores candidates may only use OCD-IDs that exist in this project's district list (e.g., Maryland only has congressional districts 1 to 8). This blocks wrong or invented districts.
6. **Agree with the candidate pipeline developer** on the OCD-ID format and the cycle field before any integration code.

## Decision log

### 2026-10-29
- **The default path is without precincts: ballot by map point** (address → districts → candidates). With public data, feasibility is 100% at the federal and state levels, versus 72% for precincts at the local level. See [feasibility-study.md](feasibility-study.md) and the summary [feasibility-summary.md](feasibility-summary.md).
- **Maryland's precincts stay:** they are an extra layer (exact ballot where available) and the ground truth for measuring the map-point method's error near boundaries.
- **Maryland is the test state:** automatic per-loader updates (file check → run only the affected loader → scheduling) are built and validated in MD before any other state. The other states replicate the same logic through configuration.
- **Precinct tasks paused, not deleted:** stale polygons and Talbot in MD, manual county layer downloads, ballots for the other Virginia localities, and DC's ballot source. The ground-truth check now measures both methods, and the DMV goal becomes "federal candidates through the map-point method".
- **Before integrating with Voting Buddy, both systems must use the same district codes (OCD-ID)**, with the election cycle alongside. Maryland gets OCD-IDs first, as the test. See "Prerequisites for integrating with Voting Buddy".

### 2026-10-28
- **Coverage is measured in registered voters, from the election authority's own precinct list**, not in precinct polygons: `precinct_registration` (MSBE precinct reference, `scripts/load_md_precinct_registration.py`) feeds the `ballot_coverage` view, `sample-ballot` returns it as `coverage.state_stats`, and the app shows it for every address in the state. Residents in polygons with no ballot can't be counted in voters (they are inside other precincts' counts), so they are estimated once from Census 2020 blocks and stated as an estimate.
- **Every source is listed with its exact URL in [references.md](references.md)**, generated from the database by `scripts/export_references.py`; re-run it after any loader. The TIGER layers have no recorded URL or vintage (they predate source tracking); Maryland's state legislative districts were checked against TIGER 2026 and match.
- **Maryland is validated against an official source before work moves to the DMV**: the polygon/ballot consistency check only proves our layers agree with each other (districts and geocoding both come from the Census); the proof that an address gets the right districts has to come from an independent official source.

### 2026-10-21
- **A ballot is inferred for a polygon of a precinct that no longer exists only when it's unambiguous**: every 2026 precinct of the same county election district whose located districts (congress, senate, delegate, city) cover most of the polygon has the very same ballot. The style is marked "(inferred)" and the UI says the ballot comes from the current precincts with the same districts. Otherwise the address keeps "districts only". 13 of 31 inferred.
- **Talbot's split precincts stay as tied styles**: they split by Board of Education district, and there is no public boundary layer for those districts.
- **Prince William precincts 706-711 get the standard 7th District ballot although their November sample ballot isn't on the county's page**: they lie 100% in the 7th District with no town or special contest, so the ballot is fully determined (it matches the 54 other plain 7th District precincts). Recorded as an inference, not a transcription.
- **Town contests are a separate style for the precincts a town lies in** (Prince William's "town residents only" ballots, like Herndon): the `place` layer picks town or non-town by address.
- **Virginia precincts come from the Department of Elections' per-locality GIS files** (one source, same schema for every locality), except Fairfax County, which keeps the county's own validated layer. Loudoun's old county layer was dropped so an address never gets two precincts; where localities' layers overlap at a border, `sample-ballot` takes the precinct of the address's county.
- **Contests and amendments shared by every Virginia ballot live in one module** (`va_general_2026.py`), so all localities link to the same rows (refactor verified: Fairfax's generated SQL is byte-identical).
- **Virginia ballots are validated against ELECT's candidate lists** (Fairfax: 25/25). The lists can't replace the sample ballots: no candidate order, no local questions.
- **A ballot whose district contests don't contain the address is shown with a warning, not hidden** (`district_mismatches`): it's most likely right for the precinct, and the voter is pointed to the state's official lookup. County-scoped contests are not checked (no boundary of their own). Known noise: where TIGER's congressional boundary differs from the official one (slivers of some Fairfax precincts), the warning can appear for a correct ballot. No false warning on the 12 test addresses.
- **Maryland precincts with no VTD get a derived code**: Garrett's and Kent's unsplit election districts come from the state layer with only a district number; the code follows each county's ballot numbering ("02-000" in Garrett, "02-001" in Kent), checked against the ballots' precinct lists. Features with no code at all are skipped instead of stored with a null id.
- **Zero-voter placeholder precincts (-098/-099/-999) are expected to have no ballot** (Anne Arundel's own layer shows 0 registered voters for them).
- **The certified ballot wins over boundary layers** when they disagree (Baltimore County 09-008): the voter gets the precinct's ballot; the district list may still show the layer's district.

### 2026-10-20
- **The precinct layer is a mirror of the live source.** `load_district_layers.py` deletes districts the source stops publishing and rebuilds MD `precincts` from `md_precincts_2026`; re-run `load_md_general_2026.py` afterwards if precinct codes changed. Reason: Howard's consolidation (118 → 67) left 51 stale polygons overlapping the new ones.
- **Precinct → congressional district in Virginia comes from the county's official precinct descriptions, not geometry.** TIGER and even the county's own CD layer disagree with precinct polygons by up to ~14% of a precinct's area; the descriptions are exact (only Pioneer is officially split).
- **Virginia's 2026 redistricting doesn't apply.** Approved by referendum (2026-04-21) but voided by the Supreme Court of Virginia (2026-05-08); the 2021 map stands.
- **Split precincts get one ballot style per variant**; `sample-ballot` keeps the style whose district contests contain the address. County-scoped contests don't count, and when styles still tie (no boundary layer tells them apart) all are shown rather than guessing.
- **Fairfax "Federal Only" ballots are not loaded**: they depend on voter status, not address.
- **Official measure explanations go in their own field** (`ballot_measures.explanation` + source URL), verbatim. `impact_yes`/`impact_no` stay reserved for the FOR/AGAINST text printed on the ballot (Maryland). Typos in official documents are kept as printed.
- **Maryland ballots are parsed from the MSBE PDFs and gated on MSBE's official candidate lists**: the loader aborts on any mismatch. It rebuilds the MD general election in one transaction and replaced the hand-transcribed Montgomery BS 125 loader.
- **County offices are scoped to their county** (same title, e.g. "County Council District 1", exists in several counties; Circuit Court judges differ by county even within one circuit). Statewide, congressional, senate and delegate contests are shared across counties.
- **Order of work: finish MD, then the DMV, then the public API.**
- **Documentation follows every decision** and the project-direction docs are kept in English and Portuguese (`*.md` and `*.pt-BR.md`).
