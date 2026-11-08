// Text formatting shared by the panels, the map and the exports.

const num = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });

const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const esc = s => String(s).replace(/[&<>"']/g, c => ENTITIES[c]);
export const fmtNum = v => num.format(v);
export const fmtPeople = n => n.toLocaleString("en-GB");
export const percent = fraction => Math.round(fraction * 100);

// Route width class of a bottleneck (catalog "status" [code, bottleneck_m, distance_m]), given the area's width levels:
// null -> "no route", 0 -> "< 40 m", 60 -> "60–100 m", the widest level -> "≥ 400 m".
export function widthLabel(bottleneck, widths) {
  if (bottleneck === null || bottleneck === undefined) return "no route";
  if (bottleneck === 0) return `< ${widths[0]} m`;
  const next = widths[widths.indexOf(bottleneck) + 1];
  return next ? `${bottleneck}–${next} m` : `≥ ${bottleneck} m`;
}

// Signed change for the ledger: "no change" when it rounds to 0.0, otherwise "+1.5 cm" / "−3 km²" in bold.
export function delta(d, unit = "") {
  if (d === null || d === undefined || Number.isNaN(d)) return "";
  if (Math.round(d * 10) === 0) return "no change";
  return `<b>${d > 0 ? "+" : "−"}${num.format(Math.abs(d))}${unit}</b>`;
}

