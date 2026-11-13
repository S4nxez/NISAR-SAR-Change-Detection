// The backend's river lifeline API (server: MonitorController), the page's only data source:
//   GET api/monitor/areas/<area>                          catalog.json: area, communities, river gauge, one entry per pass
//   GET api/monitor/areas/<area>/passes/<id>/radar.webp   HH backscatter preview
//   GET api/monitor/areas/<area>/passes/<id>/water.png    water mask (narrow channels in amber, water under vegetation in green)
//   GET api/monitor/areas/<area>/passes/<id>/change.png   water lost / gained since the previous pass of the same track
// URLs are relative to the page, so the app works under any path prefix (production, develop and PR previews).

export const areaUrl = area => `./api/monitor/areas/${encodeURIComponent(area)}`;

// URL of a file of a pass, or null when the pass has no such file
export const layerUrl = (area, pass, file) =>
  (file ? `${areaUrl(area)}/passes/${encodeURIComponent(pass.id)}/${encodeURIComponent(file)}` : null);

// Why the catalog could not be read: "missing" (404, the worker has not published the area yet), "unsupported"
// (503, the backend and the worker disagree on the catalog version) or "unavailable" (anything else).
export class CatalogError extends Error {
  constructor(status) {
    super(`The pass record could not be read (HTTP ${status})`);
    this.status = status;
    this.reason = status === 404 ? "missing" : status === 503 ? "unsupported" : "unavailable";
  }
}

// The catalog of an area. no-cache: the browser revalidates it, and the backend answers 304 until the worker
// writes a new one. fetchFn is the browser's fetch unless a test passes its own.
export async function fetchCatalog(area, fetchFn = fetch) {
  const res = await fetchFn(areaUrl(area), { cache: "no-cache", headers: { Accept: "application/json" } });
  if (!res.ok) throw new CatalogError(res.status);
  return res.json();
}
