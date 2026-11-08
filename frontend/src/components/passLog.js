// Pass log: one strip per NISAR pass on a time axis, split by how many communities were isolated, at risk or connected,
// leaning the way the satellite was flying, over the river level at the town gauge. The geometry helpers are pure.

import { DAY_MS, dayMs, daysBetween, fmtDay, fmtShort, toIso } from "../utils/dates.js";
import { gaugeOn } from "../models/record.js";

const SVGNS = "http://www.w3.org/2000/svg";
const PAD = { left: 6, right: 54, top: 26, bottom: 30 };
const MARGIN_BEFORE_MS = 10 * DAY_MS;
const MARGIN_AFTER_MS = 6 * DAY_MS;
const GAP_DAYS = 60;             // longer gaps between passes are labelled as missing data
const GAUGE_BREAK_MS = 5 * DAY_MS;
const STACK = ["isolated", "at_risk", "connected"];   // what matters sits on the baseline
const REVEAL_STEP_MS = 40;

// x position of a day between x0 and x1 for the time span t0..t1 (ms).
export const timeScale = (t0, t1, x0, x1) => iso => x0 + (x1 - x0) * (dayMs(iso) - t0) / (t1 - t0);

// First day of every month after t0 up to t1, labelled "Mar" (and "Jan 2027" for January).
export function monthTicks(t0, t1) {
  const m = new Date(t0);
  m.setUTCDate(1);
  m.setUTCMonth(m.getUTCMonth() + 1);
  const out = [];
  while (m.getTime() <= t1) {
    out.push({ iso: toIso(m), label: m.toLocaleString("en-GB", { month: "short", timeZone: "UTC" }) +
      (m.getUTCMonth() === 0 ? ` ${m.getUTCFullYear()}` : "") });
    m.setUTCMonth(m.getUTCMonth() + 1);
  }
  return out;
}

// Pairs of consecutive passes more than `days` apart.
export function recordGaps(passes, days = GAP_DAYS) {
  const out = [];
  for (let i = 1; i < passes.length; i++) {
    if (daysBetween(passes[i - 1].date, passes[i].date) > days) out.push([passes[i - 1], passes[i]]);
  }
  return out;
}

// Vertical scale of the river level: whole metres with 60 cm of margin around the readings.
export function gaugeScale(values, top, base) {
  const lo = Math.floor((Math.min(...values) - 60) / 100) * 100;
  const hi = Math.ceil((Math.max(...values) + 60) / 100) * 100;
  return { lo, hi, y: v => base - (base - top) * (v - lo) / (hi - lo) };
}

// SVG path of the gauge series, broken where readings are more than 5 days apart.
export function gaugePath(series, x, y) {
  let path = "", prevT = null;
  for (const [d, v] of series) {
    const gap = prevT !== null && dayMs(d) - prevT > GAUGE_BREAK_MS;
    path += `${!path || gap ? "M" : "L"}${x(d).toFixed(1)},${y(v).toFixed(1)}`;
    prevT = dayMs(d);
  }
  return path;
}

// Strip size from the smallest gap between passes on screen.
export function stripGeometry(xs, top, base) {
  const minGap = Math.min(...xs.slice(1).map((x, i) => x - xs[i]).filter(v => v > 0), 40);
  const w = Math.max(4, Math.min(12, minGap * 0.62));
  const h = Math.min(130, base - top - 34);
  const yb = base - 2;
  return { w, lean: w * 0.9, h, yb, yt: yb - h };
}

// Points of the parallelogram slice of a strip centred at x between heights ya (lower) and yz (upper).
export function stripPoints(geo, x, direction, ya, yz) {
  const s = direction === "ascending" ? geo.lean : -geo.lean;
  const off = y => s * (geo.yb - y) / geo.h;
  return `${x - geo.w / 2 + off(ya)},${ya} ${x + geo.w / 2 + off(ya)},${ya} ${x + geo.w / 2 + off(yz)},${yz} ${x - geo.w / 2 + off(yz)},${yz}`;
}

// Height of each status slice of a strip of height h: [[status, bottom, top], ...] from the baseline yb up.
export function stripSegments(counts, yb, h) {
  const total = counts.connected + counts.at_risk + counts.isolated || 1;
  const out = [];
  let y = yb;
  for (const s of STACK) {
    const hh = h * counts[s] / total;
    if (hh > 0) out.push([s, y, y - hh]);
    y -= hh;
  }
  return out;
}

export function passTitle(pass, level) {
  const ev = pass.evaluated && pass.counts;
  return `${fmtDay(pass.date)} · track ${pass.track} ${pass.direction}` +
    (ev ? ` · isolated ${pass.counts.isolated}, at risk ${pass.counts.at_risk}, connected ${pass.counts.connected}`
      : " · partial coverage, image only") +
    (level !== null ? ` · river ${Math.round(level)} cm` : "");
}

function svg(tag, attrs = {}, parent) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (parent) parent.appendChild(el);
  return el;
}

function text(parent, attrs, content) {
  svg("text", attrs, parent).textContent = content;
}

function drawAxis(el, x, t0, t1, base, passes, x0, x1) {
  const axis = svg("g", { class: "axis" }, el);
  svg("line", { x1: x0, x2: x1, y1: base, y2: base }, axis);
  for (const tick of monthTicks(t0, t1)) {
    const xt = x(tick.iso);
    svg("line", { x1: xt, x2: xt, y1: base, y2: base + 5 }, axis);
    text(axis, { x: xt, y: base + 18, "text-anchor": "middle" }, tick.label);
  }
  // long gaps between passes are a fact of the record, not missing rendering
  for (const [a, b] of recordGaps(passes)) {
    text(axis, { x: (x(a.date) + x(b.date)) / 2, y: base - 8, "text-anchor": "middle" }, "no NISAR data published");
  }
}

function drawGauge(el, series, x, top, base, labelX) {
  if (series.length < 2) return;
  const scale = gaugeScale(series.map(([, v]) => v), top, base);
  svg("path", { d: gaugePath(series, x, scale.y), class: "gauge-line" }, el);
  for (const v of [scale.lo, (scale.lo + scale.hi) / 2, scale.hi]) {
    text(el, { x: labelX, y: scale.y(v) + 3, class: "gauge-tick" }, `${Math.round(v)}`);
  }
  text(el, { x: labelX, y: top - 10, class: "gauge-label" }, "cm");
}

function revealOnce(g, i) {
  g.classList.add("strip-in");
  g.style.animationDelay = `${i * REVEAL_STEP_MS}ms`;
  g.addEventListener("animationend", () => { g.classList.remove("strip-in"); g.style.animationDelay = ""; }, { once: true });
}

// Draw the whole log into the <svg> element. `animate` plays the one-off reveal of the strips; onSelect(passId) is
// called when a strip is clicked or activated with the keyboard.
export function renderPassLog(el, { record, current, today, ghosts, animate, onSelect }) {
  el.innerHTML = "";
  const W = Math.max(320, el.clientWidth || 900), H = el.clientHeight || 240;
  el.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const x0 = PAD.left, x1 = W - PAD.right, top = PAD.top, base = H - PAD.bottom;
  const ps = record.passes;
  const t0 = dayMs(ps[0].date) - MARGIN_BEFORE_MS;
  const t1 = Math.max(dayMs(ps[ps.length - 1].date), dayMs(today), ...ghosts.map(g => dayMs(g.date))) + MARGIN_AFTER_MS;
  const x = timeScale(t0, t1, x0, x1);

  drawAxis(el, x, t0, t1, base, ps, x0, x1);
  const series = (record.cat.gauge?.series || []).filter(([d]) => dayMs(d) >= t0 && dayMs(d) <= t1);
  drawGauge(el, series, x, top, base, x1 + 8);

  // today and the next passes the 12-day cycle puts over the area
  const xt = x(today);
  svg("line", { x1: xt, x2: xt, y1: top - 6, y2: base, class: "today" }, el);
  text(el, { x: xt + 4, y: top - 10, class: "gauge-tick" }, "today");

  const geo = stripGeometry(ps.map(p => x(p.date)), top, base);
  for (const g of ghosts) {
    const ghost = svg("polygon", { points: stripPoints(geo, x(g.date), g.direction, geo.yb, geo.yt), class: "ghost" }, el);
    svg("title", {}, ghost).textContent = `Expected pass ${fmtDay(g.date)} · track ${g.track} ${g.direction}`;
  }

  const seen = new Map();
  ps.forEach((p, i) => {
    const dup = seen.get(p.date) || 0;   // two passes on one day sit side by side
    seen.set(p.date, dup + 1);
    const xp = x(p.date) + dup * (geo.w + 2);
    const ev = p.evaluated && p.counts;
    const g = svg("g", { class: `strip${ev ? "" : " partial"}${p === current ? " is-selected" : ""}`,
      tabindex: "0", role: "button", "data-id": p.id }, el);
    if (ev) {
      for (const [s, ya, yz] of stripSegments(p.counts, geo.yb, geo.h)) {
        svg("polygon", { points: stripPoints(geo, xp, p.direction, ya, yz), class: `seg-${s}` }, g);
      }
    }
    svg("polygon", { points: stripPoints(geo, xp, p.direction, geo.yb, geo.yt), class: "shell" }, g);
    const title = svg("title", {}, g);
    title.textContent = passTitle(p, gaugeOn(record.gauge, p.date));
    g.setAttribute("aria-label", title.textContent);
    if (animate) revealOnce(g, i);
    g.addEventListener("click", () => onSelect(p.id));
    g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(p.id); } });
  });
  if (animate) {   // never leave strips hidden if the animation did not run (throttled or frozen page)
    setTimeout(() => el.querySelectorAll(".strip-in").forEach(g => { g.classList.remove("strip-in"); g.style.animationDelay = ""; }),
      600 + ps.length * REVEAL_STEP_MS + 500);
  }
  markSelectedStrip(el, current);
}

// Highlight the strip of a pass and write its date above it.
export function markSelectedStrip(el, pass) {
  el.querySelector(".sel-label")?.remove();
  el.querySelectorAll(".strip").forEach(g => g.classList.toggle("is-selected", g.dataset.id === pass?.id));
  const g = el.querySelector(".strip.is-selected");
  if (!g) return;
  const b = g.getBBox();
  const W = el.viewBox.baseVal.width;
  text(el, { x: Math.min(b.x + b.width / 2, W - 80), y: b.y - 8, "text-anchor": "middle", class: "sel-label" },
    fmtShort(pass.date).toUpperCase());
}
