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

function makeFetch(memberships: any[]): typeof fetch {
  return async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url
    if (url.includes("geocoding.geo.census.gov")) {
      return new Response(
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
    }
    if (url.endsWith("/rest/v1/rpc/rpc_district_lookup")) {
      return new Response(JSON.stringify(memberships), { status: 200 })
    }
    throw new Error(`Unexpected fetch: ${url}`)
  }
}

Deno.test("sample-ballot: include_downballot=false returns only federal/state contests", async () => {
  const memberships = [
    { layer_id: "cd119", layer_type: "CD", district_id: "2408", district_name: "CD 8", source_url: "s", geojson: "{}" },
    { layer_id: "sldu", layer_type: "SLDU", district_id: "24-14", district_name: "SLDU 14", source_url: "s", geojson: "{}" },
    { layer_id: "sldl", layer_type: "SLDL", district_id: "24-09", district_name: "SLDL 09", source_url: "s", geojson: "{}" },
    { layer_id: "county", layer_type: "COUNTY", district_id: "24031", district_name: "Montgomery County", source_url: "s", geojson: "{}" },
  ]

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot?include_downballot=false", {
      method: "POST",
      body: JSON.stringify({ address: "x" }),
    }),
    {
      fetch: makeFetch(memberships),
      envGet: makeEnv({
        TARGET_SUPABASE_URL: "https://example.supabase.co",
        TARGET_SUPABASE_SERVICE_ROLE_KEY: "service-role",
      }),
    },
  )

  assertEquals(resp.status, 200)
  const body = await resp.json()
  assertEquals(body.include_downballot, false)
  assertEquals(body.contests.length, 3)
  assertEquals(body.contests[0].jurisdiction_level, "Federal")
})

Deno.test("sample-ballot: include_downballot=true includes local contests", async () => {
  const memberships = [
    { layer_id: "cd119", layer_type: "CD", district_id: "2408", district_name: "CD 8", source_url: "s", geojson: "{}" },
    { layer_id: "sldu", layer_type: "SLDU", district_id: "24-14", district_name: "SLDU 14", source_url: "s", geojson: "{}" },
    { layer_id: "sldl", layer_type: "SLDL", district_id: "24-09", district_name: "SLDL 09", source_url: "s", geojson: "{}" },
    { layer_id: "county", layer_type: "COUNTY", district_id: "24031", district_name: "Montgomery County", source_url: "s", geojson: "{}" },
    { layer_id: "place", layer_type: "PLACE", district_id: "12345", district_name: "Ashton", source_url: "s", geojson: "{}" },
    { layer_id: "unsd", layer_type: "UNSD", district_id: "999", district_name: "School District", source_url: "s", geojson: "{}" },
  ]

  const resp = await handleRequest(
    new Request("http://localhost/sample-ballot?include_downballot=true", {
      method: "POST",
      body: JSON.stringify({ address: "x" }),
    }),
    {
      fetch: makeFetch(memberships),
      envGet: makeEnv({
        TARGET_SUPABASE_URL: "https://example.supabase.co",
        TARGET_SUPABASE_SERVICE_ROLE_KEY: "service-role",
      }),
    },
  )

  assertEquals(resp.status, 200)
  const body = await resp.json()
  assertEquals(body.include_downballot, true)
  assertEquals(body.contests.length, 6)
  assertEquals(body.contests[0].jurisdiction_level, "Federal")
  assertEquals(body.contests[body.contests.length - 1].jurisdiction_level, "Local")
})

