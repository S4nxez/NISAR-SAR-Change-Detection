// HTML of the page's panels (headline, plate, map key, roster, ledger, dossier), built from the record.
// Pure: every function returns strings, so the texts can be tested without a browser. Names from the catalog are
// escaped here; the caller only assigns the result.

import { COLOR, LABEL, ROUTE_STATUSES } from "./config.js";
import { daysBetween, fmtDay, fmtShort } from "./dates.js";
import { delta, esc, fmtNum, fmtPeople, percent, widthLabel } from "./format.js";
import { gaugeOn, isUnconfirmed, lastLinked, routeHistory, statusOf } from "./record.js";

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const arrow = direction => (direction === "ascending" ? "↑" : "↓");
const hasResult = r => !!(r && r[0]);
// widthLabel gives text such as "< 40 m": escaped before it goes into HTML
const routeWidth = (record, r) => (hasResult(r) ? esc(widthLabel(r[1], record.cat.area.widths_m)) : "—");
const people = c => (c.population ? ` · ${fmtPeople(c.population)} people` : "");

// {meta, title, sub}: meta and sub are plain text, title is HTML.
export function headline(record, pass, day) {
  const { area } = record.cat;
  const meta = [fmtDay(pass.date), `${record.monitored.length} communities watched`];
  if (day && day !== pass.date) {
    const n = daysBetween(pass.date, day);
    meta.push(n > 0 ? `latest pass before ${fmtShort(day)}, ${plural(n, "day")} earlier`
      : `no full pass before ${fmtShort(day)}: first one ${plural(-n, "day")} later`);
  }
  if (!pass.evaluated || !pass.counts) {
    return { meta: meta.join(" · "), title: "This pass covers only part of the area.",
      sub: `The radar image is shown, but communities are not evaluated (${percent(pass.coverage)} % covered). Pick a full pass in the log below.` };
  }
  const n = pass.counts.isolated, risk = pass.counts.at_risk;
  const hub = esc(area.hub.name);
  const count = `<span class="count" style="color:${n ? COLOR.isolated : COLOR.connected}">${n}</span>`;
  const title = n === 0
    ? `${count} communities have lost their water route to ${hub}.`
    : `${count} ${n === 1 ? "community has" : "communities have"} lost the water route to ${hub}.`;
  const fresh = pass.unconfirmed?.length || 0;
  const sub = risk
    ? `${risk} more can only reach it through channels narrower than ${area.safe_width_m} m${fresh ? `, ${fresh} of them with no route on this pass for the first time` : ""}.`
    : `Every other watched community has a route at least ${area.safe_width_m} m wide.`;
  return { meta: meta.join(" · "), title, sub };
}

export function plate(record, pass) {
  const parts = ["<b>NISAR</b>", "L-band HH", `Track ${pass.track} ${arrow(pass.direction)} ${pass.direction}`,
    `${fmtDay(pass.date)} ${pass.time_utc} UTC`, `${record.cat.grid.pixel_m} m grid`, `${percent(pass.coverage)} % of the area`];
  if (pass.beta) parts.push("beta product");
  return parts.join(" · ");
}

export function mapKey(record, { water, change }) {
  const key = [];
  if (water) key.push(`<span><i class="swatch" style="background:#3d8bff"></i>Water</span>`,
    `<span><i class="swatch" style="background:#ffb020"></i>Channel &lt; ${record.cat.area.safe_width_m} m</span>`);
  if (change) key.push(`<span><i class="swatch" style="background:#e47759"></i>Water lost</span>`,
    `<span><i class="swatch" style="background:#68d6e6"></i>Water gained</span>`);
  key.push(...ROUTE_STATUSES.map(s => `<span><i class="glyph ${s}"></i>${LABEL[s]}</span>`));
  return key.join("");
}

export function markerTooltip(record, pass, community) {
  const s = statusOf(pass, community);
  const r = pass.status?.[community.id];
  return `<strong>${esc(community.name)}</strong> · ${LABEL[s]}` +
    (community.class === "monitored" && hasResult(r)
      ? `<br>Narrowest point ${routeWidth(record, r)} · water ${fmtNum(r[2])} m away` : "");
}

export function rosterItem(record, pass, { c, s, r, was }, selectedId) {
  const note = isUnconfirmed(pass, c) ? "<em>route lost, to confirm</em>" : was ? `<em>was ${LABEL[was].toLowerCase()}</em>` : "";
  return `<button type="button" class="${selectedId === c.id ? "is-selected" : ""}" data-id="${esc(c.id)}">
      <i class="glyph ${s}" aria-label="${LABEL[s]}"></i>
      <span class="who"><strong>${esc(c.name)}</strong><small>${esc(c.place)}${people(c)}</small></span>
      <span class="route"><b>${routeWidth(record, r)}</b>${note}</span></button>`;
}

export const rosterEmpty = pass => `<li class="empty">No community matches this filter on ${fmtShort(pass.date)}.</li>`;

const km2 = v => `<b>${fmtNum(v)} km²</b>`;

export function ledger(record, pass, prev) {
  const { area, gauge } = record.cat;
  const since = prev ? ` since ${fmtShort(prev.date)}` : "";
  const out = [];
  const row = (label, value, note) =>
    out.push(`<div class="row"><dt>${label}</dt><dd>${value}</dd><dd class="delta">${note || "&nbsp;"}</dd></div>`);
  if (pass.counts) {
    for (const s of ["isolated", "at_risk", "connected"]) {
      const d = prev?.counts ? pass.counts[s] - prev.counts[s] : null;
      row(`<i class="glyph ${s}"></i>${LABEL[s]}`, `${pass.counts[s]} <small>/ ${record.monitored.length}</small>`,
        d === null ? "" : `${delta(d)}${since}`);
    }
    const link = pass.hub_link;
    row(`Route ${esc(area.hub.name)} ↔ ${esc(area.river.name)}`, link ? esc(widthLabel(link[1], area.widths_m)) : "—",
      "narrowest point of the town's own route");
  } else {
    row("Communities", "—", "pass covers part of the area: not evaluated");
  }
  const ch = pass.change
    ? `${km2(pass.change.lost_km2)} lost, ${km2(pass.change.gained_km2)} gained since the last pass of this track` : "";
  row("Water in view", `${fmtNum(pass.water_km2)} <small>km²</small>`, ch);
  const level = gaugeOn(record.gauge, pass.date);
  if (level !== null) {
    const prevLevel = prev ? gaugeOn(record.gauge, prev.date) : null;
    row(`River at ${esc(gauge.name)}`, `${Math.round(level)} <small>cm</small>`,
      prevLevel !== null ? `${delta(level - prevLevel, " cm")}${since}` : "");
  }
  return out.join("");
}

function notMonitoredDossier(record, c) {
  const why = c.class === "inland"
    ? `No water within ${record.cat.area.access_radius_m} m on any pass: this place does not depend on the river, so it is not monitored.`
    : "No pass shows a water route to the hub that the radar can resolve at 20 m: the streams here are too narrow. Its status would be a guess, so it is left out of the counts.";
  return `<p class="name">${esc(c.name)}</p>
      <p class="status-line"><i class="glyph ${c.class}"></i>${LABEL[c.class] || LABEL.no_data}</p>
      <p class="quiet" style="margin-top:10px">${why}</p>`;
}

// Bars of the route width on every evaluated pass, taller for wider routes.
function historyBars(record, c, pass) {
  const levels = [null, 0, ...record.cat.area.widths_m];
  return routeHistory(record, c).map(({ q, s, r }) => {
    const height = hasResult(r) ? 16 + 84 * Math.max(0, levels.indexOf(r[1])) / (levels.length - 1) : 10;
    return `<i class="${s}${q.direction === "descending" ? " d" : ""}${q === pass ? " is-current" : ""}" style="height:${height}%"
      title="${fmtDay(q.date)} · ${LABEL[s]} · ${routeWidth(record, r)}"></i>`;
  }).join("");
}

// HTML of the selected community's dossier on a pass.
export function dossier(record, pass, c) {
  if (c.class !== "monitored") return notMonitoredDossier(record, c);
  const s = statusOf(pass, c), r = pass.status?.[c.id];
  const hist = record.evaluated;
  const linked = lastLinked(record, c, pass.date);
  const fact = (k, v) => `<div><span>${k}</span><strong>${v}</strong></div>`;
  return `
    <p class="name">${esc(c.name)}</p>
    <p class="status-line"><i class="glyph ${s}"></i>${LABEL[s]} on ${fmtDay(pass.date)}</p>
    ${isUnconfirmed(pass, c) ? `<p class="quiet">No water route on this pass. It counts as isolated if the next pass agrees.</p>` : ""}
    <div class="facts">
      ${fact("Narrowest point of the route", routeWidth(record, r))}
      ${fact("Nearest water", hasResult(r) ? `${fmtNum(r[2])} m` : "—")}
      ${fact(`Last linked to ${esc(record.cat.area.hub.name)}`, linked ? fmtDay(linked.date) : "—")}
      ${fact("Measured from", c.access ? esc(c.access_source) : "the place itself")}
      ${fact("Type", `${esc(c.place)}${people(c)}`)}
    </div>
    <p class="history-title">Route width on every evaluated pass</p>
    <div class="history">${historyBars(record, c, pass)}</div>
    <div class="history-axis"><span>${hist.length ? fmtDay(hist[0].date) : ""}</span><span>${hist.length ? fmtDay(hist[hist.length - 1].date) : ""}</span></div>`;
}

export function nextPassNote(ghost, today) {
  if (!ghost) return "";
  return `Next pass over the area<br><b>${fmtDay(ghost.date)}</b> · track ${ghost.track} ${arrow(ghost.direction)}` +
    (ghost.date === today ? "<br>acquired today, published within days" : "");
}
