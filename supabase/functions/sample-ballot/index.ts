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

type JurisdictionLevel = "Federal" | "State" | "Local"

type Candidate = {
  name: string
  party: string | null
  unopposed: boolean
  incumbent: boolean
  ballot_order: number | null
}

type Contest = {
  contest_id: string
  office_name: string
  contest_label: string
  jurisdiction_level: JurisdictionLevel
  scope: "at_large" | "district"
  district_layer_type: string | null
  district_id: string | null
  district_name: string | null
  vote_for: number
  ranked_choice_voting: boolean
  nonpartisan: boolean
  retention: boolean
  source_url: string | null
  verification_note: string | null
  candidates: Candidate[]
}

type Measure = {
  measure_id: string
  title: string
  question_text: string | null
  impact_yes: string | null
  impact_no: string | null
}

type BallotStyleSummary = {
  ballot_style_id: string
  style_code: string
  party: string | null
  election: { election_id: string; name: string; election_type: string; election_date: string; status: string } | null
}

const BALLOT_SELECT =
  "precinct_id,ballot_styles(ballot_style_id,style_code,party,certification_date,sample_ballot_url," +
  "election:elections(election_id,name,election_type,election_date,status)," +
  "ballot_style_contests(contests(contest_id,contest_label,vote_for,nonpartisan,retention,district_id,scope,verification_note," +
  "office:offices(name,level)," +
  "district_layer:district_layers(layer_type,source_url)," +
  "source:sources(source_url)," +
  "candidates(name,party,unopposed,incumbent,ballot_order)))," +
  "ballot_style_measures(ballot_measures(measure_id,title,question_text,impact_yes,impact_no)))"

async function fetchNearbyPollingLocations(
  baseUrl: string,
  serviceKey: string,
  fetchImpl: typeof fetch,
  lon: number,
  lat: number,
): Promise<any[]> {
  const resp = await fetchImpl(`${baseUrl}/rest/v1/rpc/rpc_nearby_polling_locations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: serviceKey,
      Authorization: `Bearer ${serviceKey}`,
    },
    body: JSON.stringify({ lon, lat, max_results: 5 }),
  })
  if (!resp.ok) return []
  const rows = await resp.json()
  return Array.isArray(rows) ? rows : []
}

async function fetchElectionEvents(baseUrl: string, serviceKey: string, fetchImpl: typeof fetch): Promise<any[]> {
  const url = new URL(`${baseUrl}/rest/v1/deadlines`)
  url.searchParams.set(
    "select",
    "deadline_type,deadline_at,notes,election:elections(election_id,name,election_type,election_date,status)",
  )
  url.searchParams.set("order", "deadline_at.asc")

  const resp = await fetchImpl(url.toString(), {
    method: "GET",
    headers: { apikey: serviceKey, Authorization: `Bearer ${serviceKey}` },
  })
  if (!resp.ok) return []
  const rows = await resp.json()
  return Array.isArray(rows) ? rows : []
}

function shapePollingLocations(rows: any[]) {
  return rows.map((r) => ({
    location_id: r?.location_id ?? null,
    election_name: r?.election_name ?? null,
    election_date: r?.election_date ?? null,
    location_type: r?.location_type ?? null,
    name: r?.name ?? null,
    address: r?.address ?? null,
    hours: r?.hours ?? null,
    start_date: r?.start_date ?? null,
    end_date: r?.end_date ?? null,
    distance_meters: typeof r?.distance_meters === "number" ? Math.round(r.distance_meters) : null,
  }))
}

function shapeElectionEvents(rows: any[]) {
  return rows
    .filter((r) => r?.election)
    .map((r) => ({
      election_id: r.election.election_id,
      election_name: r.election.name,
      election_type: r.election.election_type,
      election_date: r.election.election_date,
      election_status: r.election.status,
      deadline_type: r?.deadline_type ?? null,
      deadline_at: r?.deadline_at ?? null,
      notes: r?.notes ?? null,
    }))
}

async function fetchBallotStylesForPrecinct(
  baseUrl: string,
  serviceKey: string,
  fetchImpl: typeof fetch,
  precinctCode: string,
): Promise<any[]> {
  const url = new URL(`${baseUrl}/rest/v1/precincts`)
  url.searchParams.set("precinct_code", `eq.${precinctCode}`)
  url.searchParams.set("select", BALLOT_SELECT)

  const resp = await fetchImpl(url.toString(), {
    method: "GET",
    headers: { apikey: serviceKey, Authorization: `Bearer ${serviceKey}` },
  })
  if (!resp.ok) return []
  const rows = await resp.json()
  if (!Array.isArray(rows)) return []
  return rows.flatMap((r: any) => (Array.isArray(r?.ballot_styles) ? r.ballot_styles : []))
}

function shapeContests(ballotStyles: any[], memberships: Membership[], includeDownballot: boolean): Contest[] {
  const membershipByKey = new Map<string, Membership>()
  for (const m of memberships) {
    if (m.layer_type && m.district_id) membershipByKey.set(`${m.layer_type}:${m.district_id}`, m)
  }

  const dedup = new Map<string, Contest>()
  for (const style of ballotStyles) {
    const links = Array.isArray(style?.ballot_style_contests) ? style.ballot_style_contests : []
    for (const link of links) {
      const c = link?.contests
      if (!c?.contest_id) continue

      const level: JurisdictionLevel = c?.office?.level === "Federal" || c?.office?.level === "State" ? c.office.level : "Local"
      if (level === "Local" && !includeDownballot) continue

      const layerType = typeof c?.district_layer?.layer_type === "string" ? c.district_layer.layer_type : null
      const districtId = c?.district_id ?? null
      const membership = layerType && districtId ? membershipByKey.get(`${layerType}:${districtId}`) : undefined

      const candidates: Candidate[] = Array.isArray(c?.candidates)
        ? c.candidates
            .slice()
            .sort((a: any, b: any) => (a?.ballot_order ?? 0) - (b?.ballot_order ?? 0))
            .map((cand: any) => ({
              name: cand?.name ?? "",
              party: cand?.party ?? null,
              unopposed: !!cand?.unopposed,
              incumbent: !!cand?.incumbent,
              ballot_order: cand?.ballot_order ?? null,
            }))
        : []

      dedup.set(c.contest_id, {
        contest_id: c.contest_id,
        office_name: c?.office?.name ?? c?.contest_label ?? "Unknown Office",
        contest_label: c?.contest_label ?? c?.office?.name ?? "Unknown Contest",
        jurisdiction_level: level,
        scope: c?.scope === "district" ? "district" : "at_large",
        district_layer_type: layerType,
        district_id: districtId,
        district_name: membership?.district_name ?? null,
        vote_for: typeof c?.vote_for === "number" ? c.vote_for : 1,
        ranked_choice_voting: false,
        nonpartisan: !!c?.nonpartisan,
        retention: !!c?.retention,
        source_url: c?.source?.source_url ?? c?.district_layer?.source_url ?? null,
        verification_note: c?.verification_note ?? null,
        candidates,
      })
    }
  }

  const levelOrder: Record<JurisdictionLevel, number> = { Federal: 0, State: 1, Local: 2 }
  return Array.from(dedup.values()).sort((a, b) => {
    const la = levelOrder[a.jurisdiction_level]
    const lb = levelOrder[b.jurisdiction_level]
    if (la !== lb) return la - lb
    return a.office_name.localeCompare(b.office_name)
  })
}

function shapeMeasures(ballotStyles: any[]): Measure[] {
  const dedup = new Map<string, Measure>()
  for (const style of ballotStyles) {
    const links = Array.isArray(style?.ballot_style_measures) ? style.ballot_style_measures : []
    for (const link of links) {
      const m = link?.ballot_measures
      if (!m?.measure_id) continue
      dedup.set(m.measure_id, {
        measure_id: m.measure_id,
        title: m?.title ?? "",
        question_text: m?.question_text ?? null,
        impact_yes: m?.impact_yes ?? null,
        impact_no: m?.impact_no ?? null,
      })
    }
  }
  return Array.from(dedup.values())
}

function shapeBallotStyleSummaries(ballotStyles: any[]): BallotStyleSummary[] {
  return ballotStyles.map((s) => ({
    ballot_style_id: s?.ballot_style_id ?? null,
    style_code: s?.style_code ?? null,
    party: s?.party ?? null,
    election: s?.election
      ? {
          election_id: s.election.election_id,
          name: s.election.name,
          election_type: s.election.election_type,
          election_date: s.election.election_date,
          status: s.election.status,
        }
      : null,
  }))
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

  const precinctMembership = memberships.find((m) => m.layer_type === "PRECINCT" && m.district_id)
  const [ballotStylesRaw, pollingLocationsRaw, electionEventsRaw] = await Promise.all([
    precinctMembership?.district_id
      ? fetchBallotStylesForPrecinct(baseUrl, serviceKey, fetchImpl, precinctMembership.district_id)
      : Promise.resolve([]),
    fetchNearbyPollingLocations(baseUrl, serviceKey, fetchImpl, geocoded.lon, geocoded.lat),
    fetchElectionEvents(baseUrl, serviceKey, fetchImpl),
  ])

  const contests = shapeContests(ballotStylesRaw, memberships, includeDownballot)
  const measures = shapeMeasures(ballotStylesRaw)
  const ballot_styles = shapeBallotStyleSummaries(ballotStylesRaw)
  const polling_locations = shapePollingLocations(pollingLocationsRaw)
  const election_events = shapeElectionEvents(electionEventsRaw)

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
    ballot_status: ballotStylesRaw.length > 0 ? "loaded" : "not_available",
    ballot_styles,
    contests,
    measures,
    polling_locations,
    election_events,
    ...(debug ? { debug: { rpc_url: rpcUrl, supabase_url: baseUrl, precinct_code: precinctMembership?.district_id ?? null } } : {}),
  })
}

if ((import.meta as any).main) {
  Deno.serve((req: Request) => handleRequest(req))
}
