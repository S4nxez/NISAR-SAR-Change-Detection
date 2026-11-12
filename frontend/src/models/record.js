// The pass record (catalog.json written by processing/lifeline and served by the backend) and the questions the page
// asks it.
// Pure functions: no DOM, no Leaflet, so they run under node --test.

import { LINKED_STATUSES, REPEAT_DAYS, SEVERITY } from "../config.js";
import { addDays, dayMs, DAY_MS, toIso } from "../utils/dates.js";

// The catalog plus what the page derives from it: the passes it shows, the ones whose communities were evaluated,
// the river gauge by day, the communities the radar can monitor and the name of each status code (the catalog's own
// "status_codes" table, so the page never repeats the codes the processing writes).
export function buildRecord(cat) {
  const passes = cat.passes.filter(p => p.shown !== false);
  const names = cat.status_codes || {};
  return {
    cat,
    statusName: code => names[code] || "no_data",
    passes,
    evaluated: passes.filter(p => p.evaluated && p.counts),
    gauge: new Map(cat.gauge?.series || []),
    monitored: cat.communities.filter(c => c.class === "monitored"),
  };
}

// Isolation seen on a single pass is not confirmed yet (wind or rain can spoil one image):
// it is shown and counted as at risk until the next pass with data agrees.
export const isUnconfirmed = (pass, community) => !!pass?.unconfirmed?.includes(community.id);

// Status of a community on a pass: its class when it is not monitored, else the pass result.
export function statusOf(record, pass, community) {
  if (community.class && community.class !== "monitored") return community.class;
  const result = pass?.status?.[community.id];
  if (!result) return "no_data";
  return isUnconfirmed(pass, community) ? "at_risk" : record.statusName(result[0]);
}

// True when the pass found a water route (connected or at risk) for the community, whatever its confirmation.
export function hasRoute(record, pass, community) {
  const result = pass?.status?.[community.id];
  return !!result && LINKED_STATUSES.includes(record.statusName(result[0]));
}

export function previousEvaluated(record, pass) {
  const i = record.evaluated.indexOf(pass);
  return i > 0 ? record.evaluated[i - 1] : null;
}

// The pass that describes the situation on a day: the latest evaluated pass on or before it, else the first evaluated
// pass (the day is before the record), else the latest pass shown.
export function passForDay(record, day) {
  const before = record.evaluated.filter(p => p.date <= day);
  if (before.length) return before[before.length - 1];
  return record.evaluated[0] || record.passes[record.passes.length - 1];
}

// The evaluated pass before (dir -1) or after (dir +1) a pass, in record order; from a partial pass, the nearest
// evaluated one on that side. At either end of the record, the pass itself (or the nearest evaluated one).
export function stepPass(record, pass, dir) {
  const { passes, evaluated } = record;
  if (!evaluated.length) return null;
  let i = passes.indexOf(pass);
  if (i < 0) return evaluated[evaluated.length - 1];
  for (i += dir; i >= 0 && i < passes.length; i += dir) {
    if (evaluated.includes(passes[i])) return passes[i];
  }
  return evaluated.includes(pass) ? pass : (dir < 0 ? evaluated[0] : evaluated[evaluated.length - 1]);
}

// The next pass of every track that has covered the whole area, on or after today, from the 12-day repeat cycle.
// A pass due today may not be published yet.
export function nextPasses(record, today) {
  const out = [];
  for (const track of new Set(record.evaluated.map(p => p.track))) {
    const seq = record.passes.filter(p => p.track === track);
    const last = seq[seq.length - 1];
    let t = dayMs(last.date) + REPEAT_DAYS * DAY_MS;
    while (toIso(new Date(t)) < today) t += REPEAT_DAYS * DAY_MS;
    out.push({ date: toIso(new Date(t)), track, direction: last.direction });
  }
  return out.sort((a, b) => a.date.localeCompare(b.date));
}

// River level on a day, or on the nearest day with a reading up to 3 days away (the earlier day first); null if none.
export function gaugeOn(gauge, day) {
  for (let k = 0; k <= 3; k++) {
    for (const s of k ? [-k, k] : [0]) {
      const v = gauge.get(addDays(day, s));
      if (v !== undefined) return v;
    }
  }
  return null;
}

// One row per monitored community: status on the pass, its result, and the status on the previous pass when it changed
// (only between two passes with data).
export function communityRows(record, pass, prev) {
  return record.monitored.map(c => {
    const s = statusOf(record, pass, c);
    const was = prev ? statusOf(record, prev, c) : null;
    return { c, s, r: pass.status?.[c.id], was: was && was !== s && s !== "no_data" && was !== "no_data" ? was : null };
  });
}

// Rows matching the search text and the filter ("all", "changed" or a status), the most severe and narrowest first.
export function visibleRows(rows, { query = "", filter = "all" } = {}) {
  const q = query.trim().toLowerCase();
  return rows
    .filter(x => (!q || x.c.name.toLowerCase().includes(q)) &&
      (filter === "all" || (filter === "changed" ? x.was : x.s === filter)))
    .sort((a, b) => SEVERITY[b.s] - SEVERITY[a.s] || (a.r?.[1] ?? -1) - (b.r?.[1] ?? -1) || a.c.name.localeCompare(b.c.name));
}

// Result of a community on every evaluated pass.
export const routeHistory = (record, community) =>
  record.evaluated.map(q => ({ q, s: statusOf(record, q, community), r: q.status?.[community.id] }));

// The last evaluated pass, up to a day, on which the community had a water route to the hub.
export function lastLinked(record, community, upTo) {
  for (let i = record.evaluated.length - 1; i >= 0; i--) {
    const q = record.evaluated[i];
    if (q.date <= upTo && hasRoute(record, q, community)) return q;
  }
  return null;
}
