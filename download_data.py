import os
import requests
import zipfile

DATA_DIR = "data"
YEAR = "2024"

# URLs para Shapefiles Nacionais (US-wide)
# Lista de FIPS de estados dos EUA
STATE_FIPS = ["24"] # Maryland FIPS

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

if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    # Arquivo Nacional de Condados (County)
    county_url = "https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip"
    download_and_extract("COUNTY_US", county_url, os.path.join(DATA_DIR, "COUNTY"))
    
    # Maryland FIPS
    fips = "24" 
    
    # CD119 (Congresso)
    cd_url = f"https://www2.census.gov/geo/tiger/TIGER2024/CD/tl_2024_{fips}_cd119.zip"
    download_and_extract(f"CD_{fips}", cd_url, os.path.join(DATA_DIR, "CD"))
    
    # SLDU (Senado Estadual)
    sldu_url = f"https://www2.census.gov/geo/tiger/TIGER2024/SLDU/tl_2024_{fips}_sldu.zip"
    download_and_extract(f"SLDU_{fips}", sldu_url, os.path.join(DATA_DIR, "SLDU"))

    # SLDL (Câmara Estadual)
    sldl_url = f"https://www2.census.gov/geo/tiger/TIGER2024/SLDL/tl_2024_{fips}_sldl.zip"
    download_and_extract(f"SLDL_{fips}", sldl_url, os.path.join(DATA_DIR, "SLDL"))

    # Places (Municípios)
    place_url = f"https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_{fips}_place.zip"
    download_and_extract(f"PLACE_{fips}", place_url, os.path.join(DATA_DIR, "PLACE"))

    # Unified School Districts
    unsd_url = f"https://www2.census.gov/geo/tiger/TIGER2024/UNSD/tl_2024_{fips}_unsd.zip"
    download_and_extract(f"UNSD_{fips}", unsd_url, os.path.join(DATA_DIR, "UNSD"))
