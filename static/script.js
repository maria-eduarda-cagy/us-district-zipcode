let map;
let marker;
let districtLayers = [];
let layerControl;
let overlays = {};
let hasActiveSearch = false;
let clearOnNextPopupClose = false;
let activeDistrictCardKey = null;

// Values injected at runtime via /config.js (generated from environment variables)
const SUPABASE_URL = window.__APP_CONFIG__?.SUPABASE_URL;
const SUPABASE_ANON_KEY = window.__APP_CONFIG__?.SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.error('Missing configuration: SUPABASE_URL/SUPABASE_ANON_KEY were not loaded via /config.js.');
}

// Calculate functions base URL from SUPABASE_URL (as you requested)
const baseUrl = SUPABASE_URL.endsWith("/") ? SUPABASE_URL.slice(0, -1) : SUPABASE_URL;
const SUPABASE_FUNCTIONS_BASE = baseUrl + "/functions/v1";

function supabaseFunctionHeaders() {
    return {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
    };
}

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    document.getElementById('search-btn').addEventListener('click', handleSearch);
    document.getElementById('clear-btn')?.addEventListener('click', clearSearch);
    
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

    document.addEventListener('click', (e) => {
        const target = e.target;
        if (!target || !target.closest) return;
        const closeBtn = target.closest('a.leaflet-popup-close-button');
        if (!closeBtn) return;
        clearOnNextPopupClose = true;
    }, true);

    window.addEventListener('resize', () => {
        if (!map) return;
        clearTimeout(window.__leafletResizeTimer);
        window.__leafletResizeTimer = setTimeout(() => {
            try { map.invalidateSize(); } catch {}
        }, 150);
    });
});

function setSearchActive(active) {
    hasActiveSearch = Boolean(active);
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) {
        clearBtn.disabled = !hasActiveSearch;
    }
}

function clearSearch() {
    closeAllLists();
    clearOnNextPopupClose = false;
    activeDistrictCardKey = null;
    updateDistrictCardFocus(null);
    updateOfficeCardFocus(null);

    const markerToRemove = marker;
    marker = null;
    if (markerToRemove) {
        map.removeLayer(markerToRemove);
    }

    districtLayers.forEach(item => {
        try { map.removeLayer(item.layer); } catch {}
    });
    districtLayers = [];

    for (let key in overlays) {
        try { map.removeLayer(overlays[key]); } catch {}
        try { layerControl.removeLayer(overlays[key]); } catch {}
    }
    overlays = {};

    map.setView([37.0902, -95.7129], 4);

    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<p class="placeholder">Search for an address to see districts and candidates.</p><div id="downballot-results"></div>';

    setSearchActive(false);
}

function updateDistrictCardFocus(activeKey) {
    const cards = document.querySelectorAll('.district-found-card');
    cards.forEach((card) => {
        const key = card.getAttribute('data-jur-key');
        const isActive = activeKey && key === activeKey;
        card.classList.toggle('is-active', Boolean(isActive));
        card.classList.toggle('is-dim', Boolean(activeKey) && !isActive);
    });
}

function updateOfficeCardFocus(activeKey) {
    const cards = document.querySelectorAll('.office-ballot-card');
    cards.forEach((card) => {
        const key = card.getAttribute('data-jur-key');
        const isActive = activeKey && key && key === activeKey;
        card.classList.toggle('is-active', Boolean(isActive));
        card.classList.toggle('is-dim', Boolean(activeKey) && !isActive);
    });
}

function resetDistrictLayerStyles() {
    districtLayers.forEach(item => {
        const color = getDistrictColor(item.type);
        try {
            item.layer.setStyle({
                color: color,
                weight: 2,
                opacity: 0.5,
                fillColor: color,
                fillOpacity: 0.1
            });
        } catch {}
    });
}

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

    map.on('popupclose', () => {
        if (!clearOnNextPopupClose) return;
        clearOnNextPopupClose = false;
        if (activeDistrictCardKey) {
            activeDistrictCardKey = null;
            updateDistrictCardFocus(null);
            updateOfficeCardFocus(null);
            resetDistrictLayerStyles();
            if (marker && marker.getLatLng) {
                try { map.panTo(marker.getLatLng()); } catch {}
                try { marker.openPopup(); } catch {}
            }
            return;
        }
        clearSearch();
    });
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

function getDistrictColor(type) {
    return DISTRICT_COLORS[type] || DISTRICT_COLORS['default'];
}

function partyTagClass(party) {
    if (!party) return 'nonpartisan';
    const p = party.trim().toLowerCase();
    if (p.startsWith('cross')) return 'cross-filed';
    if (p.startsWith('dem')) return 'democratic';
    if (p.startsWith('rep')) return 'republican';
    return 'nonpartisan';
}

function partyTagLabel(party) {
    const cls = partyTagClass(party);
    if (cls === 'cross-filed') return 'Cross-Filing';
    if (cls === 'democratic') return 'Democrat';
    if (cls === 'republican') return 'Republican';
    return 'Non-Partisan';
}

async function handleSearch() {
    const address = document.getElementById('address-input').value;
    if (!address) return;

    closeAllLists();
    if (hasActiveSearch) {
        clearSearch();
    }

    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '<div class="loading">Searching...</div>';

    try {
        const includeDownballot = Boolean(document.getElementById('include-downballot')?.checked);
        const searchUrl = `${SUPABASE_FUNCTIONS_BASE}/search`;
        const sampleBallotUrl = `${SUPABASE_FUNCTIONS_BASE}/sample-ballot?include_downballot=${includeDownballot ? 'true' : 'false'}`;

        const [searchResult, sampleResult] = await Promise.allSettled([
            fetch(searchUrl, {
                method: 'POST',
                headers: supabaseFunctionHeaders(),
                body: JSON.stringify({ address })
            }),
            fetch(sampleBallotUrl, {
                method: 'POST',
                headers: supabaseFunctionHeaders(),
                body: JSON.stringify({ address })
            })
        ]);

        if (searchResult.status !== 'fulfilled') {
            throw new Error('Failed to find address');
        }

        const response = searchResult.value;
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || error.error || 'Failed to find address');
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
                    sampleBallotError = err.detail || err.error || 'Failed to generate sample ballot';
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
    const { lat, lon, memberships } = data;

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

    if (!memberships || memberships.length === 0) {
        const resultsDiv = document.getElementById('results');
        resultsDiv.innerHTML = '<p class="placeholder">Address found, but no legislative jurisdictions match this specific location.</p>';
        setSearchActive(true);
        return;
    }

    const typeGroups = {};

    memberships.forEach(m => {
        const districtTypeKey = m.layer_type || 'default';
        const districtTypeLabel = m.layer_type || 'Unknown';
        const color = getDistrictColor(districtTypeKey);

        if (m.geometry) {
            const layer = L.geoJSON(m.geometry, {
                style: {
                    color: color,
                    weight: 2,
                    opacity: 0.5,
                    fillColor: color,
                    fillOpacity: 0.1
                }
            });

            const popupName = m.district_name || 'District';
            const popupId = m.district_id ? `<br>ID: ${m.district_id}` : '';
            layer.bindPopup(`<strong>${popupName}</strong><br>Type: ${districtTypeLabel}${popupId}`);

            if (!typeGroups[districtTypeKey]) {
                typeGroups[districtTypeKey] = L.layerGroup().addTo(map);
                const typeLabels = {
                    'CD': 'Congressional (CD)',
                    'SLDU': 'State Senate (SLDU)',
                    'SLDL': 'State House (SLDL)',
                    'COUNTY': 'County',
                    'PLACE': 'City/Place',
                    'UNSD': 'School District',
                    'SCHOOL': 'School District',
                    'DC_WARDS_2022': 'DC Wards',
                    'DC_ANC_2023': 'DC ANCs',
                    'DC_SMD_2023': 'DC SMDs',
                    'DC_SBOE_DISTRICTS': 'DC School Board Districts',
                    'VA_FAIRFAX_SUPERVISOR_DISTRICTS': 'Fairfax Supervisor Districts',
                    'VA_LOUDOUN_ELECTION_DISTRICTS_2022': 'Loudoun Election Districts',
                    'VA_LOUDOUN_PRECINCTS': 'Loudoun Precincts'
                };
                layerControl.addOverlay(typeGroups[districtTypeKey], typeLabels[districtTypeKey] || districtTypeLabel);
                overlays[districtTypeKey] = typeGroups[districtTypeKey];
            }
            typeGroups[districtTypeKey].addLayer(layer);
            districtLayers.push({ id: m.district_id, type: districtTypeKey, layer: layer });
        }
    });

    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';

    const districtsTitle = document.createElement('h3');
    districtsTitle.className = 'section-title';
    districtsTitle.innerText = 'Districts Found';
    resultsDiv.appendChild(districtsTitle);

    memberships.forEach(m => {
        const card = document.createElement('div');
        card.className = 'ballot-card district-found-card';
        const color = getDistrictColor(m.layer_type);
        card.style.borderLeft = `5px solid ${color}`;
        const jurKey = `${m.layer_type || ''}:${m.district_id || ''}`;
        card.setAttribute('data-jur-key', jurKey);

        const sourceLink = m.source_url ? `<a href="${m.source_url}" target="_blank" class="sample-source-link">Source</a>` : '';
        const idLine = m.district_id ? `<p class="jur-name"><strong>${m.district_id}</strong></p>` : '';
        const nameLine = m.district_name ? `<p class="jur-name">${m.district_name}</p>` : '';

        card.innerHTML = `
            <div class="ballot-item-header">
                <span class="item-name">${m.layer_type || 'District'}</span>
                <span class="jur-tag" style="background-color: ${color}">${m.layer_type || 'Unknown'}</span>
            </div>
            ${idLine}
            ${nameLine}
            <div class="sample-audit">
                ${sourceLink}
                ${m.district_id && m.layer_type ? `<span class="view-on-map" onclick="focusJurisdiction('${m.district_id}', '${m.layer_type}')">Focus on Map</span>` : ''}
            </div>
        `;
        resultsDiv.appendChild(card);
    });

    updateDistrictCardFocus(activeDistrictCardKey);

    const ballotTitle = document.createElement('h3');
    ballotTitle.className = 'section-title';
    ballotTitle.innerText = 'Offices on Your Ballot';
    resultsDiv.appendChild(ballotTitle);

    if (sampleBallotError) {
        const warn = document.createElement('p');
        warn.className = 'sample-ballot-warning';
        warn.innerText = `Ballot unavailable: ${sampleBallotError}`;
        resultsDiv.appendChild(warn);
        setSearchActive(true);
        return;
    }

    if (sampleBallot && Array.isArray(sampleBallot.contests) && sampleBallot.contests.length > 0) {
        const note = document.createElement('p');
        note.className = 'sample-ballot-note';
        note.innerText = sampleBallot.ballot_status === 'loaded'
            ? 'Candidates and contests from a certified ballot style for this precinct.'
            : 'Generated from authoritative geocoding + district layers.';
        resultsDiv.appendChild(note);

        const levels = { 'Federal': [], 'State': [], 'Local': [] };
        sampleBallot.contests.forEach(c => {
            if (levels[c.jurisdiction_level]) levels[c.jurisdiction_level].push(c);
        });

        ['Federal', 'State', 'Local'].forEach(level => {
            if (levels[level].length === 0) return;
            const levelHeader = document.createElement('h3');
            levelHeader.className = 'level-header';
            levelHeader.innerText = level;
            resultsDiv.appendChild(levelHeader);

            levels[level].forEach(contest => {
                const card = document.createElement('div');
                card.className = 'sample-ballot-card office-ballot-card';

                if (contest.district_layer_type && contest.district_id) {
                    card.setAttribute('data-jur-key', `${contest.district_layer_type}:${contest.district_id}`);
                }

                const scopeLabel = contest.scope === 'at_large' ? 'At-large' : 'District';
                const rcvLabel = contest.ranked_choice_voting ? 'Ranked-choice voting' : '';
                const contestTitle = contest.contest_label || contest.office_name;
                const voteForLabel = contest.vote_for > 1 ? `Vote for up to ${contest.vote_for}` : 'Vote for 1';

                const auditLink = contest.source_url
                    ? `<a href="${contest.source_url}" target="_blank" class="sample-source-link">Source</a>`
                    : '';
                const districtLine = contest.district_name
                    ? `<p class="sample-district">${contest.district_name}</p>`
                    : '';
                const districtIdLine = contest.district_id
                    ? `<p class="sample-district-id">${contest.district_id}</p>`
                    : '';
                const focusLink = (contest.district_id && contest.district_layer_type)
                    ? `<span class="view-on-map" onclick="focusJurisdiction('${contest.district_id}', '${contest.district_layer_type}')">Focus on Map</span>`
                    : '';

                const candidates = Array.isArray(contest.candidates) ? contest.candidates : [];
                const candidatesList = candidates.length > 0
                    ? `<ul class="sample-candidates">${candidates.map(cand => `
                        <li class="sample-candidate">
                            <span class="candidate-name">${cand.name}</span>
                            <span class="candidate-tags">
                                <span class="candidate-tag ${partyTagClass(cand.party)}">${partyTagLabel(cand.party)}</span>
                                ${cand.incumbent ? '<span class="candidate-tag incumbent">Incumbent</span>' : ''}
                                ${cand.unopposed ? '<span class="candidate-tag unopposed">Unopposed</span>' : ''}
                            </span>
                        </li>
                    `).join('')}</ul>`
                    : '<p class="sample-no-candidates">No candidates loaded for this contest yet.</p>';

                card.innerHTML = `
                    <div class="sample-ballot-header">
                        <span class="sample-office">${contestTitle}</span>
                        <div class="sample-tags">
                            <span class="sample-tag level">${contest.jurisdiction_level}</span>
                            <span class="sample-tag scope">${scopeLabel}</span>
                        </div>
                    </div>
                    ${contest.office_name && contest.office_name !== contestTitle ? `<p class="sample-office-category">${contest.office_name}</p>` : ''}
                    <p class="sample-vote-for">${voteForLabel}</p>
                    ${candidatesList}
                    ${districtIdLine}
                    ${districtLine}
                    <div class="sample-audit">
                        ${contest.district_layer_type ? `<span class="sample-layer">${contest.district_layer_type}</span>` : ''}
                        ${rcvLabel ? `<span class="sample-rcv">${rcvLabel}</span>` : ''}
                        ${auditLink}
                        ${focusLink}
                    </div>
                `;
                resultsDiv.appendChild(card);
            });
        });
        updateOfficeCardFocus(activeDistrictCardKey);
    } else {
        const empty = document.createElement('p');
        empty.className = 'sample-ballot-note';
        empty.innerText = 'No offices were generated for this address.';
        resultsDiv.appendChild(empty);
    }

    renderElectionEvents(resultsDiv, sampleBallot);
    renderPollingLocations(resultsDiv, sampleBallot);

    setSearchActive(true);
}

function formatEventDate(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return date.toLocaleString(undefined, {
        weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
        hour: 'numeric', minute: '2-digit'
    });
}

const DEADLINE_LABELS = {
    election_day: 'Election Day',
    early_voting_start: 'Early Voting Begins',
    early_voting_end: 'Early Voting Ends',
    candidate_filing_deadline_nonprincipal_party: 'Candidate Filing Deadline',
};

function renderElectionEvents(resultsDiv, sampleBallot) {
    const events = Array.isArray(sampleBallot?.election_events) ? sampleBallot.election_events : [];
    if (events.length === 0) return;

    const title = document.createElement('h3');
    title.className = 'section-title';
    title.innerText = 'Election Events';
    resultsDiv.appendChild(title);

    const byElection = new Map();
    events.forEach(e => {
        if (!byElection.has(e.election_id)) byElection.set(e.election_id, []);
        byElection.get(e.election_id).push(e);
    });

    byElection.forEach(evs => {
        const card = document.createElement('div');
        card.className = 'sample-ballot-card election-events-card';
        const first = evs[0];
        const statusTag = first.election_status === 'certified'
            ? '<span class="sample-tag scope">Certified</span>'
            : '<span class="sample-tag level">Scheduled</span>';

        const rows = evs.map(e => `
            <div class="event-row">
                <span class="event-label">${DEADLINE_LABELS[e.deadline_type] || e.deadline_type}</span>
                <span class="event-date">${formatEventDate(e.deadline_at)}</span>
            </div>
        `).join('');

        card.innerHTML = `
            <div class="sample-ballot-header">
                <span class="sample-office">${first.election_name}</span>
                <div class="sample-tags">${statusTag}</div>
            </div>
            <div class="event-rows">${rows}</div>
        `;
        resultsDiv.appendChild(card);
    });
}

function renderPollingLocations(resultsDiv, sampleBallot) {
    const locations = Array.isArray(sampleBallot?.polling_locations) ? sampleBallot.polling_locations : [];
    if (locations.length === 0) return;

    const title = document.createElement('h3');
    title.className = 'section-title';
    title.innerText = 'Nearby Polling Locations';
    resultsDiv.appendChild(title);

    locations.forEach(loc => {
        const card = document.createElement('div');
        card.className = 'sample-ballot-card polling-card';

        const addr = loc.address || {};
        const addressLine = [addr.street, `${addr.city || ''}, ${addr.state || ''} ${addr.zip5 || ''}`.trim()]
            .filter(Boolean).join(', ');
        const distanceLabel = typeof loc.distance_meters === 'number'
            ? `${(loc.distance_meters / 1609.34).toFixed(1)} mi away`
            : '';
        const dateRange = (loc.start_date && loc.end_date) ? `${loc.start_date} to ${loc.end_date}` : '';

        card.innerHTML = `
            <div class="sample-ballot-header">
                <span class="sample-office">${loc.name}</span>
                <div class="sample-tags">
                    <span class="sample-tag level">${(loc.location_type || '').replace('_', ' ')}</span>
                </div>
            </div>
            <p class="sample-district">${addressLine}</p>
            <div class="sample-audit">
                ${loc.hours ? `<span>${loc.hours}</span>` : ''}
                ${dateRange ? `<span>${dateRange}</span>` : ''}
                ${distanceLabel ? `<span class="sample-rcv">${distanceLabel}</span>` : ''}
            </div>
        `;
        resultsDiv.appendChild(card);
    });
}

function focusJurisdiction(id, type) {
    activeDistrictCardKey = `${type || ''}:${id || ''}`;
    updateDistrictCardFocus(activeDistrictCardKey);
    updateOfficeCardFocus(activeDistrictCardKey);

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
