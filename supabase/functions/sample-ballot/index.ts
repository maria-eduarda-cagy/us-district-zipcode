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
  if (!resp.ok) return null

  const data = await resp.json()
  const matches = data?.result?.addressMatches
  if (!Array.isArray(matches) || matches.length === 0) return null

  const m0 = matches[0]
  const lat = m0?.coordinates?.y
  const lon = m0?.coordinates?.x
  if (typeof lat !== "number" || typeof lon !== "number") return null

  const geos = m0?.geographies ?? {}
  const blocks = geos["Census Blocks"] ?? geos["2020 Census Blocks"]
  const census_block_geoid = Array.isArray(blocks) && blocks.length > 0 ? blocks[0]?.GEOID : null

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

type Membership = {
  layer_id: string | null
  layer_type: string | null
  district_id: string | null
  district_name: string | null
  source_url: string | null
  geometry: any | null
}

type Contest = {
  contest_id: string
  office_name: string
  jurisdiction_level: "Federal" | "State" | "Local"
  scope: "at_large" | "district"
  district_layer_type: string | null
  district_id: string | null
  district_name: string | null
  ranked_choice_voting: boolean
  source_url: string | null
}

function buildContests(memberships: Membership[], includeDownballot: boolean): Contest[] {
  const includeTypes = new Set<string>(["CD", "SLDU", "SLDL"])
  if (includeDownballot) {
    includeTypes.add("COUNTY")
    includeTypes.add("PLACE")
    includeTypes.add("UNSD")
  }

  const officeByType: Record<string, { office: string; level: Contest["jurisdiction_level"]; scope: Contest["scope"] }> = {
    CD: { office: "U.S. Representative", level: "Federal", scope: "district" },
    SLDU: { office: "State Senator", level: "State", scope: "district" },
    SLDL: { office: "State Representative", level: "State", scope: "district" },
    COUNTY: { office: "County Office (At-large)", level: "Local", scope: "at_large" },
    PLACE: { office: "Municipal Office (At-large)", level: "Local", scope: "at_large" },
    UNSD: { office: "School Board (At-large)", level: "Local", scope: "at_large" },
  }

  const picked: Contest[] = []
  for (const m of memberships) {
    const t = typeof m?.layer_type === "string" ? m.layer_type : ""
    if (!t || !includeTypes.has(t)) continue
    const rule = officeByType[t]
    if (!rule) continue

    const districtId = m?.district_id ?? null
    const contestId = `${t}:${rule.scope}:${districtId ?? "at-large"}`
    picked.push({
      contest_id: contestId,
      office_name: rule.office,
      jurisdiction_level: rule.level,
      scope: rule.scope,
      district_layer_type: m?.layer_type ?? null,
      district_id: districtId,
      district_name: m?.district_name ?? null,
      ranked_choice_voting: false,
      source_url: m?.source_url ?? null,
    })
  }

  const dedup = new Map<string, Contest>()
  for (const c of picked) {
    if (!dedup.has(c.contest_id)) dedup.set(c.contest_id, c)
  }

  const levelOrder: Record<Contest["jurisdiction_level"], number> = { Federal: 0, State: 1, Local: 2 }
  return Array.from(dedup.values()).sort((a, b) => {
    const la = levelOrder[a.jurisdiction_level]
    const lb = levelOrder[b.jurisdiction_level]
    if (la !== lb) return la - lb
    return a.office_name.localeCompare(b.office_name)
  })
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

  const url = new URL(req.url)
  const includeDownballot = (url.searchParams.get("include_downballot") ?? "").toLowerCase() === "true"

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

  const debug = payload?.debug === true
  const geocoded = (await geocodeCensus(address, fetchImpl)) ?? (await geocodeArcGIS(address, fetchImpl))
  if (!geocoded) {
    return jsonResponse({ error: "Address not found" }, 404)
  }

  const supabaseUrl = (envGet("SUPABASE_URL") ?? "").trim()
  const serviceKey = (envGet("SUPABASE_SERVICE_ROLE_KEY") ?? "").trim()
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
        ...(debug ? { debug: { rpc_url: rpcUrl, supabase_url: baseUrl } } : {}),
      },
      500,
    )
  }

  const membershipsRaw = await rpcResp.json()
  const memberships: Membership[] = Array.isArray(membershipsRaw)
    ? membershipsRaw.map((m) => {
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

  const contests = buildContests(memberships, includeDownballot)
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
    include_downballot: includeDownballot,
    memberships,
    contests,
    ...(debug ? { debug: { rpc_url: rpcUrl, supabase_url: baseUrl } } : {}),
  })
}

if ((import.meta as any).main) {
  Deno.serve((req: Request) => handleRequest(req))
}
