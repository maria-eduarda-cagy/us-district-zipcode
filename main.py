import os
import logging
import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
from datetime import datetime, timezone
import threading

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, just use existing env vars
    pass

app = FastAPI()

# Frontend config endpoint
@app.get("/config.js", response_class=PlainTextResponse)
def get_config():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_anon_key:
        raise HTTPException(status_code=500, detail="Environment variables not configured")

    return f"""window.__APP_CONFIG__ = {{
    SUPABASE_URL: '{supabase_url}',
    SUPABASE_ANON_KEY: '{supabase_anon_key}'
}};"""

# Configuration
DATA_DIR = "data"
BENCHMARK = "Public_AR_Current"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("electormap")

# Global storage for GeoDataFrames
GDFs = {}
GDFS_LOCK = threading.Lock()

def ensure_data_current():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        meta_path = os.path.join(DATA_DIR, ".data_metadata.json")
        refresh_interval_hours = int(os.getenv("DATA_REFRESH_INTERVAL_HOURS", "24"))

        metadata = None
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    metadata = json.load(f)
            except Exception:
                metadata = None

        now = datetime.now(timezone.utc)
        last_refresh_ok = False
        if metadata and metadata.get("refreshed_at_utc"):
            try:
                last = datetime.fromisoformat(metadata["refreshed_at_utc"])
                age_hours = (now - last).total_seconds() / 3600
                last_refresh_ok = age_hours < refresh_interval_hours if refresh_interval_hours > 0 else False
            except Exception:
                last_refresh_ok = False

        required_paths = [
            os.path.join(DATA_DIR, "COUNTY"),
            os.path.join(DATA_DIR, "CD"),
            os.path.join(DATA_DIR, "SLDU"),
            os.path.join(DATA_DIR, "SLDL"),
            os.path.join(DATA_DIR, "PLACE"),
            os.path.join(DATA_DIR, "UNSD"),
        ]

        missing_required = any(not os.path.exists(p) for p in required_paths)
        force = os.getenv("FORCE_DATA_REFRESH", "0") == "1"

        if force or missing_required or not last_refresh_ok:
            try:
                import download_data
                logger.info("Refreshing data sources (missing_required=%s force=%s last_refresh_ok=%s)", missing_required, force, last_refresh_ok)
                download_data.run_download()
            except Exception as e:
                logger.exception("Data refresh failed: %s", e)
    except Exception as e:
        logger.exception("ensure_data_current failed: %s", e)

def load_layers():
    layer_paths = {
        "CD": os.path.join(DATA_DIR, "CD"),
        "SLDL": os.path.join(DATA_DIR, "SLDL"),
        "SLDU": os.path.join(DATA_DIR, "SLDU"),
        "COUNTY": os.path.join(DATA_DIR, "COUNTY"),
        "PLACE": os.path.join(DATA_DIR, "PLACE"),
        "SCHOOL": os.path.join(DATA_DIR, "UNSD"),
        "MD_ELECTION_2022_CD": os.path.join(DATA_DIR, "MD", "congressional_2022.geojson"),
        "MD_DELEGATE_SUBDISTRICTS_2022": os.path.join(DATA_DIR, "MD", "delegate_subdistricts_2022.geojson"),
        "MD_PRECINCTS_2022": os.path.join(DATA_DIR, "MD", "precincts_2022.geojson"),
        "MD_PRECINCTS_2026": os.path.join(DATA_DIR, "MD", "precincts_2022.geojson"),
        "DC_WARDS_2022": os.path.join(DATA_DIR, "DC", "wards_2022.geojson"),
        "DC_ANC_2023": os.path.join(DATA_DIR, "DC", "anc_2023.geojson"),
        "DC_SMD_2023": os.path.join(DATA_DIR, "DC", "smd_2023.geojson"),
        "DC_SBOE_DISTRICTS": os.path.join(DATA_DIR, "DC", "sboe_districts.geojson"),
        "VA_FAIRFAX_SUPERVISOR_DISTRICTS": os.path.join(DATA_DIR, "VA", "fairfax_supervisor_districts.geojson"),
        "VA_LOUDOUN_ELECTION_DISTRICTS_2022": os.path.join(DATA_DIR, "VA", "loudoun_election_districts_2022.geojson"),
        "VA_LOUDOUN_PRECINCTS": os.path.join(DATA_DIR, "VA", "loudoun_precincts.geojson"),
        "VA_LOUDOUN_POLLING_PLACES": os.path.join(DATA_DIR, "VA", "loudoun_polling_places.geojson"),
    }

    with GDFS_LOCK:
        for key, path in layer_paths.items():
            try:
                if not os.path.exists(path):
                    GDFs[key] = None
                    continue

                if os.path.isdir(path):
                    shp_files = [f for f in os.listdir(path) if f.endswith(".shp")]
                    if not shp_files:
                        GDFs[key] = None
                        continue

                    gdfs_to_concat = []
                    for shp in shp_files:
                        full_path = os.path.join(path, shp)
                        logger.info("Loading %s", full_path)
                        temp_gdf = gpd.read_file(full_path)
                        if temp_gdf.crs != "EPSG:4326":
                            temp_gdf = temp_gdf.to_crs("EPSG:4326")
                        gdfs_to_concat.append(temp_gdf)

                    if gdfs_to_concat:
                        logger.info("Merging %s files for %s", len(gdfs_to_concat), key)
                        GDFs[key] = gpd.GeoDataFrame(pd.concat(gdfs_to_concat, ignore_index=True))
                        GDFs[key].sindex
                    else:
                        GDFs[key] = None
                    continue

                logger.info("Loading %s", path)
                gdf = gpd.read_file(path)
                if gdf.crs != "EPSG:4326":
                    gdf = gdf.to_crs("EPSG:4326")
                GDFs[key] = gdf
                GDFs[key].sindex
            except Exception as e:
                logger.exception("Failed loading layer %s: %s", key, e)
                GDFs[key] = None

    delegate_gdf = GDFs.get("MD_DELEGATE_SUBDISTRICTS_2022")
    if delegate_gdf is not None and not delegate_gdf.empty:
        try:
            if "DISTRICT" in delegate_gdf.columns:
                senate = delegate_gdf.copy()
                senate["SEN_DIST"] = senate["DISTRICT"].astype(str).str.extract(r"^(\d+)", expand=False)
                senate = senate[senate["SEN_DIST"].notna()]
                senate = senate.dissolve(by="SEN_DIST", as_index=False)
                senate["DISTRICT"] = senate["SEN_DIST"].astype(str).str.zfill(2)
                senate = senate.drop(columns=["SEN_DIST"], errors="ignore")
                senate = gpd.GeoDataFrame(senate, crs="EPSG:4326")
                senate.sindex
                GDFs["MD_SENATE_DISTRICTS_2022"] = senate
        except Exception as e:
            logger.exception("Failed building senate districts: %s", e)
            GDFs["MD_SENATE_DISTRICTS_2022"] = None

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up...")
    required_paths = [
        os.path.join(DATA_DIR, "COUNTY"),
        os.path.join(DATA_DIR, "CD"),
        os.path.join(DATA_DIR, "SLDU"),
        os.path.join(DATA_DIR, "SLDL"),
        os.path.join(DATA_DIR, "PLACE"),
        os.path.join(DATA_DIR, "UNSD"),
    ]
    missing_required = any(not os.path.exists(p) for p in required_paths)
    if missing_required:
        ensure_data_current()

    load_layers()

    def _refresh_in_background():
        try:
            ensure_data_current()
            load_layers()
        except Exception:
            pass

    threading.Thread(target=_refresh_in_background, daemon=True).start()
    logger.info("Startup complete.")

class AddressSearch(BaseModel):
    address: str

class AddressCanonical(BaseModel):
    address_point_id: Optional[str] = None
    precision_class: Optional[str] = None
    lat: float
    lon: float
    source: str
    source_used: Optional[str] = None
    matched_address: Optional[str] = None
    census_block_geoid: Optional[str] = None
    match_score: Optional[float] = None
    state_abbr: Optional[str] = None

class Office(BaseModel):
    name: str
    level: str # Federal, State, Local
    description: Optional[str] = None
    election_type: Optional[str] = "general election"

class BallotMeasure(BaseModel):
    title: str
    level: str
    impact_yes: str
    impact_no: str
    election_type: Optional[str] = "general election"

class DistrictLayer(BaseModel):
    layer_id: str
    layer_type: str
    name: str
    jurisdiction: str
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    legal_basis: Optional[str] = None
    source_url: Optional[str] = None

class DistrictMembership(BaseModel):
    layer_id: str
    feature_id: str
    feature_name: Optional[str] = None
    resolution_method: str
    boundary_distance_meters: Optional[float] = None
    ambiguous: bool = False
    properties: Dict[str, Any] = {}
    geometry: Optional[dict] = None

class Contest(BaseModel):
    name: str
    level: str
    scope: str
    election_type: str
    district_layer_id: Optional[str] = None
    district_feature_id: Optional[str] = None
    district_label: Optional[str] = None
    ranked_choice_voting: bool = False

class OfficeMapping(BaseModel):
    name: str
    level: str
    scope: str
    election_type: str
    jurisdiction: str
    district_layer_id: Optional[str] = None
    ranked_choice_voting: bool = False

class ElectionCalendar(BaseModel):
    jurisdiction: str
    primary_election_date: Optional[str] = None
    primary_early_voting_period: Optional[str] = None
    general_election_date: Optional[str] = None
    general_early_voting_period: Optional[str] = None
    poll_hours: Optional[str] = None
    candidate_filing_deadline: Optional[str] = None
    source_url: Optional[str] = None

class Jurisdiction(BaseModel):
    id: str
    name: str
    type: str # CD, SLDL, SLDU, COUNTY, PLACE, SCHOOL
    offices: List[Office]
    measures: List[BallotMeasure] = []
    geometry: Optional[dict] = None
    primary_election_date: Optional[str] = None
    primary_early_voting_period: Optional[str] = None
    general_election_date: Optional[str] = None
    general_early_voting_period: Optional[str] = None
    poll_hours: Optional[str] = None
    official_polling_link: Optional[str] = None

class SearchResult(BaseModel):
    lat: float
    lon: float
    address_canonical: AddressCanonical
    district_layers: List[DistrictLayer]
    district_memberships: List[DistrictMembership]
    office_mappings: List[OfficeMapping]
    contests: List[Contest]
    election_calendars: List[ElectionCalendar]
    jurisdictions: List[Jurisdiction] = []

class SampleBallotContest(BaseModel):
    office_name: str
    jurisdiction_level: str
    scope: str
    ranked_choice_voting: bool = False
    district_id: Optional[str] = None
    district_name: Optional[str] = None
    district_layer_type: Optional[str] = None
    source_url: Optional[str] = None

class SampleBallotResponse(BaseModel):
    address_canonical: AddressCanonical
    contests: List[SampleBallotContest]

class OfficeRule(BaseModel):
    name: str
    level: str
    scope: str
    election_type: str
    jurisdiction: str
    district_layer_type: Optional[str] = None
    ranked_choice_voting: bool = False

def build_contests_and_mappings(
    district_layers: Dict[str, DistrictLayer],
    memberships_by_layer: Dict[str, List[DistrictMembership]],
    jurisdiction_code: Optional[str],
    election_year: int = 2026
):
    rules: List[OfficeRule] = [
        OfficeRule(
            name="U.S. House of Representatives",
            level="Federal",
            scope="district",
            election_type="general election",
            jurisdiction="US",
            district_layer_type="CD"
        ),
        OfficeRule(
            name="U.S. Senator",
            level="Federal",
            scope="at_large",
            election_type="general election",
            jurisdiction="US"
        ),
        OfficeRule(
            name="Governor",
            level="State",
            scope="at_large",
            election_type="general election",
            jurisdiction="MD"
        ),
        OfficeRule(
            name="Lieutenant Governor",
            level="State",
            scope="at_large",
            election_type="general election",
            jurisdiction="MD"
        ),
        OfficeRule(
            name="Comptroller",
            level="State",
            scope="at_large",
            election_type="general election",
            jurisdiction="MD"
        ),
        OfficeRule(
            name="Attorney General",
            level="State",
            scope="at_large",
            election_type="general election",
            jurisdiction="MD"
        ),
        OfficeRule(
            name="State Senator",
            level="State",
            scope="district",
            election_type="general election",
            jurisdiction="MD",
            district_layer_type="SLDU"
        ),
        OfficeRule(
            name="House of Delegates",
            level="State",
            scope="district",
            election_type="general election",
            jurisdiction="MD",
            district_layer_type="DELEGATE_SUBDISTRICT"
        ),
        OfficeRule(
            name="Mayor",
            level="Local",
            scope="at_large",
            election_type="general election",
            jurisdiction="DC",
            ranked_choice_voting=(election_year >= 2026)
        ),
        OfficeRule(
            name="Council Chair",
            level="Local",
            scope="at_large",
            election_type="general election",
            jurisdiction="DC",
            ranked_choice_voting=(election_year >= 2026)
        ),
        OfficeRule(
            name="Attorney General",
            level="Local",
            scope="at_large",
            election_type="general election",
            jurisdiction="DC",
            ranked_choice_voting=(election_year >= 2026)
        ),
        OfficeRule(
            name="Councilmember (Ward)",
            level="Local",
            scope="district",
            election_type="general election",
            jurisdiction="DC",
            district_layer_type="WARD",
            ranked_choice_voting=(election_year >= 2026)
        ),
        OfficeRule(
            name="ANC Commissioner",
            level="Local",
            scope="district",
            election_type="general election",
            jurisdiction="DC",
            district_layer_type="SMD",
            ranked_choice_voting=(election_year >= 2026)
        ),
        OfficeRule(
            name="State Board of Education Member",
            level="Local",
            scope="district",
            election_type="general election",
            jurisdiction="DC",
            district_layer_type="SBOE_DISTRICT"
        ),
        OfficeRule(
            name="Board of Supervisors",
            level="Local",
            scope="district",
            election_type="general election",
            jurisdiction="VA",
            district_layer_type="SUPERVISOR_DISTRICT"
        ),
    ]

    contests: List[Contest] = []
    office_mappings: List[OfficeMapping] = []

    def is_rule_applicable(rule: OfficeRule):
        if rule.jurisdiction == "US":
            return True
        return jurisdiction_code == rule.jurisdiction

    for rule in rules:
        if not is_rule_applicable(rule):
            continue

        if rule.scope == "at_large":
            contests.append(
                Contest(
                    name=rule.name,
                    level=rule.level,
                    scope=rule.scope,
                    election_type=rule.election_type,
                    ranked_choice_voting=rule.ranked_choice_voting
                )
            )
            office_mappings.append(
                OfficeMapping(
                    name=rule.name,
                    level=rule.level,
                    scope=rule.scope,
                    election_type=rule.election_type,
                    jurisdiction=rule.jurisdiction,
                    ranked_choice_voting=rule.ranked_choice_voting
                )
            )
            continue

        if rule.district_layer_type is None:
            continue

        chosen_membership = None
        for layer_id, members in memberships_by_layer.items():
            meta = district_layers.get(layer_id)
            if meta is None:
                continue
            if meta.layer_type != rule.district_layer_type:
                continue
            if rule.jurisdiction != "US" and meta.jurisdiction != rule.jurisdiction:
                continue
            if members:
                chosen_membership = members[0]
                break

        if chosen_membership is None:
            continue

        contests.append(
            Contest(
                name=rule.name,
                level=rule.level,
                scope=rule.scope,
                election_type=rule.election_type,
                district_layer_id=chosen_membership.layer_id,
                district_feature_id=chosen_membership.feature_id,
                district_label=chosen_membership.feature_name,
                ranked_choice_voting=rule.ranked_choice_voting
            )
        )
        office_mappings.append(
            OfficeMapping(
                name=rule.name,
                level=rule.level,
                scope=rule.scope,
                election_type=rule.election_type,
                jurisdiction=rule.jurisdiction,
                district_layer_id=chosen_membership.layer_id,
                ranked_choice_voting=rule.ranked_choice_voting
            )
        )

    return contests, office_mappings

def _meters_to_boundary(point: Point, polygon_geom) -> Optional[float]:
    try:
        g1 = gpd.GeoSeries([polygon_geom], crs="EPSG:4326").to_crs("EPSG:3857").iloc[0]
        p1 = gpd.GeoSeries([point], crs="EPSG:4326").to_crs("EPSG:3857").iloc[0]
        return float(g1.boundary.distance(p1))
    except Exception:
        return None

def _geocode_arcgis(address: str, geocode_url: str, source: str) -> Optional[AddressCanonical]:
    params = {
        "address": address,
        "f": "json",
        "outFields": "*",
        "outSR": "4326",
        "maxLocations": 1,
        "countryCode": "USA"
    }
    try:
        r = requests.get(geocode_url, params=params, timeout=15)
        if r.status_code != 200:
            return None
        candidates = r.json().get("candidates", [])
        if not candidates:
            return None
        match = candidates[0]
        lat = match["location"]["y"]
        lon = match["location"]["x"]
        score = match.get("score")
        attrs = match.get("attributes") or {}
        addr_type = attrs.get("Addr_type") or match.get("attributes", {}).get("Addr_type")
        precision = None
        if addr_type in ("PointAddress", "Subaddress"):
            precision = "rooftop"
        elif addr_type in ("Parcel", "POI"):
            precision = "parcel_centroid"
        elif addr_type in ("StreetAddress", "StreetName", "Postal"):
            precision = "interpolated"
        ref_id = attrs.get("Ref_ID") or attrs.get("LOC_ID") or attrs.get("MAR_ID") or attrs.get("OBJECTID")
        region = attrs.get("RegionAbbr") or attrs.get("Region") or attrs.get("RegionName")
        state_abbr = None
        if isinstance(region, str) and len(region.strip()) == 2:
            state_abbr = region.strip().upper()
        if state_abbr is None and match.get("address"):
            addr = str(match.get("address"))
            if ", DC" in addr:
                state_abbr = "DC"
            elif ", MD" in addr:
                state_abbr = "MD"
            elif ", VA" in addr:
                state_abbr = "VA"
        return AddressCanonical(
            address_point_id=str(ref_id) if ref_id is not None else None,
            precision_class=precision,
            lat=lat,
            lon=lon,
            source=source,
            source_used=source,
            matched_address=match.get("address")
            ,
            match_score=float(score) if score is not None else None,
            state_abbr=state_abbr
        )
    except Exception:
        return None

def _geocode_census_geographies(address: str) -> Optional[Dict[str, Any]]:
    try:
        url = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
        params = {
            "address": address,
            "benchmark": BENCHMARK,
            "vintage": "Current_Current",
            "format": "json"
        }
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

def _geocode_census_geographies_by_coords(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    try:
        url = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
        params = {
            "x": str(lon),
            "y": str(lat),
            "benchmark": BENCHMARK,
            "vintage": "Current_Current",
            "format": "json"
        }
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

def _attach_census_block_geoid(address_canonical: AddressCanonical) -> None:
    if address_canonical.census_block_geoid is not None:
        return
    census = _geocode_census_geographies_by_coords(address_canonical.lat, address_canonical.lon)
    if not census:
        return
    try:
        geos = census.get("result", {}).get("geographies", {})
        blocks = geos.get("Census Blocks") or geos.get("2020 Census Blocks")
        if blocks and len(blocks) > 0:
            address_canonical.census_block_geoid = blocks[0].get("GEOID")
    except Exception:
        return

def geocode_hierarchical(address: str) -> AddressCanonical:
    world = _geocode_arcgis(
        address,
        "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates",
        "ArcGISWorld"
    )
    state_guess = world.state_abbr if world is not None else None

    vgin = None
    if state_guess in (None, "VA"):
        vgin = _geocode_arcgis(
            address,
            "https://gismaps.vdem.virginia.gov/arcgis/rest/services/Geocoding/VGIN_Composite_Locator/GeocodeServer/findAddressCandidates",
            "VGIN"
        )

    md = None
    if state_guess in (None, "MD"):
        md = _geocode_arcgis(
            address,
            "https://mdgeodata.md.gov/imap/rest/services/GeocodeServices/MD_MultiroleLocator/GeocodeServer/findAddressCandidates",
            "iMAP"
        )

    dc = None
    if state_guess in (None, "DC"):
        dc = _geocode_arcgis(
            address,
            "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_APPS/DCGIS_MAR/GeocodeServer/findAddressCandidates",
            "MAR"
        )

    candidates = [c for c in [vgin, md, dc, world] if c is not None]
    if not candidates:
        census = _geocode_census_geographies(address)
        if census:
            try:
                matches = census.get("result", {}).get("addressMatches", [])
                if matches:
                    m0 = matches[0]
                    coords = m0.get("coordinates", {})
                    lat = coords.get("y")
                    lon = coords.get("x")
                    if lat is not None and lon is not None:
                        chosen = AddressCanonical(
                            lat=float(lat),
                            lon=float(lon),
                            source="Census",
                            source_used="Census",
                            precision_class="interpolated",
                            matched_address=m0.get("matchedAddress")
                        )
                        geos = m0.get("geographies", {})
                        blocks = geos.get("Census Blocks") or geos.get("2020 Census Blocks")
                        if blocks and len(blocks) > 0:
                            chosen.census_block_geoid = blocks[0].get("GEOID")
                        if chosen.matched_address:
                            addr = str(chosen.matched_address)
                            if ", DC" in addr:
                                chosen.state_abbr = "DC"
                            elif ", MD" in addr:
                                chosen.state_abbr = "MD"
                            elif ", VA" in addr:
                                chosen.state_abbr = "VA"
                        return chosen
            except Exception:
                pass
        raise HTTPException(status_code=404, detail="Address not found.")

    source_priority = {"VGIN": 3, "iMAP": 3, "MAR": 3, "ArcGISWorld": 1}
    def _rank(c: AddressCanonical):
        return (
            source_priority.get(c.source, 0),
            c.match_score if c.match_score is not None else 0
        )
    chosen = sorted(candidates, key=_rank, reverse=True)[0]
    if chosen.source_used is None:
        chosen.source_used = chosen.source
    census = _geocode_census_geographies(address)
    if census:
        try:
            matches = census.get("result", {}).get("addressMatches", [])
            if matches:
                geos = matches[0].get("geographies", {})
                blocks = geos.get("Census Blocks") or geos.get("2020 Census Blocks")
                if blocks and len(blocks) > 0:
                    chosen.census_block_geoid = blocks[0].get("GEOID")
        except Exception:
            pass
    _attach_census_block_geoid(chosen)
    return chosen

def _get_tiger_year_from_metadata() -> Optional[str]:
    try:
        meta_path = os.path.join(DATA_DIR, ".data_metadata.json")
        if not os.path.exists(meta_path):
            return None
        with open(meta_path, "r") as f:
            meta = json.load(f)
        y = meta.get("tiger_year")
        return str(y) if y is not None else None
    except Exception:
        return None

def _extract_ward_number(name: Optional[str]) -> Optional[int]:
    if name is None:
        return None
    digits = "".join(ch for ch in str(name) if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None

def _sample_ballot_source_url(layer_id: str, tiger_year: Optional[str]) -> Optional[str]:
    fixed = {
        "MD_ELECTION_2022_CD": "https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer/0",
        "MD_SENATE_DISTRICTS_2022": "https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer/1",
        "DC_WARDS_2022": "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/53",
        "DC_ANC_2023": "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/54",
        "DC_SMD_2023": "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/55",
        "DC_SBOE_DISTRICTS": "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Education_WebMercator/MapServer/9",
        "VA_FAIRFAX_SUPERVISOR_DISTRICTS": "https://www.fairfaxcounty.gov/idrisi/rest/services/Jade/Electoral/MapServer/2",
        "VA_LOUDOUN_ELECTION_DISTRICTS_2022": "https://logis.loudoun.gov/gis/rest/services/COL/ElectionDistricts/MapServer/8",
        "CD": None,
        "SLDU": None,
    }
    if layer_id in fixed and fixed[layer_id] is not None:
        return fixed[layer_id]
    if tiger_year is None:
        return None
    if layer_id == "CD":
        return f"https://www2.census.gov/geo/tiger/TIGER{tiger_year}/CD/"
    if layer_id == "SLDU":
        return f"https://www2.census.gov/geo/tiger/TIGER{tiger_year}/SLDU/"
    if layer_id == "SLDL":
        return f"https://www2.census.gov/geo/tiger/TIGER{tiger_year}/SLDL/"
    if layer_id == "COUNTY":
        return f"https://www2.census.gov/geo/tiger/TIGER{tiger_year}/COUNTY/"
    if layer_id == "PLACE":
        return f"https://www2.census.gov/geo/tiger/TIGER{tiger_year}/PLACE/"
    if layer_id == "SCHOOL":
        return f"https://www2.census.gov/geo/tiger/TIGER{tiger_year}/UNSD/"
    return None

def _state_abbr_to_fips(state_abbr: Optional[str]) -> Optional[str]:
    mapping = {"DC": "11", "MD": "24", "VA": "51"}
    return mapping.get(state_abbr) if state_abbr is not None else None

def _sample_ballot_district_id(layer_id: str, membership: DistrictMembership, state_abbr: Optional[str]) -> Optional[str]:
    fips = _state_abbr_to_fips(state_abbr)
    props = membership.properties or {}
    if layer_id == "CD":
        if "STATEFP" in props and "CD119FP" in props:
            return f"{props.get('STATEFP')}{props.get('CD119FP')}"
        if fips and "CD119FP" in props:
            return f"{fips}{props.get('CD119FP')}"
        return None
    if layer_id == "MD_ELECTION_2022_CD":
        dist = props.get("DISTRICT")
        if dist is None:
            return None
        dist_str = str(dist).strip()
        if fips is None:
            return dist_str
        if len(dist_str) == 1:
            dist_str = f"0{dist_str}"
        return f"{fips}{dist_str}"
    return None

def get_maryland_2026_offices(dist_type: str) -> List[Office]:
    mapping = {
        "CD": [Office(name="U.S. House of Representatives", level="Federal", description="U.S. House Representative", election_type="general election")],
        "SLDU": [Office(name="State Senator", level="State", description="Maryland State Senator", election_type="general election")],
        "SLDL": [Office(name="House of Delegates", level="State", description="Maryland House Delegate", election_type="general election")],
        "COUNTY": [
            Office(name="County Executive", level="Local", description="County Executive", election_type="general election"),
            Office(name="County Council", level="Local", description="County Council Member", election_type="general election"),
            Office(name="Sheriff", level="Local", description="County Sheriff", election_type="general election"),
            Office(name="State's Attorney", level="Local", description="State's Attorney", election_type="general election"),
            Office(name="Circuit Court Judge", level="Local", description="Circuit Court Judge", election_type="general election")
        ],
        "SCHOOL": [Office(name="Board of Education Member", level="Local", description="Board of Education Member", election_type="general election")]
    }
    
    offices = mapping.get(dist_type, [])
    
    if dist_type == "SLDU":
        statewide = [
            Office(name="Governor", level="State", description="Governor of Maryland", election_type="general election"),
            Office(name="Lieutenant Governor", level="State", description="Lieutenant Governor of Maryland", election_type="general election"),
            Office(name="Comptroller", level="State", description="State Comptroller", election_type="general election"),
            Office(name="Attorney General", level="State", description="State Attorney General", election_type="general election")
        ]
        offices.extend(statewide)
        
    return offices

def get_offices_for_jurisdiction(dist_type: str, state_fp: str = None) -> List[Office]:
    if state_fp == "24": # Maryland
        return get_maryland_2026_offices(dist_type)
        
    mapping = {
        "CD": [Office(name="U.S. Representative", level="Federal", description="U.S. House Representative", election_type="general election")],
        "SLDU": [Office(name="State Senator", level="State", description="State Senator", election_type="general election")],
        "SLDL": [Office(name="State Representative", level="State", description="State Representative", election_type="general election")],
        "COUNTY": [
            Office(name="Sheriff", level="Local", description="County Sheriff", election_type="general election"),
            Office(name="County Commissioner", level="Local", description="County Commissioner", election_type="general election"),
            Office(name="District Attorney", level="Local", description="District Attorney", election_type="general election")
        ],
        "PLACE": [
            Office(name="Mayor", level="Local", description="City Mayor", election_type="general election"),
            Office(name="City Council", level="Local", description="City Council Member", election_type="general election")
        ],
        "SCHOOL": [Office(name="School Board Member", level="Local", description="School Board Member", election_type="general election")]
    }
    return mapping.get(dist_type, [])

def get_measures_for_jurisdiction(dist_type: str, name: str) -> List[BallotMeasure]:
    measures = []
    if dist_type == "PLACE":
        measures.append(BallotMeasure(
            title=f"Local Referendum - {name}",
            level="Local",
            impact_yes="Approves funding for new parks.",
            impact_no="Maintains current budget.",
            election_type="general election"
        ))
    elif dist_type == "SLDU":
        measures.append(BallotMeasure(
            title="State Constitutional Amendment 1",
            level="State",
            impact_yes="Protects environmental rights in the constitution.",
            impact_no="No change to the constitution.",
            election_type="primary election"
        ))
    return measures

@app.post("/api/search", response_model=SearchResult)
async def search_address(data: AddressSearch):
    address_canonical = geocode_hierarchical(data.address)
    point = Point(address_canonical.lon, address_canonical.lat)

    jurisdiction_code = address_canonical.state_abbr if address_canonical.state_abbr in ("MD", "DC", "VA") else None
    _attach_census_block_geoid(address_canonical)
    census_geo = _geocode_census_geographies_by_coords(address_canonical.lat, address_canonical.lon) or {}
    census_geos = census_geo.get("result", {}).get("geographies", {}) if isinstance(census_geo, dict) else {}
    expected_geoids = {
        "CD": ((census_geos.get("119th Congressional Districts") or [{}])[0].get("GEOID") if isinstance(census_geos.get("119th Congressional Districts"), list) else None),
        "SLDU": ((census_geos.get("2024 State Legislative Districts - Upper") or [{}])[0].get("GEOID") if isinstance(census_geos.get("2024 State Legislative Districts - Upper"), list) else None),
        "SLDL": ((census_geos.get("2024 State Legislative Districts - Lower") or [{}])[0].get("GEOID") if isinstance(census_geos.get("2024 State Legislative Districts - Lower"), list) else None),
    }

    layer_meta: Dict[str, DistrictLayer] = {
        "MD_ELECTION_2022_CD": DistrictLayer(
            layer_id="MD_ELECTION_2022_CD",
            layer_type="CD",
            name="US Congressional Districts 2022 (Maryland)",
            jurisdiction="MD",
            effective_from="2022-01-01",
            legal_basis="Maryland SB 1012 (2022)",
            source_url="https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer/0"
        ),
        "MD_SENATE_DISTRICTS_2022": DistrictLayer(
            layer_id="MD_SENATE_DISTRICTS_2022",
            layer_type="SLDU",
            name="Maryland Senate Districts 2022 (derived)",
            jurisdiction="MD",
            effective_from="2022-01-01",
            legal_basis="Maryland SJR 2 (2022)",
            source_url="https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer/1"
        ),
        "MD_DELEGATE_SUBDISTRICTS_2022": DistrictLayer(
            layer_id="MD_DELEGATE_SUBDISTRICTS_2022",
            layer_type="DELEGATE_SUBDISTRICT",
            name="Maryland Delegate Subdistricts 2022",
            jurisdiction="MD",
            effective_from="2022-01-01",
            legal_basis="Maryland SJR 2 (2022)",
            source_url="https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer/1"
        ),
        "MD_PRECINCTS_2022": DistrictLayer(
            layer_id="MD_PRECINCTS_2022",
            layer_type="PRECINCT",
            name="Maryland Precincts 2022",
            jurisdiction="MD",
            effective_from="2022-01-01",
            source_url="https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer/2"
        ),
        "DC_WARDS_2022": DistrictLayer(
            layer_id="DC_WARDS_2022",
            layer_type="WARD",
            name="Washington, DC Wards 2022",
            jurisdiction="DC",
            effective_from="2022-01-01",
            source_url="https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/53"
        ),
        "DC_ANC_2023": DistrictLayer(
            layer_id="DC_ANC_2023",
            layer_type="ANC",
            name="Washington, DC Advisory Neighborhood Commissions 2023",
            jurisdiction="DC",
            effective_from="2023-01-01",
            legal_basis="Advisory Neighborhood Commission Boundaries Act of 2022",
            source_url="https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/54"
        ),
        "DC_SMD_2023": DistrictLayer(
            layer_id="DC_SMD_2023",
            layer_type="SMD",
            name="Washington, DC Single Member Districts 2023",
            jurisdiction="DC",
            effective_from="2023-01-01",
            legal_basis="Advisory Neighborhood Commission Boundaries Act of 2022",
            source_url="https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer/55"
        ),
        "DC_SBOE_DISTRICTS": DistrictLayer(
            layer_id="DC_SBOE_DISTRICTS",
            layer_type="SBOE_DISTRICT",
            name="Washington, DC State Board of Education Districts",
            jurisdiction="DC",
            source_url="https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Education_WebMercator/MapServer/9"
        ),
        "VA_FAIRFAX_SUPERVISOR_DISTRICTS": DistrictLayer(
            layer_id="VA_FAIRFAX_SUPERVISOR_DISTRICTS",
            layer_type="SUPERVISOR_DISTRICT",
            name="Fairfax County Supervisor Districts",
            jurisdiction="VA",
            source_url="https://www.fairfaxcounty.gov/idrisi/rest/services/Jade/Electoral/MapServer/2"
        ),
        "VA_LOUDOUN_ELECTION_DISTRICTS_2022": DistrictLayer(
            layer_id="VA_LOUDOUN_ELECTION_DISTRICTS_2022",
            layer_type="SUPERVISOR_DISTRICT",
            name="Loudoun County Election Districts 2022",
            jurisdiction="VA",
            effective_from="2022-06-07",
            source_url="https://logis.loudoun.gov/gis/rest/services/COL/ElectionDistricts/MapServer/8"
        ),
        "VA_LOUDOUN_PRECINCTS": DistrictLayer(
            layer_id="VA_LOUDOUN_PRECINCTS",
            layer_type="PRECINCT",
            name="Loudoun County Precincts",
            jurisdiction="VA",
            source_url="https://logis.loudoun.gov/gis/rest/services/COL/ElectionDistricts/MapServer/3"
        ),
        "CD": DistrictLayer(layer_id="CD", layer_type="CD", name="US Congressional Districts (TIGER)", jurisdiction="US"),
        "SLDU": DistrictLayer(layer_id="SLDU", layer_type="SLDU", name="State Senate Districts (TIGER)", jurisdiction="US"),
        "SLDL": DistrictLayer(layer_id="SLDL", layer_type="SLDL", name="State House Districts (TIGER)", jurisdiction="US"),
        "COUNTY": DistrictLayer(layer_id="COUNTY", layer_type="COUNTY", name="Counties (TIGER)", jurisdiction="US"),
        "PLACE": DistrictLayer(layer_id="PLACE", layer_type="PLACE", name="Places (TIGER)", jurisdiction="US"),
        "SCHOOL": DistrictLayer(layer_id="SCHOOL", layer_type="SCHOOL", name="Unified School Districts (TIGER)", jurisdiction="US"),
    }

    ordered_layers = [
        "MD_ELECTION_2022_CD",
        "MD_SENATE_DISTRICTS_2022",
        "MD_DELEGATE_SUBDISTRICTS_2022",
        "MD_PRECINCTS_2022",
        "DC_WARDS_2022",
        "DC_ANC_2023",
        "DC_SMD_2023",
        "DC_SBOE_DISTRICTS",
        "VA_FAIRFAX_SUPERVISOR_DISTRICTS",
        "VA_LOUDOUN_ELECTION_DISTRICTS_2022",
        "VA_LOUDOUN_PRECINCTS",
        "CD",
        "SLDU",
        "SLDL",
        "COUNTY",
        "PLACE",
        "SCHOOL",
    ]

    if jurisdiction_code is not None:
        ordered_layers = [
            k for k in ordered_layers
            if (k in layer_meta and (layer_meta[k].jurisdiction in (jurisdiction_code, "US")))
        ]

    district_memberships: List[DistrictMembership] = []
    jurisdictions: List[Jurisdiction] = []

    for key in ordered_layers:
        gdf = GDFs.get(key)
        if gdf is None or gdf.empty:
            continue

        try:
            possible_matches_index = gdf.sindex.query(point, predicate="intersects")
            candidates = gdf.iloc[possible_matches_index]
            containing = candidates[candidates.contains(point)]
        except Exception as e:
            logger.exception("Error querying %s: %s", key, e)
            continue

        if containing.empty:
            continue

        prepared = []
        for _, row in containing.iterrows():
            props = {k: v for k, v in dict(row).items() if k != "geometry"}
            boundary_m = _meters_to_boundary(point, row.geometry)

            candidate_geoid = None
            if key == "CD":
                cd_col = "CD119FP" if "CD119FP" in props else ("CD118FP" if "CD118FP" in props else None)
                if props.get("STATEFP") is not None and cd_col is not None and props.get(cd_col) is not None:
                    candidate_geoid = f"{props.get('STATEFP')}{props.get(cd_col)}"
            elif key == "SLDU":
                if props.get("STATEFP") is not None and props.get("SLDUST") is not None:
                    candidate_geoid = f"{props.get('STATEFP')}{props.get('SLDUST')}"
            elif key == "SLDL":
                if props.get("STATEFP") is not None and props.get("SLDLST") is not None:
                    candidate_geoid = f"{props.get('STATEFP')}{props.get('SLDLST')}"

            prepared.append((candidate_geoid, boundary_m, row, props))

        ambiguous_multi = len(prepared) > 1
        if ambiguous_multi:
            expected = expected_geoids.get(key)
            def _dist_key(d):
                return d if d is not None else -1.0
            if expected is not None:
                prepared.sort(key=lambda t: (t[0] == expected, _dist_key(t[1])), reverse=True)
            else:
                prepared.sort(key=lambda t: _dist_key(t[1]), reverse=True)

        for _, boundary_m, row, props in prepared:
            feature_id = None
            feature_name = None

            if key == "DC_ANC_2023":
                feature_id = props.get("ANC_ID")
                feature_name = props.get("NAME")
            elif key == "DC_SMD_2023":
                feature_id = props.get("SMD_ID")
                feature_name = props.get("NAME")
            elif key == "DC_WARDS_2022":
                feature_id = props.get("WARD_ID") or props.get("GEOID") or props.get("WARD")
                ward_no = props.get("WARD")
                feature_name = f"Ward {ward_no}" if ward_no is not None else (props.get("LABEL") or props.get("NAME"))
            elif key == "DC_SBOE_DISTRICTS":
                feature_id = props.get("GIS_ID") or props.get("OBJECTID")
                dist_no = props.get("NAME")
                feature_name = f"SBOE District {dist_no}" if dist_no is not None else "SBOE District"
            elif key == "MD_SENATE_DISTRICTS_2022":
                feature_id = props.get("DISTRICT")
                feature_name = f"Senate District {props.get('DISTRICT')}" if props.get("DISTRICT") is not None else None
            elif key == "MD_DELEGATE_SUBDISTRICTS_2022":
                feature_id = props.get("DISTRICT")
                feature_name = f"Delegate Subdistrict {props.get('DISTRICT')}" if props.get("DISTRICT") is not None else None
            elif key in ("MD_PRECINCTS_2022", "MD_PRECINCTS_2026"):
                feature_id = props.get("VTD") or props.get("PRECINCT") or props.get("OBJECTID")
                feature_name = props.get("NAME") or props.get("PRECINCT") or props.get("VTD")
            elif key == "VA_FAIRFAX_SUPERVISOR_DISTRICTS":
                feature_id = props.get("IDENTIFIER") or props.get("DISTRICT") or props.get("OBJECTID")
                feature_name = props.get("DISTRICT") or props.get("NAME")
            elif key == "VA_LOUDOUN_ELECTION_DISTRICTS_2022":
                feature_id = props.get("EL_NUMBER") or props.get("EL_NAME") or props.get("OBJECTID")
                feature_name = props.get("EL_NAME")
            elif key == "VA_LOUDOUN_PRECINCTS":
                feature_id = props.get("PR_NUMBER") or props.get("OBJECTID")
                feature_name = props.get("PR_NAME")
            else:
                feature_name = (
                    props.get("NAMELSAD")
                    or props.get("NAME")
                    or props.get("name")
                    or props.get("LABEL")
                    or props.get("WARD")
                )
                feature_id = props.get("GEOID") or props.get("OBJECTID") or props.get("FID") or props.get("id")

            feature_id = str(feature_id) if feature_id is not None else "unknown"
            feature_name = str(feature_name) if feature_name is not None else None

            ambiguous_distance = boundary_m is not None and boundary_m < 15

            geo_json = json.loads(gpd.GeoSeries([row.geometry]).to_json())["features"][0]["geometry"]
            logger.info("Resolved membership layer=%s feature_id=%s distance_m=%s ambiguous=%s", key, feature_id, boundary_m, bool(ambiguous_multi or ambiguous_distance))
            membership_properties = {k: str(v) for k, v in props.items() if v is not None}
            if ambiguous_multi and key in ("MD_PRECINCTS_2022", "MD_PRECINCTS_2026", "VA_LOUDOUN_PRECINCTS"):
                if address_canonical.census_block_geoid is not None:
                    membership_properties["census_block_geoid"] = str(address_canonical.census_block_geoid)
                membership_properties["split_precinct_possible"] = "true"
            if key == "VA_LOUDOUN_PRECINCTS":
                polling = GDFs.get("VA_LOUDOUN_POLLING_PLACES")
                precinct_name = props.get("PR_NAME")
                if polling is not None and precinct_name is not None and "PP_PRECINCT" in polling.columns:
                    try:
                        pp = polling[polling["PP_PRECINCT"].astype(str).str.upper() == str(precinct_name).upper()]
                        if not pp.empty:
                            row0 = pp.iloc[0].to_dict()
                            membership_properties["polling_place_name"] = str(row0.get("PP_NAME") or "")
                            membership_properties["polling_place_address"] = str(row0.get("PP_ADDRESS") or "")
                            membership_properties["polling_place_number"] = str(row0.get("PP_NUMBER") or "")
                    except Exception:
                        pass

            district_memberships.append(
                DistrictMembership(
                    layer_id=key,
                    feature_id=feature_id,
                    feature_name=feature_name,
                    resolution_method="point-in-polygon",
                    boundary_distance_meters=boundary_m,
                    ambiguous=bool(ambiguous_multi or ambiguous_distance),
                    properties=membership_properties,
                    geometry=geo_json
                )
            )

            if key in (
                "CD",
                "SLDU",
                "SLDL",
                "COUNTY",
                "PLACE",
                "SCHOOL",
                "DC_WARDS_2022",
                "DC_ANC_2023",
                "DC_SMD_2023",
                "DC_SBOE_DISTRICTS",
                "VA_FAIRFAX_SUPERVISOR_DISTRICTS",
                "VA_LOUDOUN_ELECTION_DISTRICTS_2022",
            ):
                state_fp = props.get("STATEFP")
                dist_id = f"{key}:{feature_id}"
                offices = []
                measures = []

                if key in ("CD", "SLDU", "SLDL", "COUNTY", "PLACE", "SCHOOL"):
                    dist_id = "Unknown"
                    if key == "CD":
                        cd_col = "CD119FP" if "CD119FP" in props else ("CD118FP" if "CD118FP" in props else "DISTRICT")
                        dist_id = f"{props.get('STATEFP', '')}{props.get(cd_col, '??')}"
                    elif key == "SLDL":
                        dist_id = f"{props.get('STATEFP', '')}{props.get('SLDLST', '')}"
                    elif key == "SLDU":
                        dist_id = f"{props.get('STATEFP', '')}{props.get('SLDUST', '')}"
                    elif key == "COUNTY":
                        dist_id = f"{props.get('STATEFP', '')}{props.get('COUNTYFP', '')}"
                    elif key == "PLACE":
                        dist_id = f"{props.get('STATEFP', '')}{props.get('PLACEFP', '')}"
                    elif key == "SCHOOL":
                        dist_id = f"{props.get('STATEFP', '')}{props.get('UNSDLEA', '')}"

                    offices = get_offices_for_jurisdiction(key, str(state_fp) if state_fp is not None else None)
                    measures = get_measures_for_jurisdiction(key, str(feature_name) if feature_name is not None else "")

                jurisdictions.append(
                    Jurisdiction(
                        id=str(dist_id),
                        name=str(feature_name) if feature_name is not None else "Unknown Jurisdiction",
                        type=key,
                        offices=offices,
                        measures=measures,
                        geometry=geo_json
                    )
                )
                if key in ("CD", "SLDU", "SLDL", "COUNTY", "PLACE", "SCHOOL"):
                    if str(state_fp) == "24":
                        jurisdictions[-1].primary_election_date = "June 23, 2026"
                        jurisdictions[-1].primary_early_voting_period = "June 11 - June 18, 2026"
                        jurisdictions[-1].general_election_date = "November 3, 2026"
                        jurisdictions[-1].general_early_voting_period = "October 22 - October 29, 2026"
                        jurisdictions[-1].poll_hours = "07:00 AM to 08:00 PM"
                        jurisdictions[-1].official_polling_link = "https://elections.maryland.gov/voting/where.html"
                    elif str(state_fp) == "11":
                        jurisdictions[-1].primary_election_date = "June 16, 2026"
                        jurisdictions[-1].general_election_date = "November 3, 2026"
                        jurisdictions[-1].poll_hours = "07:00 AM to 08:00 PM"
                        jurisdictions[-1].official_polling_link = "https://dcboe.org/voters/where-vote"
                    elif str(state_fp) == "51":
                        jurisdictions[-1].primary_election_date = "August 4, 2026"
                        jurisdictions[-1].general_election_date = "November 3, 2026"
                        jurisdictions[-1].poll_hours = "06:00 AM to 07:00 PM"
                        jurisdictions[-1].official_polling_link = "https://www.elections.virginia.gov/casting-a-ballot/polling-place-lookup/"

    memberships_by_layer = {}
    for m in district_memberships:
        memberships_by_layer.setdefault(m.layer_id, []).append(m)
    contests, office_mappings = build_contests_and_mappings(
        layer_meta,
        memberships_by_layer,
        jurisdiction_code,
        election_year=2026
    )

    election_calendars: List[ElectionCalendar] = []
    if "MD_ELECTION_2022_CD" in memberships_by_layer or any(m.layer_id.startswith("MD_") for m in district_memberships):
        election_calendars.append(
            ElectionCalendar(
                jurisdiction="MD",
                primary_election_date="June 23, 2026",
                primary_early_voting_period="June 11 - June 18, 2026",
                general_election_date="November 3, 2026",
                general_early_voting_period="October 22 - October 29, 2026",
                poll_hours="07:00 AM to 08:00 PM",
                source_url="https://elections.maryland.gov/"
            )
        )

    if any(m.layer_id.startswith("DC_") for m in district_memberships) or "DC_WARDS_2022" in memberships_by_layer:
        election_calendars.append(
            ElectionCalendar(
                jurisdiction="DC",
                primary_election_date="June 16, 2026",
                general_election_date="November 3, 2026",
                poll_hours="07:00 AM to 08:00 PM",
                source_url="https://dcboe.org/"
            )
        )

    if any(m.layer_id.startswith("VA_") for m in district_memberships):
        election_calendars.append(
            ElectionCalendar(
                jurisdiction="VA",
                primary_election_date="August 4, 2026",
                general_election_date="November 3, 2026",
                poll_hours="06:00 AM to 07:00 PM",
                source_url="https://www.elections.virginia.gov/"
            )
        )

    if any(m.layer_id in ("SLDU", "SLDL", "CD", "COUNTY", "PLACE") for m in district_memberships) and not election_calendars:
        election_calendars.append(ElectionCalendar(jurisdiction="US"))

    returned_layers: List[DistrictLayer] = []
    for key in ordered_layers:
        if key in memberships_by_layer and key in layer_meta:
            returned_layers.append(layer_meta[key])

    return SearchResult(
        lat=address_canonical.lat,
        lon=address_canonical.lon,
        address_canonical=address_canonical,
        district_layers=returned_layers,
        district_memberships=district_memberships,
        office_mappings=office_mappings,
        contests=contests,
        election_calendars=election_calendars,
        jurisdictions=jurisdictions
    )

@app.post("/api/sample-ballot", response_model=SampleBallotResponse)
async def sample_ballot(data: AddressSearch, include_downballot: bool = False):
    address_canonical = geocode_hierarchical(data.address)
    point = Point(address_canonical.lon, address_canonical.lat)
    jurisdiction_code = address_canonical.state_abbr if address_canonical.state_abbr in ("MD", "DC", "VA") else None

    ordered_layers = []
    if jurisdiction_code == "MD":
        ordered_layers = ["MD_ELECTION_2022_CD", "MD_SENATE_DISTRICTS_2022", "CD", "SLDU"]
        if include_downballot:
            ordered_layers = [
                "MD_DELEGATE_SUBDISTRICTS_2022",
                "COUNTY",
                "SCHOOL",
                "PLACE",
            ] + ordered_layers
    elif jurisdiction_code == "DC":
        ordered_layers = ["DC_WARDS_2022", "DC_SMD_2023", "CD"]
        if include_downballot:
            ordered_layers = ["DC_SBOE_DISTRICTS"] + ordered_layers
    elif jurisdiction_code == "VA":
        ordered_layers = ["VA_FAIRFAX_SUPERVISOR_DISTRICTS", "VA_LOUDOUN_ELECTION_DISTRICTS_2022", "CD", "SLDU"]
        if include_downballot:
            ordered_layers = [
                "SLDL",
                "COUNTY",
                "SCHOOL",
                "PLACE",
            ] + ordered_layers
    else:
        ordered_layers = ["CD"]

    memberships_by_layer: Dict[str, List[DistrictMembership]] = {}
    for key in ordered_layers:
        gdf = GDFs.get(key)
        if gdf is None or getattr(gdf, "empty", True):
            continue
        try:
            possible_matches_index = gdf.sindex.query(point, predicate="intersects")
            candidates = gdf.iloc[possible_matches_index]
            containing = candidates[candidates.contains(point)]
        except Exception:
            continue

        if containing.empty:
            continue

        for _, row in containing.iterrows():
            props = {k: v for k, v in dict(row).items() if k != "geometry"}
            feature_id = None
            feature_name = None

            if key == "DC_SMD_2023":
                feature_id = props.get("SMD_ID")
                feature_name = props.get("NAME")
            elif key == "DC_WARDS_2022":
                feature_id = props.get("WARD_ID") or props.get("GEOID") or props.get("WARD")
                ward_no = props.get("WARD")
                feature_name = f"Ward {ward_no}" if ward_no is not None else (props.get("LABEL") or props.get("NAME"))
            elif key == "MD_SENATE_DISTRICTS_2022":
                feature_id = props.get("DISTRICT")
                feature_name = f"Senate District {props.get('DISTRICT')}" if props.get("DISTRICT") is not None else None
            elif key == "MD_DELEGATE_SUBDISTRICTS_2022":
                feature_id = props.get("DISTRICT")
                feature_name = f"Delegate Subdistrict {props.get('DISTRICT')}" if props.get("DISTRICT") is not None else None
            elif key == "MD_ELECTION_2022_CD":
                feature_id = props.get("DISTRICT") or props.get("OBJECTID") or props.get("GEOID")
                dist = props.get("DISTRICT")
                if dist is not None:
                    dist_str = str(dist).strip()
                    dist_id = _sample_ballot_district_id("MD_ELECTION_2022_CD", DistrictMembership(layer_id=key, feature_id="x", resolution_method="x", properties={"DISTRICT": dist_str}), "MD")
                    feature_name = f"{dist_id} - Congressional District {int(dist_str)}" if dist_id is not None and dist_str.isdigit() else f"Congressional District {dist_str}"
                else:
                    feature_name = props.get("NAME") or props.get("NAMELSAD")
            elif key == "VA_FAIRFAX_SUPERVISOR_DISTRICTS":
                feature_id = props.get("IDENTIFIER") or props.get("DISTRICT") or props.get("OBJECTID")
                feature_name = props.get("DISTRICT") or props.get("NAME")
            elif key == "VA_LOUDOUN_ELECTION_DISTRICTS_2022":
                feature_id = props.get("EL_NUMBER") or props.get("EL_NAME") or props.get("OBJECTID")
                feature_name = props.get("EL_NAME")
            else:
                feature_name = props.get("NAMELSAD") or props.get("NAME")
                feature_id = props.get("GEOID") or props.get("OBJECTID") or props.get("id")

            feature_id = str(feature_id) if feature_id is not None else "unknown"
            feature_name = str(feature_name) if feature_name is not None else None

            memberships_by_layer.setdefault(key, []).append(
                DistrictMembership(
                    layer_id=key,
                    feature_id=feature_id,
                    feature_name=feature_name,
                    resolution_method="point-in-polygon",
                    boundary_distance_meters=_meters_to_boundary(point, row.geometry),
                    ambiguous=False,
                    properties={k: str(v) for k, v in props.items() if v is not None},
                    geometry=None
                )
            )

    tiger_year = _get_tiger_year_from_metadata()

    contests: List[SampleBallotContest] = []
    preferred_by_type: Dict[str, List[str]] = {}
    if jurisdiction_code == "MD":
        preferred_by_type = {
            "CD": ["MD_ELECTION_2022_CD", "CD"],
            "SLDU": ["MD_SENATE_DISTRICTS_2022", "SLDU"],
            "DELEGATE_SUBDISTRICT": ["MD_DELEGATE_SUBDISTRICTS_2022"],
            "COUNTY": ["COUNTY"],
            "SCHOOL": ["SCHOOL"],
            "PLACE": ["PLACE"],
        }
    elif jurisdiction_code == "DC":
        preferred_by_type = {
            "CD": ["CD"],
            "WARD": ["DC_WARDS_2022"],
            "SMD": ["DC_SMD_2023"],
            "SBOE_DISTRICT": ["DC_SBOE_DISTRICTS"],
        }
    elif jurisdiction_code == "VA":
        preferred_by_type = {
            "CD": ["CD"],
            "SLDU": ["SLDU"],
            "SLDL": ["SLDL"],
            "SUPERVISOR_DISTRICT": ["VA_FAIRFAX_SUPERVISOR_DISTRICTS", "VA_LOUDOUN_ELECTION_DISTRICTS_2022"],
            "COUNTY": ["COUNTY"],
            "SCHOOL": ["SCHOOL"],
            "PLACE": ["PLACE"],
        }

    def pick_membership(layer_ids: List[str]) -> Optional[DistrictMembership]:
        for lid in layer_ids:
            members = memberships_by_layer.get(lid) or []
            if members:
                return members[0]
        return None

    rules: List[OfficeRule] = []
    election_year = 2026
    if jurisdiction_code == "MD":
        rules.extend([
            OfficeRule(name="U.S. Representative", level="Federal", scope="district", election_type="general election", jurisdiction="US", district_layer_type="CD"),
            OfficeRule(name="State Senator", level="State", scope="district", election_type="general election", jurisdiction="MD", district_layer_type="SLDU"),
            OfficeRule(name="Governor", level="State", scope="at_large", election_type="general election", jurisdiction="MD"),
            OfficeRule(name="Lt. Governor", level="State", scope="at_large", election_type="general election", jurisdiction="MD"),
            OfficeRule(name="Attorney General", level="State", scope="at_large", election_type="general election", jurisdiction="MD"),
            OfficeRule(name="Comptroller", level="State", scope="at_large", election_type="general election", jurisdiction="MD"),
        ])
        if include_downballot:
            rules.extend([
                OfficeRule(name="House of Delegates", level="State", scope="district", election_type="general election", jurisdiction="MD", district_layer_type="DELEGATE_SUBDISTRICT"),
                OfficeRule(name="County Executive", level="Local", scope="district", election_type="general election", jurisdiction="MD", district_layer_type="COUNTY"),
                OfficeRule(name="County Council", level="Local", scope="district", election_type="general election", jurisdiction="MD", district_layer_type="COUNTY"),
                OfficeRule(name="Sheriff", level="Local", scope="district", election_type="general election", jurisdiction="MD", district_layer_type="COUNTY"),
                OfficeRule(name="State's Attorney", level="Local", scope="district", election_type="general election", jurisdiction="MD", district_layer_type="COUNTY"),
                OfficeRule(name="Circuit Court Judge", level="Local", scope="district", election_type="general election", jurisdiction="MD", district_layer_type="COUNTY"),
                OfficeRule(name="Board of Education Member", level="Local", scope="district", election_type="general election", jurisdiction="MD", district_layer_type="SCHOOL"),
            ])
    elif jurisdiction_code == "DC":
        rules.extend([
            OfficeRule(name="Mayor", level="Local", scope="at_large", election_type="general election", jurisdiction="DC", ranked_choice_voting=(election_year >= 2026)),
            OfficeRule(name="Chairman of the Council", level="Local", scope="at_large", election_type="general election", jurisdiction="DC", ranked_choice_voting=(election_year >= 2026)),
            OfficeRule(name="At-large Member of the Council", level="Local", scope="at_large", election_type="general election", jurisdiction="DC", ranked_choice_voting=(election_year >= 2026)),
            OfficeRule(name="Attorney General", level="Local", scope="at_large", election_type="general election", jurisdiction="DC", ranked_choice_voting=(election_year >= 2026)),
            OfficeRule(name="Councilmember (Ward)", level="Local", scope="district", election_type="general election", jurisdiction="DC", district_layer_type="WARD", ranked_choice_voting=(election_year >= 2026)),
            OfficeRule(name="ANC Commissioner", level="Local", scope="district", election_type="general election", jurisdiction="DC", district_layer_type="SMD", ranked_choice_voting=False),
            OfficeRule(name="Delegate to the US House", level="Federal", scope="at_large", election_type="general election", jurisdiction="DC"),
        ])
        if include_downballot:
            rules.append(
                OfficeRule(name="State Board of Education Member", level="Local", scope="district", election_type="general election", jurisdiction="DC", district_layer_type="SBOE_DISTRICT")
            )
    elif jurisdiction_code == "VA":
        rules.extend([
            OfficeRule(name="U.S. Representative", level="Federal", scope="district", election_type="general election", jurisdiction="US", district_layer_type="CD"),
            OfficeRule(name="State Senator", level="State", scope="district", election_type="general election", jurisdiction="VA", district_layer_type="SLDU"),
            OfficeRule(name="Board of Supervisors Member", level="Local", scope="district", election_type="general election", jurisdiction="VA", district_layer_type="SUPERVISOR_DISTRICT"),
        ])
        if include_downballot:
            rules.extend([
                OfficeRule(name="State Delegate", level="State", scope="district", election_type="general election", jurisdiction="VA", district_layer_type="SLDL"),
                OfficeRule(name="Sheriff", level="Local", scope="district", election_type="general election", jurisdiction="VA", district_layer_type="COUNTY"),
                OfficeRule(name="Commonwealth's Attorney", level="Local", scope="district", election_type="general election", jurisdiction="VA", district_layer_type="COUNTY"),
                OfficeRule(name="School Board Member", level="Local", scope="district", election_type="general election", jurisdiction="VA", district_layer_type="SCHOOL"),
            ])
    else:
        rules.append(
            OfficeRule(name="U.S. Representative", level="Federal", scope="district", election_type="general election", jurisdiction="US", district_layer_type="CD")
        )

    for rule in rules:
        if rule.jurisdiction not in ("US", jurisdiction_code):
            continue

        if rule.scope == "at_large":
            contests.append(
                SampleBallotContest(
                    office_name=rule.name,
                    jurisdiction_level=rule.level,
                    scope="at_large",
                    ranked_choice_voting=rule.ranked_choice_voting,
                )
            )
            continue

        if rule.district_layer_type is None:
            continue

        layer_ids = preferred_by_type.get(rule.district_layer_type) or []
        member = pick_membership(layer_ids)
        if member is None:
            continue

        if rule.district_layer_type == "WARD":
            ward_no = _extract_ward_number(member.feature_name)
            if ward_no not in (1, 3, 5, 6):
                continue

        source_layer_id = member.layer_id
        contests.append(
            SampleBallotContest(
                office_name=rule.name,
                jurisdiction_level=rule.level,
                scope="district",
                ranked_choice_voting=rule.ranked_choice_voting,
                district_id=_sample_ballot_district_id(source_layer_id, member, jurisdiction_code),
                district_name=member.feature_name,
                district_layer_type=rule.district_layer_type,
                source_url=_sample_ballot_source_url(source_layer_id, tiger_year),
            )
        )

    unique = {}
    for c in contests:
        key = (c.office_name, c.jurisdiction_level, c.scope, c.district_name)
        if key not in unique:
            unique[key] = c

    return SampleBallotResponse(
        address_canonical=address_canonical,
        contests=list(unique.values())
    )

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
