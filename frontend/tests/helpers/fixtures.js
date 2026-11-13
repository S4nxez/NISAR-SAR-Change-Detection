// A small catalog in the shape processing/lifeline writes and the backend serves, for the page's tests.

export const WIDTHS = [40, 60, 100, 200, 400];

const pass = (id, extra) => {
  const [date, rest] = id.split("_t");
  return { id, date, time_utc: "10:02", track: Number(rest.slice(0, 3)),
    direction: rest.endsWith("A") ? "ascending" : "descending", coverage: 0.99, water_km2: 800, shown: true,
    evaluated: true, files: { radar: "radar.webp", water: "water.png" }, unconfirmed: [], ...extra };
};

export function catalog() {
  return {
    area: { id: "tefe", name: "Lake Tefé", hub: { name: "Tefé", lon: -64.71, lat: -3.35, radius_m: 2000 },
      river: { name: "Solimões", lon: -64.6, lat: -3.3 }, access_radius_m: 1000, safe_width_m: 60, widths_m: WIDTHS,
      circle: { lon: -64.75, lat: -3.4, radius_km: 55 } },
    grid: { pixel_m: 19.9, bounds: [[-3.9, -65.2], [-2.9, -64.3]] },
    schema_version: 1,
    status_codes: { 0: "no_data", 1: "connected", 2: "at_risk", 3: "isolated" },
    sources: { radar: "NISAR", places: "OSM" },
    gauge: { name: "Tefé gauge", source: "ANA", series: [["2026-07-06", 1800], ["2026-07-19", 1700], ["2026-08-19", 1300],
      ["2026-08-31", 1150]] },
    communities: [
      { id: "a", name: "Alpha", place: "village", lat: -3.3, lon: -64.6, class: "monitored", population: 1200 },
      { id: "b", name: "Bravo <b>", place: "hamlet", lat: -3.4, lon: -64.7, class: "monitored",
        access: [-64.71, -3.41], access_source: "pier" },
      { id: "c", name: "Charlie", place: "hamlet", lat: -3.5, lon: -64.8, class: "inland" },
      { id: "d", name: "Delta", place: "hamlet", lat: -3.6, lon: -64.9, class: "unresolved" },
    ],
    passes: [
      pass("2025-11-02_t060A", { shown: false, evaluated: false, coverage: 0 }),
      pass("2026-07-07_t161A", { status: { a: [1, 200, 20], b: [1, 100, 30], c: [3, null, 1500], d: [3, null, 300] },
        counts: { no_data: 0, connected: 2, at_risk: 0, isolated: 0 }, hub_link: [1, 400, 0] }),
      pass("2026-07-19_t161A", { status: { a: [1, 100, 20], b: [2, 0, 30], c: [3, null, 1500], d: [3, null, 300] },
        counts: { no_data: 0, connected: 1, at_risk: 1, isolated: 0 }, hub_link: [1, 400, 0],
        change: { since: "2026-07-07_t161A", lost_km2: 12.34, gained_km2: 0 }, files: { radar: "radar.webp",
          water: "water.png", change: "change.png" } }),
      pass("2026-08-12_t169D", { evaluated: false, coverage: 0.25 }),
      pass("2026-08-19_t097D", { status: { a: [1, 60, 20], b: [3, null, 40] }, unconfirmed: ["b"],
        counts: { no_data: 0, connected: 1, at_risk: 1, isolated: 0 }, hub_link: [1, 200, 0] }),
      pass("2026-08-31_t097D", { status: { a: [2, 40, 25], b: [3, null, 160] }, beta: true,
        counts: { no_data: 0, connected: 0, at_risk: 1, isolated: 1 }, hub_link: [1, 200, 0] }),
    ],
  };
}
