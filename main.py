import os
import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json

app = FastAPI()

# Configuration
DATA_DIR = "data"
BENCHMARK = "Public_AR_Current"

# Global storage for GeoDataFrames
GDFs = {}

def load_shapefiles():
    paths = {
        "CD": os.path.join(DATA_DIR, "CD"),
        "SLDL": os.path.join(DATA_DIR, "SLDL"),
        "SLDU": os.path.join(DATA_DIR, "SLDU"),
        "COUNTY": os.path.join(DATA_DIR, "COUNTY"),
        "PLACE": os.path.join(DATA_DIR, "PLACE"),
        "SCHOOL": os.path.join(DATA_DIR, "UNSD")
    }
    
    for key, path in paths.items():
        if os.path.exists(path):
            # Encontra todos os arquivos .shp na pasta
            shp_files = [f for f in os.listdir(path) if f.endswith(".shp")]
            if not shp_files:
                GDFs[key] = None
                continue
                
            gdfs_to_concat = []
            for shp in shp_files:
                full_path = os.path.join(path, shp)
                print(f"Loading {shp}...")
                try:
                    temp_gdf = gpd.read_file(full_path)
                    if temp_gdf.crs != "EPSG:4326":
                        temp_gdf = temp_gdf.to_crs("EPSG:4326")
                    gdfs_to_concat.append(temp_gdf)
                except Exception as e:
                    print(f"Error loading {shp}: {e}")
            
            if gdfs_to_concat:
                print(f"Merging {len(gdfs_to_concat)} files for {key}...")
                GDFs[key] = gpd.GeoDataFrame(pd.concat(gdfs_to_concat, ignore_index=True))
                # Criar índice espacial para busca ultra-rápida
                GDFs[key].sindex 

@app.on_event("startup")
async def startup_event():
    print("Starting up...")
    # Em um ambiente nacional real, carregaríamos sob demanda ou usaríamos um DB espacial
    # Para o MVP, carregamos o que estiver disponível na pasta data
    load_shapefiles()
    print("Startup complete.")

class AddressSearch(BaseModel):
    address: str

class Office(BaseModel):
    name: str
    level: str # Federal, State, Local
    description: Optional[str] = None

class BallotMeasure(BaseModel):
    title: str
    level: str
    impact_yes: str
    impact_no: str

class Jurisdiction(BaseModel):
    id: str
    name: str
    type: str # CD, SLDL, SLDU, COUNTY, PLACE, SCHOOL
    offices: List[Office]
    measures: List[BallotMeasure] = []
    geometry: Optional[dict] = None

class SearchResult(BaseModel):
    lat: float
    lon: float
    jurisdictions: List[Jurisdiction]

def get_offices_for_jurisdiction(dist_type: str) -> List[Office]:
    mapping = {
        "CD": [Office(name="U.S. Representative", level="Federal", description="Representante no Congresso dos EUA")],
        "SLDU": [Office(name="State Senator", level="State", description="Senador Estadual")],
        "SLDL": [Office(name="State Representative", level="State", description="Representante Estadual")],
        "COUNTY": [
            Office(name="Sheriff", level="Local", description="Xerife do Condado"),
            Office(name="County Commissioner", level="Local", description="Comissário do Condado"),
            Office(name="District Attorney", level="Local", description="Promotor de Justiça")
        ],
        "PLACE": [
            Office(name="Mayor", level="Local", description="Prefeito Municipal"),
            Office(name="City Council", level="Local", description="Vereador/Conselho Municipal")
        ],
        "SCHOOL": [Office(name="School Board Member", level="Local", description="Membro do Conselho Escolar")]
    }
    return mapping.get(dist_type, [])

def get_measures_for_jurisdiction(dist_type: str, name: str) -> List[BallotMeasure]:
    measures = []
    if dist_type == "PLACE":
        measures.append(BallotMeasure(
            title=f"Referendo Municipal - {name}",
            level="Local",
            impact_yes="Aprova o financiamento para novos parques.",
            impact_no="Mantém o orçamento atual."
        ))
    elif dist_type == "SLDU":
        measures.append(BallotMeasure(
            title="Emenda Constitucional Estadual 1",
            level="State",
            impact_yes="Protege direitos ambientais na constituição.",
            impact_no="Nenhuma mudança na constituição."
        ))
    return measures

@app.post("/api/search", response_model=SearchResult)
async def search_address(data: AddressSearch):
    # 1. Geocoding using ArcGIS REST API (More robust and matches autocomplete)
    geocode_url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
    params = {
        "address": data.address,
        "f": "json",
        "outFields": "Addr_type,Score",
        "maxLocations": 1,
        "countryCode": "USA"
    }
    
    response = requests.get(geocode_url, params=params)
    print(f"Geocoding request for: {data.address}")
    if response.status_code != 200:
        print(f"Geocoding API error: {response.status_code}")
        raise HTTPException(status_code=500, detail="Geocoding service unavailable")
    
    candidates = response.json().get("candidates", [])
    print(f"Found {len(candidates)} candidates")
    
    if not candidates:
        print("No candidates found in API response")
        raise HTTPException(status_code=404, detail="Endereço não encontrado.")
    
    match = candidates[0]
    lat = match["location"]["y"]
    lon = match["location"]["x"]
    point = Point(lon, lat)
    
    # 2. Point-in-Polygon Logic
    districts = []
    
    for key, gdf in GDFs.items():
        if gdf is None or gdf.empty:
            continue
            
        # Find which polygon contains the point using spatial index for performance
        try:
            possible_matches_index = gdf.sindex.query(point, predicate="intersects")
            containing_districts = gdf.iloc[possible_matches_index]
            # Refine to ensure exact containment
            containing_districts = containing_districts[containing_districts.contains(point)]
        except Exception as e:
            print(f"Error querying {key}: {e}")
            continue
        
        for _, row in containing_districts.iterrows():
            # Get internal ID and Name based on layer type
            if key == "CD":
                cd_col = 'CD119FP' if 'CD119FP' in row else ('CD118FP' if 'CD118FP' in row else 'DISTRICT')
                dist_id = f"{row['STATEFP']}{row.get(cd_col, '??')}"
            elif key == "SLDL":
                dist_id = f"{row['STATEFP']}{row['SLDLST']}"
            elif key == "SLDU":
                dist_id = f"{row['STATEFP']}{row['SLDUST']}"
            elif key == "COUNTY":
                dist_id = f"{row['STATEFP']}{row['COUNTYFP']}"
            elif key == "PLACE":
                dist_id = f"{row['STATEFP']}{row['PLACEFP']}"
            elif key == "SCHOOL":
                dist_id = f"{row['STATEFP']}{row['UNSDLEA']}"
            else:
                dist_id = "Unknown"

            name = row.get('NAMELSAD', row.get('NAME', 'Unknown Jurisdiction'))

            # Convert geometry to GeoJSON for frontend
            geo_json = json.loads(gpd.GeoSeries([row.geometry]).to_json())['features'][0]['geometry']

            jurisdictions.append(Jurisdiction(
                id=dist_id,
                name=name,
                type=key,
                offices=get_offices_for_jurisdiction(key),
                measures=get_measures_for_jurisdiction(key, name),
                geometry=geo_json
            ))

    return SearchResult(lat=lat, lon=lon, jurisdictions=jurisdictions)

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
