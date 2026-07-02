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

Deno.test("search: OPTIONS returns 200", async () => {
  const resp = await handleRequest(new Request("http://localhost", { method: "OPTIONS" }))
  assertEquals(resp.status, 200)
})

Deno.test("search: POST missing address returns 400", async () => {
  const resp = await handleRequest(
    new Request("http://localhost", { method: "POST", body: JSON.stringify({}) }),
  )
  assertEquals(resp.status, 400)
})

Deno.test("search: address not found returns 404", async () => {
  const fakeFetch: typeof fetch = async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url
    if (url.includes("geocoding.geo.census.gov")) {
      return new Response(JSON.stringify({ result: { addressMatches: [] } }), { status: 200 })
    }
    if (url.includes("geocode.arcgis.com") && url.includes("findAddressCandidates")) {
      return new Response(JSON.stringify({ candidates: [] }), { status: 200 })
    }
    throw new Error(`Unexpected fetch: ${url}`)
  }

  const resp = await handleRequest(
    new Request("http://localhost", { method: "POST", body: JSON.stringify({ address: "x" }) }),
    {
      fetch: fakeFetch,
      envGet: makeEnv({
        SUPABASE_URL: "https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY: "service-role",
      }),
    },
  )
  assertEquals(resp.status, 404)
})

Deno.test("search: success returns memberships with parsed geometry", async () => {
  const fakeFetch: typeof fetch = async (input) => {
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
      return new Response(
        JSON.stringify([
          {
            layer_id: "cd119",
            layer_type: "CD",
            district_id: "2408",
            district_name: "Congressional District 8",
            source_url: "https://example/source",
            geojson: "{\"type\":\"Polygon\",\"coordinates\":[]}",
          },
        ]),
        { status: 200 },
      )
    }
    throw new Error(`Unexpected fetch: ${url}`)
  }

  const resp = await handleRequest(
    new Request("http://localhost", { method: "POST", body: JSON.stringify({ address: "x" }) }),
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
  assertEquals(body.lat, 39.0)
  assertEquals(body.lon, -77.0)
  assertEquals(Array.isArray(body.memberships), true)
  assertEquals(body.memberships[0].geometry.type, "Polygon")
})

Deno.test("search: falls back to ArcGIS when Census fails", async () => {
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
    throw new Error(`Unexpected fetch: ${url}`)
  }

  const resp = await handleRequest(
    new Request("http://localhost", { method: "POST", body: JSON.stringify({ address: "x, USA" }) }),
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
