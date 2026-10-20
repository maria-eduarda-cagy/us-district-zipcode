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
    'UNSD': '#e74c3c',
    'DELEGATE_SUBDISTRICT': '#d35400',
    'PRECINCT': '#607d8b',
    'COUNCIL_DISTRICT': '#f39c12',
    'BOE_DISTRICT': '#8e5b3f',
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

const DISTRICT_TYPE_LABELS = {
    'CD': 'Congressional District',
    'SLDU': 'State Senate District',
    'SLDL': 'State House District',
    'COUNTY': 'County',
    'PLACE': 'City / Place',
    'UNSD': 'School District',
    'SCHOOL': 'School District',
    'DELEGATE_SUBDISTRICT': 'House of Delegates Subdistrict',
    'PRECINCT': 'Precinct',
    'COUNCIL_DISTRICT': 'County Council District',
    'BOE_DISTRICT': 'Board of Education District',
    'DC_WARDS_2022': 'DC Ward',
    'DC_ANC_2023': 'DC Advisory Neighborhood Commission',
    'DC_SMD_2023': 'DC Single-Member District',
    'DC_SBOE_DISTRICTS': 'DC School Board District',
    'VA_FAIRFAX_SUPERVISOR_DISTRICTS': 'Fairfax Supervisor District',
    'VA_LOUDOUN_ELECTION_DISTRICTS_2022': 'Loudoun Election District',
    'VA_LOUDOUN_PRECINCTS': 'Loudoun Precinct'
};

function districtTypeLabel(type) {
    return DISTRICT_TYPE_LABELS[type] || type || 'District';
}

function partyTagClass(party) {
    if (!party) return 'nonpartisan';
    const p = party.trim().toLowerCase();
    if (p.startsWith('cross')) return 'cross-filed';
    if (p.startsWith('dem')) return 'democratic';
    if (p.startsWith('rep')) return 'republican';
    return 'other-party';
}

function partyTagLabel(party) {
    const cls = partyTagClass(party);
    if (cls === 'cross-filed') return 'Cross-Filing';
    if (cls === 'democratic') return 'Democrat';
    if (cls === 'republican') return 'Republican';
    if (cls === 'other-party') return party;
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
        const typeLabel = districtTypeLabel(districtTypeKey);
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
            layer.bindPopup(`<strong>${popupName}</strong><br>Type: ${typeLabel}${popupId}`);

            if (!typeGroups[districtTypeKey]) {
                typeGroups[districtTypeKey] = L.layerGroup().addTo(map);
                layerControl.addOverlay(typeGroups[districtTypeKey], typeLabel);
                overlays[districtTypeKey] = typeGroups[districtTypeKey];
            }
            typeGroups[districtTypeKey].addLayer(layer);
            districtLayers.push({ id: m.district_id, type: districtTypeKey, layer: layer });
        }
    });

    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';

    renderDataFreshness(resultsDiv, sampleBallot);
    renderOfficesSection(resultsDiv, sampleBallot, sampleBallotError);
    renderDistrictsSection(resultsDiv, memberships);
    renderElectionEvents(resultsDiv, sampleBallot);
    renderPollingLocations(resultsDiv, sampleBallot);

    setSearchActive(true);
}

function renderDistrictsSection(resultsDiv, memberships) {
    const details = document.createElement('details');
    details.className = 'districts-section';

    const summary = document.createElement('summary');
    summary.className = 'section-title districts-summary';
    summary.innerText = `Districts Found (${memberships.length})`;
    details.appendChild(summary);

    memberships.forEach(m => {
        const card = document.createElement('div');
        card.className = 'ballot-card district-found-card';
        const color = getDistrictColor(m.layer_type);
        card.style.borderLeft = `5px solid ${color}`;
        const jurKey = `${m.layer_type || ''}:${m.district_id || ''}`;
        card.setAttribute('data-jur-key', jurKey);

        const cardTitle = m.district_name || districtTypeLabel(m.layer_type);
        const sourceLink = m.source_url ? `<a href="${m.source_url}" target="_blank" class="sample-source-link">Source</a>` : '';
        const idLine = m.district_id ? `<p class="jur-name">ID: <strong>${m.district_id}</strong></p>` : '';

        card.innerHTML = `
            <div class="ballot-item-header">
                <span class="item-name">${cardTitle}</span>
                <span class="jur-tag" style="background-color: ${color}">${m.layer_type || 'Unknown'}</span>
            </div>
            ${idLine}
            <div class="sample-audit">
                ${sourceLink}
                ${m.district_id && m.layer_type ? `<span class="view-on-map" onclick="focusJurisdiction('${m.district_id}', '${m.layer_type}')">Focus on Map</span>` : ''}
            </div>
        `;
        details.appendChild(card);
    });

    resultsDiv.appendChild(details);
    updateDistrictCardFocus(activeDistrictCardKey);
}

function renderOfficesSection(resultsDiv, sampleBallot, sampleBallotError) {
    const ballotTitle = document.createElement('h3');
    ballotTitle.className = 'section-title';
    ballotTitle.innerText = 'Offices on Your Ballot';
    resultsDiv.appendChild(ballotTitle);

    if (sampleBallotError) {
        const warn = document.createElement('p');
        warn.className = 'sample-ballot-warning';
        warn.innerText = `Ballot unavailable: ${sampleBallotError}`;
        resultsDiv.appendChild(warn);
        return;
    }

    const contests = Array.isArray(sampleBallot?.contests) ? sampleBallot.contests : [];
    const measures = Array.isArray(sampleBallot?.measures) ? sampleBallot.measures : [];
    if (contests.length === 0 && measures.length === 0) {
        resultsDiv.appendChild(renderCoverageNotice(sampleBallot?.coverage));
        return;
    }

    const note = document.createElement('p');
    note.className = 'sample-ballot-note';
    note.innerText = sampleBallot.ballot_status === 'loaded'
        ? 'Candidates and contests from a certified ballot style for this precinct.'
        : 'Generated from authoritative geocoding + district layers.';
    resultsDiv.appendChild(note);

    groupByElection(contests, measures).forEach(group => {
        renderElectionHeader(resultsDiv, group.election);

        const levels = { 'Federal': [], 'State': [], 'Local': [] };
        group.contests.forEach(c => {
            if (levels[c.jurisdiction_level]) levels[c.jurisdiction_level].push(c);
        });

        ['Federal', 'State', 'Local'].forEach(level => {
            if (levels[level].length === 0) return;
            const levelHeader = document.createElement('h3');
            levelHeader.className = 'level-header';
            levelHeader.innerText = level;
            resultsDiv.appendChild(levelHeader);
            levels[level].forEach(contest => resultsDiv.appendChild(renderContestCard(contest)));
        });

        if (group.measures.length > 0) {
            const measuresHeader = document.createElement('h3');
            measuresHeader.className = 'level-header';
            measuresHeader.innerText = 'Ballot Questions';
            resultsDiv.appendChild(measuresHeader);
            group.measures.forEach(m => resultsDiv.appendChild(renderMeasureCard(m)));
        }
    });
    updateOfficeCardFocus(activeDistrictCardKey);
}

// Explains why there's no ballot instead of implying the address has no races.
function renderCoverageNotice(coverage) {
    const notice = document.createElement('div');
    notice.className = 'coverage-notice';
    if (coverage?.level === 'districts_only') {
        const place = coverage.county_name ? `${coverage.county_name}, ${coverage.state}` : coverage.state;
        notice.innerHTML = `
            <strong>Ballot not available yet for this precinct (${place}).</strong>
            <p>The districts below come from official boundary layers, but candidates and contests
            are only loaded for some precincts so far. Check your official sample ballot with your
            local board of elections.</p>
        `;
    } else {
        notice.innerHTML = `
            <strong>This address is outside the area this tool covers.</strong>
            <p>Coverage is limited to Washington, DC, Maryland and Virginia.</p>
        `;
    }
    return notice;
}

function todayIsoDate() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// Upcoming elections first (soonest first), then past ones (most recent first).
function groupByElection(contests, measures) {
    const groups = new Map();
    const groupFor = (election) => {
        const key = election?.election_id || 'unknown';
        if (!groups.has(key)) groups.set(key, { election, contests: [], measures: [] });
        return groups.get(key);
    };
    contests.forEach(c => groupFor(c.election).contests.push(c));
    measures.forEach(m => groupFor(m.election).measures.push(m));

    const isUpcoming = (g) => isUpcomingElection(g.election);
    return Array.from(groups.values()).sort((a, b) => {
        const ua = isUpcoming(a), ub = isUpcoming(b);
        if (ua !== ub) return ua ? -1 : 1;
        const da = a.election?.election_date || '', db = b.election?.election_date || '';
        return ua ? da.localeCompare(db) : db.localeCompare(da);
    });
}

function formatDateOnly(isoDate) {
    if (!isoDate) return '';
    // Date-only strings parse as UTC midnight; pin the time so the local day doesn't shift.
    const date = new Date(`${isoDate.slice(0, 10)}T12:00:00`);
    if (isNaN(date.getTime())) return isoDate;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function renderElectionHeader(resultsDiv, election) {
    const header = document.createElement('div');
    header.className = 'election-header';
    if (!election) {
        header.innerHTML = '<span class="election-name">Election</span>';
        resultsDiv.appendChild(header);
        return;
    }
    const upcoming = isUpcomingElection(election);
    // Say outright what the group is: contests to vote on, or already-decided results.
    const explainer = upcoming
        ? `You will vote on these contests in the ${election.name} on ${formatDateOnly(election.election_date)}.`
        : `Already decided: official results of the ${election.name}. These are not on your upcoming ballot.`;
    header.innerHTML = `
        <span class="election-name">${election.name}</span>
        <span class="election-date">${formatDateOnly(election.election_date)}</span>
        <span class="election-badge ${upcoming ? 'upcoming' : 'past'}">${upcoming ? 'On your ballot' : 'Results'}</span>
        <p class="election-explainer">${explainer}</p>
    `;
    resultsDiv.appendChild(header);
}

function isUpcomingElection(election) {
    return (election?.election_date || '') >= todayIsoDate();
}

// Short per-card label so a card read on its own still says which election it's from.
function electionTagLabel(election) {
    if (!election) return '';
    const kind = election.election_type === 'primary' ? 'Primary' : election.election_type === 'general' ? 'General' : 'Election';
    const date = formatDateOnly(election.election_date);
    return isUpcomingElection(election) ? `${kind} · ${date}` : `${kind} results · ${date}`;
}

function renderCandidateResults(cand) {
    const results = Array.isArray(cand.results) ? cand.results : [];
    if (results.length === 0) return '';
    // Cross-filed candidates have one total per party primary; label which is which.
    const showParty = results.length > 1;
    return `<div class="candidate-results">${results.map(r => `
        <span class="result-line">
            ${showParty && r.primary_party ? `<span class="result-party">${r.primary_party} primary:</span>` : ''}
            ${r.votes.toLocaleString()} votes${r.pct !== null ? ` · ${r.pct}%` : ''}
            ${r.is_winner ? '<span class="candidate-tag winner">Won</span>' : ''}
        </span>
    `).join('')}</div>`;
}

function renderContestCard(contest) {
    const card = document.createElement('div');
    card.className = 'sample-ballot-card office-ballot-card';

    if (contest.district_layer_type && contest.district_id) {
        card.setAttribute('data-jur-key', `${contest.district_layer_type}:${contest.district_id}`);
    }

    const scopeLabel = contest.scope === 'at_large' ? 'At-large' : 'District';
    const rcvLabel = contest.ranked_choice_voting ? 'Ranked-choice voting' : '';
    const contestTitle = contest.contest_label || contest.office_name;
    const voteForLabel = contest.retention
        ? 'Vote Yes or No for continuance in office'
        : contest.vote_for > 1 ? `Vote for up to ${contest.vote_for}` : 'Vote for 1';

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
    // The ballot prints no party for some partisan-office candidates (e.g. judges
    // in the general election); show no tag rather than inventing "Non-Partisan".
    const partyTag = (party) => (!party && !contest.nonpartisan)
        ? ''
        : `<span class="candidate-tag ${partyTagClass(party)}">${partyTagLabel(party)}</span>`;
    const candidatesList = candidates.length > 0
        ? `<ul class="sample-candidates">${candidates.map(cand => `
            <li class="sample-candidate">
                <div class="candidate-main">
                    <span class="candidate-name">${cand.name}</span>
                    <span class="candidate-tags">
                        ${partyTag(cand.party)}
                        ${cand.incumbent ? '<span class="candidate-tag incumbent">Incumbent</span>' : ''}
                        ${cand.unopposed ? '<span class="candidate-tag unopposed">Unopposed</span>' : ''}
                    </span>
                </div>
                ${renderCandidateResults(cand)}
            </li>
        `).join('')}</ul>`
        : '<p class="sample-no-candidates">No candidates loaded for this contest yet.</p>';

    const allResults = candidates.flatMap(c => c.results || []);
    const reportingUnit = allResults.map(r => r.reporting_unit).find(Boolean);
    const primaryParties = [...new Set(allResults.map(r => r.primary_party).filter(Boolean))];
    const primaryLabel = primaryParties.length === 1 ? `${primaryParties[0]} primary · ` : '';
    const resultsNote = reportingUnit
        ? `<p class="results-note">${primaryLabel}Official results, totals for all of ${reportingUnit}</p>`
        : '';
    const electionTag = electionTagLabel(contest.election);

    const verificationWarning = contest.verification_note
        ? `<div class="verification-warning">
            <span class="verification-warning-label">Data conflict — not verified</span>
            <p class="verification-warning-text">${contest.verification_note}</p>
        </div>`
        : '';

    card.innerHTML = `
        <div class="sample-ballot-header">
            <span class="sample-office">${contestTitle}</span>
            <div class="sample-tags">
                ${electionTag ? `<span class="sample-tag election ${isUpcomingElection(contest.election) ? 'upcoming' : 'past'}">${electionTag}</span>` : ''}
                <span class="sample-tag level">${contest.jurisdiction_level}</span>
                <span class="sample-tag scope">${scopeLabel}</span>
            </div>
        </div>
        ${verificationWarning}
        ${contest.office_name && contest.office_name !== contestTitle ? `<p class="sample-office-category">${contest.office_name}</p>` : ''}
        <p class="sample-vote-for">${voteForLabel}</p>
        ${resultsNote}
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
    return card;
}

function renderMeasureCard(measure) {
    const card = document.createElement('div');
    card.className = 'sample-ballot-card measure-card';
    const electionTag = electionTagLabel(measure.election);
    card.innerHTML = `
        <div class="sample-ballot-header">
            <span class="sample-office">${measure.title}</span>
            ${electionTag ? `<div class="sample-tags"><span class="sample-tag election ${isUpcomingElection(measure.election) ? 'upcoming' : 'past'}">${electionTag}</span></div>` : ''}
        </div>
        ${measure.question_text ? `<p class="measure-text">${measure.question_text}</p>` : ''}
        ${measure.impact_yes ? `<p class="measure-impact">${measure.impact_yes}</p>` : ''}
        ${measure.impact_no ? `<p class="measure-impact">${measure.impact_no}</p>` : ''}
        ${measure.explanation ? `
        <details class="measure-explanation">
            <summary>Official explanation</summary>
            ${measure.explanation.split('\n\n').map((p) => `<p>${p}</p>`).join('')}
            ${measure.explanation_source_url ? `<a href="${measure.explanation_source_url}" target="_blank" rel="noopener">Source</a>` : ''}
        </details>` : ''}
    `;
    return card;
}

const SOURCE_TYPE_LABELS = {
    certified_ballot_pdf: 'Certified ballot (PDF)',
    election_results_csv: 'Official results (CSV)',
    election_calendar: 'Election calendar',
    early_voting_centers_pdf: 'Early voting centers (PDF)',
};

function renderDataFreshness(resultsDiv, sampleBallot) {
    const sources = Array.isArray(sampleBallot?.data_sources) ? sampleBallot.data_sources : [];
    if (!sampleBallot?.data_last_updated) return;

    const box = document.createElement('details');
    box.className = 'data-freshness';
    box.innerHTML = `
        <summary>Data last updated: <strong>${formatDateOnly(sampleBallot.data_last_updated)}</strong></summary>
        <ul class="data-source-list">${sources.map(s => `
            <li>
                <a href="${s.source_url}" target="_blank" class="sample-source-link">${SOURCE_TYPE_LABELS[s.source_type] || s.source_type}</a>
                <span class="data-source-file">${s.source_url.split('/').pop()}</span>
                <span class="data-source-dates">
                    ${s.effective_date ? `published ${formatDateOnly(s.effective_date)} · ` : ''}loaded ${formatDateOnly(s.fetched_at)}
                </span>
            </li>
        `).join('')}</ul>
    `;
    resultsDiv.appendChild(box);
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
