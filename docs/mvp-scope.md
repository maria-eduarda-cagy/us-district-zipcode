# MVP scope

Last updated: 2026-07-02 (County Council + Board of Education district layers loaded; a real data conflict was found and flagged, not silently resolved — see [dmv-expansion-plan.md](dmv-expansion-plan.md)).

## County Council and Board of Education district layers (2026-07-02)

Loaded both previously-missing Montgomery County layers (`md_montgomery_council_districts`, `md_montgomery_board_of_education_districts`) via `scripts/load_district_layers.py`. County Council checks out cleanly (Ashton = District 7 on the ballot and in the geometry). Board of Education does not: the certified ballot says District 3 for this precinct, but the county's own boundary layer and two other official PDFs all say District 5. Rather than pick a side, that contest is flagged with a new `contests.verification_note` column and shows a visible warning in the UI instead of a district link. Full writeup in [dmv-expansion-plan.md](dmv-expansion-plan.md).

## Multi-party candidates + colored tags (2026-07-02)

Loaded the full Republican ballot (`BS REP 125`, 13 contests) for the same precinct 008-006, via `scripts/load_montgomery_primary_2026_bs_rep_125.py`. Since `contests` was already party-agnostic by design (its unique key doesn't include party), merging Democratic+Republican candidates into the same card happened **with no schema or query change at all** — just loading data into the already-existing `contest_id` rows.

**Independent verification**: the 13 Republican contests were cross-checked coordinate by coordinate (`pdftohtml -xml`, pages 763-764) against the certified PDF, not just trusted from the `friendly.json` — result: 0 discrepancies (unlike the bug found in the Board of Education office).

**Finding that changed the data model**: the 5 Circuit Court Judge candidates (Circuit 6) appear **identically** on both the Democratic and Republican ballots — *cross-filing*, a legal Maryland practice where a judicial candidate runs in both party primaries simultaneously. Fixed: those 5 candidates' `candidates.party` changed from `'Democratic'` to `'Cross-filed'` (they were previously loaded as Democratic-only, which under-represented the situation).

**Frontend**: every candidate now shows a party tag — Democrat (blue `#eaf2fb`/`#2874a6`), Republican (red `#fdecea`/`#c0392b`), Non-Partisan (gray `#ecf0f1`/`#7f8c8d`), and a new fourth tag, "Cross-Filing" (red→blue gradient), for cross-filed judges.

Result for precinct 008-006: `Representative in Congress District 8` shows 4 Dem + 4 Rep on the same card; `Governor / Lieutenant Governor` shows 2 Dem tickets + 9 Rep tickets; `Board of Education` stays shared (no duplication); `Republican Central Committee At-Large/District 14` became 2 new contests (party committees are separate organizations per party, they don't merge with the Democratic one). 10/10 automated tests passing.

## Audit against the full county extraction (2026-07-02)

The user provided their own structured extraction of the full certified PDF (771 ballot styles: 257 Democratic + 257 Republican + 257 Non-Partisan, all 257 precincts in Montgomery County). Cross-check against the database:

- **Real coverage**: 1 of 771 ballot styles loaded (0.13%) — an MVP scope decision, not a bug.
- **Data bug found in the user's extraction**: the "Board of Education" (district, not At-Large) office showed the same 5 candidates and "District 3" across **all 771 ballot styles** — every other district-based office (County Council, State Senator, House of Delegates, Central Committee) had correct diversity across precincts. Isolated specifically to this office. For our precinct 008-006 specifically, we re-verified via `pdftohtml -xml` (exact top/left coordinates, not `pdftotext -layout`) and confirmed that the "District 3" value with those 5 candidates **is correct for this precinct** — the bug affects other precincts in the county, not ours.
- **3 districts identified with no geographic layer**: Montgomery County Council (1-7), Montgomery Board of Education, Judicial Circuit — see [dmv-expansion-plan.md](dmv-expansion-plan.md).
- **Extra finding**: Montgomery County has its own ArcGIS elections service (`gis3.montgomerycountymd.gov/arcgis/rest/services/elections`) with `polling_place` (voting location **per precinct**, `District_P` field) and `drop_boxes` — resolves the "where to vote on election day" gap that was previously documented as having no known source.

**Phase 1 of the remediation plan completed**: the 4 contests missing from precinct 008-006 (Democratic Central Committee At-Large and District 14, Board of Education At-Large and District 3) were loaded, with `nonpartisan=true` and `party=null` for Board of Education candidates (the ballot itself says they have no mandatory party affiliation — we didn't invent one for them). Precinct 008-006 is now at **18/18 real contests**, validated visually in the browser.

## End-to-end validation (task 7, 2026-07-02)

Full run for the test address, with three checks:

1. **Automated cross-check against the certified PDF**: the 50 candidate names returned by the API were compared programmatically (not manually) against the raw text extracted from the official PDF — **0 discrepancies**. The 14 "vote for N" rules also match exactly.
2. **Visual test in the browser** (not just `curl`): found a real bug that the API check missed — the `scope` field (`at_large` vs `district`) was being incorrectly inferred from whether `district_id` was null. Contests like "County Executive" and "County Council At-Large" have `district_id` set (to link to the county's name/geometry) but are at-large offices, not district ones — the old inference inverted this. Fixed with an explicit `scope` column on `contests` (migration `20260702160000_contests_explicit_scope.sql`), read directly instead of inferred. 6 contests were affected; all fixed and re-verified visually.
3. **Negative case** (address outside the MVP, `1600 Pennsylvania Avenue NW, Washington, DC`): geocodes and shows DC's districts normally (real data, loaded in task 2), but the ballot section correctly degrades to "No offices were generated for this address" — without fabricating anything, no console error.

9/9 automated tests passing.

## Decision

The MVP runs end-to-end **only for the test address**:

```
104 Ashton Oaks Court, Ashton, Maryland 20861
```

This is not general MD/DC/VA coverage. Real election data (ballot styles, contests, candidates) only exists for this address. The geography side (districts) has broader but uneven coverage — see details below. Expanding to the whole DMV is future work, described in [dmv-expansion-plan.md](dmv-expansion-plan.md).

## What works today, end-to-end

For the test address, `search` and `sample-ballot` (production Edge Functions) return:

- Real geocoding (Census, ArcGIS fallback)
- All districts: Congressional District 8, State Senate District 14, State Legislative District 14, Montgomery County, Ashton-Sandy Spring CDP, Montgomery County Public Schools, House of Delegates Subdistrict 14, precinct 008-006
- Real, certified ballot styles: **BS DEM 125** and **BS REP 125** (2026-06-23 primary)
- 20 contests (18 shared/Democratic + 2 Republican-only committees) and real candidates from both parties, extracted from the MSBE certified PDF, with party tags in the UI
- **Real polling locations**, ordered by distance (RPC `rpc_nearby_polling_locations`): Montgomery County's 14 official early voting centers for the 2026 primary, including the one closest to the test address (Sandy Spring VFD, ~1.7km)
- **Real election events**: early voting start/end, election day, and filing deadline, for the primary (certified) and the general (scheduled)

## Coverage by layer (what's DMV-wide vs. only the test address)

| Layer | Real coverage |
|---|---|
| Legacy districts (CD, SLDU, SLDL, county, place, unsd) | All of MD, all of VA, DC — inherited from the original `download_data.py`, predates this work |
| Precincts (MD) | All of MD (2074 precincts, every county) |
| Delegate subdistricts (MD) | All of MD (71 subdistricts) |
| DC (wards, ANC, SMD, SBOE) | All of DC |
| VA (supervisor districts, precincts) | **Only Fairfax and Loudoun County** — missing Arlington, Alexandria, Prince William, Falls Church, Fairfax City, Manassas, Manassas Park |
| **Ballot styles + contests + real candidates** | **Only 1 precinct**: 008-006, Ashton, Montgomery County — **Democratic (18/18) + Republican (13/13)**, with party tags in the frontend |
| Polling locations | **Only Montgomery County early voting** (14 centers, 2026 primary) — per-precinct election-day locations and drop boxes not loaded; VA (Loudoun) and DC not loaded |
| Ballot measures (questions/referendums) | Not loaded yet |
| November 2026 general election | Doesn't exist yet — no certified ballot published (see [election-research-notes.md](election-research-notes.md)) |

## What was deliberately left out (not a bug, a decision)

- **General election (Nov 2026)**: no certified candidates yet — see deadlines in [election-research-notes.md](election-research-notes.md).
- **Non-Partisan ballot (`BS NON 125`) as its own record**: its 2 contests (Board of Education) are already reachable via the Democratic and Republican ballot_styles (shared, `party=null`) — we didn't create a dedicated `ballot_styles` row for it, since it wouldn't add any new candidate.

## Why this doesn't expand automatically

Every new layer (one more VA county, one more party, one more election) requires manually repeating the certified-PDF extraction process (task 3), because there's no structured API for ballot styles/candidates in MD/DC/VA — only PDFs. This is a conscious scope decision, not a hidden technical limitation.
