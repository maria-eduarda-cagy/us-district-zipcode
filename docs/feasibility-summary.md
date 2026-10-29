# Districts and precincts — feasibility summary

2026-10-29. **The ballot can be shown in all 50 states without relying on precincts: address → map point → districts → candidates. With free public data only, this covers 100% of the population at the federal and state levels.** Details, data and full sources: [feasibility-study.md](feasibility-study.md). Versão em português: [feasibility-summary.pt-BR.md](feasibility-summary.pt-BR.md).

## 1. Districts: feasible in all 50 states

**A district is the area that elects an office** (e.g., Maryland's 8th congressional district). It answers "who represents you?".

**Why it's feasible:** the Census publishes districts for every state, free and in a single format ([TIGER/Line](https://www.census.gov/geographies/mapping-files/2027/dec/rdo/120-congressional-district-bef.html)). The [Redistricting Data Hub](https://redistrictingdatahub.org/state/national/) also publishes the 2026 national maps.

| Level | Districts needed | Feasibility with public data |
|---|---|---|
| Federal | State and congressional district | 100% |
| State | State House and Senate districts | ~100% |
| Local | County, municipality, school district | 100% |

**The only risk is redistricting.** [9 states switched congressional maps for 2026](https://en.wikipedia.org/wiki/2025%E2%80%932026_United_States_redistricting), some about 5 months before the election. National sources take 3 to 13 months to reflect a new map. So new maps should be read straight from the state's source, with an automatic change alert.

## 2. Precincts: the bottleneck

**A precinct is the smallest unit of an election**, similar to Brazil's electoral zone/section. It sets where a person votes and which ballot they get. A district contains many precincts.

**Why it's a problem:**

- They're drawn by [6,461 local election offices](https://www.eac.gov/sites/default/files/2026-07/2024_EAVS_Data_Brief_US.pdf), each in its own format.
- They change before many elections, with no calendar and no news coverage (e.g., Howard County, MD, went from 118 to 67 precincts in 2026).
- There's no current national base: the latest open one is from 2020; 2022–2024 are paid.
- [17 of 51 don't publish precincts](https://redistrictingdatahub.org/resources/precinct-level-data-sources/) at the state level; it's county by county.

| Precinct situation | States | % of US population |
|---|---|---|
| Statewide source (public) | 34 | 72% (65% free) |
| County by county | 17 | 28% |

New York, Pennsylvania, Ohio, Arizona and Missouri alone account for 18% of the US in that hard group.

## 3. The solution: ballot by map point

**Instead of finding the precinct, the app finds the address's districts and builds the ballot from them.** It's [Ballotpedia's](https://ballotpedia.org/Sample_Ballot_Frequently_Asked_Questions) method, and the project already has the pieces.

1. **Address → point:** geocoding.
2. **Point → districts:** point-in-polygon in PostGIS.
3. **Districts → candidates:** the official list for each contest.
4. **No map for a local district:** show every contest of that type in the county, with a warning.

| Level | Through precincts | By map point |
|---|---|---|
| Federal (what Voting Buddy uses today) | Not needed | 100% |
| State | Not needed | ~100% |
| Local | 72% | 100%, but less precise where maps are missing (county fallback) |

**Where precincts are still needed:** to show the polling place, for ballot styles with no public map, and to check addresses near boundaries (in Fairfax, the Census boundary differs from precincts by up to ~14% of the area).

**This is the chosen path.** Without precincts, the change alert only needs to watch district maps (about 50 state sources, plus the Census) instead of thousands of counties. The precincts already loaded for Maryland and Virginia are now used only to validate the method.

## 4. What it costs

**At the federal and state levels, nothing: the maps are public and free.** Paying only makes sense to outsource a part.

| Paid option | What it solves | Price |
|---|---|---|
| [Geocodio](https://geocod.io/pay-as-you-go-geocoding) | Federal and state districts by address | 2,500 lookups/day free; then US$1 per 1,000 |
| [Cicero](https://www.cicerodata.com/pricing/) | Districts, including local | From US$298 for 5,000 addresses |
| [Ballotpedia](https://www.ballotpedia.org/Ballotpedia:Buy_Political_Data) | Candidates by map point | From US$500; exact price on request |

Ballotpedia uses the same method with public data. What it sells is the work of collecting candidate lists, which is the real cost at the local level.

## 5. Conclusion and next steps

**Go by districts, not precincts.** Federal (what Voting Buddy needs today) is 100% feasible in all 50 states with public data only. Precincts are left for the polling place and the local level later.

1. **Launch federal in all 50 states** with the map-point method.
2. **Read new maps from the state's source**, with an automatic redistricting alert.
3. **Run the Maryland ground-truth check**, which measures the error near boundaries.
4. **Leave state and local for later**; locally, get a quote from Ballotpedia for candidate lists.

To watch: Maryland's amendment is on the 2026-11-03 ballot and could bring a new congressional map in 2028.

## Main sources

- [Census, 120th Congress Block Equivalency Files](https://www.census.gov/geographies/mapping-files/2027/dec/rdo/120-congressional-district-bef.html)
- [Redistricting Data Hub, national data](https://redistrictingdatahub.org/state/national/) and [precinct sources by state](https://redistrictingdatahub.org/resources/precinct-level-data-sources/)
- [Wikipedia, 2025–2026 redistricting](https://en.wikipedia.org/wiki/2025%E2%80%932026_United_States_redistricting)
- [EAC, EAVS 2024](https://www.eac.gov/sites/default/files/2026-07/2024_EAVS_Data_Brief_US.pdf)
- [Ballotpedia, how the sample ballot works](https://ballotpedia.org/Sample_Ballot_Frequently_Asked_Questions)
- [2020 Census, population by state](https://planning.maryland.gov/MSDC/Documents/Census/Census2020/resident-population.pdf)

The full list is in the technical study.
