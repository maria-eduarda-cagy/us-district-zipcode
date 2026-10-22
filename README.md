# ElectorMap & Downballot Finder (DMV + 2026 cycle)

English version. Versão em português: [README.pt-BR.md](README.pt-BR.md).

Type an address in DC, Maryland or Virginia and get its districts, its **real certified ballot** for the November 3, 2026 general election (contests, candidates, ballot questions with official explanations), nearby early voting centers and the election calendar. Ballots come from official sources (state and county sample ballots), are validated against official candidate lists, and are never fabricated: where we don't have a ballot, the app says so.

Current direction, coverage and every decision: [docs/roadmap.md](docs/roadmap.md) ([pt-BR](docs/roadmap.pt-BR.md)).

## Features
- **Geocoding**: Census geocoder, ArcGIS fallback.
- **Districts (point-in-polygon)**: PostGIS on Supabase — congressional, state legislative, county, city/town, school district, precinct, delegate subdistricts, DC wards/ANC/SMD, VA supervisor districts.
- **Ballot by precinct**: the address's precinct → its ballot style(s) → contests, candidates (party, ballot order) and questions. Split precincts (a precinct with several ballot styles, e.g. part of it inside a town) are resolved from the address's districts; when nothing can tell them apart, every possible ballot is shown.
- **Honest gaps**: a coverage notice when there's no ballot, a warning when the ballot's districts don't contain the address (precinct maps older than the election), and a note when a ballot is inferred.
- **Ballot questions**: question text, the FOR/AGAINST explanation printed on the ballot (Maryland) or the official explanation published separately (Virginia amendments, county bonds), with its source.
- **Primary results** (2026 Maryland primary, one test precinct), **early voting centers** (all of Maryland), **election calendar**, and **data freshness** (every source with its date).
- **Interactive map** (Leaflet.js).

## Coverage (2026 general election)

| Area | Ballots |
|---|---|
| Maryland (24 jurisdictions) | 1,988 of 2,040 precincts. The rest: 34 zero-voter "ghost" precincts and 18 polygons of precincts that no longer exist (the state's map predates 2026 changes) |
| Fairfax County, VA | All 266 precincts |
| Alexandria, VA | All 32 precincts |
| Prince William County, VA | All 103 precincts |
| Arlington, Fairfax City, Falls Church, Loudoun, Manassas, Manassas Park (VA) | Districts and precincts only — sample ballots not loaded yet |
| Washington, DC | Districts only — ballot source not confirmed yet |

## Prerequisites
- Supabase (Postgres + PostGIS) with Edge Functions `search` and `sample-ballot` deployed.
- Deno (to run tests and the Edge Functions locally).
- Python 3.9+ (local frontend server and the data loaders); `pdftotext`/`pdftohtml` (poppler) and `ogr2ogr` (GDAL) for the loaders.

## Setup & Run

### Step 1: Clone the repository
```bash
git clone <repo-url>
cd us-district-zipcode
```

### Step 2: Configure environment variables
Create a `.env` file (do not commit) containing at least:
```bash
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-jwt-starting-with-eyJ...>
# for the data loaders (psql):
SUPABASE_DB_HOST=... SUPABASE_DB_PORT=... SUPABASE_DB_NAME=... SUPABASE_DB_USER=... SUPABASE_DB_PASSWORD=...
```

Notes:
- The anon key must be the JWT (usually starts with `eyJ...`), not the publishable key (`sb_publishable...`).
- For local development with `supabase functions serve`, this project also supports `TARGET_SUPABASE_URL` and `TARGET_SUPABASE_SERVICE_ROLE_KEY`.

### Step 3: Run the frontend locally
```bash
set -a; source .env; set +a
venv/bin/python main.py   # http://localhost:8000
```
The page calls the deployed Edge Functions. After changing them, deploy with `supabase functions deploy sample-ballot` (or `search`).

### Loading data
Loaders print SQL to stdout; apply it with `psql -v ON_ERROR_STOP=1 -1 -f out.sql`. Every loader is idempotent. See [docs/architecture.md](docs/architecture.md) for the full list:
- `scripts/load_district_layers.py` — boundary layers (MD precincts, DC, Fairfax, Loudoun districts…)
- `scripts/load_va_precincts.py` — Northern Virginia precincts (VA Department of Elections GIS)
- `scripts/load_md_general_2026.py <pdf dir>` — all Maryland ballots (parses the 24 MSBE PDFs; aborts unless they match MSBE's official candidate lists)
- `scripts/load_fairfax_general_2026.py`, `scripts/load_va_localities_general_2026.py` — Virginia ballots

## Test addresses
Checked against production on 2026-10-22. Tick **Include downballot offices** to see local contests.

| Address | What it shows |
|---|---|
| 104 Ashton Oaks Court, Ashton, MD 20861 | Montgomery: 2026 primary with results + general (19 contests, 3 questions with FOR/AGAINST text) |
| 100 Holliday St, Baltimore, MD 21202 | Baltimore City: 14 contests, 12 questions (9 city bonds and charter amendments) |
| 57 N Liberty St, Cumberland, MD 21502 | Allegany: City of Cumberland mayor and council |
| 12 E Church St, Frederick, MD 21701 | Frederick: congressional district taken from the official candidate list (the ballot prints no number) |
| 3430 Court House Dr, Ellicott City, MD 21043 | Howard: county charter questions (precinct map reloaded after Howard's 2026 consolidation) |
| 203 S 4th St, Oakland, MD 21550 | Garrett: precinct whose code the state map omits (derived) |
| 11 N Washington St, Easton, MD 21601 | Talbot: split precinct with no boundary to tell its styles apart — all 3 possible ballots shown |
| 1920 Haven Ln, Dunkirk, MD 20754 | Calvert: obsolete precinct polygon — ballot inferred, with a note |
| 777 Lynn St, Herndon, VA 20170 | Fairfax: Town of Herndon mayor and council, county bonds, official explanations |
| 6021 Farrington Ave, Alexandria, VA 22304 | Fairfax precinct split between two congressional districts — 8th District side |
| 6540 Franconia Rd, Springfield, VA 22150 | Same precinct — 11th District side |
| 7145 Main St, Clifton, VA 20124 | Fairfax: 10th District |
| 301 King St, Alexandria, VA 22314 | Alexandria: one ballot for the whole city |
| 15000 Washington St, Haymarket, VA 20169 | Prince William: Town of Haymarket contests |
| 17739 Main St, Dumfries, VA 22026 | Prince William: Town of Dumfries contests, 7th District |
| 8100 Birmingham Dr, Manassas, VA 20111 | Prince William: House of Delegates District 20 special election |
| 2100 Clarendon Blvd, Arlington, VA 22201 | Arlington: districts only, with a notice (ballot not loaded) |
| 1350 Pennsylvania Ave NW, Washington, DC 20004 | DC: districts only, with a notice |
| 20 Meadow Rd, Princeton, NJ 08540 | Outside the covered area |

API example:
```bash
curl -s -X POST "https://<project-ref>.supabase.co/functions/v1/sample-ballot?include_downballot=true" \
  -H "Content-Type: application/json" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -d '{"address":"777 Lynn St, Herndon, VA 20170"}' | head
```

## Automated Tests
Unit tests for the Edge Functions (offline, using mocks):
```bash
deno test -A supabase/functions/search supabase/functions/sample-ballot
```
GitHub Actions runs them on every push/PR; a git hook runs them before each commit.

## Project Structure
- `supabase/functions/search`: Edge Function `search` (address → geocode → PostGIS RPC → memberships).
- `supabase/functions/sample-ballot`: Edge Function `sample-ballot` (memberships → precinct → ballot styles → contests, candidates, questions; coverage, mismatch warnings, polling places, calendar, data sources).
- `supabase/migrations/`: database schema.
- `scripts/`: data loaders and the MSBE ballot PDF parser.
- `static/`: frontend (HTML/JS/CSS, Leaflet.js), served by `main.py`.
- `docs/`: roadmap and decisions, architecture, data sources, public API plan.
