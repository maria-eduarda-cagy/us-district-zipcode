# ElectorMap & Downballot Finder

MVP for identifying legislative districts and candidates using address geocoding and TIGER/Line Shapefiles.

## Features
- **Geocoding**: Converts full addresses or ZIP+4 into coordinates using the Census Geocoder API.
- **Point-in-Polygon Logic**: Uses GeoPandas to identify districts from TIGER/Line shapefiles.
- **Interactive Map**: Visualizes the user's location and district boundaries using Leaflet.js.
- **Downballot Data**: Lists candidates for Congress, State Legislature, School Boards, and local measures.

## Setup & Running

1. **Install Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Download Data** (Minnesota focus for MVP):
   ```bash
   python download_data.py
   ```

3. **Run Server**:
   ```bash
   python main.py
   ```

### Running with Docker (Recommended for Build)
Se você deseja realizar um "build" completo e rodar em um ambiente isolado:

1. **Build e Run**:
   ```bash
   docker-compose up --build
   ```

2. **Acesse**: `http://localhost:8000`

4. **Access UI**:
   Open `http://localhost:8000` in your browser.

## Validation
Test address: `3001 Broadway St NE, Minneapolis, MN 55413`
(Note: `3256 Epiphenomenal Ave` is a placeholder address and may not be found by the official Census Geocoder).
