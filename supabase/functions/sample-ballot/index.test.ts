import { handleRequest } from "./index.ts"

declare const Deno: any

function assertEquals(actual: unknown, expected: unknown) {
  if (actual !== expected) {
    throw new Error(`Assertion failed: expected ${JSON.stringify(expected)} but got ${JSON.stringify(actual)}`)
  }
}

function makeEnv(values: Record<string, string>) {
  return (name: string) => values[name]
}

const CENSUS_OK = () =>
  new Response(
    JSON.stringify({
      result: {
        addressMatches: [
          {
            coordinates: { x: -77.0, y: 39.0 },
            matchedAddress: "OK",
            geographies: { "Census Blocks": [{ GEOID: "123" }] },
          },
        ],
      },
    }),
    { status: 200 },
  )

function makeFetch(
  memberships: any[],
  precinctRows: any[] = [],
  pollingRows: any[] = [],
  deadlineRows: any[] = [],
  requests: { url: string; body: string | null }[] = [],
): typeof fetch {
  return async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url
    const body = (init as any)?.body
    requests.push({ url, body: typeof body === "string" ? body : null })
    if (url.includes("geocoding.geo.census.gov")) return CENSUS_OK()
    if (url.endsWith("/rest/v1/rpc/rpc_district_lookup")) {
      return new Response(JSON.stringify(memberships), { status: 200 })
    }
    if (url.endsWith("/rest/v1/rpc/rpc_nearby_polling_locations")) {
      return new Response(JSON.stringify(pollingRows), { status: 200 })
    }
    if (url.includes("/rest/v1/deadlines")) {
      return new Response(JSON.stringify(deadlineRows), { status: 200 })
    }
    if (url.includes("/rest/v1/precincts")) {
      return new Response(JSON.stringify(precinctRows), { status: 200 })
    }
    throw new Error(`Unexpected fetch: ${url}`)
  }
}

Deno.test("sample-ballot: no precinct membership resolves to no ballot available", async () => {
  const memberships = [
    { layer_id: "cd119", layer_type: "CD", district_id: "2408", district_name: "CD 8", source_url: "s", geojson: "{}" },
  ]

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch(memberships),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )

  assertEquals(resp.status, 200)
  const body = await resp.json()
  assertEquals(body.ballot_status, "not_available")
  assertEquals(body.contests.length, 0)
  assertEquals(body.measures.length, 0)
  assertEquals(body.ballot_styles.length, 0)
})

Deno.test("sample-ballot: precinct with a loaded ballot style returns real contests and candidates", async () => {
  const memberships = [
    { layer_id: "cd119", layer_type: "CD", district_id: "2408", district_name: "Congressional District 8", source_url: null, geojson: "{}" },
    { layer_id: "county", layer_type: "COUNTY", district_id: "24031", district_name: "Montgomery County", source_url: null, geojson: "{}" },
    { layer_id: "md_precincts_2026", layer_type: "PRECINCT", district_id: "2403108-006", district_name: "Montgomery Precinct 08-006", source_url: null, geojson: "{}" },
  ]

  const precinctRows = [
    {
      precinct_id: "precinct-uuid",
      ballot_styles: [
        {
          ballot_style_id: "style-uuid",
          style_code: "BS DEM 125",
          party: "Democratic",
          election: { election_id: "election-uuid", name: "2026 Gubernatorial Primary Election", election_type: "primary", election_date: "2026-06-23", status: "certified" },
          ballot_style_contests: [
            {
              contests: {
                contest_id: "contest-cd8",
                contest_label: "Representative in Congress District 8",
                vote_for: 1,
                nonpartisan: false,
                retention: false,
                district_id: "2408",
                scope: "district",
                office: { name: "U.S. Representative", level: "Federal" },
                district_layer: { layer_type: "CD", source_url: null },
                source: { source_url: "https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf" },
                candidates: [
                  { name: "Jamie Raskin", party: "Democratic", unopposed: false, incumbent: true, ballot_order: 3 },
                  { name: "J. D. Kumar", party: "Democratic", unopposed: false, incumbent: false, ballot_order: 1 },
                ],
              },
            },
            {
              contests: {
                contest_id: "contest-county-exec",
                contest_label: "County Executive",
                vote_for: 1,
                nonpartisan: false,
                retention: false,
                district_id: "24031",
                // at_large even though district_id is set (linked to the county for
                // map/name purposes) -- regression test for a scope inversion bug
                // where scope was inferred from district_id instead of read from the DB.
                scope: "at_large",
                verification_note: "Conflicts with the county's own precinct-to-district crosswalk; not resolved.",
                office: { name: "County Executive", level: "Local" },
                district_layer: { layer_type: "COUNTY", source_url: null },
                source: { source_url: "https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf" },
                candidates: [
                  { name: "Marc Elrich", party: "Democratic", unopposed: false, incumbent: true, ballot_order: 1 },
                ],
              },
            },
          ],
          ballot_style_measures: [],
        },
      ],
    },
  ]

  const respWithoutDownballot = await handleRequest(
    new Request("http://localhost/sample-ballot?include_downballot=false", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch(memberships, precinctRows),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )
  const bodyWithoutDownballot = await respWithoutDownballot.json()
  assertEquals(bodyWithoutDownballot.ballot_status, "loaded")
  assertEquals(bodyWithoutDownballot.contests.length, 1)
  assertEquals(bodyWithoutDownballot.contests[0].office_name, "U.S. Representative")
  assertEquals(bodyWithoutDownballot.contests[0].candidates.length, 2)
  assertEquals(bodyWithoutDownballot.contests[0].candidates[0].name, "J. D. Kumar")
  assertEquals(bodyWithoutDownballot.contests[0].candidates[1].incumbent, true)
  assertEquals(bodyWithoutDownballot.contests[0].district_name, "Congressional District 8")
  assertEquals(bodyWithoutDownballot.contests[0].source_url, "https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf")
  assertEquals(bodyWithoutDownballot.contests[0].scope, "district")
  assertEquals(bodyWithoutDownballot.contests[0].verification_note, null)
  assertEquals(bodyWithoutDownballot.ballot_styles[0].style_code, "BS DEM 125")

  const respWithDownballot = await handleRequest(
    new Request("http://localhost/sample-ballot?include_downballot=true", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch(memberships, precinctRows),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )
  const bodyWithDownballot = await respWithDownballot.json()
  assertEquals(bodyWithDownballot.contests.length, 2)
  assertEquals(bodyWithDownballot.contests[1].jurisdiction_level, "Local")
  assertEquals(bodyWithDownballot.contests[1].candidates[0].name, "Marc Elrich")
  assertEquals(bodyWithDownballot.contests[1].scope, "at_large")
  assertEquals(bodyWithDownballot.contests[1].district_id, "24031")
  assertEquals(bodyWithDownballot.contests[1].verification_note, "Conflicts with the county's own precinct-to-district crosswalk; not resolved.")
})

Deno.test("sample-ballot: merges candidates from multiple parties into one contest when ballot styles share a contest_id", async () => {
  const memberships = [
    { layer_id: "cd119", layer_type: "CD", district_id: "2408", district_name: "Congressional District 8", source_url: null, geojson: "{}" },
    { layer_id: "md_precincts_2026", layer_type: "PRECINCT", district_id: "2403108-006", district_name: "Montgomery Precinct 08-006", source_url: null, geojson: "{}" },
  ]

  // PostgREST embeds candidates(...) by contest_id, not by ballot_style -- so every
  // occurrence of the same contest_id (whichever ballot_style traversal found it)
  // already returns the FULL, already-combined candidate list. The mock reflects
  // that: both ballot styles' copies of "contest-cd8" carry the same merged array,
  // not a split-then-merged one.
  const mergedCandidates = [
    { name: "Jamie Raskin", party: "Democratic", unopposed: false, incumbent: true, ballot_order: 3 },
    { name: "J. D. Kumar", party: "Democratic", unopposed: false, incumbent: false, ballot_order: 1 },
    { name: "Anita Mpambara Cox", party: "Republican", unopposed: false, incumbent: false, ballot_order: 1 },
    { name: "Donald L. Lech", party: "Republican", unopposed: false, incumbent: false, ballot_order: 2 },
  ]
  const sharedContest = {
    contest_id: "contest-cd8",
    contest_label: "Representative in Congress District 8",
    vote_for: 1,
    nonpartisan: false,
    retention: false,
    district_id: "2408",
    scope: "district",
    office: { name: "U.S. Representative", level: "Federal" },
    district_layer: { layer_type: "CD", source_url: null },
    source: { source_url: "https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf" },
    candidates: mergedCandidates,
  }

  const precinctRows = [
    {
      precinct_id: "precinct-uuid",
      ballot_styles: [
        {
          ballot_style_id: "style-dem",
          style_code: "BS DEM 125",
          party: "Democratic",
          election: { election_id: "election-uuid", name: "2026 Gubernatorial Primary Election", election_type: "primary", election_date: "2026-06-23", status: "certified" },
          ballot_style_contests: [{ contests: sharedContest }],
          ballot_style_measures: [],
        },
        {
          ballot_style_id: "style-rep",
          style_code: "BS REP 125",
          party: "Republican",
          election: { election_id: "election-uuid", name: "2026 Gubernatorial Primary Election", election_type: "primary", election_date: "2026-06-23", status: "certified" },
          ballot_style_contests: [{ contests: sharedContest }],
          ballot_style_measures: [],
        },
      ],
    },
  ]

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot?include_downballot=false", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch(memberships, precinctRows),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )

  const body = await resp.json()
  assertEquals(body.contests.length, 1)
  assertEquals(body.contests[0].candidates.length, 4)
  assertEquals(body.contests[0].candidates.some((c: any) => c.party === "Democratic"), true)
  assertEquals(body.contests[0].candidates.some((c: any) => c.party === "Republican"), true)
  assertEquals(body.ballot_styles.length, 2)
})

Deno.test("sample-ballot: merges candidates from multiple parties into one contest when ballot styles share a contest_id", async () => {
  const memberships = [
    { layer_id: "cd119", layer_type: "CD", district_id: "2408", district_name: "Congressional District 8", source_url: null, geojson: "{}" },
    { layer_id: "md_precincts_2026", layer_type: "PRECINCT", district_id: "2403108-006", district_name: "Montgomery Precinct 08-006", source_url: null, geojson: "{}" },
  ]

  // PostgREST embeds candidates(...) by contest_id, not by ballot_style -- so every
  // occurrence of the same contest_id (whichever ballot_style traversal found it)
  // already returns the FULL, already-combined candidate list. The mock reflects
  // that: both ballot styles' copies of "contest-cd8" carry the same merged array,
  // not a split-then-merged one.
  const mergedCandidates = [
    { name: "Jamie Raskin", party: "Democratic", unopposed: false, incumbent: true, ballot_order: 3 },
    { name: "J. D. Kumar", party: "Democratic", unopposed: false, incumbent: false, ballot_order: 1 },
    { name: "Anita Mpambara Cox", party: "Republican", unopposed: false, incumbent: false, ballot_order: 1 },
    { name: "Donald L. Lech", party: "Republican", unopposed: false, incumbent: false, ballot_order: 2 },
  ]
  const sharedContest = {
    contest_id: "contest-cd8",
    contest_label: "Representative in Congress District 8",
    vote_for: 1,
    nonpartisan: false,
    retention: false,
    district_id: "2408",
    scope: "district",
    office: { name: "U.S. Representative", level: "Federal" },
    district_layer: { layer_type: "CD", source_url: null },
    source: { source_url: "https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf" },
    candidates: mergedCandidates,
  }

  const precinctRows = [
    {
      precinct_id: "precinct-uuid",
      ballot_styles: [
        {
          ballot_style_id: "style-dem",
          style_code: "BS DEM 125",
          party: "Democratic",
          election: { election_id: "election-uuid", name: "2026 Gubernatorial Primary Election", election_type: "primary", election_date: "2026-06-23", status: "certified" },
          ballot_style_contests: [{ contests: sharedContest }],
          ballot_style_measures: [],
        },
        {
          ballot_style_id: "style-rep",
          style_code: "BS REP 125",
          party: "Republican",
          election: { election_id: "election-uuid", name: "2026 Gubernatorial Primary Election", election_type: "primary", election_date: "2026-06-23", status: "certified" },
          ballot_style_contests: [{ contests: sharedContest }],
          ballot_style_measures: [],
        },
      ],
    },
  ]

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot?include_downballot=false", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch(memberships, precinctRows),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )

  const body = await resp.json()
  assertEquals(body.contests.length, 1)
  assertEquals(body.contests[0].candidates.length, 4)
  assertEquals(body.contests[0].candidates.some((c: any) => c.party === "Democratic"), true)
  assertEquals(body.contests[0].candidates.some((c: any) => c.party === "Republican"), true)
  assertEquals(body.ballot_styles.length, 2)
})

Deno.test("sample-ballot: attaches election, primary results with per-party percentages, and data freshness", async () => {
  const memberships = [
    { layer_id: "md_precincts_2026", layer_type: "PRECINCT", district_id: "2403108-006", district_name: "Montgomery Precinct 08-006", source_url: null, geojson: "{}" },
  ]
  const primary = { election_id: "primary-uuid", name: "2026 Gubernatorial Primary Election", election_type: "primary", election_date: "2026-06-23", status: "certified" }
  const general = { election_id: "general-uuid", name: "2026 General Election", election_type: "general", election_date: "2026-11-03", status: "scheduled" }
  const ballotSource = { source_type: "certified_ballot_pdf", source_url: "https://example.org/general.pdf", effective_date: "2026-09-03", fetched_at: "2026-10-20T14:00:00+00:00" }
  const resultsSource = { source_type: "election_results_csv", source_url: "https://example.org/results.csv", effective_date: "2026-07-23", fetched_at: "2026-10-20T14:05:00+00:00" }

  const precinctRows = [
    {
      precinct_id: "precinct-uuid",
      ballot_styles: [
        {
          ballot_style_id: "style-primary",
          style_code: "BS DEM 125",
          party: "Democratic",
          election: primary,
          source: { ...ballotSource, source_url: "https://example.org/primary.pdf", fetched_at: "2026-07-02T17:32:20+00:00" },
          ballot_style_contests: [
            {
              contests: {
                contest_id: "contest-judge",
                contest_label: "Judge of the Circuit Court Circuit 6",
                vote_for: 4,
                nonpartisan: false,
                retention: false,
                district_id: null,
                scope: "at_large",
                office: { name: "Judge of the Circuit Court", level: "State" },
                district_layer: null,
                source: null,
                candidates: [
                  {
                    name: "Judge A", party: "Cross-filed", unopposed: false, incumbent: false, ballot_order: 1,
                    results: [
                      { primary_party: "Democratic", reporting_unit: "Montgomery County", votes: 300, is_winner: true, source: resultsSource },
                      { primary_party: "Republican", reporting_unit: "Montgomery County", votes: 10, is_winner: false, source: resultsSource },
                    ],
                  },
                  {
                    name: "Judge B", party: "Cross-filed", unopposed: false, incumbent: false, ballot_order: 2,
                    results: [
                      { primary_party: "Democratic", reporting_unit: "Montgomery County", votes: 100, is_winner: false, source: resultsSource },
                      { primary_party: "Republican", reporting_unit: "Montgomery County", votes: 30, is_winner: true, source: resultsSource },
                    ],
                  },
                ],
              },
            },
          ],
          ballot_style_measures: [],
        },
        {
          ballot_style_id: "style-general",
          style_code: "BS 125",
          party: null,
          election: general,
          source: ballotSource,
          ballot_style_contests: [],
          ballot_style_measures: [
            { ballot_measures: { measure_id: "q2", title: "Question 2", question_text: null, impact_yes: null, impact_no: null, order_on_ballot: 2 } },
            { ballot_measures: { measure_id: "q1", title: "Question 1", question_text: null, impact_yes: null, impact_no: null, explanation: "Present law: x", explanation_source_url: "https://example.gov/q1", order_on_ballot: 1 } },
          ],
        },
      ],
    },
  ]

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch(memberships, precinctRows),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )

  const body = await resp.json()
  const judge = body.contests[0]
  assertEquals(judge.election.election_type, "primary")
  assertEquals(judge.candidates[0].results.length, 2)
  // Percentages are within each party's primary, not across both.
  assertEquals(judge.candidates[0].results[0].pct, 75)
  assertEquals(judge.candidates[0].results[1].pct, 25)
  assertEquals(judge.candidates[1].results[1].is_winner, true)
  assertEquals(body.measures.length, 2)
  assertEquals(body.measures[0].title, "Question 1")
  assertEquals(body.measures[0].election.election_type, "general")
  assertEquals(body.measures[0].explanation, "Present law: x")
  assertEquals(body.measures[0].explanation_source_url, "https://example.gov/q1")
  assertEquals(body.measures[1].explanation, null)
  assertEquals(body.data_sources.length, 3)
  assertEquals(body.data_sources[0].source_type, "election_results_csv")
  assertEquals(body.data_last_updated, "2026-10-20T14:05:00+00:00")
})

Deno.test("sample-ballot: surfaces nearby polling locations and election events", async () => {
  const pollingRows = [
    {
      location_id: "loc-1",
      election_name: "2026 Gubernatorial Primary Election",
      election_date: "2026-06-23",
      location_type: "early_vote",
      name: "Sandy Spring Volunteer Fire Department - The Ballroom",
      address: { street: "17921 Brooke Road", city: "Sandy Spring", state: "MD", zip5: "20860" },
      hours: "7:00 AM - 8:00 PM",
      start_date: "2026-06-11",
      end_date: "2026-06-18",
      distance_meters: 1627.4,
      source_type: "early_voting_centers_pdf",
      source_url: "https://elections.maryland.gov/elections/2026/2026_Early_Voting_Centers-EN.pdf",
      source_effective_date: "2026-04-23",
      source_fetched_at: "2026-07-02T18:02:48+00:00",
    },
  ]
  const deadlineRows = [
    {
      deadline_type: "election_day",
      deadline_at: "2026-06-23T20:00:00-04:00",
      notes: null,
      election: { election_id: "election-uuid", name: "2026 Gubernatorial Primary Election", election_type: "primary", election_date: "2026-06-23", status: "certified" },
    },
  ]

  const memberships = [
    { layer_id: "county", layer_type: "COUNTY", district_id: "24031", district_name: "Montgomery County", source_url: null, geojson: "{}" },
  ]
  const requests: { url: string; body: string | null }[] = []

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch(memberships, [], pollingRows, deadlineRows, requests),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )

  const body = await resp.json()
  // Locations restricted to the address's county, calendar to its state.
  const pollingRequest = requests.find((r) => r.url.endsWith("/rpc/rpc_nearby_polling_locations"))
  assertEquals(JSON.parse(pollingRequest!.body!).county_fips, "24031")
  const deadlinesUrl = new URL(requests.find((r) => r.url.includes("/rest/v1/deadlines"))!.url)
  assertEquals(deadlinesUrl.searchParams.get("election.state"), "eq.MD")
  assertEquals(body.coverage.level, "districts_only")
  assertEquals(body.coverage.state, "MD")
  assertEquals(body.coverage.county_name, "Montgomery County")
  assertEquals(body.polling_locations.length, 1)
  assertEquals(body.polling_locations[0].name, "Sandy Spring Volunteer Fire Department - The Ballroom")
  assertEquals(body.polling_locations[0].distance_meters, 1627)
  assertEquals(body.election_events.length, 1)
  assertEquals(body.election_events[0].deadline_type, "election_day")
  assertEquals(body.election_events[0].election_name, "2026 Gubernatorial Primary Election")
  assertEquals(body.data_sources.length, 1)
  assertEquals(body.data_sources[0].source_type, "early_voting_centers_pdf")
  assertEquals(body.data_last_updated, "2026-07-02T18:02:48+00:00")
})

Deno.test("sample-ballot: address outside DC/MD/VA gets no polling locations or calendar", async () => {
  const memberships = [
    { layer_id: "county", layer_type: "COUNTY", district_id: "42101", district_name: "Philadelphia County", source_url: null, geojson: "{}" },
  ]
  const requests: { url: string; body: string | null }[] = []

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch(memberships, [], [{ name: "should not be used" }], [{ deadline_type: "x" }], requests),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )

  const body = await resp.json()
  assertEquals(body.coverage.level, "outside_coverage")
  assertEquals(body.coverage.state, null)
  assertEquals(body.polling_locations.length, 0)
  assertEquals(body.election_events.length, 0)
  assertEquals(requests.some((r) => r.url.includes("rpc_nearby_polling_locations") || r.url.includes("/deadlines")), false)
})

Deno.test("sample-ballot: falls back to ArcGIS when Census fails", async () => {
  const fakeFetch: typeof fetch = async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url
    if (url.includes("geocoding.geo.census.gov")) {
      return new Response(JSON.stringify({ result: { addressMatches: [] } }), { status: 200 })
    }
    if (url.includes("geocode.arcgis.com") && url.includes("findAddressCandidates")) {
      return new Response(
        JSON.stringify({
          candidates: [
            { address: "OK", location: { x: -77.0, y: 39.0 }, attributes: { Addr_type: "PointAddress" } },
          ],
        }),
        { status: 200 },
      )
    }
    if (url.endsWith("/rest/v1/rpc/rpc_district_lookup")) {
      return new Response(JSON.stringify([]), { status: 200 })
    }
    if (url.endsWith("/rest/v1/rpc/rpc_nearby_polling_locations")) {
      return new Response(JSON.stringify([]), { status: 200 })
    }
    if (url.includes("/rest/v1/deadlines")) {
      return new Response(JSON.stringify([]), { status: 200 })
    }
    throw new Error(`Unexpected fetch: ${url}`)
  }

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot?include_downballot=false", {
      method: "POST",
      body: JSON.stringify({ address: "x, USA" }),
    }),
    {
      fetch: fakeFetch,
      envGet: makeEnv({
        SUPABASE_URL: "https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY: "service-role",
      }),
    },
  )

  assertEquals(resp.status, 200)
  const body = await resp.json()
  assertEquals(body.address_canonical.source_used, "ArcGIS")
})

Deno.test("sample-ballot: split precinct keeps only the ballot style matching the address's districts", async () => {
  const election = { election_id: "va-general", name: "2026 General Election", election_type: "general", election_date: "2026-11-03", status: "scheduled" }
  const house = {
    contests: {
      contest_id: "contest-cd11", contest_label: "Member House of Representatives 11th District", vote_for: 1,
      nonpartisan: false, retention: false, district_id: "5111", scope: "district",
      office: { name: "U.S. Representative", level: "Federal" }, district_layer: { layer_type: "CD", source_url: null },
      source: null, candidates: [],
    },
  }
  const mayor = {
    contests: {
      contest_id: "contest-herndon-mayor", contest_label: "Mayor Town of Herndon", vote_for: 1,
      nonpartisan: true, retention: false, district_id: "5136648", scope: "district",
      office: { name: "Mayor", level: "Local" }, district_layer: { layer_type: "PLACE", source_url: null },
      source: null, candidates: [],
    },
  }
  const precinctRows = [{
    precinct_id: "p",
    ballot_styles: [
      { ballot_style_id: "town", style_code: "Herndon Full", party: null, election, ballot_style_contests: [house, mayor], ballot_style_measures: [] },
      { ballot_style_id: "exception", style_code: "Herndon Town Exception", party: null, election, ballot_style_contests: [house], ballot_style_measures: [] },
    ],
  }]
  const base = [
    { layer_id: "cd119", layer_type: "CD", district_id: "5111", district_name: "CD 11", source_url: null, geojson: "{}" },
    { layer_id: "county", layer_type: "COUNTY", district_id: "51059", district_name: "Fairfax County", source_url: null, geojson: "{}" },
    { layer_id: "va_fairfax_precincts", layer_type: "PRECINCT", district_id: "51059-324", district_name: "Herndon #3", source_url: null, geojson: "{}" },
  ]
  const run = async (memberships: any[]) => {
    const resp = await handleRequest(
      new Request("http://localhost/sample-ballot?include_downballot=true", { method: "POST", body: JSON.stringify({ address: "x" }) }),
      {
        fetch: makeFetch(memberships, precinctRows),
        envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
      },
    )
    return await resp.json()
  }

  const inTown = await run([...base, { layer_id: "place", layer_type: "PLACE", district_id: "5136648", district_name: "Herndon town", source_url: null, geojson: "{}" }])
  assertEquals(inTown.ballot_styles.length, 1)
  assertEquals(inTown.ballot_styles[0].style_code, "Herndon Full")
  assertEquals(inTown.contests.length, 2)

  const outsideTown = await run(base)
  assertEquals(outsideTown.ballot_styles.length, 1)
  assertEquals(outsideTown.ballot_styles[0].style_code, "Herndon Town Exception")
  assertEquals(outsideTown.contests.length, 1)
  assertEquals(outsideTown.contests[0].contest_id, "contest-cd11")
})

Deno.test("sample-ballot: split precinct with no layer to tell styles apart keeps every tied style", async () => {
  const election = { election_id: "md-general", name: "2026 General Election", election_type: "general", election_date: "2026-11-03", status: "scheduled" }
  const boe = (n: string) => ({
    contests: {
      contest_id: `boe-${n}`, contest_label: `Board of Education District ${n}`, vote_for: 1, nonpartisan: true, retention: false,
      district_id: "24041", scope: "district", office: { name: "Board of Education", level: "Local" },
      district_layer: { layer_type: "COUNTY", source_url: null }, source: null, candidates: [],
    },
  })
  const precinctRows = [{
    precinct_id: "p",
    ballot_styles: [
      { ballot_style_id: "s1", style_code: "BS 1", party: null, election, ballot_style_contests: [boe("1")], ballot_style_measures: [] },
      { ballot_style_id: "s2", style_code: "BS 2", party: null, election, ballot_style_contests: [boe("3")], ballot_style_measures: [] },
      { ballot_style_id: "s3", style_code: "BS 3", party: null, election, ballot_style_contests: [], ballot_style_measures: [] },
    ],
  }]
  const memberships = [
    { layer_id: "county", layer_type: "COUNTY", district_id: "24041", district_name: "Talbot County", source_url: null, geojson: "{}" },
    { layer_id: "md_precincts_2026", layer_type: "PRECINCT", district_id: "2404101-001", district_name: "Talbot 01-001", source_url: null, geojson: "{}" },
  ]
  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot?include_downballot=true", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch(memberships, precinctRows),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )
  const body = await resp.json()
  assertEquals(body.ballot_styles.length, 3)
  assertEquals(body.contests.length, 2)
})
