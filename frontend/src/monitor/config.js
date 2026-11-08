// Constants of the River Lifeline page and where its data lives.

export const DEFAULT_AREA = "tefe";
export const REFRESH_MS = 10 * 60 * 1000;   // how often the page looks for passes added by the watcher
export const REPEAT_DAYS = 12;              // NISAR repeat cycle: the same track comes back every 12 days
export const PLAY_STEP_MS = 1300;

// Status codes written by processing/lifeline (catalog.json "status": [code, bottleneck_m, distance_m])
export const STATUS_BY_CODE = { 0: "no_data", 1: "connected", 2: "at_risk", 3: "isolated" };
export const ROUTE_STATUSES = ["connected", "at_risk", "isolated"];
export const LABEL = { connected: "Connected", at_risk: "At risk", isolated: "Isolated", no_data: "No data",
  inland: "Not river-dependent", unresolved: "Not resolvable" };
export const COLOR = { connected: "#7dd3b0", at_risk: "#f2b544", isolated: "#ff6b5b" };
export const SEVERITY = { isolated: 3, at_risk: 2, connected: 1, no_data: 0 };

const AREA_ID = /^[a-z0-9_-]+$/i;

// Area id from the page's query string (?area=<id>); anything that is not a plain id falls back to the default,
// so the value can never point the data requests outside public/data/monitor/.
export function areaFromSearch(search) {
  const area = new URLSearchParams(search).get("area");
  return area && AREA_ID.test(area) ? area : DEFAULT_AREA;
}

// Relative to the page, so the app works under any path prefix (production, develop and PR previews).
export const dataUrl = area => `./public/data/monitor/${area}/`;
