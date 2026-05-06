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

class Candidate(BaseModel):
    name: str
    office: str
    party: str
    bio: Optional[str] = "Biografia não disponível no momento."
    survey: Optional[str] = "Este candidato ainda não respondeu à pesquisa de eleitores."
    context: Optional[str] = None # Para medidas de votação (Sim/Não impacto)

class DistrictInfo(BaseModel):
    id: str
    name: str
    type: str # CD, SLDL, SLDU, COUNTY, PLACE, SCHOOL
    candidates: List[Candidate]
    geometry: Optional[dict] = None

class SearchResult(BaseModel):
    lat: float
    lon: float
    districts: List[DistrictInfo]

# Mock candidate database (In real life, connect to Ballotpedia or similar)
CANDIDATE_DB = {
    "2705": [ # MN Congressional District 5
        Candidate(name="Ilhan Omar", office="U.S. Representative", party="Democratic"),
        Candidate(name="Dalia Al-Aqidi", office="U.S. Representative", party="Republican")
    ],
    "27061A": [ # MN State House 61A
        Candidate(name="Katie Jones", office="State Representative", party="Democratic")
    ],
    "27061": [ # MN State Senate 61
        Candidate(name="Scott Dibble", office="State Senator", party="Democratic")
    ],
    "SCHOOL_BOARD_MN_MPS": [
        Candidate(name="Kim Ellison", office="School Board Member", party="Non-partisan"),
        Candidate(name="Adriana Cerrillo", office="School Board Member", party="Non-partisan")
    ],
    "LOCAL_MEASURES_MN": [
        Candidate(name="Referendum 1", office="School Funding Measure", party="N/A"),
        Candidate(name="Amendment 1", office="Constitutional Amendment", party="N/A")
    ]
}

def get_candidates(district_id: str, dist_type: str) -> List[Candidate]:
    candidates = []
    
    # Simulação de candidatos com contexto enriquecido
    if dist_type == "CD":
        candidates.append(Candidate(
            name="Candidato Federal", 
            office="U.S. Representative", 
            party="Independente",
            bio="Veterano com 20 anos de serviço público focado em transparência governamental.",
            survey="Prioriza a reforma do financiamento de campanha e infraestrutura nacional."
        ))
    elif dist_type == "COUNTY":
        candidates.append(Candidate(
            name="Xerife Local", 
            office="County Sheriff", 
            party="Não-partidário",
            bio="Delegado de carreira com mestrado em Segurança Pública.",
            survey="Propõe patrulhamento comunitário e modernização tecnológica da frota."
        ))
    elif dist_type == "SCHOOL":
        candidates.append(Candidate(
            name="Conselheiro Escolar", 
            office="School Board Member", 
            party="Não-partidário",
            bio="Professor aposentado e pai de três alunos da rede pública.",
            survey="Foco na expansão de programas de artes e saúde mental nas escolas."
        ))
    elif dist_type == "PLACE":
        candidates.append(Candidate(
            name="Prefeito Municipal", 
            office="Mayor", 
            party="Democrata",
            bio="Ex-vereador focado em desenvolvimento urbano sustentável.",
            survey="Planeja aumentar ciclovias e investir em habitação acessível."
        ))
        candidates.append(Candidate(
            name="Referendo sobre Parques",
            office="Medida de Votação (Local)",
            party="N/A",
            context="Um voto 'Sim' aprova o aumento de 0.5% no imposto sobre vendas para financiar parques. Um voto 'Não' mantém a taxa atual e o orçamento atual dos parques."
        ))
    elif dist_type == "JUDICIAL":
        candidates.append(Candidate(
            name="Juiz Distrital",
            office="District Judge",
            party="Não-partidário",
            bio="Juiz com 15 anos de experiência em varas de família e criminais.",
            survey="Foco na redução da reincidência através de programas de reabilitação."
        ))

    if not candidates:
        candidates.append(Candidate(name="Candidato Genérico", office="Cargo Local", party="Independente"))
        
    return candidates

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

            districts.append(DistrictInfo(
                id=dist_id,
                name=name,
                type=key,
                candidates=get_candidates(dist_id, key),
                geometry=geo_json
            ))

    return SearchResult(lat=lat, lon=lon, districts=districts)

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
