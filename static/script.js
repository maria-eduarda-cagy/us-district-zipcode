let map;
let marker;
let districtLayers = [];
let layerControl;
let overlays = {};

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

    // Initialize Layer Control
    layerControl = L.control.layers(null, null, { collapsed: false }).addTo(map);
}

const DISTRICT_COLORS = {
    'CD': '#3498db',      // Blue for Congressional
    'SLDU': '#e67e22',    // Orange for State Senate
    'SLDL': '#2ecc71',    // Green for State House
    'COUNTY': '#9b59b6',  // Purple for County
    'PLACE': '#f1c40f',   // Yellow for City/Place
    'SCHOOL': '#e74c3c',  // Red for School Districts
    'DC_WARDS_2022': '#1abc9c',
    'DC_ANC_2023': '#16a085',
    'DC_SMD_2023': '#27ae60',
    'DC_SBOE_DISTRICTS': '#c0392b',
    'VA_FAIRFAX_SUPERVISOR_DISTRICTS': '#8e44ad',
    'VA_LOUDOUN_ELECTION_DISTRICTS_2022': '#7f8c8d',
    'VA_LOUDOUN_PRECINCTS': '#34495e',
    'default': '#95a5a6'
};

function hashStringToInt(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) - hash) + str.charCodeAt(i);
        hash |= 0;
    }
    return hash >>> 0;
}

function getDistrictColor(type, id) {
    const key = `${type || 'default'}:${id || ''}`;
    const h = hashStringToInt(key) % 360;
    const s = 62 + (hashStringToInt(key + ':s') % 18);
    const l = 42 + (hashStringToInt(key + ':l') % 10);
    return `hsl(${h}, ${s}%, ${l}%)`;
}

async function handleSearch() {
    const address = document.getElementById('address-input').value;
    if (!address) return;

    closeAllLists();

    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading">Searching...</div>';

    try {
        const includeDownballot = Boolean(document.getElementById('include-downballot')?.checked);
        const sampleBallotUrl = `/api/sample-ballot?include_downballot=${includeDownballot ? 'true' : 'false'}`;

        const [searchResult, sampleResult] = await Promise.allSettled([
            fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address })
            }),
            fetch(sampleBallotUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address })
            })
        ]);

        if (searchResult.status !== 'fulfilled') {
            throw new Error('Failed to find address');
        }

        const response = searchResult.value;
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to find address');
        }
        const data = await response.json();

        let sampleBallot = null;
        let sampleBallotError = null;
        if (sampleResult.status === 'fulfilled') {
            const sbResp = sampleResult.value;
            if (sbResp.ok) {
                sampleBallot = await sbResp.json();
            } else {
                try {
                    const err = await sbResp.json();
                    sampleBallotError = err.detail || 'Failed to generate sample ballot';
                } catch {
                    sampleBallotError = 'Failed to generate sample ballot';
                }
            }
        } else {
            sampleBallotError = 'Failed to generate sample ballot';
        }

        updateUI(data, sampleBallot, sampleBallotError);
    } catch (error) {
        resultsDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    }
}

function updateUI(data, sampleBallot, sampleBallotError) {
    const { lat, lon, jurisdictions } = data;

    // Update Map
    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lon]).addTo(map)
        .bindPopup("Your Location")
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
        resultsDiv.innerHTML = '<p class="placeholder">Address found, but no legislative jurisdictions match this specific location.</p>';
        return;
    }

    // Organize by levels and group layers by type
    const levels = { 'Federal': [], 'State': [], 'Local': [] };
    const typeGroups = {};

    jurisdictions.forEach(jur => {
        const color = getDistrictColor(jur.type, jur.id);
        
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
            layer.bindPopup(`<strong>${jur.name}</strong><br>Type: ${jur.type}`);
            
            if (!typeGroups[jur.type]) {
                typeGroups[jur.type] = L.layerGroup().addTo(map);
                const typeLabels = {
                    'CD': 'Congressional (CD)',
                    'SLDU': 'State Senate (SLDU)',
                    'SLDL': 'State House (SLDL)',
                    'COUNTY': 'County',
                    'PLACE': 'City/Place',
                    'SCHOOL': 'School District',
                    'DC_WARDS_2022': 'DC Wards',
                    'DC_ANC_2023': 'DC ANCs',
                    'DC_SMD_2023': 'DC SMDs',
                    'DC_SBOE_DISTRICTS': 'DC School Board Districts',
                    'VA_FAIRFAX_SUPERVISOR_DISTRICTS': 'Fairfax Supervisor Districts',
                    'VA_LOUDOUN_ELECTION_DISTRICTS_2022': 'Loudoun Election Districts',
                    'VA_LOUDOUN_PRECINCTS': 'Loudoun Precincts'
                };
                layerControl.addOverlay(typeGroups[jur.type], typeLabels[jur.type] || jur.type);
                overlays[jur.type] = typeGroups[jur.type];
            }
            typeGroups[jur.type].addLayer(layer);
            districtLayers.push({ id: jur.id, type: jur.type, layer: layer, color });
        }
    });

    // Render Ballot
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';
    
    const calData = jurisdictions.find(j => j.primary_election_date && j.general_election_date);
    if (calData) {
        const calendarSection = document.createElement('div');
        calendarSection.className = 'calendar-section';
        calendarSection.innerHTML = `
            <h3 class="section-title">Voter Calendar</h3>
            <div class="calendar-grid">
                <div class="calendar-card primary">
                    <h4>Primary Election</h4>
                    <p><strong>Election Day:</strong> ${calData.primary_election_date}</p>
                    ${calData.primary_early_voting_period ? `<p><strong>Early Voting:</strong> ${calData.primary_early_voting_period}</p>` : ''}
                </div>
                <div class="calendar-card general">
                    <h4>General Election</h4>
                    <p><strong>Election Day:</strong> ${calData.general_election_date}</p>
                    ${calData.general_early_voting_period ? `<p><strong>Early Voting:</strong> ${calData.general_early_voting_period}</p>` : ''}
                </div>
            </div>
            <div class="poll-info">
                ${calData.poll_hours ? `<p><strong>Poll Hours:</strong> ${calData.poll_hours}</p>` : ''}
                ${calData.official_polling_link ? `<a href="${calData.official_polling_link}" target="_blank" class="official-link">Find My Polling Place (Official)</a>` : ''}
            </div>
        `;
        resultsDiv.appendChild(calendarSection);
    }

    const ballotSection = document.createElement('div');
    ballotSection.className = 'sample-ballot-section';
    ballotSection.innerHTML = `<h3 class="section-title">Ballot Summary</h3>`;

    const ballotNote = document.createElement('p');
    ballotNote.className = 'sample-ballot-note';
    ballotNote.innerText = 'Offices are generated from geocoding + district layers (no candidates). Measures come from the jurisdiction cards.';
    ballotSection.appendChild(ballotNote);

    const officesHeader = document.createElement('h3');
    officesHeader.className = 'level-header';
    officesHeader.innerText = 'Offices';
    ballotSection.appendChild(officesHeader);

    if (sampleBallotError) {
        const warn = document.createElement('p');
        warn.className = 'sample-ballot-warning';
        warn.innerText = `Sample ballot unavailable: ${sampleBallotError}`;
        ballotSection.appendChild(warn);
    } else if (sampleBallot && Array.isArray(sampleBallot.contests) && sampleBallot.contests.length > 0) {
        sampleBallot.contests.forEach(contest => {
            const card = document.createElement('div');
            card.className = 'sample-ballot-card';

            const scopeLabel = contest.scope === 'at_large' ? 'At-large' : 'District';
            const rcvLabel = contest.ranked_choice_voting ? 'Ranked-choice voting' : '';

            const auditLink = contest.source_url
                ? `<a href="${contest.source_url}" target="_blank" class="sample-source-link">Source</a>`
                : '';
            const districtLine = contest.district_name
                ? `<p class="sample-district">${contest.district_name}</p>`
                : '';
            const districtIdLine = contest.district_id
                ? `<p class="sample-district-id">${contest.district_id}</p>`
                : '';

            card.innerHTML = `
                <div class="sample-ballot-header">
                    <span class="sample-office">${contest.office_name}</span>
                    <div class="sample-tags">
                        <span class="sample-tag level">${contest.jurisdiction_level}</span>
                        <span class="sample-tag scope">${scopeLabel}</span>
                    </div>
                </div>
                ${districtIdLine}
                ${districtLine}
                <div class="sample-audit">
                    ${contest.district_layer_type ? `<span class="sample-layer">${contest.district_layer_type}</span>` : ''}
                    ${rcvLabel ? `<span class="sample-rcv">${rcvLabel}</span>` : ''}
                    ${auditLink}
                </div>
            `;
            ballotSection.appendChild(card);
        });
    } else {
        const empty = document.createElement('p');
        empty.className = 'sample-ballot-note';
        empty.innerText = 'No offices were generated for this address.';
        ballotSection.appendChild(empty);
    }

    const measuresOnly = []
        .concat(levels['Federal'].filter(x => x.isMeasure))
        .concat(levels['State'].filter(x => x.isMeasure))
        .concat(levels['Local'].filter(x => x.isMeasure));

    const measuresHeader = document.createElement('h3');
    measuresHeader.className = 'level-header';
    measuresHeader.innerText = 'Measures';
    ballotSection.appendChild(measuresHeader);

    if (measuresOnly.length === 0) {
        const none = document.createElement('p');
        none.className = 'sample-ballot-note';
        none.innerText = 'No measures were listed for this address.';
        ballotSection.appendChild(none);
    } else {
        measuresOnly.forEach(item => {
            const card = document.createElement('div');
            card.className = 'ballot-card';
            const color = getDistrictColor(item.jurType, item.jurId);
            card.style.borderLeft = `5px solid ${color}`;

            card.innerHTML = `
                <div class="ballot-item-header">
                    <span class="item-name">${item.title}</span>
                    <span class="jur-tag" style="background-color: ${color}">${item.jurType}</span>
                </div>
                <div class="measure-impact">
                    <p><strong>YES Vote:</strong> ${item.impact_yes}</p>
                    <p><strong>NO Vote:</strong> ${item.impact_no}</p>
                </div>
                <div class="election-type-tag">${item.election_type}</div>
                <span class="view-on-map" onclick="focusJurisdiction('${item.jurId}', '${item.jurType}')">Focus on Map</span>
            `;
            ballotSection.appendChild(card);
        });
    }

    resultsDiv.appendChild(ballotSection);
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
            const color = item.color || getDistrictColor(item.type, item.id);
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
