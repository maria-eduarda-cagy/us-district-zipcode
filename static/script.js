let map;
let marker;
let districtLayers = [];

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    document.getElementById('search-btn').addEventListener('click', handleSearch);
    
    const addressInput = document.getElementById('address-input');
    addressInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    // Autocomplete logic
    addressInput.addEventListener('input', debounce(handleAutocomplete, 300));
    
    // Close suggestions when clicking outside
    document.addEventListener('click', (e) => {
        if (e.target.id !== 'address-input') {
            closeAllLists();
        }
    });
});

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

async function handleAutocomplete() {
    const val = document.getElementById('address-input').value;
    closeAllLists();
    if (!val || val.length < 3) return;

    try {
        // Using ArcGIS Suggest API (Free and great for US addresses)
        const url = `https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/suggest?text=${encodeURIComponent(val)}&f=json&countryCode=USA&maxSuggestions=5`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.suggestions) {
            const list = document.getElementById('autocomplete-list');
            data.suggestions.forEach(suggestion => {
                const item = document.createElement('div');
                item.innerHTML = `<strong>${suggestion.text}</strong>`;
                item.addEventListener('click', () => {
                    document.getElementById('address-input').value = suggestion.text;
                    closeAllLists();
                    handleSearch();
                });
                list.appendChild(item);
            });
        }
    } catch (error) {
        console.error('Autocomplete error:', error);
    }
}

function closeAllLists() {
    const list = document.getElementById('autocomplete-list');
    list.innerHTML = '';
}

function initMap() {
    map = L.map('map').setView([37.0902, -95.7129], 4); // Center of US
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
}

const DISTRICT_COLORS = {
    'CD': '#3498db',      // Blue for Congressional
    'SLDU': '#e67e22',    // Orange for State Senate
    'SLDL': '#2ecc71',    // Green for State House
    'COUNTY': '#9b59b6',  // Purple for County
    'PLACE': '#f1c40f',   // Yellow for City/Place
    'SCHOOL': '#e74c3c',  // Red for School Districts
    'default': '#95a5a6'
};

function getDistrictColor(type) {
    return DISTRICT_COLORS[type] || DISTRICT_COLORS['default'];
}

async function handleSearch() {
    const address = document.getElementById('address-input').value;
    if (!address) return;

    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading">Searching...</div>';

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to find address');
        }

        const data = await response.json();
        updateUI(data);
    } catch (error) {
        resultsDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    }
}

function updateUI(data) {
    const { lat, lon, jurisdictions } = data;

    // Update Map
    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lon]).addTo(map)
        .bindPopup("Sua Localização")
        .openPopup();
    
    map.setView([lat, lon], 12);

    // Clear old layers
    districtLayers.forEach(item => map.removeLayer(item.layer));
    districtLayers = [];
    
    // Clear Layer Control overlays
    for (let key in overlays) {
        map.removeLayer(overlays[key]);
        layerControl.removeLayer(overlays[key]);
    }
    overlays = {};

    if (!jurisdictions || jurisdictions.length === 0) {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = '<p class="placeholder">Endereço encontrado, mas nenhuma jurisdição legislativa corresponde a esta localização específica.</p>';
        return;
    }

    // Organizar por níveis e agrupar camadas por tipo
    const levels = { 'Federal': [], 'State': [], 'Local': [] };
    const typeGroups = {};

    jurisdictions.forEach(jur => {
        const color = getDistrictColor(jur.type);
        
        // Group offices/measures
        jur.offices.forEach(office => {
            levels[office.level].push({ ...office, jurName: jur.name, jurId: jur.id, jurType: jur.type });
        });
        jur.measures.forEach(measure => {
            levels[measure.level].push({ isMeasure: true, ...measure, jurName: jur.name, jurId: jur.id, jurType: jur.type });
        });

        // Add to map groups
        if (jur.geometry) {
            const layer = L.geoJSON(jur.geometry, {
                style: {
                    color: color,
                    weight: 2,
                    opacity: 0.5,
                    fillColor: color,
                    fillOpacity: 0.1
                }
            });
            layer.bindPopup(`<strong>${jur.name}</strong><br>Tipo: ${jur.type}`);
            
            if (!typeGroups[jur.type]) {
                typeGroups[jur.type] = L.layerGroup().addTo(map);
                const typeLabels = {
                    'CD': 'Congresso (CD)',
                    'SLDU': 'Senado Estadual (SLDU)',
                    'SLDL': 'Câmara Estadual (SLDL)',
                    'COUNTY': 'Condado (County)',
                    'PLACE': 'Município (Place)',
                    'SCHOOL': 'Distrito Escolar (School)'
                };
                layerControl.addOverlay(typeGroups[jur.type], typeLabels[jur.type] || jur.type);
                overlays[jur.type] = typeGroups[jur.type];
            }
            typeGroups[jur.type].addLayer(layer);
            districtLayers.push({ id: jur.id, type: jur.type, layer: layer });
        }
    });

    // Render Ballot
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';
    
    const intro = document.createElement('p');
    intro.className = 'ballot-intro';
    intro.innerHTML = `Para o seu endereço, você votará nos seguintes cargos e medidas no ciclo de <strong>2026</strong>:`;
    resultsDiv.appendChild(intro);

    ['Federal', 'State', 'Local'].forEach(level => {
        if (levels[level].length > 0) {
            const levelHeader = document.createElement('h3');
            levelHeader.className = 'level-header';
            levelHeader.innerText = level;
            resultsDiv.appendChild(levelHeader);

            levels[level].forEach(item => {
                const card = document.createElement('div');
                card.className = 'ballot-card';
                const color = getDistrictColor(item.jurType);
                card.style.borderLeft = `5px solid ${color}`;

                if (item.isMeasure) {
                    card.innerHTML = `
                        <div class="ballot-item-header">
                            <span class="item-name">${item.title}</span>
                            <span class="jur-tag" style="background-color: ${color}">${item.jurType}</span>
                        </div>
                        <div class="measure-impact">
                            <p><strong>Voto SIM:</strong> ${item.impact_yes}</p>
                            <p><strong>Voto NÃO:</strong> ${item.impact_no}</p>
                        </div>
                        <span class="view-on-map" onclick="focusJurisdiction('${item.jurId}', '${item.jurType}')">Focar nesta jurisdição</span>
                    `;
                } else {
                    const isLegislative = ['CD', 'SLDL', 'SLDU'].includes(item.jurType);
                    const displayName = isLegislative ? `<strong>${item.jurId}</strong> - ${item.jurName}` : item.jurName;
                    
                    card.innerHTML = `
                        <div class="ballot-item-header">
                            <span class="item-name">${item.name}</span>
                            <span class="jur-tag" style="background-color: ${color}">${item.jurType}</span>
                        </div>
                        <p class="jur-name">${displayName}</p>
                        <p class="office-desc">${item.description || ''}</p>
                        <span class="view-on-map" onclick="focusJurisdiction('${item.jurId}', '${item.jurType}')">Focar nesta jurisdição</span>
                    `;
                }
                resultsDiv.appendChild(card);
            });
        }
    });
}

function focusJurisdiction(id, type) {
    districtLayers.forEach(item => {
        if (item.id === id && item.type === type) {
            // Highlight the selected layer
            item.layer.setStyle({
                fillOpacity: 0.4,
                weight: 4,
                opacity: 1
            });
            map.fitBounds(item.layer.getBounds());
            item.layer.openPopup();
        } else {
            // Reset other layers to default
            const color = getDistrictColor(item.type);
            item.layer.setStyle({
                color: color,
                weight: 2,
                opacity: 0.5,
                fillColor: color,
                fillOpacity: 0.1
            });
        }
    });
}
