import "jsr:@supabase/functions-js@^2/edge-runtime.d.ts"
declare const Deno: any

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
    },
  })
}

function normalizeInputAddress(address: string) {
  return address
    .replace(/\s+/g, " ")
    .replace(/,\s*(USA|United States)$/i, "")
    .trim()
}

async function geocodeCensus(address: string, fetchImpl: typeof fetch) {
  const url = new URL("https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress")
  url.searchParams.set("address", address)
  url.searchParams.set("benchmark", "Public_AR_Current")
  url.searchParams.set("vintage", "Current_Current")
  url.searchParams.set("format", "json")

  const resp = await fetchImpl(url.toString(), { method: "GET" })
  if (!resp.ok) {
    return null
  }
  const data = await resp.json()
  const matches = data?.result?.addressMatches
  if (!Array.isArray(matches) || matches.length === 0) {
    return null
  }
  const m0 = matches[0]
  const lat = m0?.coordinates?.y
  const lon = m0?.coordinates?.x
  if (typeof lat !== "number" || typeof lon !== "number") {
    return null
  }

  const geos = m0?.geographies ?? {}
  const blocks = geos["Census Blocks"] ?? geos["2020 Census Blocks"]
  const census_block_geoid =
    Array.isArray(blocks) && blocks.length > 0 ? blocks[0]?.GEOID : null

  const matched_address = m0?.matchedAddress ?? null
  return { lat, lon, census_block_geoid, matched_address, source_used: "Census", precision_class: "interpolated" }
}

async function geocodeArcGIS(address: string, fetchImpl: typeof fetch) {
  const url = new URL(
    "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates",
  )
  url.searchParams.set("f", "json")
  url.searchParams.set("singleLine", address)
  url.searchParams.set("countryCode", "USA")
  url.searchParams.set("maxLocations", "1")
  url.searchParams.set("outFields", "Match_addr,Addr_type")

  const resp = await fetchImpl(url.toString(), { method: "GET" })
  if (!resp.ok) return null
  const data = await resp.json()
  const candidates = data?.candidates
  if (!Array.isArray(candidates) || candidates.length === 0) return null

  const c0 = candidates[0]
  const lat = c0?.location?.y
  const lon = c0?.location?.x
  if (typeof lat !== "number" || typeof lon !== "number") return null

  const matched_address = c0?.address ?? null
  const addrType = typeof c0?.attributes?.Addr_type === "string" ? c0.attributes.Addr_type : ""
  const precision_class = addrType === "PointAddress" ? "rooftop" : "interpolated"
  return { lat, lon, census_block_geoid: null, matched_address, source_used: "ArcGIS", precision_class }
}

export type EdgeDeps = {
  fetch?: typeof fetch
  envGet?: (name: string) => string | undefined
}

export async function handleRequest(req: Request, deps: EdgeDeps = {}) {
  const fetchImpl = deps.fetch ?? fetch
  const envGet = deps.envGet ?? ((name: string) => Deno?.env?.get?.(name))

  if (req.method === "OPTIONS") {
    return jsonResponse({ ok: true }, 200)
  }
  if (req.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405)
  }

  let payload: any = null
  try {
    payload = await req.json()
  } catch {
    return jsonResponse({ error: "Invalid JSON body" }, 400)
  }

  const address = typeof payload?.address === "string" ? normalizeInputAddress(payload.address) : ""
  if (!address) {
    return jsonResponse({ error: "Missing address" }, 400)
  }

  const geocoded = (await geocodeCensus(address, fetchImpl)) ?? (await geocodeArcGIS(address, fetchImpl))
  if (!geocoded) {
    return jsonResponse({ error: "Address not found" }, 404)
  }

  const debug = payload?.debug === true

  const supabaseUrl =
    (envGet("TARGET_SUPABASE_URL") ?? "").trim() || (envGet("SUPABASE_URL") ?? "").trim()
  const serviceKey =
    (envGet("TARGET_SUPABASE_SERVICE_ROLE_KEY") ?? "").trim() || (envGet("SUPABASE_SERVICE_ROLE_KEY") ?? "").trim()
  if (!supabaseUrl || !serviceKey) {
    return jsonResponse({ error: "Server misconfigured: missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY" }, 500)
  }

  const baseUrl = supabaseUrl.endsWith("/") ? supabaseUrl.slice(0, -1) : supabaseUrl
  const rpcUrl = `${baseUrl}/rest/v1/rpc/rpc_district_lookup`
  const rpcResp = await fetchImpl(rpcUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
    },
    body: JSON.stringify({ lon: geocoded.lon, lat: geocoded.lat }),
  })

  if (!rpcResp.ok) {
    const txt = await rpcResp.text()
    return jsonResponse(
      {
        error: `rpc_district_lookup failed: ${txt}`,
        hint: "Create rpc_district_lookup in Supabase SQL Editor and load district tables.",
        ...(debug ? { debug: { rpc_url: rpcUrl, supabase_url: baseUrl } } : {}),
      },
      500,
    )
  }

  const memberships = await rpcResp.json()
  const normalizedMemberships = Array.isArray(memberships)
    ? memberships.map((m) => {
        const geojson = typeof m?.geojson === "string" ? m.geojson : null
        let geometry: any = null
        if (geojson) {
          try {
            geometry = JSON.parse(geojson)
          } catch {
            geometry = null
          }
        }

        return {
          layer_id: m?.layer_id ?? null,
          layer_type: m?.layer_type ?? null,
          district_id: m?.district_id ?? null,
          district_name: m?.district_name ?? null,
          source_url: m?.source_url ?? null,
          geometry,
        }
      })
    : []

  return jsonResponse({
    lat: geocoded.lat,
    lon: geocoded.lon,
    address_canonical: {
      lat: geocoded.lat,
      lon: geocoded.lon,
      source: geocoded.source_used,
      source_used: geocoded.source_used,
      precision_class: geocoded.precision_class,
      matched_address: geocoded.matched_address,
      census_block_geoid: geocoded.census_block_geoid,
    },
    memberships: normalizedMemberships,
    ...(debug ? { debug: { rpc_url: rpcUrl, supabase_url: baseUrl } } : {}),
  })
}

if ((import.meta as any).main) {
  Deno.serve((req: Request) => handleRequest(req))
}
