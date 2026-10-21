# Roadmap and decisions

Last updated: 2026-10-21. This is the project's current direction; update it whenever a decision is made. Versão em português: [roadmap.pt-BR.md](roadmap.pt-BR.md).

## Direction

1. **Finish Maryland** — close the coverage gaps below.
2. **Finish the DMV** — DC and the rest of Northern Virginia.
3. **Public API** — see [public-api-plan.md](public-api-plan.md). Starts only after the DMV is complete.

## Where we are (2026-10-21)

| Area | 2026 general ballot | Notes |
|---|---|---|
| Maryland (24 jurisdictions) | **Loaded**: 1,991 styles on 1,975 of 2,040 precincts | The 65 without a ballot: 34 zero-voter placeholders (-09x/-999) and 31 stale polygons (below). Primary + results only for Montgomery precinct 008-006 |
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
- **Stale polygons** — the state layer is built from county files of 2025, older than some 2026 precinct changes:
  - **Anne Arundel 04-025** (new precinct, no polygon anywhere — the county's own layer also predates it): its voters fall into a neighbor's polygon whose ballot has a **different congressional/senate district**. Mitigated 2026-10-21: `sample-ballot` now flags such ballots (`district_mismatches`) and the UI points to the official voter lookup. A real fix still needs the precinct's polygon.
  - **Calvert 03-002** (no polygon) and **31 precincts in 8 counties** that are in the layer but on no ballot (likely consolidated): those addresses get districts only, no ballot.
  - **Worcester 01-003/01-004** (no polygon): harmless, all four 01-00x ballots are identical.
- **Talbot**: 5 split precincts differ only by Board of Education district; with no boundary layer, all possible styles are shown.

### 2. Finish the DMV
- Virginia localities beyond Fairfax and Alexandria: precincts are loaded for all of them; ballots need each locality's sample ballots. The 5 blocked sites (Arlington, Fairfax City, Manassas, Manassas Park, Loudoun) need the PDFs downloaded in a browser; Falls Church has no sample ballot file.
- Virginia calendar: only election day is loaded (registration and early voting deadlines missing).
- DC: confirm the sample ballot source.

### 3. Public API
See [public-api-plan.md](public-api-plan.md).

## Decision log

### 2026-10-21
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
