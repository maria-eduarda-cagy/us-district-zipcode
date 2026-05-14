# ElectorMap & Downballot Finder (DMV + 2026 cycle)

English version. Versão em português: [README.pt-BR.md](README.pt-BR.md).

This project is an MVP to identify legislative districts (DC/MD/VA), generate a “sample ballot” (offices only, no candidates), and show an election calendar (when available), using address geocoding + geographic layers (TIGER/Line + local authoritative sources).

## Features
- **Hierarchical geocoding**: Converts an address into coordinates and normalizes the address (prioritizing local sources when applicable, with fallback).
- **Spatial logic (point-in-polygon)**: Finds districts via PostGIS (Supabase) with TIGER/Line layers loaded in the database.
- **Interactive map**: Visualizes the location and district boundaries via Leaflet.js.
- **Sample Ballot (Offices Only)**: Generates an offices list by district and at-large; supports optional “downballot”.
- **Election calendar**: Shows the 2026 cycle calendar (currently Maryland).

## Prerequisites
- Supabase (Postgres + PostGIS) with Edge Functions `search` and `sample-ballot` deployed.
- Deno (to run tests locally).
- [Optional] Python 3.9+ (only for the legacy local server and/or helper scripts).

## Setup & Run

### Step 1: Clone the repository
```bash
git clone <repo-url>
cd us-district-zipcode
```

### Step 2: Configure environment variables (for local tests and curl calls)
Create a `.env` file (do not commit) containing at least:
```bash
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-jwt-starting-with-eyJ...>
```

Notes:
- The anon key used here must be the JWT (usually starts with `eyJ...`). Do not use the publishable key (`sb_publishable...`).
- For local development with `supabase functions serve`, this project also supports:
  - `TARGET_SUPABASE_URL`
  - `TARGET_SUPABASE_SERVICE_ROLE_KEY`

---

## Quick Validation
To quickly verify:
- Open the frontend and search an address in MD/DC/VA (the input already comes with an MD example).
- In **Sample Ballot (Offices Only)**:
  - With “Include downballot offices” unchecked: you get top-of-ticket (e.g., U.S. Representative, State Senator, etc.).
  - With it checked: you also get downballot offices (e.g., county, school, etc., when applicable).

API tests (production example):
```bash
curl -s -X POST "https://<project-ref>.supabase.co/functions/v1/search" \
  -H "Content-Type: application/json" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -d '{"address":"104 Ashton Oaks Court, Ashton, Maryland 20861"}' | head

curl -s -X POST "https://<project-ref>.supabase.co/functions/v1/sample-ballot?include_downballot=true" \
  -H "Content-Type: application/json" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -d '{"address":"104 Ashton Oaks Court, Ashton, Maryland 20861"}' | head
```

## Automated Tests
This repository includes unit tests for the Edge Functions (offline, using mocks).

Run locally:
```bash
deno test -A supabase/functions/search supabase/functions/sample-ballot
```

CI:
- GitHub Actions runs tests automatically on push/PR.

## Project Structure
- `supabase/functions/search`: Edge Function `search` (address → geocode → PostGIS RPC → memberships).
- `supabase/functions/sample-ballot`: Edge Function `sample-ballot` (generates contests/offices from memberships).
- `supabase/config.toml`: Edge Functions config (includes `verify_jwt`).
- `main.py`: Legacy FastAPI server (not required for the Supabase path).
- `download_data.py`: Helper script to download local data (when applicable).
- `static/`: Frontend (HTML/JS/CSS) using Leaflet.js.
- `requirements.txt`: Python dependencies list.
