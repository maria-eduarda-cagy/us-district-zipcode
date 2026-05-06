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
    const { lat, lon, districts } = data;

    // Update Map
    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lon]).addTo(map)
        .bindPopup("Your Location")
        .openPopup();
    
    map.setView([lat, lon], 12);

    // Clear old district layers
    districtLayers.forEach(layer => map.removeLayer(layer));
    districtLayers = [];

    // Update Results Panel
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';

    if (districts.length === 0) {
        resultsDiv.innerHTML = '<p class="placeholder">Address found, but no legislative districts match this specific location.</p>';
        return;
    }

    districts.forEach(dist => {
        const color = getDistrictColor(dist.type);
        let layer;
        
        // Render District Polygon
        if (dist.geometry) {
            layer = L.geoJSON(dist.geometry, {
                style: {
                    color: color,
                    weight: 2,
                    opacity: 0.5,
                    fillColor: color,
                    fillOpacity: 0.1
                }
            }).addTo(map);
            
            layer.bindPopup(`<strong>${dist.name}</strong><br>ID: ${dist.id}`);
            districtLayers.push(layer);
        }

        const card = document.createElement('div');
        card.className = 'district-card';
        card.style.borderLeft = `5px solid ${color}`;

        let candidateHtml = '';
        if (dist.candidates && dist.candidates.length > 0) {
            candidateHtml = `
                <div class="candidate-list">
                    ${dist.candidates.map(c => `
                        <div class="candidate-item">
                            <div class="candidate-name">${c.name}</div>
                            <div class="candidate-party">${c.party} - ${c.office}</div>
                            ${c.bio ? `<div class="candidate-bio"><strong>Bio:</strong> ${c.bio}</div>` : ''}
                            ${c.survey ? `<div class="candidate-survey"><strong>Pesquisa:</strong> ${c.survey}</div>` : ''}
                            ${c.context ? `<div class="candidate-context"><strong>Impacto:</strong> ${c.context}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            candidateHtml = '<p>No candidates found.</p>';
        }

        card.innerHTML = `
            <div class="district-header">
                <h3>${dist.name || 'Unknown Name'}</h3>
                <span class="district-type-tag" style="background-color: ${color}">${dist.type}</span>
            </div>
            <p><strong>ID:</strong> ${dist.id}</p>
            <span class="view-on-map" onclick="highlightDistrict('${dist.id}')">Destacar no Mapa</span>
            <h4>Sample Ballot:</h4>
            ${candidateHtml}
        `;
        resultsDiv.appendChild(card);
    });
}

function highlightDistrict(distId) {
    districtLayers.forEach(layer => {
        const layerDistId = layer.getLayers()[0].feature.id || layer.getLayers()[0].feature.properties.id; 
        // Note: In real app, we'd ensure ID is in properties
        
        // Simplified for MVP: Highlight by color/opacity
        layer.setStyle({
            fillOpacity: 0.4,
            weight: 4,
            opacity: 1
        });
        
        // In a real implementation, we would match the specific layer by ID
    });
}
