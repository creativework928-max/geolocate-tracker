const DEFAULT_TIMEOUT_MS = 9000;

async function requestJson(url, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(
        () => controller.abort(),
        options.timeout ?? DEFAULT_TIMEOUT_MS
    );

    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
            headers: {
                Accept: "application/json",
                ...(options.headers || {})
            }
        });

        let payload = null;

        try {
            payload = await response.json();
        } catch {
            payload = null;
        }

        if (!response.ok) {
            const message =
                payload?.error?.message ||
                `Request failed with HTTP ${response.status}.`;

            const error = new Error(message);
            error.status = response.status;
            error.code = payload?.error?.code;
            throw error;
        }

        return payload;
    } catch (error) {
        if (error.name === "AbortError") {
            throw new Error(
                "The request timed out. Please try again."
            );
        }

        throw error;
    } finally {
        clearTimeout(timeout);
    }
}

export async function lookupIP(ip) {
    const encoded = encodeURIComponent(ip.trim());

    return requestJson(`/api/v1/lookup/${encoded}`);
}

export async function detectMyIP() {
    return requestJson("/api/v1/my-location");
}

export async function getHealth() {
    return requestJson("/health", {
        timeout: 4000
    });
}