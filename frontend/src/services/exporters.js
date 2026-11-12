// "Download this day": the monitored communities on the selected pass as CSV or GeoJSON.

import { widthLabel } from "../utils/format.js";

const CSV_HEAD = ["community", "place", "lat", "lon", "status", "route_narrowest", "nearest_water_m", "measured_from",
  "pass_date", "track"];
const BOM = "\uFEFF";   // so spreadsheet programs read the file as UTF-8 (en dashes, accents)

// A CSV cell: numbers as they are, text quoted. Text that a spreadsheet would run as a formula is prefixed with '.
export function csvCell(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return String(value);
  const text = /^[=+\-@\t\r]/.test(value) ? `'${value}` : String(value);
  return `"${text.replace(/"/g, '""')}"`;
}

function rowValues(row, pass, widths) {
  const { c, s, r } = row;
  const routed = !!(r && r[0]);
  return { name: c.name, place: c.place, lat: c.lat, lon: c.lon, status: s,
    route: routed ? widthLabel(r[1], widths) : null, water: routed ? r[2] : null,
    from: c.access ? c.access_source : "place", date: pass.date, track: pass.track };
}

export function toCsv(rows, pass, widths) {
  const lines = [CSV_HEAD.join(",")];
  for (const row of rows) {
    const v = rowValues(row, pass, widths);
    lines.push([v.name, v.place, v.lat, v.lon, v.status, v.route ?? "", v.water ?? "", v.from, v.date, v.track]
      .map(csvCell).join(","));
  }
  return BOM + lines.join("\n");
}

export function toGeojson(rows, pass, widths) {
  const features = rows.map(row => {
    const v = rowValues(row, pass, widths);
    return { type: "Feature", geometry: { type: "Point", coordinates: [v.lon, v.lat] },
      properties: { name: v.name, place: v.place, status: v.status, route_narrowest: v.route, nearest_water_m: v.water,
        measured_from: v.from, pass_date: v.date, track: v.track } };
  });
  return JSON.stringify({ type: "FeatureCollection", features }, null, 1);
}

export const exportName = (area, pass, ext) => `communities_${area}_${pass.date}.${ext}`;

export function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
