let map = null;
let marker = null;
let accuracyCircle = null;

const DEFAULT_CENTER = [20, 0];
const DEFAULT_ZOOM = 2;

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = String(value ?? "—");
    return div.innerHTML;
}

export function initializeMap(tileUrl, attribution) {
    if (map) {
        return map;
    }

    map = L.map("map", {
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
        minZoom: 2,
        worldCopyJump: true,
        zoomControl: true
    });

    L.control.scale({
        imperial: false
    }).addTo(map);

    L.tileLayer(tileUrl, {
        attribution,
        maxZoom: 19
    }).addTo(map);

    return map;
}

export function clearLocation() {
    if (!map) {
        return;
    }

    if (marker) {
        map.removeLayer(marker);
        marker = null;
    }

    if (accuracyCircle) {
        map.removeLayer(accuracyCircle);
        accuracyCircle = null;
    }
}

export function showLocation(data) {
    if (!map) {
        throw new Error("Map has not been initialized.");
    }

    clearLocation();

    const lat = Number(data.latitude);
    const lon = Number(data.longitude);

    if (
        !Number.isFinite(lat) ||
        !Number.isFinite(lon) ||
        lat < -90 ||
        lat > 90 ||
        lon < -180 ||
        lon > 180
    ) {
        map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
        return;
    }

    marker = L.marker([lat, lon]).addTo(map);

    const city = data.city || "Unknown city";
    const region = data.region || "Unknown region";
    const country = data.country || "Unknown country";

    const popup = `
        <div class="map-popup">
            <strong>Approximate IP Location</strong>
            <div>${escapeHtml(data.ip)}</div>
            <div>${escapeHtml(city)}, ${escapeHtml(region)}</div>
            <div>${escapeHtml(country)}</div>
            <div>
                ${lat.toFixed(5)}, ${lon.toFixed(5)}
            </div>
        </div>
    `;

    marker.bindPopup(popup).openPopup();

    if (
        data.accuracy_radius_km !== null &&
        data.accuracy_radius_km !== undefined &&
        Number.isFinite(Number(data.accuracy_radius_km)) &&
        Number(data.accuracy_radius_km) > 0
    ) {
        accuracyCircle = L.circle([lat, lon], {
            radius: Number(data.accuracy_radius_km) * 1000,
            color: "#38bdf8",
            weight: 2,
            fillColor: "#38bdf8",
            fillOpacity: 0.12
        }).addTo(map);
    }

    const layers = [marker];

    if (accuracyCircle) {
        layers.push(accuracyCircle);
    }

    const group = L.featureGroup(layers);

    map.fitBounds(group.getBounds(), {
        padding: [40, 40],
        maxZoom: 10
    });
}

export function invalidateMapSize() {
    if (map) {
        setTimeout(() => map.invalidateSize(), 100);
    }
}