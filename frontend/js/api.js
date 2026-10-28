/* Plantorix - API client.
   Base URL, in order of priority:
     1. ?api=http://host:port in the page address
     2. same origin, when the page is served by FastAPI on port 8000
     3. http://127.0.0.1:8000 (e.g. when the page is opened from Live Server) */
const Api = (() => {
    const fromQuery = new URLSearchParams(window.location.search).get("api");
    const base = (fromQuery ||
        (window.location.port === "8000" ? "" : "http://127.0.0.1:8000")).replace(/\/$/, "");

    async function get(path, timeoutMs = 15000) {
        const ctl = new AbortController();
        const timer = setTimeout(() => ctl.abort(), timeoutMs);
        let res;
        try {
            res = await fetch(base + path, { signal: ctl.signal });
        } catch (err) {
            throw new Error(err.name === "AbortError"
                ? "The API did not respond in time."
                : "Cannot reach the API at " + (base || window.location.origin) +
                ". Start it with: uvicorn backend.main:app --reload");
        } finally {
            clearTimeout(timer);
        }
        if (!res.ok) {
            let detail = res.status + " " + res.statusText;
            try {
                const body = await res.json();
                if (typeof body.detail === "string") detail = body.detail;
                else if (Array.isArray(body.detail) && body.detail[0]) detail = body.detail[0].msg;
            } catch (_) { /* keep the status text */ }
            throw new Error(detail);
        }
        return res.json();
    }

    return { base, get };
})(); s