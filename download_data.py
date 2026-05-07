import os
import requests
import zipfile
import shutil
import json
from datetime import datetime, timezone
import time

DATA_DIR = "data"
YEAR = "2025"

# URLs para Shapefiles Nacionais (US-wide)
# Lista de FIPS de estados dos EUA
STATE_FIPS = ["24"] # Maryland FIPS

def url_exists(url):
    try:
        r = requests.get(url, stream=True, timeout=20, headers={"Range": "bytes=0-0"})
        return r.status_code in (200, 206)
    except Exception:
        return False

def resolve_latest_tiger_year():
    current_year = datetime.now(timezone.utc).year
    candidates = list(range(current_year, current_year - 6, -1))
    for y in candidates:
        test_url = f"https://www2.census.gov/geo/tiger/TIGER{y}/COUNTY/tl_{y}_us_county.zip"
        if url_exists(test_url):
            return str(y)
    return YEAR

def download_and_extract(name, url, extract_to):
    print(f"Downloading {name} from {url}...")
    local_zip = os.path.join(DATA_DIR, f"{name}.zip")
    os.makedirs(extract_to, exist_ok=True)
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(local_zip, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            with zipfile.ZipFile(local_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            os.remove(local_zip)
            return True
        else:
            print(f"Failed {url}: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error {url}: {e}")
        return False

def download_arcgis_layer_geojson(layer_url, output_path, max_retries=4):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)

    features = []
    result_offset = 0
    page_size = 1000

    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": str(result_offset),
            "resultRecordCount": str(page_size)
        }
        last_error = None
        resp = None
        for attempt in range(max_retries):
            try:
                resp = requests.get(f"{layer_url}/query", params=params, timeout=60)
                if resp.status_code == 200:
                    break
                last_error = f"HTTP {resp.status_code}"
            except Exception as e:
                last_error = str(e)
            time.sleep(min(2 ** attempt, 8))

        if resp is None or resp.status_code != 200:
            print(f"Failed to fetch {layer_url} at offset {result_offset}: {last_error}")
            return False

        data = resp.json()
        batch = data.get("features", [])
        if not batch:
            break
        features.extend(batch)
        result_offset += page_size

    fc = {"type": "FeatureCollection", "features": features}
    with open(output_path, "w") as f:
        json.dump(fc, f)
    return True

def run_download(tiger_year=None):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    resolved_year = tiger_year or resolve_latest_tiger_year()

    county_dir = os.path.join(DATA_DIR, "COUNTY")
    if os.path.exists(county_dir):
        shutil.rmtree(county_dir)
    os.makedirs(county_dir, exist_ok=True)
    county_url = f"https://www2.census.gov/geo/tiger/TIGER{resolved_year}/COUNTY/tl_{resolved_year}_us_county.zip"
    download_and_extract("COUNTY_US", county_url, county_dir)

    layer_dirs = {
        "CD": os.path.join(DATA_DIR, "CD"),
        "SLDU": os.path.join(DATA_DIR, "SLDU"),
        "SLDL": os.path.join(DATA_DIR, "SLDL"),
        "PLACE": os.path.join(DATA_DIR, "PLACE"),
        "UNSD": os.path.join(DATA_DIR, "UNSD"),
    }
    for d in layer_dirs.values():
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    fips_list = ["24", "11", "51"]
    for fips in fips_list:
        cd_url = f"https://www2.census.gov/geo/tiger/TIGER{resolved_year}/CD/tl_{resolved_year}_{fips}_cd119.zip"
        if url_exists(cd_url):
            download_and_extract(f"CD_{fips}", cd_url, layer_dirs["CD"])

        sldu_url = f"https://www2.census.gov/geo/tiger/TIGER{resolved_year}/SLDU/tl_{resolved_year}_{fips}_sldu.zip"
        if url_exists(sldu_url):
            download_and_extract(f"SLDU_{fips}", sldu_url, layer_dirs["SLDU"])

        sldl_url = f"https://www2.census.gov/geo/tiger/TIGER{resolved_year}/SLDL/tl_{resolved_year}_{fips}_sldl.zip"
        if url_exists(sldl_url):
            download_and_extract(f"SLDL_{fips}", sldl_url, layer_dirs["SLDL"])

        place_url = f"https://www2.census.gov/geo/tiger/TIGER{resolved_year}/PLACE/tl_{resolved_year}_{fips}_place.zip"
        if url_exists(place_url):
            download_and_extract(f"PLACE_{fips}", place_url, layer_dirs["PLACE"])

        unsd_url = f"https://www2.census.gov/geo/tiger/TIGER{resolved_year}/UNSD/tl_{resolved_year}_{fips}_unsd.zip"
        if url_exists(unsd_url):
            download_and_extract(f"UNSD_{fips}", unsd_url, layer_dirs["UNSD"])

    failures = []

    md_base = "https://mdgeodata.md.gov/imap/rest/services/Boundaries/MD_ElectionBoundaries/MapServer"
    print("Downloading Maryland iMAP election boundaries (GeoJSON)...")
    if not download_arcgis_layer_geojson(f"{md_base}/0", os.path.join(DATA_DIR, "MD", "congressional_2022.geojson")):
        failures.append({"layer": "MD_ELECTION_2022_CD", "url": f"{md_base}/0"})
    if not download_arcgis_layer_geojson(f"{md_base}/1", os.path.join(DATA_DIR, "MD", "delegate_subdistricts_2022.geojson")):
        failures.append({"layer": "MD_DELEGATE_SUBDISTRICTS_2022", "url": f"{md_base}/1"})
    if not download_arcgis_layer_geojson(f"{md_base}/2", os.path.join(DATA_DIR, "MD", "precincts_2026.geojson")):
        failures.append({"layer": "MD_PRECINCTS_2026", "url": f"{md_base}/2"})

    print("Downloading Washington, DC operational boundaries (GeoJSON)...")
    dc_admin = "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Administrative_Other_Boundaries_WebMercator/MapServer"
    if not download_arcgis_layer_geojson(f"{dc_admin}/53", os.path.join(DATA_DIR, "DC", "wards_2022.geojson")):
        failures.append({"layer": "DC_WARDS_2022", "url": f"{dc_admin}/53"})
    if not download_arcgis_layer_geojson(f"{dc_admin}/54", os.path.join(DATA_DIR, "DC", "anc_2023.geojson")):
        failures.append({"layer": "DC_ANC_2023", "url": f"{dc_admin}/54"})
    if not download_arcgis_layer_geojson(f"{dc_admin}/55", os.path.join(DATA_DIR, "DC", "smd_2023.geojson")):
        failures.append({"layer": "DC_SMD_2023", "url": f"{dc_admin}/55"})

    dc_education = "https://maps2.dcgis.dc.gov/DCGIS/rest/services/DCGIS_DATA/Education_WebMercator/MapServer"
    if not download_arcgis_layer_geojson(f"{dc_education}/9", os.path.join(DATA_DIR, "DC", "sboe_districts.geojson")):
        failures.append({"layer": "DC_SBOE_DISTRICTS", "url": f"{dc_education}/9"})

    print("Downloading Virginia local election layers (GeoJSON)...")
    fairfax_supervisor = "https://www.fairfaxcounty.gov/idrisi/rest/services/Jade/Electoral/MapServer/2"
    if not download_arcgis_layer_geojson(fairfax_supervisor, os.path.join(DATA_DIR, "VA", "fairfax_supervisor_districts.geojson")):
        failures.append({"layer": "VA_FAIRFAX_SUPERVISOR_DISTRICTS", "url": fairfax_supervisor})

    loudoun_base = "https://logis.loudoun.gov/gis/rest/services/COL/ElectionDistricts/MapServer"
    if not download_arcgis_layer_geojson(f"{loudoun_base}/8", os.path.join(DATA_DIR, "VA", "loudoun_election_districts_2022.geojson")):
        failures.append({"layer": "VA_LOUDOUN_ELECTION_DISTRICTS_2022", "url": f"{loudoun_base}/8"})
    if not download_arcgis_layer_geojson(f"{loudoun_base}/3", os.path.join(DATA_DIR, "VA", "loudoun_precincts.geojson")):
        failures.append({"layer": "VA_LOUDOUN_PRECINCTS", "url": f"{loudoun_base}/3"})
    if not download_arcgis_layer_geojson(f"{loudoun_base}/0", os.path.join(DATA_DIR, "VA", "loudoun_polling_places.geojson")):
        failures.append({"layer": "VA_LOUDOUN_POLLING_PLACES", "url": f"{loudoun_base}/0"})

    meta = {
        "tiger_year": resolved_year,
        "refreshed_at_utc": datetime.now(timezone.utc).isoformat(),
        "failures": failures
    }
    with open(os.path.join(DATA_DIR, ".data_metadata.json"), "w") as f:
        json.dump(meta, f)

    return meta

if __name__ == "__main__":
    run_download()
