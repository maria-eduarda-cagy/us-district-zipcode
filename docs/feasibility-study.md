# Feasibility study: districts and precincts across the US

Researched 2026-10-29. Question: does the project scale to every state, and how do we keep the data current, before the Voting Buddy integration? Versão em português: [feasibility-study.pt-BR.md](feasibility-study.pt-BR.md).

## Summary

**Districts are feasible nationwide; precincts only partly. For what Voting Buddy shows today (federal candidates), only districts are needed.**

The report has two parts: **Part 1 — Districts** and **Part 2 — Precincts**, each assessed at the federal, state and local levels.

| Level | Districts (Part 1) | Precincts (Part 2) |
|---|---|---|
| Federal | 100% feasible, high confidence. Free public data only | Not needed |
| State | ~100% feasible, high confidence. Free public data only | Not needed, apart from a few exceptions |
| Local | Partial: county, city and school district in 100% of states; other local districts not measured | Needed: 72% of the population with public data (65% free), medium confidence; 28% county by county |

- **Redistricting:** 9 states switched congressional maps for 2026. National sources take 3 to 13 months to reflect a new map; the state's own source publishes immediately.
- **Private data:** districts by address are cheap (Geocodio, Cicero). Ballot by address, with no precincts, is quote-based (Ballotpedia from US$500).
- **In the project today:** districts for MD, VA and DC (4.7% of the US population); Maryland precincts and ballots covering 99.45% of registered voters.
- **Out of scope:** state and local candidate lists.

**Main suggestion:** show the ballot by map point (address → districts → candidates), without precincts. With public data, this covers 100% of the population at the federal and state levels, and 100% locally using the county as a fallback (see Part 2).

Definitions: **coverage** = the share of the population (or voters) the project serves. **Feasibility** = the share of the population where the feature can be built and maintained with free public data. Neither measures **accuracy**: only the Maryland ground-truth check will.

Sources: [2020 Census population by state](https://planning.maryland.gov/MSDC/Documents/Census/Census2020/resident-population.pdf); Maryland coverage from the [roadmap](roadmap.md) (`ballot_coverage` view, 2026-10-28).

## What a district is and what a precinct is

**For the federal candidates Voting Buddy shows today, precincts aren't needed: the congressional district is enough.** Precincts only matter once the app shows the full ballot, the polling place or local races.

**What a precinct is:** the smallest unit of election administration in the US. It's a small area, usually a neighborhood or part of one, where every voter:

- **votes at the same place** (the same polling location);
- **gets the same ballot** (the same offices and candidates);
- **has their votes counted together** (results are reported "by precinct").

It's similar to Brazil's electoral zone/section: the address sets the section, and the section sets the polling place. Example: Howard County, Maryland, has 67 precincts, and every address falls in exactly one of them.

A **district** answers "who represents you?". A **precinct** answers "where do you vote and which ballot do you get?". A district contains many precincts.

| | District | Precinct |
|---|---|---|
| What it is | An area that elects an office (e.g., the 8th congressional district) | An administrative election area, similar to Brazil's electoral zone/section |
| What it's for | Political representation: who represents you | Logistics: where a person votes, which ballot they get, how votes are counted |
| Who draws it | State legislature, commission or court | The local election office |
| When it changes | At redistricting (rare) | Before any election, for practical reasons |
| How they relate | A district contains many precincts | Each precinct sits inside one district of each type, or is split |

## How often each one changes

Redistricting is rare but no longer predictable. Precincts change far more often and are the real bottleneck: there is no current national file for them.

| Layer | Who decides | How often it changes | Current national source? |
|---|---|---|---|
| Congressional districts | State legislature, commission, court or referendum | Every 10 years (Census) and now mid-decade: 9 states switched maps for 2026 | Yes, with lag: Census (120th Congress) and Redistricting Data Hub |
| State legislative districts | Same | Every 10 years, plus exceptions (Alabama also changed its state Senate in 2026) | Yes: RDH national 2026 file (2026-09-16) |
| County, city, school district | Local governments | Rarely, through annexations | Yes: TIGER/Line, annual |
| Precincts | County or municipality | Before many elections, no national calendar (e.g., Howard County, MD, 118 → 67 in 2026) | No: the latest open national file is from 2020; 2022–2024 are paid |

Consequence: districts can cover the whole US from national sources. Precincts (and therefore ballots) must be sourced state by state, sometimes county by county.

# Part 1 — Districts

**Districts are feasible in all 50 states at the federal and state levels, with free public data only.** Locally, the Census covers the basic layers; the rest depends on each county or city.

## District feasibility by level

| Level | What the address must resolve | Public source | Feasibility | Confidence | Maintenance |
|---|---|---|---|---|---|
| Federal | State (President and Senate) and congressional district (House) | Census (120th Congress), Redistricting Data Hub, state source for new maps | 100% | High | Watch for redistricting: 9 states changed for 2026 |
| State | State House and Senate districts | Census (legislative layers), Redistricting Data Hub (2026 file) | ~100% (DC has no legislature) | High | Same pace as congressional; Alabama changed its state Senate in 2026 |
| Local | County, city and school district; plus councils, wards, judges and special districts | Census covers county, city and school district; the rest only from the county or city | Basic layers: 100%. Others: not measured | Low | One source per county or city |

- **In the project today:** districts for MD, VA and DC, 4.7% of the US population.
- **Paid alternative:** Geocodio (federal and state; 2,500 lookups/day free, then US$1 per 1,000) and Cicero (includes local districts; from US$298 for 5,000 addresses). Details in "Private data and prices", Part 2.
- **Rule of thumb:** read new maps straight from the state's source. The Census and aggregators lag by months (see below).

## National sources

| Source | What it offers | Cost and license | Format | Currency |
|---|---|---|---|---|
| Census TIGER/Line | Congressional and legislative districts, counties, places, school districts | Free, public domain | Shapefile, GeoPackage, ArcGIS API (TIGERweb) | Annual. The 120th Congress already includes the 9 states with new maps (page revised 2026-10-07) |
| Redistricting Data Hub (RDH) | Current congressional and legislative plans with block assignment files; 2020 national precincts | Free with an account; API only for approved users; terms to be checked | Shapefile, CSV | 120th Congress and 2026 legislative plans published 2026-09-16 |
| VEST / UF Election Lab | Precinct boundaries with election results | 2016–2020 free (CC BY-NC-ND: non-commercial); 2022–2024 by subscription | GIS files | Historical; useful for validation, not for the current election |
| Google Civic Information API | `divisionByAddress` (address → OCD-IDs), elections | Free with a key | JSON API | The representatives endpoint was turned down in April 2025 |
| Voting Information Project | Polling places and ballot info approved by election offices | Free for states; accessed through Google's API; no open download | API | 40+ states and DC participate |
| Cicero (Melissa) | Districts by address and elected officials | Paid, credit-based | API | Claims real-time tracking of changes |

License note: Voting Buddy is commercial, so CC BY-NC-ND data (VEST) can't be used in the product without permission. Open question: BallotReady and L2 pricing was not researched.

## Mid-decade redistricting (2025–2026)

Between August 2025 and June 2026, 9 states adopted a new congressional map for 2026 (the Census list). Some maps changed about 5 months before the election, so monitoring must be continuous, not just after the Census.

| Date | State | How | In effect for 2026? |
|---|---|---|---|
| 2026-08-04 | Maryland | Constitutional amendment passed; goes to voters in November. No new map | No (opens the way to a new map in 2028) |
| 2026-06-02 | Alabama | Supreme Court allowed the legislature's 2023 map | Yes |
| 2026-05-29 | Louisiana | Legislature, after Louisiana v. Callais; primary moved to Nov 3 | Yes |
| 2026-05-07 | Tennessee | Legislature | Yes |
| 2026-05-04 | Florida | Legislature | Yes |
| 2026-04-21 | Virginia | Referendum, struck down by the state Supreme Court on 2026-05-08 | No (2021 map applies) |
| 2025-11-10 | Utah | State court | Yes |
| 2025-11-04 | California | Referendum (Proposition 50) | Yes |
| 2025-10-31 | Ohio | Redistricting commission | Yes |
| 2025-10-22 | North Carolina | Legislature | Yes |
| 2025-09-28 | Missouri | Legislature; blocked in court | No (old map applies) |
| 2025-08-29 | Texas | Legislature | Yes |

Time until it becomes public data:

- **State source:** the file comes out with the proposal, before enactment. In Texas, plans are on the Capitol Data Portal with a shapefile and block equivalency file. But each state publishes differently: one commission released only a block table and a PDF.
- **National sources:** 3 to 13 months later. RDH published the 120th Congress on 2026-09-16 (3.5 months after Alabama, 12.5 after Texas). The Census revised its file on 2026-10-07; the date each state entered the Census file is not published.
- **Public and free** in every case checked. No map had to be paid for.

Consequence: to be right on election day, the project has to read the state's own source, not wait for the Census.

# Part 2 — Precincts

**Precincts are only needed at the local level.** There, 72% of the population can be covered with public data; the other 28% need county-by-county work or a paid ballot API.

## Precinct feasibility by level

| Level | Precinct needed? | Why | Feasibility | Confidence |
|---|---|---|---|---|
| Federal | No | Candidates come from the congressional district. A precinct would only matter to show the polling place | Not applicable | — |
| State | No, in most cases | Candidates come from the legislative districts. Exception: state-level districts with no public layer (e.g., Board of Education in Talbot, MD) | Not applicable, apart from exceptions | — |
| Local | Yes | The local ballot and the polling place are set by precinct | 72% of the population with public data (65% free); 28% county by county | Medium |

- **In the project today:** Maryland covering 99.45% of registered voters; in Virginia, ballots in Fairfax, Alexandria and Prince William.
- **Paid alternative:** ballot-by-address APIs (BallotReady, Ballotpedia, Democracy Works) skip precincts. Price on request; details in "Private data and prices".

## Suggestion: ballot by map point, without precincts

**It's a good way to avoid precincts, and it's what Ballotpedia does.** With public data, it covers 100% of the population at the federal and state levels. Locally, it covers county, municipal and school district offices, and falls back to the whole county for the rest.

How it works:

1. **Address → point:** geocoding (Census, with ArcGIS as fallback; already in the project).
2. **Point → districts:** point-in-polygon in PostGIS, with Census and state layers.
3. **Districts → contests and candidates:** FEC for federal, always confirmed against the state's official list.
4. **No map for a local district:** show every contest of that type in the county, with a warning (what [Ballotpedia does](https://ballotpedia.org/Sample_Ballot_Frequently_Asked_Questions)).

| Level | Feasibility with public data | Precision | Confidence |
|---|---|---|---|
| Federal | 100% of the population | High, except addresses near boundaries | High |
| State | ~100% (DC, 0.2% of the population, has no state legislature) | High, except addresses near boundaries | High |
| Local: county, municipality, school district | 100% (Census layers) | High | Medium |
| Local: councils, wards, judges, special districts | With a map: not measured. With the county fallback: 100% | Low in the fallback (shows extra contests) | Low |

Compared: through precincts, the local level reaches 72% of the population with public data. By point, it reaches 100% coverage, but with less precision where maps are missing.

**Where precincts still win:**

- **Addresses near boundaries:** geocoding or the Census layer can put them on the wrong side. In Fairfax, the Census congressional boundary differs from the precinct polygons by up to ~14% of the area.
- **Exact ballot:** some ballot styles depend on districts with no public layer (e.g., Board of Education in Talbot, MD).
- **Polling place:** depends on the precinct, or on a third-party API.
- **Candidates:** the map doesn't solve the candidate list, which is still the heavy work.

Recommendation: use the point method by default, and precincts only where they're indispensable (polling place and ballot styles with no public layer). The Maryland ground-truth check measures the error near boundaries.

## Why precincts are harder to track

- They're drawn by thousands of local offices: there were [6,461 election jurisdictions in 2024](https://www.eac.gov/sites/default/files/2026-07/2024_EAVS_Data_Brief_US.pdf), each with its own format.
- They change for practical reasons (a new polling place, population growth, a new district), with no calendar and no news coverage.
- Not every county publishes its map in a GIS format. Some only have a PDF or an on-screen map.
- The only official national base (Census VTDs) is updated every 10 years. The 2020 one is already outdated.

## Survey of all 50 states + DC

**34 of 51 have some statewide precinct source; 17 don't, which means county by county.** The base is the [Redistricting Data Hub's precinct data sources table](https://redistrictingdatahub.org/resources/precinct-level-data-sources/) (updated 2026-05-05), cross-checked with what this study verified.

Group criteria:

- **Group 1:** official statewide file, currency confirmed in this study.
- **Group 2:** a statewide file exists (online or on request), but it is outdated, incomplete, or its currency hasn't been confirmed yet. Some of this group should move to group 1 once checked.
- **Group 3:** the state doesn't publish. Precincts have to come from each county.

### Northeast

| State | Precinct source | Group | Note |
|---|---|---|---|
| Connecticut | Not published by the state | 3 | County by county |
| Maine | Not published by the state | 3 | County by county |
| Massachusetts | [MassGIS, wards and precincts](https://www.mass.gov/info-details/massgis-data-2022-wards-and-precincts) | 2 | 2022 version |
| New Hampshire | [NH GRANIT, voting wards](https://www.nhgeodata.unh.edu/datasets/NHGRANIT::new-hampshire-political-districts-voting-wards/about) | 2 | Currency to confirm |
| New Jersey | [NJOGIS, voting districts](https://njogis-newjersey.opendata.arcgis.com/search?q=voting%20districts) | 2 | Currency to confirm |
| New York | Not published by the state | 3 | County by county; 20.2 million people |
| Pennsylvania | Not published by the state | 3 | 67 counties |
| Rhode Island | [RIGIS, 2022 precincts](https://www.rigis.org/datasets/edc::voting-precincts-2022/about) | 2 | 2022 version |
| Vermont | [VCGI, vote tabulation areas](https://vcgi.vermont.gov/data-release/vt-house-and-senate-vote-tabulation-areas-municipal-voting-districts-available) | 2 | Currency to confirm |

### Midwest

| State | Precinct source | Group | Note |
|---|---|---|---|
| North Dakota | [Secretary of State](https://www.sos.nd.gov/elections/election-resources) | 2 | Currency to confirm |
| South Dakota | Not published by the state | 3 | County by county |
| Illinois | [State Board of Elections, precinct maps](https://www.elections.il.gov/precinctmaps/) | 2 | Currency and format to confirm |
| Indiana | [IndianaMap, 2023](https://indianamap-inmap.hub.arcgis.com/datasets/INMap::voting-district-boundaries-2023/about) | 2 | 2023 version |
| Iowa | [Secretary of State](https://sos.iowa.gov/precinct-and-district-shapefiles) | 2 | 2022 precinct plans, 2020 Census base |
| Kansas | Not published by the state | 3 | County by county |
| Michigan | [Michigan GIS, 2022 precincts](https://gis-michigan.opendata.arcgis.com/datasets/2022-voting-precincts/explore) | 2 | 2022 version |
| Minnesota | [Secretary of State](https://sos.mn.gov/election-administration-campaigns/data-maps/voting-precincts/) | 2 | Currency to confirm |
| Missouri | Not published by the state | 3 | County by county |
| Nebraska | Not published by the state | 3 | County by county |
| Ohio | Not published by the state | 3 | 88 counties |
| Wisconsin | [LTSB](https://gis-ltsb.hub.arcgis.com/pages/download-data) | 1 | Spring 2026 version |

### South

| State | Precinct source | Group | Note |
|---|---|---|---|
| Alabama | Not published by the state | 3 | County by county |
| Arkansas | [Arkansas GIS Office](http://gis.arkansas.gov/product/election-precincts/) | 2 | Currency to confirm |
| North Carolina | [NCSBE](https://dl.ncsbe.gov/?prefix=PrecinctMaps/) | 1 | Folder with current and past versions |
| South Carolina | County maps on request from the state, free | 2 | No direct download |
| Delaware | [FirstMap, election districts](https://de-firstmap-delaware.hub.arcgis.com/datasets/delaware::election-districts-1/explore) | 2 | Currency to confirm |
| District of Columbia | [Open Data DC, precincts](https://opendata.dc.gov/datasets/voting-precinct-2002/explore) | 2 | Link vintage to confirm |
| Florida | County maps on request from the state, for a fee | 2 | No direct download; 21.5 million people |
| Georgia | [Office of Reapportionment](https://www.legis.ga.gov/joint-office/reapportionment) | 2 | Good for 105 of 159 counties |
| Kentucky | Not published by the state | 3 | County by county |
| Louisiana | [Legislature, 2020 shapefiles](https://redist.legis.la.gov/default_ShapeFiles2020) | 2 | 2020 base; congressional map changed in 2026 |
| Maryland | [iMAP](https://data.imap.maryland.gov/datasets/e2d183719fe345c8abfffc9cc4196390_2/explore) | 2 | Most counties from 2025 (already loaded in the project) |
| Mississippi | Not published by the state | 3 | County by county |
| Oklahoma | [OU, precincts](https://csagis-uok.opendata.arcgis.com/datasets/8c2c841e2eb54007bd1872c4274d6e07_0/explore) | 2 | Published by a university; currency to confirm |
| Tennessee | [TNMap, voting districts](https://hub.arcgis.com/datasets/tnmap::tn-voting-districts/about) | 2 | Currency to confirm |
| Texas | [Texas Legislative Council](https://data.capitol.texas.gov/dataset/precincts) | 2 | 2024 VTDs (updated 2025-01-29) |
| Virginia | [Department of Elections](https://www.elections.virginia.gov/casting-a-ballot/redistricting/gis/) | 1 | By locality, same format (already loaded in the project) |
| West Virginia | [WVGIS Clearinghouse](https://data.wvgis.wvu.edu/pub/Clearinghouse/Boundaries/) | 2 | Currency to confirm |

### West

| State | Precinct source | Group | Note |
|---|---|---|---|
| Alaska | [State of Alaska, precincts](https://dcra-cdo-dcced.opendata.arcgis.com/datasets/precincts/about) | 2 | Currency to confirm |
| Arizona | Not published by the state | 3 | County by county |
| California | [Statewide Database](https://statewidedatabase.org/election.html) | 2 | Published after each election; before it, only from the 58 counties |
| Colorado | Not published by the state | 3 | County by county |
| Hawaii | [State ArcGIS](https://www.arcgis.com/home/item.html?id=37f83ac7f930421b97976956cccbd840) | 2 | Currency to confirm |
| Idaho | Not published by the state | 3 | County by county |
| Montana | [State Library](https://mslservices.mt.gov/geographic_information/data/datalist/datalist_Details.aspx?did=%7Bb5296489-2764-4a09-9fec-1b0c3c74690c%7D) | 2 | Currency to confirm |
| Nevada | [Secretary of State, county maps](https://www.nvsos.gov/sos/elections/county-precinct-maps) | 2 | Per-county format to confirm |
| New Mexico | [RGIS (UNM)](https://rgis.unm.edu/rgis6/) | 2 | Published by a university; currency to confirm |
| Oregon | Not published by the state | 3 | County by county |
| Utah | [UGRC, VISTA ballot areas](https://opendata.gis.utah.gov/datasets/utah-vista-ballot-areas/about) | 2 | From the state's election system; strong group 1 candidate |
| Washington | [Secretary of State](https://www.sos.wa.gov/elections/data-research/election-results-and-voters-pamphlets) | 2 | Currency to confirm |
| Wyoming | Not published by the state | 3 | County by county |

## National precinct result

**With all 51 assessed, precinct feasibility is 72% of the US population** (groups 1 and 2). The other 28% live in 17 states with no statewide source.

| Group | States | Population (2020 Census) | % of US |
|---|---|---|---|
| 1 — official and current | 3 | 25.0 million | 7.5% |
| 2 — statewide file | 29 | 185.8 million | 56.1% |
| 2 — on request (FL, SC) | 2 | 26.7 million | 8.0% |
| 3 — county by county | 17 | 94.0 million | 28.4% |

- **Most of the cost sits in 5 states:** New York, Pennsylvania, Ohio, Arizona and Missouri total 58 million people (18% of the US), nearly two-thirds of group 3.
- **The uncertainty is now in group 2:** 19 of those states still have currency to confirm. Checking each source is the next step to move states into group 1.
- **It matches the source:** RDH says about two-thirds of states publish precincts; here it came to 34 of 51 (67%).

**The 72% uses public, government data only.** Florida comes with a small fee charged by the state. With free public data only, feasibility is 65%. No private-company data was counted (see "Private data and prices").

Calculation: each state's population from the [2020 Census](https://planning.maryland.gov/MSDC/Documents/Census/Census2020/resident-population.pdf), summed by group.

## Private data and prices

**No vendor sells "current precincts for all 50 states" at a public price.** What exists are APIs that solve the problem another way: address → districts (public, cheap pricing) or address → full ballot (price on request). Both skip precincts.

| Vendor | What it solves | Precincts? | Price |
|---|---|---|---|
| [Geocodio](https://geocod.io/pay-as-you-go-geocoding) | Congressional and legislative districts by address | No | 2,500 lookups/day free; then US$1 per 1,000. Each district append counts as one extra lookup |
| [Cicero (Melissa)](https://www.cicerodata.com/pricing/) | Districts (including local) and officials by address | No | From US$298 for 5,000 addresses to US$8,848 for 1 million (US$0.06 to 0.009 each); 1,000 free to test; about 10% off for nonprofits |
| [Ballotpedia](https://www.ballotpedia.org/Ballotpedia:Buy_Political_Data) | Elections and candidates by point (lat/long): federal, statewide, legislative and the top 100 cities; local in 32 states | No (resolves by point) | Packages from US$500; exact price on request |
| [BallotReady](https://organizations.ballotready.org/ballotready-api) | Every candidate on the ballot, positions, polling places, district polygons down to the local level | Not stated | On request (demo) |
| [Democracy Works](https://www.democracy.works/elections-api) | Dates, polling places and ballot (contests and candidates) in jurisdictions over 5,000 residents | Not stated | On request; it's a nonprofit |
| [UF Election Lab (VEST)](https://election.lab.ufl.edu/paid-datasets) | Precinct boundaries with results, 2022–2024 | Yes, historical | On request |
| L2 | Voter file with each voter's precinct; RDH has used it to [estimate each block's precinct](https://redistrictingdatahub.org/wp-content/uploads/2023/06/readme_al_20230403_vf_precs.txt) | Indirect | On request. Market reference (not L2's price): [US$2,000–15,000 per state, US$5,000–50,000+ per year](https://www.vottiv.com/blog/voter-database-pricing) |

**How much of the 28% this solves:**

- **Current precinct polygons:** no paid option solves it cleanly. VEST and L2 cover the 17 group 3 states, but with historical or estimated data that would also need maintenance.
- **Ballot by address:** BallotReady, Ballotpedia and Democracy Works cover federal and state nationwide. Local depth varies (Ballotpedia: 32 states; Democracy Works: jurisdictions over 5,000 residents).
- **Conclusion:** with private data, the ballot feature can get close to 100% at federal and state levels without touching precincts. The cost can't be pinned down without requesting quotes from those three.

**For Voting Buddy's budget:** the federal level is already free with public data, and Geocodio covers about 1,250 addresses a day at no cost. Paying only makes sense at the local level, and the first step there is a quote from Ballotpedia (the only one with a published starting price).

Open question: voter files sold by the states themselves also include each voter's precinct, but price and usage rules vary by state and weren't researched.

# Common to both parts

## Alert system (districts and precincts)

Two layers feed a single alert, and neither changes data on its own:

```
Official sources ─► File check (modified date, hash) ──┐
                                                        ├─► Alert (issue / email) ─► Human review ─► Loader + validation ─► Updated data
News and courts ──► AI triage ─────────────────────────┘
```

The file check is the primary detector, because precinct changes almost never make the news. AI covers redistricting, which shows up in the news before the official file changes.

| Source type | Change signal | Example |
|---|---|---|
| CKAN portal | Dataset `metadata_modified` field | Texas Capitol Data Portal |
| ArcGIS portal | Last edit date when the service exposes it; otherwise a file hash | Wisconsin wards |
| File folder | New file or changed date in the listing | NCSBE (`dl.ncsbe.gov`) |
| HTML page | Content hash or revision date | Census 120th Congress page |
| News and trackers | New text, read by the AI | Ballotpedia, NCSL |

Where AI fits:

- **Input:** pages and news published since the last check.
- **Structured output:** state, layer (congressional, legislative, precinct), type (map enacted, court ruling, referendum), date and source link.
- **Rule:** AI only opens the alert. Reloading is a human decision, because AI can be wrong or miss things.

Minimal version to start: a list of sources in the repo ([references.md](references.md) already has the URLs), a daily GitHub Actions job comparing dates and hashes, and one issue per change. AI comes in once that base works.

### With precincts vs without precincts

**The chosen path is without precincts.** Since precinct feasibility is lower (72% of the population locally, versus 100% with the map-point method), the alert system only watches district maps. That makes it much simpler.

| | With precincts | Without precincts (chosen path) |
|---|---|---|
| What to watch | District and precinct maps | District maps only |
| How many sources | 34 statewide files plus the counties of the 17 states with no statewide source | About 50 state sources, plus the Census and Redistricting Data Hub |
| How often it changes | Before many elections | Rarely: only at redistricting |
| Main detector | File check, because precinct changes almost never make the news | AI triage, because redistricting always makes the news; the file check confirms |

**What is still tracked on the path without precincts:**

- **District maps** (congressional and legislative), straight from each state's source.
- **Candidate lists:** they change until certification (withdrawals, replacements). This becomes the heaviest part of the work.

**The precincts already loaded (Maryland and Virginia) become a validation tool:** they're used to check whether the map-point method gets addresses near boundaries right. They no longer need to be kept current for the product to work.

## Recommendation and next steps

**Part 1 — Districts:**

1. **Launch the federal level for all 50 states** with public data; the state level follows right after, from the same sources.
2. **Read new maps straight from the state's source**, without waiting for the Census.
3. **Build the minimal alert system** (daily job + GitHub issue) for redistricting.
4. **Run the Maryland ground-truth check** and publish the hit rate.

**Part 2 — Precincts:**

1. **Use the ballot-by-map-point method by default; only invest in precincts for polling places and ballot styles with no public layer.**
2. **Confirm the currency of the 19 group 2 sources** marked "to confirm".
3. **Request a quote from Ballotpedia** and compare it with BallotReady and Democracy Works, as an alternative for the 28% with no statewide source.
4. **Check licenses** before using data in the product: Redistricting Data Hub terms and any CC BY-NC data.

To watch now:

- **Maryland:** the constitutional amendment is on the 2026-11-03 ballot. If it passes, a new congressional map could come in 2028, and the project will need to replace the 2022 layer.
- **Missouri:** the new map was blocked for 2026, but the fight may return for 2028.

# Short conclusion

**Go by districts, not precincts.** Short version of this study: [feasibility-summary.md](feasibility-summary.md).

- **Districts:** 100% feasible at the federal level and ~100% at the state level, with free public data only. The risk is redistricting (9 states in 2026), handled by reading the state's source with an automatic alert.
- **Precincts:** 72% of the population has a public statewide source (65% free); 28% needs county-by-county work. That's why they're the bottleneck.
- **Solution:** ballot by map point (address → districts → candidates). It covers 100% at the federal and state levels, and 100% locally using the county as a fallback, with less precision.
- **Precincts remain necessary** only for polling places, ballot styles with no public map, and addresses near boundaries.
- **Cost:** zero at the federal and state levels. Locally, the real cost is candidate lists (Ballotpedia from US$500).
- **Next step:** federal in all 50 states with the map-point method, and the Maryland ground-truth check to measure the error near boundaries.

## Sources

- [Wikipedia, 2025–2026 United States redistricting](https://en.wikipedia.org/wiki/2025%E2%80%932026_United_States_redistricting)
- [NCSL, Changing the Maps: Tracking Mid-Decade Redistricting](https://www.ncsl.org/redistricting-and-census/changing-the-maps-tracking-mid-decade-redistricting)
- [WYPR, Maryland redistricting amendment (2026-08-04)](https://www.wypr.org/wypr-news/2026-08-04/maryland-lawmakers-pass-redistricting-constitutional-amendment-voters-will-have-final-say)
- [Census, 120th Congress Block Equivalency Files](https://www.census.gov/geographies/mapping-files/2027/dec/rdo/120-congressional-district-bef.html)
- [TIGERweb, 120th Congressional Districts layer](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/54)
- [Redistricting Data Hub, national data](https://redistrictingdatahub.org/state/national/) and [about RDH](https://redistrictingdatahub.org/about/)
- [UF Election Lab / VEST, precinct data](https://election.lab.ufl.edu/precinct-data/)
- [Google, Representatives API turndown](https://groups.google.com/g/google-civicinfo-api/c/9fwFn-dhktA/m/ftUoL83mAwAJ)
- [Democracy Works, Voting Information Project](https://www.democracy.works/voting-info-project)
- [SD Times, Cicero API](https://sdtimes.com/data/melissas-cicero-api-accurate-address-matching-for-legislative-districts-and-officeholders/)
- [revaddress, 2026 redistricting files](https://revaddress.com/blog/2026-redistricting-address-files/)
- [Texas Capitol Data Portal, PLANC2323](https://data.capitol.texas.gov/dataset/planc2323) and [VTDs](https://data.capitol.texas.gov/dataset/vtds)
- [NCSBE, Voting Maps/Redistricting](https://www.ncsbe.gov/results-data/voting-maps-redistricting)
- [LTSB, WI Municipal Wards](https://gis-ltsb.hub.arcgis.com/maps/2cfddfff49474fda9c81955bede7f0bd)
- [Statewide Database, 2024 general](https://statewidedatabase.org/d20/g24_geo_conv.html)
- RDH readmes: [Ohio 2024](https://redistrictingdatahub.org/wp-content/uploads/2025/05/readme_oh_2024_gen_prec.txt), [Georgia 2024](https://redistrictingdatahub.org/wp-content/uploads/2025/07/readme_ga_2024_gen_pber.txt), [North Carolina](https://redistrictingdatahub.org/state/north-carolina/)
