"""ETL: pulls supplemental election-boundary layers (MD precincts/delegate
subdistricts, DC wards/ANC/SMD/SBOE, VA Fairfax/Loudoun) from their official
ArcGIS REST services and generates SQL to load them into the
district_layers/district_boundaries tables created by the
20260702120000_district_layers_and_lookup migration.

These are layers download_data.py already knows how to fetch as GeoJSON, but
that never made it into Postgres. TIGER-derived layers (CD/SLDU/SLDL/COUNTY/
PLACE/UNSD) are intentionally excluded: they already live in the legacy
cd119/sldu/sldl/county/place/unsd tables and stay there.

Usage:
    python3 scripts/load_district_layers.py > out.sql
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PAGE_SIZE = 500


def fetch_features(base_url: str) -> list:
    features = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": str(offset),
            "resultRecordCount": str(PAGE_SIZE),
        }
        url = f"{base_url}/query?{urllib.parse.urlencode(params)}"
        last_error = None
        data = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    data = json.load(resp)
                break
            except (urllib.error.URLError, TimeoutError) as e:
                last_error = e
                time.sleep(min(2**attempt, 8))
        if data is None:
            raise RuntimeError(f"Failed to fetch {base_url} at offset {offset}: {last_error}")

        batch = data.get("features", [])
        if not batch:
            break
        features.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return features


def dq(value: str, tag: str) -> str:
    """Dollar-quote a string literal to sidestep single-quote escaping."""
    return f"${tag}${value}${tag}$"


def sql_text(value) -> str:
    if value is None:
        return "null"
    return dq(str(value), "q")


def md_delegate_subdistrict(props):
    district = str(props.get("DISTRICT"))
    return district, f"House of Delegates Subdistrict {district}"


def md_precinct(props):
    return props.get("VTD"), props.get("NAME")


def dc_ward(props):
    ward = str(props.get("WARD"))
    return ward, props.get("NAME")


def dc_anc(props):
    return props.get("ANC_ID"), props.get("NAME")


def dc_smd(props):
    return props.get("SMD_ID"), props.get("NAME")


def dc_sboe(props):
    raw = props.get("NAME")
    num = str(int(raw)) if isinstance(raw, (int, float)) else str(raw)
    return num, f"State Board of Education District {num}"


def va_fairfax_supervisor(props):
    district = str(props.get("DISTRICT", "")).title()
    return props.get("IDENTIFIER"), f"{district} District"


def va_loudoun_election_district(props):
    number = str(props.get("EL_NUMBER"))
    name = str(props.get("EL_NAME", "")).title()
    return number, f"{name} District"


def va_loudoun_precinct(props):
    number = str(props.get("PR_NUMBER"))
    name = str(props.get("PR_NAME", "")).title()
    return number, name


# Year suffixes below match each source agency's own layer name (verified
# against live MapServer metadata, e.g. GET {MapServer}?f=json -> layers[].name),
# not a snapshot/fetch date. Every run below queries the live ArcGIS service,
# so the geometry and attributes are always current regardless of the suffix;
# re-check the MapServer metadata occasionally in case an agency republishes
# a layer under a new vintage (e.g. MD precincts moved from a "2022" service
# name to "Maryland Precincts 2026").
LAYERS = [
    {
        "layer_id": "md_delegate_subdistricts_2022",
        "layer_type": "DELEGATE_SUBDISTRICT",
        "name": "Maryland House of Delegates Subdistricts (2022)",
        "state": "MD",
        "jurisdiction": "MD",
        "url": "https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer/1",
        "mapper": md_delegate_subdistrict,
    },
    {
        "layer_id": "md_precincts_2026",
        "layer_type": "PRECINCT",
        "name": "Maryland Election Precincts (2026)",
        "state": "MD",
        "jurisdiction": "MD",
        "url": "https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer/2",
        "mapper": md_precinct,
    },
    {
        "layer_id": "dc_wards_2022",
        "layer_type": "WARD",
        "name": "DC Wards (2022)",
        "state": "DC",
        "jurisdiction": "DC",
        "url": "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/53",
        "mapper": dc_ward,
    },
    {
        "layer_id": "dc_anc_2023",
        "layer_type": "ANC",
        "name": "DC Advisory Neighborhood Commissions (2023)",
        "state": "DC",
        "jurisdiction": "DC",
        "url": "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/54",
        "mapper": dc_anc,
    },
    {
        "layer_id": "dc_smd_2023",
        "layer_type": "SMD",
        "name": "DC Single Member Districts (2023)",
        "state": "DC",
        "jurisdiction": "DC",
        "url": "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/55",
        "mapper": dc_smd,
    },
    {
        "layer_id": "dc_sboe_districts",
        "layer_type": "SBOE_DISTRICT",
        "name": "DC State Board of Education Districts",
        "state": "DC",
        "jurisdiction": "DC",
        "url": "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Education_WebMercator/MapServer/9",
        "mapper": dc_sboe,
    },
    {
        "layer_id": "va_fairfax_supervisor_districts",
        "layer_type": "SUPERVISOR_DISTRICT",
        "name": "Fairfax County Board of Supervisors Districts",
        "state": "VA",
        "jurisdiction": "Fairfax County, VA",
        "url": "https://www.fairfaxcounty.gov/idrisi/rest/services/Jade/Electoral/MapServer/2",
        "mapper": va_fairfax_supervisor,
    },
    {
        "layer_id": "va_loudoun_election_districts_2022",
        "layer_type": "SUPERVISOR_DISTRICT",
        "name": "Loudoun County Election Districts (2022)",
        "state": "VA",
        "jurisdiction": "Loudoun County, VA",
        "url": "https://logis.loudoun.gov/gis/rest/services/COL/ElectionDistricts/MapServer/8",
        "mapper": va_loudoun_election_district,
    },
    {
        "layer_id": "va_loudoun_precincts",
        "layer_type": "PRECINCT",
        "name": "Loudoun County Precincts",
        "state": "VA",
        "jurisdiction": "Loudoun County, VA",
        "url": "https://logis.loudoun.gov/gis/rest/services/COL/ElectionDistricts/MapServer/3",
        "mapper": va_loudoun_precinct,
    },
]


def main():
    only = set(sys.argv[1:]) or None
    out = sys.stdout
    out.write("-- Generated by scripts/load_district_layers.py. Idempotent: safe to re-run.\n\n")

    for layer in LAYERS:
        if only and layer["layer_id"] not in only:
            continue
        print(f"Fetching {layer['layer_id']}...", file=sys.stderr)
        source_url = f"{layer['url']}/query"
        out.write(
            "insert into district_layers (layer_id, layer_type, name, state, jurisdiction, source_url)\n"
            f"values ({sql_text(layer['layer_id'])}, {sql_text(layer['layer_type'])}, "
            f"{sql_text(layer['name'])}, {sql_text(layer['state'])}, {sql_text(layer['jurisdiction'])}, "
            f"{sql_text(source_url)})\n"
            "on conflict (layer_id) do update set name = excluded.name, source_url = excluded.source_url;\n\n"
        )

        try:
            features = fetch_features(layer["url"])
        except RuntimeError as e:
            print(f"WARNING: skipping {layer['layer_id']}: {e}", file=sys.stderr)
            out.write(f"-- SKIPPED {layer['layer_id']}: fetch failed, see stderr from load run\n\n")
            continue

        print(f"  {len(features)} features", file=sys.stderr)
        rows = 0
        for feat in features:
            geom = feat.get("geometry")
            props = feat.get("properties", {})
            if not geom:
                continue
            district_id, district_name = layer["mapper"](props)
            geojson_text = json.dumps(geom)
            out.write(
                "insert into district_boundaries (layer_id, district_id, district_name, geom, source_url)\n"
                f"values ({sql_text(layer['layer_id'])}, {sql_text(district_id)}, {sql_text(district_name)}, "
                f"st_multi(st_setsrid(st_geomfromgeojson({dq(geojson_text, 'g')}), 4326)), "
                f"{sql_text(source_url)})\n"
                "on conflict (layer_id, district_id, effective_from) do update "
                "set geom = excluded.geom, district_name = excluded.district_name;\n\n"
            )
            rows += 1
        print(f"  wrote {rows} insert statements", file=sys.stderr)

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
