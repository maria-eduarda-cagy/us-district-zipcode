# Plan: a public API for district and ballot data

Status: **future idea, not started** (written 2026-10-20). Comes after the DMV is complete — see [roadmap.md](roadmap.md). Versão em português: [public-api-plan.pt-BR.md](public-api-plan.pt-BR.md).

## Idea

Offer what the app already computes — address → districts → ballot, polling places, calendar — as an API other people can build on.

## What already exists

The two Supabase Edge Functions are, in practice, a private API:

- `search`: address → geocode → every district containing it
- `sample-ballot`: the same, plus the ballot (contests, candidates, questions, official explanations), nearby polling locations, election calendar, coverage level and data freshness (`data_sources`, `data_last_updated`)

So the work is less "build an API" and more "operate one".

## What a public API needs that we don't have

- **Per-client API keys, rate limits, usage logs.** Today anyone with the anon key can call the functions, and every call spends a geocoding request (Census, ArcGIS fallback).
- **A stable, versioned contract** (`/v1/...`): field changes must not break consumers. The current response shape grew organically and needs a review before it's frozen.
- **Documentation** (OpenAPI) with an explicit coverage statement and an accuracy disclaimer — wrong election data has real consequences.
- **Caching**: districts and ballots change rarely; most responses can be cached for hours (by geocoded point or precinct).

## Keeping the data current

The hard part. Effort depends on the kind of data:

| Data | How often it changes | Upkeep |
|---|---|---|
| Districts (congressional, legislative, county) | Each redistricting (every 10 years, plus exceptions like Virginia's 2026 attempt, voided in court) | Low: Census TIGER covers the whole US, published yearly |
| Precincts | Before elections, per county | Medium: each county publishes its own way (see the Garrett/Kent/Howard gaps in MD) |
| Ballots, candidates | Every election; candidates change until certification | High: one format per state or county |
| Results, polling places, deadlines | Every election | Medium |

What makes it sustainable is the pattern the loaders already follow: **fetch the official source live, re-runnable without harm, and abort on validation failure** (e.g. the MD general loader checks every ballot against MSBE's official candidate list). Next step: run them on a schedule (daily near elections, weekly otherwise) and alert when a validation fails — then "constant updating" becomes "investigate alerts".

## Scope: the US vs. the DMV

- **Districts for the whole US**: feasible and cheap to maintain (TIGER). Could ship as a separate, national layer of the API.
- **Ballots for the whole US**: 3,000+ counties, each with its own format. Hand-built parsers (as done for MD) don't scale for one person. Organizations that cover the country do it with dedicated teams or standardized state feeds: the Voting Information Project (states publish standardized files), and commercial providers that license data (BallotReady, Ballotpedia). A realistic national path is to combine one of those with our own official-source data where we want more precision. Check licensing before redistributing any third-party data.

## Recommended approach (when we get there)

1. Launch with what's verified: DC, MD, VA, ballots validated against official sources.
2. Add national districts (TIGER) as a separate, low-maintenance layer.
3. Expand ballots state by state, starting with states that publish structured data.
4. Before launch: API keys + rate limiting, `/v1` contract review, OpenAPI docs, response caching, scheduled loaders with alerts.
