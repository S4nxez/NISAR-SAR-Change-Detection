// River Lifeline. Reads the static files written by processing/river_monitor.py:
//   public/data/monitor/<area>/catalog.json              area, communities, river gauge, one entry per pass
//   public/data/monitor/<area>/passes/<id>/radar.webp    HH backscatter preview
//   public/data/monitor/<area>/passes/<id>/water.png     water mask (narrow channels in amber)
//   public/data/monitor/<area>/passes/<id>/change.png    water lost / gained since the previous pass of the same track

const AREA = new URLSearchParams(location.search).get("area") || "tefe";
const DATA = `./public/data/monitor/${AREA}/`;
const REFRESH_MS = 10 * 60 * 1000;
const REPEAT_DAYS = 12; // NISAR repeat cycle: the same track comes back every 12 days
const CODE = { 0: "no_data", 1: "connected", 2: "at_risk", 3: "isolated" };
const LABEL = { connected: "Connected", at_risk: "At risk", isolated: "Isolated", no_data: "No data",
  inland: "Not river-dependent", unresolved: "Not resolvable" };
const COLOR = { connected: "#7dd3b0", at_risk: "#f2b544", isolated: "#ff6b5b" };
const SEVERITY = { isolated: 3, at_risk: 2, connected: 1, no_data: 0 };
const SVGNS = "http://www.w3.org/2000/svg";

const num = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });
const dayFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const shortFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const $ = sel => document.querySelector(sel);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

const state = { cat: null, passes: [], evaluated: [], pass: null, prev: null, selected: null, filter: "all",
  query: "", base: "radar", layers: {}, markers: {}, playing: null, day: null, gauge: new Map(), drawn: false };
let map, markerLayer, otherLayer;

// ---------------------------------------------------------------- helpers
const day = iso => new Date(iso + "T00:00:00Z");
const iso = d => d.toISOString().slice(0, 10);
const fmtDay = d => dayFmt.format(day(d));
const fmtShort = d => shortFmt.format(day(d));
const daysBetween = (a, b) => Math.round((day(b) - day(a)) / 86400000);
const passUrl = (p, f) => `${DATA}passes/${p.id}/${f}`;
const hubName = () => state.cat.area.hub.name;
const monitored = () => state.cat.communities.filter(c => c.class === "monitored");
const arrow = p => (p.direction === "ascending" ? "↑" : "↓");

// Isolation seen on a single pass is not confirmed yet (wind or rain can spoil one image):
// it is shown and counted as at risk until the next pass with data agrees.
const unconfirmed = (pass, c) => !!pass?.unconfirmed?.includes(c.id);

function statusOf(pass, c) {
  if (c.class && c.class !== "monitored") return c.class;
  const r = pass?.status?.[c.id];
  if (!r) return "no_data";
  return unconfirmed(pass, c) ? "at_risk" : CODE[r[0]];
}

function widthLabel(b) {
  if (b === null || b === undefined) return "no route";
  const w = state.cat.area.widths_m;
  if (b === 0) return `< ${w[0]} m`;
  const next = w[w.indexOf(b) + 1];
  return next ? `${b}–${next} m` : `≥ ${b} m`;
}

function gaugeOn(d) {
  for (let k = 0; k <= 3; k++) {
    for (const s of k ? [-k, k] : [0]) {
      const v = state.gauge.get(iso(new Date(day(d).getTime() + s * 86400000)));
      if (v !== undefined) return v;
    }
  }
  return null;
}

function previousEvaluated(pass) {
  const i = state.evaluated.indexOf(pass);
  return i > 0 ? state.evaluated[i - 1] : null;
}

function passForDay(d) {
  const ev = state.evaluated.filter(p => p.date <= d);
  return ev.length ? ev[ev.length - 1] : state.evaluated[0] || state.passes[state.passes.length - 1];
}

function nextPasses() {
  const today = iso(new Date());
  const out = [];
  // only tracks whose passes cover the whole area; a pass due today may not be published yet
  for (const track of new Set(state.evaluated.map(p => p.track))) {
    const seq = state.passes.filter(p => p.track === track);
    const last = seq[seq.length - 1];
    let t = day(last.date).getTime() + REPEAT_DAYS * 86400000;
    while (iso(new Date(t)) < today) t += REPEAT_DAYS * 86400000;
    out.push({ date: iso(new Date(t)), track, direction: last.direction });
  }
  return out.sort((a, b) => a.date.localeCompare(b.date));
}

// ---------------------------------------------------------------- map
function glyphIcon(status, selected) {
  const size = status === "connected" || status === "at_risk" || status === "isolated" ? 14 : 9;
  return L.divIcon({ className: "", iconSize: [size, size],
    html: `<div class="mk ${status}${selected ? " is-selected" : ""}"></div>` });
}

function initMap() {
  map = L.map("map", { zoomControl: true, scrollWheelZoom: true, attributionControl: true, zoomSnap: 0.25 });
  // OpenStreetMap standard tiles need no API key; monitor.css darkens them.
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors · NISAR: NASA/ISRO, ASF DAAC", maxZoom: 18, className: "basemap-dark"
  }).addTo(map);
  map.createPane("radar").style.zIndex = 330;
  map.createPane("water").style.zIndex = 340;
  map.createPane("change").style.zIndex = 350;
  otherLayer = L.layerGroup();
  markerLayer = L.layerGroup().addTo(map);
  map.fitBounds(state.cat.grid.bounds);

  // the edge of the monitored area, drawn like a sensor footprint
  const circ = state.cat.area.circle;
  if (circ) {
    L.circle([circ.lat, circ.lon], { radius: circ.radius_km * 1000, color: "#b6c3ff", weight: 1, opacity: 0.55,
      dashArray: "2 6", fill: false, interactive: false }).addTo(map);
  }

  const { hub } = state.cat.area;
  const at = hub.access || hub;
  L.marker([at.lat, at.lon], { icon: L.divIcon({ className: "", html: '<div class="hub-mk"></div>', iconSize: [16, 16] }),
    zIndexOffset: 1000, keyboard: false })
    .bindTooltip(`<strong>${esc(hub.name)}</strong><br>Hub town: routes are traced to here`, { className: "tip" }).addTo(map);
  placeMarkers();
}

// Monitored communities on the main layer, the rest on the optional one. Classes come from the
// whole record, so they can change when new passes arrive.
function placeMarkers() {
  markerLayer.clearLayers();
  otherLayer.clearLayers();
  for (const c of state.cat.communities) {
    let m = state.markers[c.id];
    if (!m) {
      m = L.marker([c.lat, c.lon], { icon: glyphIcon("no_data"), keyboard: false })
        .bindTooltip("", { className: "tip" })
        .on("click", () => selectCommunity(c.id, false));
      state.markers[c.id] = m;
    }
    (c.class === "monitored" ? markerLayer : otherLayer).addLayer(m);
  }
}

function setOverlay(key, url, pane, opacity, on) {
  if (state.layers[key]) { state.layers[key].remove(); state.layers[key] = null; }
  if (on && url) state.layers[key] = L.imageOverlay(url, state.cat.grid.bounds, { pane, opacity, interactive: false }).addTo(map);
}

function refreshLayers() {
  const p = state.pass;
  const op = Number($("#opacity").value) / 100;
  setOverlay("radar", passUrl(p, p.files.radar), "radar", 1, state.base === "radar");
  setOverlay("water", passUrl(p, p.files.water), "water", op, $("#toggle-water").checked);
  setOverlay("change", p.files.change && passUrl(p, p.files.change), "change", 1, $("#toggle-change").checked);
  if ($("#toggle-other").checked) otherLayer.addTo(map); else otherLayer.remove();
  const key = [];
  if ($("#toggle-water").checked) key.push(`<span><i class="swatch" style="background:#3d8bff"></i>Water</span>`,
    `<span><i class="swatch" style="background:#ffb020"></i>Channel &lt; ${state.cat.area.safe_width_m} m</span>`);
  if ($("#toggle-change").checked) key.push(`<span><i class="swatch" style="background:#e47759"></i>Water lost</span>`,
    `<span><i class="swatch" style="background:#68d6e6"></i>Water gained</span>`);
  key.push(...["connected", "at_risk", "isolated"].map(s => `<span><i class="glyph ${s}"></i>${LABEL[s]}</span>`));
  $("#map-key").innerHTML = key.join("");
}

function refreshMarkers() {
  for (const c of state.cat.communities) {
    const s = statusOf(state.pass, c);
    const r = state.pass.status?.[c.id];
    const m = state.markers[c.id];
    m.setIcon(glyphIcon(s, c.id === state.selected));
    m.setZIndexOffset(SEVERITY[s] ? SEVERITY[s] * 100 : 0);
    m.setTooltipContent(`<strong>${esc(c.name)}</strong> · ${LABEL[s]}` +
      (c.class === "monitored" && r && r[0] ? `<br>Narrowest point ${widthLabel(r[1])} · water ${num.format(r[2])} m away` : ""));
  }
}

// ---------------------------------------------------------------- headline and plate
function renderHeadline() {
  const p = state.pass;
  const total = monitored().length;
  const meta = [fmtDay(p.date), `${total} communities watched`];
  if (state.day && state.day !== p.date) meta.push(`latest pass before ${fmtShort(state.day)}, ${daysBetween(p.date, state.day)} days earlier`);
  $("#headline-meta").textContent = meta.join(" · ");
  if (!p.evaluated || !p.counts) {
    $("#headline-text").textContent = "This pass covers only part of the area.";
    $("#headline-sub").textContent = `The radar image is shown, but communities are not evaluated (${Math.round(p.coverage * 100)} % covered). Pick a full pass in the log below.`;
    return;
  }
  const n = p.counts.isolated, risk = p.counts.at_risk;
  const count = `<span class="count" style="color:${n ? COLOR.isolated : COLOR.connected}">${n}</span>`;
  $("#headline-text").innerHTML = n === 0
    ? `${count} communities have lost their water route to ${esc(hubName())}.`
    : `${count} ${n === 1 ? "community has" : "communities have"} lost the water route to ${esc(hubName())}.`;
  const fresh = p.unconfirmed?.length || 0;
  const bits = [];
  if (risk) bits.push(`${risk} more can only reach it through channels narrower than ${state.cat.area.safe_width_m} m${fresh ? `, ${fresh} of them with no route on this pass for the first time` : ""}.`);
  else bits.push(`Every other watched community has a route at least ${state.cat.area.safe_width_m} m wide.`);
  $("#headline-sub").textContent = bits.join(" ");
}

function renderPlate() {
  const p = state.pass;
  const parts = [`<b>NISAR</b>`, "L-band HH", `Track ${p.track} ${arrow(p)} ${p.direction}`, `${fmtDay(p.date)} ${p.time_utc} UTC`,
    `${state.cat.grid.pixel_m} m grid`, `${Math.round(p.coverage * 100)} % of the area`];
  if (p.beta) parts.push("beta product");
  $("#plate").innerHTML = parts.join(" · ");
}

// ---------------------------------------------------------------- roster
function rows() {
  const p = state.pass, prev = state.prev;
  return monitored().map(c => {
    const s = statusOf(p, c), was = prev ? statusOf(prev, c) : null;
    return { c, s, r: p.status?.[c.id], was: was && was !== s && s !== "no_data" && was !== "no_data" ? was : null };
  });
}

function renderRoster() {
  const q = state.query.trim().toLowerCase();
  const all = rows();
  const list = all.filter(x => (!q || x.c.name.toLowerCase().includes(q)) &&
    (state.filter === "all" || (state.filter === "changed" ? x.was : x.s === state.filter)));
  list.sort((a, b) => SEVERITY[b.s] - SEVERITY[a.s] || (a.r?.[1] ?? -1) - (b.r?.[1] ?? -1) || a.c.name.localeCompare(b.c.name));
  const el = $("#community-list");
  el.innerHTML = list.length ? "" : `<li class="empty">No community matches this filter on ${fmtShort(state.pass.date)}.</li>`;
  for (const { c, s, r, was } of list) {
    const li = document.createElement("li");
    const note = unconfirmed(state.pass, c) ? "<em>route lost, to confirm</em>" : was ? `<em>was ${LABEL[was].toLowerCase()}</em>` : "";
    li.innerHTML = `<button type="button" class="${state.selected === c.id ? "is-selected" : ""}" data-id="${c.id}">
      <i class="glyph ${s}" aria-label="${LABEL[s]}"></i>
      <span class="who"><strong>${esc(c.name)}</strong><small>${esc(c.place)}${c.population ? ` · ${c.population.toLocaleString("en-GB")} people` : ""}</small></span>
      <span class="route"><b>${r && r[0] ? widthLabel(r[1]) : "—"}</b>${note}</span></button>`;
    li.firstElementChild.addEventListener("click", () => selectCommunity(c.id, true));
    el.appendChild(li);
  }
  $("#roster-count").textContent = `${list.length} of ${all.length}`;
}

// ---------------------------------------------------------------- pass log (signature)
function svg(tag, attrs = {}, parent) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (parent) parent.appendChild(el);
  return el;
}

function renderSwath() {
  const el = $("#swath");
  el.innerHTML = "";
  const W = Math.max(320, el.clientWidth || 900), H = el.clientHeight || 240;
  el.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const L0 = 6, R0 = W - 54, top = 26, base = H - 30;
  const ps = state.passes;
  const ghosts = nextPasses();
  const today = iso(new Date());
  const t0 = day(ps[0].date).getTime() - 10 * 86400000;
  const tEnd = Math.max(day(ps[ps.length - 1].date).getTime(), day(today).getTime(), ...ghosts.map(g => day(g.date).getTime())) + 6 * 86400000;
  const X = d => L0 + (R0 - L0) * (day(d).getTime() - t0) / (tEnd - t0);

  // axis: months
  const axis = svg("g", { class: "axis" }, el);
  svg("line", { x1: L0, x2: R0, y1: base, y2: base }, axis);
  const m = new Date(t0); m.setUTCDate(1); m.setUTCMonth(m.getUTCMonth() + 1);
  while (m.getTime() <= tEnd) {
    const x = X(iso(m));
    svg("line", { x1: x, x2: x, y1: base, y2: base + 5 }, axis);
    const t = svg("text", { x, y: base + 18, "text-anchor": "middle" }, axis);
    t.textContent = m.toLocaleString("en-GB", { month: "short", timeZone: "UTC" }) + (m.getUTCMonth() === 0 ? ` ${m.getUTCFullYear()}` : "");
    m.setUTCMonth(m.getUTCMonth() + 1);
  }

  // long gaps between passes are a fact of the record, not missing rendering
  for (let i = 1; i < ps.length; i++) {
    if (daysBetween(ps[i - 1].date, ps[i].date) > 60) {
      const t = svg("text", { x: (X(ps[i - 1].date) + X(ps[i].date)) / 2, y: base - 8, "text-anchor": "middle" }, axis);
      t.textContent = "no NISAR data published";
    }
  }

  // river gauge
  const gs = (state.cat.gauge?.series || []).filter(([d]) => day(d).getTime() >= t0 && day(d).getTime() <= tEnd);
  if (gs.length > 1) {
    const vals = gs.map(([, v]) => v);
    const lo = Math.floor((Math.min(...vals) - 60) / 100) * 100, hi = Math.ceil((Math.max(...vals) + 60) / 100) * 100;
    const Y = v => base - (base - top) * (v - lo) / (hi - lo);
    let path = "", prevT = null;
    for (const [d, v] of gs) {
      const gap = prevT !== null && day(d).getTime() - prevT > 5 * 86400000;
      path += `${!path || gap ? "M" : "L"}${X(d).toFixed(1)},${Y(v).toFixed(1)}`;
      prevT = day(d).getTime();
    }
    svg("path", { d: path, class: "gauge-line" }, el);
    for (const v of [lo, (lo + hi) / 2, hi]) {
      const t = svg("text", { x: R0 + 8, y: Y(v) + 3, class: "gauge-tick" }, el);
      t.textContent = `${Math.round(v)}`;
    }
    const lbl = svg("text", { x: R0 + 8, y: top - 10, class: "gauge-label" }, el);
    lbl.textContent = "cm";
  }

  // today and the next passes the 12-day cycle puts over the area
  const xt = X(today);
  svg("line", { x1: xt, x2: xt, y1: top - 6, y2: base, class: "today" }, el);
  const tt = svg("text", { x: xt + 4, y: top - 10, class: "gauge-tick" }, el); tt.textContent = "today";

  const minGap = Math.min(...ps.slice(1).map((p, i) => X(p.date) - X(ps[i].date)).filter(v => v > 0), 40);
  const w = Math.max(4, Math.min(12, minGap * 0.62));
  const lean = w * 0.9, h = Math.min(130, base - top - 34), yb = base - 2, yt = yb - h;
  const shape = (x, dir, ya, yz) => {          // parallelogram slice between heights ya (lower) and yz (upper)
    const s = dir === "ascending" ? lean : -lean;
    const off = y => s * (yb - y) / h;
    return `${x - w / 2 + off(ya)},${ya} ${x + w / 2 + off(ya)},${ya} ${x + w / 2 + off(yz)},${yz} ${x - w / 2 + off(yz)},${yz}`;
  };

  for (const g of ghosts) {
    const ghost = svg("polygon", { points: shape(X(g.date), g.direction, yb, yt), class: "ghost" }, el);
    svg("title", {}, ghost).textContent = `Expected pass ${fmtDay(g.date)} · track ${g.track} ${g.direction}`;
  }

  const seen = new Map();
  ps.forEach((p, i) => {
    const dup = seen.get(p.date) || 0;
    seen.set(p.date, dup + 1);
    const x = X(p.date) + dup * (w + 2);
    const g = svg("g", { class: `strip${p.evaluated && p.counts ? "" : " partial"}${p === state.pass ? " is-selected" : ""}`,
      tabindex: "0", role: "button", "data-id": p.id }, el);
    const ev = p.evaluated && p.counts;
    if (ev) {
      const tot = p.counts.connected + p.counts.at_risk + p.counts.isolated || 1;
      let y = yb;
      for (const s of ["isolated", "at_risk", "connected"]) {   // what matters sits on the baseline
        const hh = h * p.counts[s] / tot;
        if (hh > 0) svg("polygon", { points: shape(x, p.direction, y, y - hh), class: `seg-${s}` }, g);
        y -= hh;
      }
    }
    svg("polygon", { points: shape(x, p.direction, yb, yt), class: "shell" }, g);
    const lvl = gaugeOn(p.date);
    const title = svg("title", {}, g);
    title.textContent = `${fmtDay(p.date)} · track ${p.track} ${p.direction}` +
      (ev ? ` · isolated ${p.counts.isolated}, at risk ${p.counts.at_risk}, connected ${p.counts.connected}` : " · partial coverage, image only") +
      (lvl !== null ? ` · river ${Math.round(lvl)} cm` : "");
    g.setAttribute("aria-label", title.textContent);
    // one-off "downlink" reveal on first draw; skipped when motion is reduced or the page is hidden
    // (hidden pages pause animations, which would leave the strips invisible)
    if (!state.drawn && !reducedMotion && document.visibilityState === "visible") {
      g.classList.add("strip-in");
      g.style.animationDelay = `${i * 40}ms`;
      g.addEventListener("animationend", () => { g.classList.remove("strip-in"); g.style.animationDelay = ""; }, { once: true });
    }
    g.addEventListener("click", () => selectPass(p.id, true));
    g.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectPass(p.id, true); } });
  });
  if (!state.drawn) {   // never leave strips hidden if the animation did not run (throttled or frozen page)
    setTimeout(() => el.querySelectorAll(".strip-in").forEach(g => { g.classList.remove("strip-in"); g.style.animationDelay = ""; }),
      600 + ps.length * 40 + 500);
  }
  state.drawn = true;
  markSelectedStrip();

  const ng = ghosts[0];
  $("#next-pass-note").innerHTML = ng ? `Next pass over the area<br><b>${fmtDay(ng.date)}</b> · track ${ng.track} ${ng.direction === "ascending" ? "↑" : "↓"}` +
    (ng.date === today ? "<br>acquired today, published within days" : "") : "";
}

function markSelectedStrip() {
  const el = $("#swath");
  el.querySelector(".sel-label")?.remove();
  el.querySelectorAll(".strip").forEach(g => g.classList.toggle("is-selected", g.dataset.id === state.pass?.id));
  const g = el.querySelector(".strip.is-selected");
  if (!g) return;
  const b = g.getBBox();
  const W = el.viewBox.baseVal.width;
  const t = svg("text", { x: Math.min(b.x + b.width / 2, W - 80), y: b.y - 8, "text-anchor": "middle", class: "sel-label" }, el);
  t.textContent = fmtShort(state.pass.date).toUpperCase();
}

// ---------------------------------------------------------------- ledger and dossier
function delta(d, unit = "") {
  if (d === null || d === undefined || Number.isNaN(d)) return "";
  if (Math.round(d * 10) === 0) return "no change";
  return `<b>${d > 0 ? "+" : "−"}${num.format(Math.abs(d))}${unit}</b>`;
}

function renderLedger() {
  const p = state.pass, prev = state.prev;
  const total = monitored().length;
  const since = prev ? ` since ${fmtShort(prev.date)}` : "";
  const out = [];
  const row = (label, value, note) => out.push(`<div class="row"><dt>${label}</dt><dd>${value}</dd><dd class="delta">${note || "&nbsp;"}</dd></div>`);
  if (p.counts) {
    for (const s of ["isolated", "at_risk", "connected"]) {
      const d = prev?.counts ? p.counts[s] - prev.counts[s] : null;
      row(`<i class="glyph ${s}"></i>${LABEL[s]}`, `${p.counts[s]} <small>/ ${total}</small>`, d === null ? "" : `${delta(d)}${since}`);
    }
    const link = p.hub_link;
    row(`Route ${esc(hubName())} ↔ ${esc(state.cat.area.river.name)}`, link ? widthLabel(link[1]) : "—", "narrowest point of the town's own route");
  } else {
    row("Communities", "—", "pass covers part of the area: not evaluated");
  }
  const ch = p.change ? `${delta(-p.change.lost_km2, " km²")} lost, ${delta(p.change.gained_km2, " km²")} gained since the last pass of this track` : "";
  row("Water in view", `${num.format(p.water_km2)} <small>km²</small>`, ch);
  const lvl = gaugeOn(p.date);
  if (lvl !== null) {
    const pl = prev ? gaugeOn(prev.date) : null;
    row(`River at ${esc(state.cat.gauge.name)}`, `${Math.round(lvl)} <small>cm</small>`, pl !== null ? `${delta(lvl - pl, " cm")}${since}` : "");
  }
  $("#ledger").innerHTML = out.join("");
}

function renderDossier() {
  const c = state.cat.communities.find(x => x.id === state.selected);
  if (!c) return;
  const p = state.pass, s = statusOf(p, c), r = p.status?.[c.id];
  $("#dossier-title").textContent = "Community";
  if (c.class !== "monitored") {
    $("#dossier").innerHTML = `<p class="name">${esc(c.name)}</p>
      <p class="status-line"><i class="glyph ${c.class}"></i>${LABEL[c.class]}</p>
      <p class="quiet" style="margin-top:10px">${c.class === "inland"
        ? `No water within ${state.cat.area.access_radius_m} m on any pass: this place does not depend on the river, so it is not monitored.`
        : "No pass shows a water route to the hub that the radar can resolve at 20 m: the streams here are too narrow. Its status would be a guess, so it is left out of the counts."}</p>`;
    return;
  }
  const hist = state.evaluated.map(q => ({ q, s: statusOf(q, c), r: q.status?.[c.id] }));
  const levels = [null, 0, ...state.cat.area.widths_m];
  const bars = hist.map(({ q, s, r }) => {
    const hpc = r && r[0] ? 16 + 84 * Math.max(0, levels.indexOf(r[1])) / (levels.length - 1) : 10;
    return `<i class="${s}${q.direction === "descending" ? " d" : ""}${q === p ? " is-current" : ""}" style="height:${hpc}%"
      title="${fmtDay(q.date)} · ${LABEL[s]} · ${r && r[0] ? widthLabel(r[1]) : "—"}"></i>`;
  }).join("");
  const lastOk = [...hist].reverse().find(h => h.q.date <= p.date && (h.s === "connected" || h.s === "at_risk"));
  const fact = (k, v) => `<div><span>${k}</span><strong>${v}</strong></div>`;
  $("#dossier").innerHTML = `
    <p class="name">${esc(c.name)}</p>
    <p class="status-line"><i class="glyph ${s}"></i>${LABEL[s]} on ${fmtDay(p.date)}</p>
    ${unconfirmed(p, c) ? `<p class="quiet">No water route on this pass. It counts as isolated if the next pass agrees.</p>` : ""}
    <div class="facts">
      ${fact("Narrowest point of the route", r && r[0] ? widthLabel(r[1]) : "—")}
      ${fact("Nearest water", r && r[0] ? `${num.format(r[2])} m` : "—")}
      ${fact(`Last linked to ${esc(hubName())}`, lastOk ? fmtDay(lastOk.q.date) : "—")}
      ${fact("Measured from", c.access ? esc(c.access_source) : "the place itself")}
      ${fact("Type", `${esc(c.place)}${c.population ? ` · ${c.population.toLocaleString("en-GB")} people` : ""}`)}
    </div>
    <p class="history-title">Route width on every evaluated pass</p>
    <div class="history">${bars}</div>
    <div class="history-axis"><span>${hist.length ? fmtDay(hist[0].q.date) : ""}</span><span>${hist.length ? fmtDay(hist[hist.length - 1].q.date) : ""}</span></div>`;
}

// ---------------------------------------------------------------- selection
function selectPass(id, fromUser) {
  const p = state.passes.find(q => q.id === id);
  if (!p) return;
  state.pass = p;
  state.prev = p.evaluated ? previousEvaluated(p) : null;
  if (fromUser) { state.day = p.date; $("#date-input").value = p.date; }
  refreshLayers();
  refreshMarkers();
  renderHeadline();
  renderPlate();
  renderRoster();
  renderLedger();
  renderDossier();
  markSelectedStrip();
  writeHash();
}

function selectCommunity(id, fly) {
  state.selected = id;
  const c = state.cat.communities.find(x => x.id === id);
  if (c && fly) map.flyTo([c.lat, c.lon], Math.max(map.getZoom(), 12), { duration: reducedMotion ? 0 : 0.6 });
  refreshMarkers();
  renderRoster();
  renderDossier();
  writeHash();
}

function writeHash() {
  const h = new URLSearchParams();
  if (state.day) h.set("d", state.day);
  if (state.selected) h.set("c", state.selected);
  history.replaceState(null, "", "#" + h.toString());
}

function step(dir) {
  const ev = state.evaluated;
  const i = ev.indexOf(state.pass);
  const j = i < 0 ? ev.length - 1 : Math.min(ev.length - 1, Math.max(0, i + dir));
  if (ev[j]) selectPass(ev[j].id, true);
}

function togglePlay() {
  const btn = $("#play");
  if (state.playing) {
    clearInterval(state.playing); state.playing = null;
    btn.setAttribute("aria-pressed", "false"); btn.textContent = "Play record";
    return;
  }
  if (state.evaluated.indexOf(state.pass) === state.evaluated.length - 1) selectPass(state.evaluated[0].id, true);
  btn.setAttribute("aria-pressed", "true"); btn.textContent = "Pause";
  state.playing = setInterval(() => {
    if (state.evaluated.indexOf(state.pass) >= state.evaluated.length - 1) return togglePlay();
    step(1);
  }, 1300);
}

// ---------------------------------------------------------------- exports
function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function exportCsv() {
  const head = ["community", "place", "lat", "lon", "status", "route_narrowest", "nearest_water_m", "measured_from", "pass_date", "track"];
  const lines = [head.join(",")];
  for (const { c, s, r } of rows()) {
    lines.push([`"${c.name.replace(/"/g, '""')}"`, c.place, c.lat, c.lon, s, r && r[0] ? widthLabel(r[1]) : "", r && r[0] ? r[2] : "",
      `"${c.access ? c.access_source : "place"}"`, state.pass.date, state.pass.track].join(","));
  }
  download(`communities_${AREA}_${state.pass.date}.csv`, lines.join("\n"), "text/csv");
}

function exportGeojson() {
  const features = rows().map(({ c, s, r }) => ({ type: "Feature", geometry: { type: "Point", coordinates: [c.lon, c.lat] },
    properties: { name: c.name, place: c.place, status: s, route_narrowest: r && r[0] ? widthLabel(r[1]) : null,
      nearest_water_m: r && r[0] ? r[2] : null, measured_from: c.access ? c.access_source : "place",
      pass_date: state.pass.date, track: state.pass.track } }));
  download(`communities_${AREA}_${state.pass.date}.geojson`, JSON.stringify({ type: "FeatureCollection", features }, null, 1), "application/geo+json");
}

// ---------------------------------------------------------------- boot
async function loadCatalog() {
  const res = await fetch(DATA + "catalog.json", { cache: "no-cache" });
  if (!res.ok) throw new Error("catalog.json not found");
  return res.json();
}

function applyCatalog(cat) {
  state.cat = cat;
  state.passes = cat.passes.filter(p => p.shown !== false);
  state.evaluated = state.passes.filter(p => p.evaluated && p.counts);
  state.gauge = new Map((cat.gauge?.series || []).map(([d, v]) => [d, v]));
  $("#mast-mission").textContent = `NISAR L-band radar · ${cat.area.name}`;
  $("#gauge-name").textContent = cat.gauge?.name || "the town gauge";
  $("#foot-sources").textContent = `Radar: ${cat.sources.radar} · Places: ${cat.sources.places}` +
    (cat.gauge ? ` · River level: ${cat.gauge.source}` : "");
  $("#foot-search").textContent = cat.last_search ? `Last check for new passes: ${cat.last_search.replace("T", " ").replace("Z", " UTC")}` : "";
  const di = $("#date-input");
  di.min = state.passes[0].date;
  di.max = iso(new Date());
}

function bindUi() {
  $("#date-input").addEventListener("change", e => {
    if (!e.target.value) return;
    state.day = e.target.value;
    const p = passForDay(state.day);
    if (p) selectPass(p.id, false);
  });
  $("#prev-pass").addEventListener("click", () => step(-1));
  $("#next-pass").addEventListener("click", () => step(1));
  $("#play").addEventListener("click", togglePlay);
  document.querySelectorAll(".layers-base button").forEach(b => b.addEventListener("click", () => {
    state.base = b.dataset.base;
    document.querySelectorAll(".layers-base button").forEach(x => x.classList.toggle("is-on", x === b));
    refreshLayers();
  }));
  ["#toggle-water", "#toggle-change", "#toggle-other", "#opacity"].forEach(s => $(s).addEventListener("input", refreshLayers));
  $("#search").addEventListener("input", e => { state.query = e.target.value; renderRoster(); });
  document.querySelectorAll(".filter").forEach(b => b.addEventListener("click", () => {
    state.filter = b.dataset.filter;
    document.querySelectorAll(".filter").forEach(x => x.classList.toggle("is-on", x === b));
    renderRoster();
  }));
  $("#export-csv").addEventListener("click", exportCsv);
  $("#export-geojson").addEventListener("click", exportGeojson);
  let t;
  addEventListener("resize", () => { clearTimeout(t); t = setTimeout(renderSwath, 150); });
}

function showNotice(html) {
  const n = document.createElement("div");
  n.className = "notice";
  n.innerHTML = html;
  document.querySelector(".map-frame").appendChild(n);
}

async function boot() {
  let cat;
  try {
    cat = await loadCatalog();
  } catch {
    $("#headline-meta").textContent = "No record yet";
    $("#headline-text").textContent = "The pass record has not been built.";
    showNotice(`Run <code>python processing/river_monitor.py communities</code> and <code>python processing/river_monitor.py update</code>, then reload this page.`);
    return;
  }
  if (!cat.passes?.length) return;
  applyCatalog(cat);
  initMap();
  bindUi();
  const h = new URLSearchParams(location.hash.slice(1));
  state.selected = h.get("c");
  state.day = h.get("d") || state.evaluated[state.evaluated.length - 1]?.date || state.passes[state.passes.length - 1].date;
  $("#date-input").value = state.day;
  state.pass = passForDay(state.day);
  renderSwath();
  selectPass(state.pass.id, false);

  // The watcher (river_monitor.py watch) keeps adding passes; pick them up without a reload.
  setInterval(async () => {
    try {
      const fresh = await loadCatalog();
      if (fresh.passes.length === state.cat.passes.length && fresh.last_search === state.cat.last_search) return;
      const atLatest = state.pass === state.evaluated[state.evaluated.length - 1];
      const keep = state.pass.id;
      applyCatalog(fresh);
      placeMarkers();
      renderSwath();
      const latest = state.evaluated[state.evaluated.length - 1];
      selectPass(atLatest && latest ? latest.id : keep, atLatest);
    } catch { /* keep the current view if the refresh fails */ }
  }, REFRESH_MS);
}

window.addEventListener("load", boot);
