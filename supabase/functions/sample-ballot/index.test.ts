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
): typeof fetch {
  return async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url
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

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: makeFetch([], [], pollingRows, deadlineRows),
      envGet: makeEnv({ SUPABASE_URL: "https://example.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service-role" }),
    },
  )

  const body = await resp.json()
  assertEquals(body.polling_locations.length, 1)
  assertEquals(body.polling_locations[0].name, "Sandy Spring Volunteer Fire Department - The Ballroom")
  assertEquals(body.polling_locations[0].distance_meters, 1627)
  assertEquals(body.election_events.length, 1)
  assertEquals(body.election_events[0].deadline_type, "election_day")
  assertEquals(body.election_events[0].election_name, "2026 Gubernatorial Primary Election")
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
