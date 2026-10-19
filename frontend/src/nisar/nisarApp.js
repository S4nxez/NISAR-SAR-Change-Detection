// NISAR change-detection page. Reads the static files produced by processing/nisar_cambio.py:
//   public/data/nisar/pares.json            index of acquisition pairs
//   public/data/nisar/<id>/cambio.json      metadata, statistics and change zones
//   public/data/nisar/<id>/*.webp|png       image overlays and 20 m zone crops

const DATA = "./public/data/nisar/";
const CLASS_LABELS = {
  agua_nueva: { en: "New water", read: "Surface that now returns a smooth-water echo: possible flooding or river rise." },
  agua_desaparece: { en: "Water receded", read: "Surface that was water and no longer is: receding flood or shrinking lake." },
  descenso: { en: "Backscatter drop", read: "Weaker radar echo: possible clearing, harvest or drier ground." },
  aumento: { en: "Backscatter rise", read: "Stronger radar echo: growing vegetation, new structures or wetter ground." }
};
const fmt = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });
const fmt2 = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });
const $ = sel => document.querySelector(sel);

const state = { pair: null, base: "antes", zones: [], selected: null, layers: {}, charts: {} };
let map, zoneLayer, highlight;

function initMap() {
  map = L.map("map", { zoomControl: true, scrollWheelZoom: true }).setView([0, 0], 2);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap &copy; CARTO · NISAR: NASA/ISRO, ASF DAAC", subdomains: "abcd", maxZoom: 18
  }).addTo(map);
  map.createPane("radar").style.zIndex = 350;
  map.createPane("change").style.zIndex = 360;
  zoneLayer = L.layerGroup().addTo(map);
}

function overlay(url, bounds, pane, opacity = 1) {
  return L.imageOverlay(url, bounds, { pane, opacity, interactive: false });
}

function refreshLayers() {
  const { layers, base } = state;
  ["antes", "despues"].forEach(k => {
    if (!layers[k]) return;
    if (k === base) layers[k].addTo(map); else layers[k].remove();
  });
  const opacity = Number($("#opacity").value) / 100;
  const show = (layer, on) => { if (!layer) return; layer.setOpacity(opacity); on ? layer.addTo(map) : layer.remove(); };
  show(layers.cambio, $("#toggle-change").checked);
  show(layers.diferencia, $("#toggle-diff").checked);
  document.querySelectorAll(".seg button").forEach(b => b.classList.toggle("is-on", b.dataset.base === base));
}

function daysBetween(a, b) {
  const d = (new Date(b) - new Date(a)) / 86400000;
  return Number.isFinite(d) ? Math.round(d) : null;
}

async function loadPair(entry) {
  const res = await fetch(DATA + entry.ruta);
  if (!res.ok) throw new Error(`Cannot load ${entry.ruta}`);
  const pair = await res.json();
  const dir = DATA + entry.ruta.replace(/cambio\.json$/, "");
  state.pair = { ...pair, dir };
  state.zones = pair.zonas;
  state.selected = null;

  Object.values(state.layers).forEach(l => l.remove());
  const b = pair.bounds;
  state.layers = {
    antes: overlay(dir + pair.imagenes.antes, b, "radar"),
    despues: overlay(dir + pair.imagenes.despues, b, "radar"),
    diferencia: overlay(dir + pair.imagenes.diferencia, b, "change"),
    cambio: overlay(dir + pair.imagenes.cambio, b, "change")
  };
  map.fitBounds(b, { padding: [10, 10] });
  refreshLayers();
  renderNote(pair);
  renderStats(pair);
  renderKey(pair);
  renderZones();
  renderCharts(pair);
  renderDetail(null);
}

function renderNote(pair) {
  const el = $("#pair-note");
  const parts = [];
  if (pair.simulado) parts.push("<strong>SIMULATED</strong>");
  if (pair.nota) parts.push(pair.nota);
  el.innerHTML = parts.join(" ");
  el.hidden = parts.length === 0;
  $("#data-tag").textContent = pair.simulado ? "SIMULATED AFTER-IMAGE" : "NISAR GCOV · HH";
}

function renderStats(pair) {
  const s = pair.estadisticas;
  const changed = Object.values(s.zonas_km2_por_clase).reduce((t, v) => t + v, 0);
  $("#stat-area").textContent = fmt.format(s.area_valida_km2);
  $("#stat-changed").textContent = fmt.format(changed);
  $("#stat-changed-foot").textContent = `km² in ${s.zonas_total} change zones · ${fmt2.format(100 * changed / s.area_valida_km2)}% of area`;
  const d1 = new Date(pair.antes.fecha), d2 = new Date(pair.despues.fecha);
  const short = d => d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }).toUpperCase();
  $("#stat-dates").innerHTML = `${short(d1)} → ${short(d2)} <small>${d2.getFullYear()}</small>`;
  const days = daysBetween(pair.antes.fecha, pair.despues.fecha);
  $("#stat-days").textContent = `${days ?? "?"} days apart · track ${pair.pista ?? "?"} / frame ${pair.frame ?? "?"}`;
  const shift = pair.parametros.desplazamiento_global_dB;
  $("#stat-shift").textContent = `${shift > 0 ? "+" : ""}${fmt2.format(shift)} dB`;
}

function renderKey(pair) {
  $("#class-key").innerHTML = Object.entries(pair.clases).map(([k, c]) =>
    `<span><i class="key-swatch" style="background:${c.color}"></i>${CLASS_LABELS[k]?.en ?? c.nombre}</span>`).join("");
}

function renderZones() {
  const list = $("#zone-list");
  const { zones, pair } = state;
  $("#zone-count").textContent = `${zones.length}${pair.estadisticas.zonas_total > zones.length ? "+" : ""} ZONES`;
  list.replaceChildren();
  zoneLayer.clearLayers();
  zones.slice(0, 60).forEach((z, i) => {
    const color = pair.clases[z.clase].color;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `site-item ${state.selected === z.id ? "is-selected" : ""}`;
    btn.dataset.id = z.id;
    btn.innerHTML = `
      <span class="site-index">${String(i + 1).padStart(2, "0")}</span>
      <span class="site-main"><strong><i class="zone-dot" style="background:${color}"></i> ${CLASS_LABELS[z.clase]?.en ?? z.nombre}</strong>
        <small>${z.lat.toFixed(3)}°, ${z.lng.toFixed(3)}°${z.recorte ? " · 20 m crop" : ""}</small></span>
      <span class="site-change"><b style="color:${color}">${fmt2.format(z.area_km2)} km²</b><small>${z.cambio_dB > 0 ? "+" : ""}${fmt.format(z.cambio_dB)} dB</small></span>`;
    btn.addEventListener("click", () => selectZone(z.id));
    list.append(btn);
  });
  zones.slice(0, 60).forEach(z => {
    const color = pair.clases[z.clase].color;
    L.circleMarker([z.lat, z.lng], {
      radius: Math.max(4, Math.min(12, 3 + Math.sqrt(z.area_km2) * 2.2)), color: "#101b25", weight: 1.5,
      fillColor: color, fillOpacity: .95
    }).bindTooltip(`${CLASS_LABELS[z.clase]?.en ?? z.nombre} · ${fmt2.format(z.area_km2)} km²`, { direction: "top" })
      .on("click", () => selectZone(z.id)).addTo(zoneLayer);
  });
}

function selectZone(id) {
  const z = state.zones.find(item => item.id === id);
  if (!z) return;
  state.selected = id;
  document.querySelectorAll("#zone-list .site-item").forEach(b => {
    const on = b.dataset.id === id;
    b.classList.toggle("is-selected", on);
    b.setAttribute("aria-pressed", String(on));
    if (on) b.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
  if (highlight) highlight.remove();
  highlight = L.rectangle(z.bounds, { color: "#edf4f7", weight: 1.5, fill: false, dashArray: "4 4" }).addTo(map);
  map.flyToBounds(z.recorte ? z.recorte.bounds : z.bounds, { padding: [30, 30], duration: .6, maxZoom: 14 });
  renderDetail(z);
}

function renderDetail(z) {
  const box = $("#zone-detail");
  if (!z) {
    $("#zone-title").textContent = "Select a zone";
    box.innerHTML = `<p class="section-copy">Pick a zone in the list or on the map to see full-resolution (20 m) before / after crops.</p>`;
    return;
  }
  const c = state.pair.clases[z.clase];
  $("#zone-title").textContent = `${CLASS_LABELS[z.clase]?.en ?? z.nombre} · ${z.id.toUpperCase()}`;
  const dir = state.pair.dir + "zonas/";
  const crops = z.recorte ? `
    <div class="crops">
      <figure><div class="crop"><img src="${dir}${z.id}_antes.webp" alt="Before, 20 m"></div><figcaption>BEFORE · ${state.pair.antes.fecha}</figcaption></figure>
      <figure><div class="crop"><img src="${dir}${z.id}_despues.webp" alt="After, 20 m"></div><figcaption>AFTER · ${state.pair.despues.fecha}</figcaption></figure>
      <figure><div class="crop"><img src="${dir}${z.id}_despues.webp" alt=""><img src="${dir}${z.id}_cambio.png" alt="Detected change"></div><figcaption>DETECTED CHANGE · ${z.recorte.lado_km} km</figcaption></figure>
    </div>` : `<p class="section-copy">No 20 m crop for this zone (only the largest zones get one).</p>`;
  box.innerHTML = `
    <div class="insight-status"><span class="level-indicator" style="background:${c.color}"></span><span>${(CLASS_LABELS[z.clase]?.en ?? z.nombre).toUpperCase()}</span></div>
    ${crops}
    <div class="zone-facts">
      <div><span>AREA</span><strong>${fmt2.format(z.area_km2)} km²</strong></div>
      <div><span>MEAN CHANGE</span><strong style="color:${c.color}">${z.cambio_dB > 0 ? "+" : ""}${fmt.format(z.cambio_dB)} dB</strong></div>
      <div><span>LOCATION</span><strong>${z.lat.toFixed(3)}, ${z.lng.toFixed(3)}</strong></div>
    </div>
    <p class="zone-reading">${CLASS_LABELS[z.clase]?.read ?? c.lectura}</p>`;
}

function renderCharts(pair) {
  Object.values(state.charts).forEach(c => c.destroy());
  const keys = Object.keys(pair.clases);
  const grid = { color: "#263742" }, ticks = { color: "#8fa2ae" };
  const tooltip = { backgroundColor: "#172530", titleColor: "#edf4f7", bodyColor: "#c1d0d8", padding: 10 };
  state.charts.cls = new Chart($("#class-chart"), {
    type: "bar",
    data: {
      labels: keys.map(k => CLASS_LABELS[k]?.en ?? pair.clases[k].nombre),
      datasets: [{ data: keys.map(k => pair.estadisticas.zonas_km2_por_clase[k]), backgroundColor: keys.map(k => pair.clases[k].color), borderRadius: 6 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, indexAxis: "y",
      plugins: { legend: { display: false }, tooltip: { ...tooltip, callbacks: { label: c => `${fmt2.format(c.raw)} km²` } } },
      scales: { x: { grid, ticks, border: { display: false }, title: { display: true, text: "km²", color: "#8fa2ae" } },
                y: { grid: { display: false }, ticks, border: { display: false } } }
    }
  });
  const h = pair.estadisticas.histograma_cambio;
  const [lo, , step] = h.bordes_dB;
  const centers = h.conteos.map((_, i) => lo + step * (i + 0.5));
  const thr = pair.parametros.umbral_dB;
  const total = h.conteos.reduce((t, v) => t + v, 0);
  state.charts.hist = new Chart($("#hist-chart"), {
    type: "bar",
    data: {
      labels: centers.map(v => v.toFixed(1)),
      datasets: [{ data: h.conteos.map(v => 100 * v / total),
        backgroundColor: centers.map(v => v <= -thr ? "#e47759" : v >= thr ? "#68b6a3" : "#72b8d055"), barPercentage: 1, categoryPercentage: 1 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { ...tooltip, callbacks: { title: c => `${c[0].label} dB`, label: c => `${c.raw.toFixed(3)}% of pixels` } } },
      scales: { x: { grid: { display: false }, ticks: { ...ticks, maxTicksLimit: 7 }, border: { display: false }, title: { display: true, text: "change after global shift (dB)", color: "#8fa2ae" } },
                y: { type: "logarithmic", grid, ticks: { ...ticks, maxTicksLimit: 4, callback: v => `${v}%` }, border: { display: false } } }
    }
  });
}

async function init() {
  initMap();
  document.querySelectorAll(".seg button").forEach(b => b.addEventListener("click", () => { state.base = b.dataset.base; refreshLayers(); }));
  ["#toggle-change", "#toggle-diff", "#opacity"].forEach(s => $(s).addEventListener("input", refreshLayers));
  try {
    const res = await fetch(DATA + "pares.json");
    if (!res.ok) throw new Error("pares.json not found");
    const { pares } = await res.json();
    const select = $("#pair-select");
    select.innerHTML = pares.map(p => `<option value="${p.id}">${p.titulo} · ${p.antes} → ${p.despues}${p.simulado ? " (simulated)" : ""}</option>`).join("");
    select.addEventListener("change", () => loadPair(pares.find(p => p.id === select.value)));
    const fromHash = pares.find(p => `#${p.id}` === location.hash);
    const first = fromHash ?? pares[0];
    select.value = first.id;
    await loadPair(first);
  } catch (error) {
    console.error(error);
    $("#pair-note").hidden = false;
    $("#pair-note").innerHTML = "<strong>NO DATA</strong> Run processing/nisar_cambio.py to generate public/data/nisar/pares.json.";
  }
}

window.addEventListener("load", init);
