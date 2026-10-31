/* Plantorix - API client.
   Base URL, in order of priority:
     1. ?api=http://host:port in the page address
     2. same origin, when the page is served by FastAPI (port 8000 locally, or any
        deployed host such as Vercel)
     3. http://127.0.0.1:8000 (only when the page is opened from a local dev server
        on another port, e.g. Live Server) */
const Api = (() => {
  const fromQuery = new URLSearchParams(window.location.search).get("api");
  const host = window.location.hostname;
  const isLocalHost = host === "localhost" || host === "127.0.0.1" || host === "[::1]";
  const sameOrigin = !isLocalHost || window.location.port === "8000";
  const base = (fromQuery || (sameOrigin ? "" : "http://127.0.0.1:8000")).replace(/\/$/, "");

  async function get(path, timeoutMs = 15000, as = "json") {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), timeoutMs);
    let res;
    try {
      res = await fetch(base + path, { signal: ctl.signal });
    } catch (err) {
      if (window.location.protocol === "file:") {
        throw new Error("This page was opened as a local file, so the browser blocks access to the API. " +
          "Start the server (uvicorn backend.main:app --reload) and open http://127.0.0.1:8000/ instead.");
      }
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
    return as === "blob" ? res.blob() : res.json();
  }

  return { base, get };
})();
