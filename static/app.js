/* AeroClust AI Client JavaScript Application Logic */

let leafletMap = null;
let markerLayerGroup = null;
let allHotspots = [];
let archetypeChart = null;
let regionChart = null;
let currentMapFilter = 'all';

const ARCHETYPE_COLORS = {
    "Type 1: Industrial & Power Combustion Hotspot": "#e11d48",
    "Type 2: Dense Urban-Vehicular Smog Corridor": "#f97316",
    "Type 3: Agricultural Biomass & Stubble Burning Plume": "#eab308",
    "Type 4: Clean Background & Resilient Airshed": "#10b981"
};

const SHORT_ARCHETYPES = {
    "Type 1: Industrial & Power Combustion Hotspot": "Industrial/Power",
    "Type 2: Dense Urban-Vehicular Smog Corridor": "Urban Smog",
    "Type 3: Agricultural Biomass & Stubble Burning Plume": "Biomass Plume",
    "Type 4: Clean Background & Resilient Airshed": "Clean Airshed"
};

document.addEventListener("DOMContentLoaded", async () => {
    initLeafletMap();
    await Promise.all([
        loadStats(),
        loadHotspots(),
        loadValidationMetrics(),
        loadHiddenHotspots()
    ]);
    runSimulation(); // Initial calculation
});

// Tab Navigation
function switchTab(tabId) {
    document.querySelectorAll(".nav-tab").forEach(tab => tab.classList.remove("active"));
    document.querySelectorAll(".tab-view").forEach(view => view.classList.add("hidden"));

    const activeTab = document.getElementById(`tab-${tabId}`);
    const activeView = document.getElementById(`view-${tabId}`);
    if (activeTab) activeTab.classList.add("active");
    if (activeView) activeView.classList.remove("hidden");

    if (tabId === "map" && leafletMap) {
        setTimeout(() => {
            leafletMap.invalidateSize();
        }, 200);
    }
}

// -------------------------------------------------------------------------
// 1. STATS & OVERVIEW CHARTS
// -------------------------------------------------------------------------
async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();

        document.getElementById("stat-total-grids").innerText = data.total_cells.toLocaleString();
        const indCount = data.archetype_distribution["Type 1: Industrial & Power Combustion Hotspot"] || 0;
        document.getElementById("stat-ind-count").innerText = indCount.toLocaleString();
        document.getElementById("stat-ind-pct").innerText = `${(indCount / data.total_cells * 100).toFixed(1)}%`;

        document.getElementById("stat-deficits-count").innerText = data.airshed_deficits_count.toLocaleString();
        document.getElementById("stat-deficits-pct").innerText = `${data.airshed_deficits_percentage}%`;
        document.getElementById("stat-hidden-count").innerText = data.hidden_hotspots_detected.toLocaleString();

        renderArchetypeChart(data.archetype_distribution);
    } catch (e) {
        console.error("Failed to load system stats:", e);
    }
}

function renderArchetypeChart(distribution) {
    const ctx = document.getElementById("chart-archetype-dist").getContext("2d");
    const labels = Object.keys(distribution).map(k => SHORT_ARCHETYPES[k] || k);
    const values = Object.values(distribution);
    const colors = Object.keys(distribution).map(k => ARCHETYPE_COLORS[k] || "#94a3b8");

    if (archetypeChart) archetypeChart.destroy();
    archetypeChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: { color: "#cbd5e1", font: { family: "Plus Jakarta Sans", size: 11 }, padding: 12 }
                }
            },
            cutout: "68%"
        }
    });
}

function renderRegionBarChart(hotspots) {
    const regionMeans = {};
    hotspots.forEach(h => {
        if (!regionMeans[h.region_name]) regionMeans[h.region_name] = [];
        regionMeans[h.region_name].push(h.satellite_pollution_index);
    });

    const labels = Object.keys(regionMeans).map(r => r.split(" ")[0]);
    const values = Object.keys(regionMeans).map(r => {
        const arr = regionMeans[r];
        return Math.round(arr.reduce((a, b) => a + b, 0) / arr.length);
    });

    const ctx = document.getElementById("chart-region-bars").getContext("2d");
    if (regionChart) regionChart.destroy();
    regionChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Mean Pollution Index",
                data: values,
                backgroundColor: "#3b82f6",
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            scales: {
                x: {
                    grid: { color: "rgba(51, 65, 85, 0.3)" },
                    ticks: { color: "#94a3b8" }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: "#cbd5e1", font: { size: 10 } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// -------------------------------------------------------------------------
// 2. HOTSPOTS DATA & TABLE
// -------------------------------------------------------------------------
async function loadHotspots() {
    try {
        const res = await fetch("/api/hotspots?limit=500");
        const data = await res.json();
        allHotspots = data.hotspots;

        populateTable(allHotspots);
        plotHotspotsOnMap(allHotspots);
        renderRegionBarChart(allHotspots);
    } catch (e) {
        console.error("Failed to load hotspots:", e);
    }
}

function populateTable(hotspots) {
    const tbody = document.getElementById("table-hotspots-body");
    tbody.innerHTML = "";

    const displayList = hotspots.slice(0, 50);
    displayList.forEach(h => {
        const tr = document.createElement("tr");

        let badgeClass = "bg-slate-800 text-slate-300";
        if (h.predicted_archetype.includes("Industrial")) badgeClass = "bg-rose-500/20 text-rose-400 border border-rose-500/30";
        else if (h.predicted_archetype.includes("Urban")) badgeClass = "bg-orange-500/20 text-orange-400 border border-orange-500/30";
        else if (h.predicted_archetype.includes("Biomass")) badgeClass = "bg-amber-500/20 text-amber-400 border border-amber-500/30";
        else badgeClass = "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";

        const statusBadge = h.airshed_deficit_flag
            ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">DEFICIT</span>`
            : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">ADEQUATE</span>`;

        tr.innerHTML = `
            <td class="font-mono font-bold text-white">${h.cell_id}</td>
            <td>${h.region_name}</td>
            <td><span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeClass}">${SHORT_ARCHETYPES[h.predicted_archetype] || h.predicted_archetype}</span></td>
            <td class="font-bold text-white">${h.satellite_pollution_index}</td>
            <td>${h.so2_column_umol_m2}</td>
            <td>${h.no2_column_umol_m2}</td>
            <td>${h.aerosol_optical_depth_550}</td>
            <td>${h.airshed_assimilative_capacity}</td>
            <td>${statusBadge}</td>
        `;
        tbody.appendChild(tr);
    });
}

function filterTable() {
    const archFilter = document.getElementById("filter-table-archetype").value;
    const query = document.getElementById("filter-table-search").value.toLowerCase();

    const filtered = allHotspots.filter(h => {
        const matchArch = archFilter ? h.predicted_archetype === archFilter : true;
        const matchQuery = query ? (h.region_name.toLowerCase().includes(query) || h.cell_id.toLowerCase().includes(query)) : true;
        return matchArch && matchQuery;
    });

    populateTable(filtered);
}

// -------------------------------------------------------------------------
// 3. LEAFLET SATELLITE MAP
// -------------------------------------------------------------------------
function initLeafletMap() {
    leafletMap = L.map("map-container", {
        center: [22.8, 80.0],
        zoom: 5,
        zoomControl: true
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; Sentinel-5P / MODIS',
        subdomains: "abcd",
        maxZoom: 19
    }).addTo(leafletMap);

    markerLayerGroup = L.layerGroup().addTo(leafletMap);
}

function plotHotspotsOnMap(hotspots) {
    if (!markerLayerGroup) return;
    markerLayerGroup.clearLayers();

    hotspots.forEach(h => {
        const color = ARCHETYPE_COLORS[h.predicted_archetype] || "#94a3b8";
        const radius = Math.max(4, h.satellite_pollution_index * 0.18);

        const circle = L.circleMarker([h.latitude, h.longitude], {
            radius: radius,
            fillColor: color,
            color: "#ffffff",
            weight: 0.8,
            opacity: 0.9,
            fillOpacity: 0.75
        });

        circle.bindPopup(`
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 12px; line-height: 1.5;">
                <div style="font-weight: 800; font-size: 14px; margin-bottom: 4px; color: ${color};">
                    ${h.cell_id} - ${SHORT_ARCHETYPES[h.predicted_archetype]}
                </div>
                <div><b>Region:</b> ${h.region_name}</div>
                <div><b>Pollution Index:</b> ${h.satellite_pollution_index} / 100</div>
                <hr style="margin: 6px 0; border: 0; border-top: 1px solid #334155;">
                <div><b>NO2 Column:</b> ${h.no2_column_umol_m2} µmol/m²</div>
                <div><b>SO2 Column:</b> ${h.so2_column_umol_m2} µmol/m²</div>
                <div><b>AOD 550nm:</b> ${h.aerosol_optical_depth_550}</div>
                <div><b>FRP:</b> ${h.fire_radiative_power_mw} MW</div>
                <div style="margin-top: 4px;">
                    <b>Capacity:</b> ${h.airshed_assimilative_capacity}
                    ${h.airshed_deficit_flag ? '<span style="color:#ef4444; font-weight:bold;"> [DEFICIT]</span>' : '<span style="color:#10b981;"> [OK]</span>'}
                </div>
            </div>
        `);

        circle.hotspotData = h;
        markerLayerGroup.addLayer(circle);
    });

    document.getElementById("map-counter-label").innerText = `Showing ${hotspots.length} grid cells`;
}

function toggleMapFilter(type) {
    currentMapFilter = type;
    if (!markerLayerGroup) return;

    let filtered = allHotspots;
    if (type === 'ind') {
        filtered = allHotspots.filter(h => h.predicted_archetype.includes("Industrial"));
    } else if (type === 'urb') {
        filtered = allHotspots.filter(h => h.predicted_archetype.includes("Urban"));
    } else if (type === 'bio') {
        filtered = allHotspots.filter(h => h.predicted_archetype.includes("Biomass"));
    } else if (type === 'clean') {
        filtered = allHotspots.filter(h => h.predicted_archetype.includes("Clean"));
    } else if (type === 'hidden') {
        filtered = allHotspots.filter(h => !h.ground_station_installed && (h.predicted_archetype.includes("Industrial") || h.predicted_archetype.includes("Biomass")) && h.airshed_deficit_flag === 1);
    }

    plotHotspotsOnMap(filtered);
}

// -------------------------------------------------------------------------
// 4. REAL-TIME SIMULATOR
// -------------------------------------------------------------------------
function updateSimValue(id) {
    const el = document.getElementById(`sim-${id}`);
    const display = document.getElementById(`val-${id}`);
    if (el && display) display.innerText = el.value;
}

async function runSimulation() {
    const payload = {
        no2_column_umol_m2: parseFloat(document.getElementById("sim-no2").value),
        so2_column_umol_m2: parseFloat(document.getElementById("sim-so2").value),
        co_column_mmol_m2: parseFloat(document.getElementById("sim-co").value),
        hcho_column_umol_m2: parseFloat(document.getElementById("sim-hcho").value),
        methane_ch4_ppb: parseFloat(document.getElementById("sim-ch4").value),
        aerosol_optical_depth_550: parseFloat(document.getElementById("sim-aod").value),
        uv_aerosol_index: parseFloat(document.getElementById("sim-uvai").value),
        fire_radiative_power_mw: parseFloat(document.getElementById("sim-frp").value),
        land_surface_temp_c: parseFloat(document.getElementById("sim-lst").value),
        boundary_layer_height_m: parseFloat(document.getElementById("sim-blh").value),
        surface_wind_speed_ms: parseFloat(document.getElementById("sim-wind").value),
        relative_humidity_pct: parseFloat(document.getElementById("sim-rh").value),
        precipitation_rate_mm: 0.5
    };

    try {
        const res = await fetch("/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        document.getElementById("sim-res-archetype").innerText = SHORT_ARCHETYPES[data.predicted_archetype] || data.predicted_archetype;
        document.getElementById("sim-res-tier").innerText = data.predicted_risk_tier;
        document.getElementById("sim-res-index").innerText = `${data.satellite_pollution_index} / 100`;

        const statusEl = document.getElementById("sim-res-status");
        if (data.airshed_deficit_flag) {
            statusEl.innerText = "DEFICIT BREACH";
            statusEl.className = "text-sm font-bold px-3 py-1 rounded-full bg-rose-500/20 text-rose-400 inline-block mt-1";
        } else {
            statusEl.innerText = "WITHIN CAPACITY";
            statusEl.className = "text-sm font-bold px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 inline-block mt-1";
        }

        document.getElementById("sim-res-mitigation").innerText = `Action Protocol: ${data.mitigation_protocol}`;
    } catch (e) {
        console.error("Simulation failed:", e);
    }
}

// -------------------------------------------------------------------------
// 5. BATCH INGESTION
// -------------------------------------------------------------------------
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/batch-predict", {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        document.getElementById("batch-results-panel").classList.remove("hidden");
        document.getElementById("batch-count-badge").innerText = `${data.total_records} records processed | ${data.deficits_detected} deficits`;

        const tbody = document.getElementById("batch-table-body");
        tbody.innerHTML = "";
        data.records.slice(0, 30).forEach(r => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="font-mono font-bold text-white">${r.cell_id}</td>
                <td>${r.region_name}</td>
                <td class="font-bold text-rose-400">${SHORT_ARCHETYPES[r.predicted_archetype] || r.predicted_archetype}</td>
                <td>${r.predicted_risk_tier}</td>
                <td class="font-bold text-white">${r.satellite_pollution_index}</td>
                <td>${r.estimated_assimilative_capacity}</td>
                <td>${r.airshed_deficit_flag ? '<span class="text-rose-400 font-bold">YES</span>' : '<span class="text-emerald-400">NO</span>'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        alert("Batch ingestion failed: " + e);
    }
}

// -------------------------------------------------------------------------
// 6. VALIDATION & HIDDEN HOTSPOTS
// -------------------------------------------------------------------------
async function loadValidationMetrics() {
    try {
        const res = await fetch("/api/validation");
        const data = await res.json();
        const agr = data.agreement_metrics;

        document.getElementById("val-ari").innerText = agr.Adjusted_Rand_Index_ARI.toFixed(4);
        document.getElementById("val-nmi").innerText = agr.Normalized_Mutual_Info_NMI.toFixed(4);
        document.getElementById("val-kappa").innerText = agr.Quadratic_Weighted_Kappa.toFixed(4);
    } catch (e) {
        console.error("Failed to load validation:", e);
    }
}

async function loadHiddenHotspots() {
    try {
        const res = await fetch("/api/hidden-hotspots?limit=50");
        const data = await res.json();

        document.getElementById("hidden-counter-badge").innerText = `${data.length} Sampled`;
        const tbody = document.getElementById("table-hidden-body");
        tbody.innerHTML = "";

        data.forEach(h => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="font-mono font-bold text-purple-400">${h.cell_id}</td>
                <td>${h.region_name}</td>
                <td class="font-mono text-xs">${h.latitude.toFixed(2)}°N, ${h.longitude.toFixed(2)}°E</td>
                <td><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400">${SHORT_ARCHETYPES[h.predicted_archetype] || h.predicted_archetype}</span></td>
                <td class="font-bold text-white">${h.satellite_pollution_index}</td>
                <td>${h.so2_column_umol_m2}</td>
                <td>${h.no2_column_umol_m2}</td>
                <td><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400">NO GROUND STATION</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Failed to load hidden hotspots:", e);
    }
}
