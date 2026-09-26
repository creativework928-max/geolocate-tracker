import {
    detectMyIP,
    getHealth,
    lookupIP
} from "./api.js";

import {
    initializeMap,
    invalidateMapSize,
    showLocation
} from "./map.js";


const state = {
    loading: false
};

const elements = {
    form: document.getElementById("lookupForm"),
    input: document.getElementById("ipInput"),
    lookupButton: document.getElementById("lookupButton"),
    detectButton: document.getElementById("detectButton"),

    inputError: document.getElementById("inputError"),
    globalError: document.getElementById("globalError"),

    emptyState: document.getElementById("emptyState"),
    results: document.getElementById("results"),

    loadingOverlay: document.getElementById("loadingOverlay"),

    apiStatusDot: document.getElementById("apiStatusDot"),
    apiStatusText: document.getElementById("apiStatusText"),
    providerBadge: document.getElementById("providerBadge"),

    mapStatus: document.getElementById("mapStatus"),
    lastLookup: document.getElementById("lastLookup"),

    statIp: document.getElementById("statIp"),
    statVersion: document.getElementById("statVersion"),
    statLocation: document.getElementById("statLocation"),
    statCountry: document.getElementById("statCountry"),
    statCoordinates: document.getElementById("statCoordinates"),
    statTimezone: document.getElementById("statTimezone"),
    statNetwork: document.getElementById("statNetwork"),
    statAsn: document.getElementById("statAsn"),
    statAccuracy: document.getElementById("statAccuracy"),

    detailCountry: document.getElementById("detailCountry"),
    detailRegion: document.getElementById("detailRegion"),
    detailCity: document.getElementById("detailCity"),
    detailPostal: document.getElementById("detailPostal"),
    detailCoordinates: document.getElementById("detailCoordinates"),
    detailIsp: document.getElementById("detailIsp"),
    detailOrg: document.getElementById("detailOrg"),
    detailAsn: document.getElementById("detailAsn"),
    detailVersion: document.getElementById("detailVersion"),
    detailTimezone: document.getElementById("detailTimezone"),
    detailAccuracy: document.getElementById("detailAccuracy"),
    detailProvider: document.getElementById("detailProvider"),

    indicatorVpn: document.getElementById("indicatorVpn"),
    indicatorProxy: document.getElementById("indicatorProxy"),
    indicatorTor: document.getElementById("indicatorTor"),
    indicatorHosting: document.getElementById("indicatorHosting")
};


function valueOrDash(value) {
    return (
        value === null ||
        value === undefined ||
        value === ""
    ) ? "—" : String(value);
}


function booleanIndicator(value) {
    if (value === null || value === undefined) {
        return "Not supplied";
    }

    return value ? "Detected" : "Not detected";
}


function formatAccuracy(value) {
    if (
        value === null ||
        value === undefined ||
        !Number.isFinite(Number(value))
    ) {
        return "Not supplied";
    }

    return `${Number(value).toFixed(1)} km`;
}


function formatCoordinates(data) {
    if (
        data.latitude === null ||
        data.latitude === undefined ||
        data.longitude === null ||
        data.longitude === undefined
    ) {
        return "Not supplied";
    }

    return (
        `${Number(data.latitude).toFixed(5)}, ` +
        `${Number(data.longitude).toFixed(5)}`
    );
}


function formatLocation(data) {
    const parts = [
        data.city,
        data.region
    ].filter(Boolean);

    return parts.length
        ? parts.join(", ")
        : valueOrDash(data.country);
}


function formatTimestamp(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString();
}


function setLoading(isLoading) {
    state.loading = isLoading;

    elements.lookupButton.disabled = isLoading;
    elements.detectButton.disabled = isLoading;
    elements.input.disabled = isLoading;

    elements.loadingOverlay.classList.toggle(
        "hidden",
        !isLoading
    );
}


function clearError() {
    elements.inputError.textContent = "";
    elements.globalError.textContent = "";
    elements.globalError.classList.add("hidden");
}


function showError(message) {
    elements.globalError.textContent = message;
    elements.globalError.classList.remove("hidden");
}


function validateInput(value) {
    if (!value.trim()) {
        return "Enter an IPv4 or IPv6 address.";
    }

    if (value.length > 45) {
        return "The IP address is too long.";
    }

    return "";
}


function renderResult(payload) {
    const data = payload.data;

    elements.emptyState.classList.add("hidden");
    elements.results.classList.remove("hidden");

    elements.lastLookup.textContent =
        formatTimestamp(payload.meta?.timestamp);

    elements.providerBadge.textContent =
        `Provider — ${valueOrDash(payload.meta?.provider)}`;

    elements.statIp.textContent = valueOrDash(data.ip);
    elements.statVersion.textContent =
        `IPv${valueOrDash(data.version)}`;

    elements.statLocation.textContent =
        formatLocation(data);

    elements.statCountry.textContent =
        valueOrDash(data.country);

    elements.statCoordinates.textContent =
        formatCoordinates(data);

    elements.statTimezone.textContent =
        valueOrDash(data.timezone);

    elements.statNetwork.textContent =
        valueOrDash(data.isp || data.organization);

    elements.statAsn.textContent =
        valueOrDash(data.asn);

    elements.statAccuracy.textContent =
        formatAccuracy(data.accuracy_radius_km);

    elements.detailCountry.textContent =
        valueOrDash(data.country);

    elements.detailRegion.textContent =
        valueOrDash(data.region);

    elements.detailCity.textContent =
        valueOrDash(data.city);

    elements.detailPostal.textContent =
        valueOrDash(data.postal_code);

    elements.detailCoordinates.textContent =
        formatCoordinates(data);

    elements.detailIsp.textContent =
        valueOrDash(data.isp);

    elements.detailOrg.textContent =
        valueOrDash(data.organization);

    elements.detailAsn.textContent =
        valueOrDash(data.asn);

    elements.detailVersion.textContent =
        `IPv${valueOrDash(data.version)}`;

    elements.detailTimezone.textContent =
        valueOrDash(data.timezone);

    elements.detailAccuracy.textContent =
        formatAccuracy(data.accuracy_radius_km);

    elements.detailProvider.textContent =
        valueOrDash(data.provider);

    elements.indicatorVpn.textContent =
        booleanIndicator(data.is_vpn);

    elements.indicatorProxy.textContent =
        booleanIndicator(data.is_proxy);

    elements.indicatorTor.textContent =
        booleanIndicator(data.is_tor);

    elements.indicatorHosting.textContent =
        booleanIndicator(data.is_hosting);

    elements.mapStatus.textContent = "UPDATED";

    if (
        data.latitude !== null &&
        data.latitude !== undefined &&
        data.longitude !== null &&
        data.longitude !== undefined
    ) {
        showLocation(data);
    }

    invalidateMapSize();
}


async function performLookup(operation) {
    if (state.loading) {
        return;
    }

    clearError();

    setLoading(true);

    try {
        const payload = await operation();

        if (!payload?.success || !payload?.data) {
            throw new Error(
                "The API returned an unexpected response."
            );
        }

        renderResult(payload);
    } catch (error) {
        showError(
            error.message ||
            "Unable to resolve the IP location."
        );

        elements.mapStatus.textContent = "ERROR";
    } finally {
        setLoading(false);
    }
}


elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const value = elements.input.value.trim();
    const validationError = validateInput(value);

    elements.inputError.textContent = validationError;

    if (validationError) {
        elements.input.focus();
        return;
    }

    await performLookup(() => lookupIP(value));
});


elements.detectButton.addEventListener("click", async () => {
    await performLookup(detectMyIP);
});


async function checkHealth() {
    try {
        const payload = await getHealth();

        elements.apiStatusDot.classList.add("success");
        elements.apiStatusDot.classList.remove("error");
        elements.apiStatusText.textContent =
            payload.status === "healthy"
                ? "API operational"
                : "API degraded";
    } catch {
        elements.apiStatusDot.classList.add("error");
        elements.apiStatusDot.classList.remove("success");
        elements.apiStatusText.textContent = "API unavailable";
    }
}


function initialize() {
    initializeMap(
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        '&copy; <a href="https://www.openstreetmap.org/copyright" ' +
        'target="_blank" rel="noopener noreferrer">' +
        'OpenStreetMap</a> contributors'
    );

    checkHealth();
}


initialize();