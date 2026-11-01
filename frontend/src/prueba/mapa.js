// Mapa interactivo de la página de pruebas (Leaflet): capas, comparador, lectura al pasar el ratón y zonas.
import { copiar, esc, mostrarTip, num, ocultarTip } from "./util.js";

export const CLAVES_CLASE = [null, "agua_nueva", "agua_desaparece", "descenso", "aumento"];

const BASES = {
  oscuro: ["https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    { attribution: "&copy; OpenStreetMap &copy; CARTO", subdomains: "abcd", maxZoom: 19 }],
  satelite: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Imagen &copy; Esri, Maxar, Earthstar Geographics", maxZoom: 19 }],
  calles: ["https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap", maxZoom: 19 }],
};

export class Mapa {
  constructor(el, { alSeleccionar, alLeer } = {}) {
    this.el = el;
    this.alSeleccionar = alSeleccionar;
    this.alLeer = alLeer;
    this.map = L.map(el, { zoomControl: true, minZoom: 3, worldCopyJump: true });
    this.map.attributionControl.setPrefix(false);
    const panes = { radarA: 250, radarB: 260, difer: 300, dens: 310, clases: 320 };
    for (const [n, z] of Object.entries(panes)) this.map.createPane(n).style.zIndex = z;
    this.capasBase = Object.fromEntries(Object.entries(BASES).map(([k, [u, o]]) => [k, L.tileLayer(u, o)]));
    this.capasBase.oscuro.addTo(this.map);
    this.base = "oscuro";
    this.fondo = "antes";
    this.visibles = { clases: true, diferencia: false, densidad: false, zonas: true };
    this.opacidad = 0.85;
    this.swipe = 0.5;
    this.filtro = () => true;
    this.capas = {};
    this.poligonos = new Map();
    this.zonasGrupo = L.featureGroup().addTo(this.map);
    this.recorte = [];
    this._crearSwipe();
    this.map.on("move zoom resize", () => this._clip());
    this.map.on("mousemove", (e) => this._mover(e));
    this.map.on("mouseout", () => { ocultarTip(); this.alLeer?.(null); });
    this.map.on("click", (e) => this._clic(e));
  }

  // ------------------------------------------------------------ carga
  cargar(r, base, valores) {
    this.r = r;
    this.carpeta = base;
    this.val = valores;
    for (const c of Object.values(this.capas)) c.remove();
    this.capas = {};
    this.zonasGrupo.clearLayers();
    this.poligonos.clear();
    this._quitarRecorte();
    const b = r.bounds, im = r.imagenes;
    const img = (f, pane, op = 1) => L.imageOverlay(base + f, b, { pane, opacity: op, interactive: false });
    this.capas.antesA = img(im.antes, "radarA");
    this.capas.despuesA = img(im.despues, "radarA");
    this.capas.despuesB = img(im.despues, "radarB");
    this.capas.diferencia = img(im.diferencia, "difer", this.opacidad);
    if (im.densidad) this.capas.densidad = img(im.densidad, "dens", this.opacidad);
    this.capas.clases = img(im.cambio, "clases", this.opacidad);
    for (const z of r.zonas) {
      const col = r.clases[z.clase]?.color || "#fff";
      // contorno real (exterior + huecos; Leaflet rellena con evenodd) o, si no hay, el rectángulo
      const forma = z.contorno?.length ? L.polygon(z.contorno.flat())
        : z.poligono?.length > 2 ? L.polygon(z.poligono) : L.rectangle(z.bounds);
      forma.setStyle({ color: col, weight: 1.6, fillColor: col, fillOpacity: 0.08, opacity: 0.9 });
      forma.bindTooltip(() => this.tipZona(z), { sticky: true, className: "pr-ltip", direction: "top", offset: [0, -8] });
      forma.on("click", (e) => { L.DomEvent.stopPropagation(e); this.alSeleccionar?.(z); });
      forma.on("mouseover", () => { ocultarTip(); });
      this.poligonos.set(z.id, forma);
    }
    this.actualizar();
    this.map.fitBounds(b, { padding: [16, 16] });
    setTimeout(() => this.map.invalidateSize(), 50);
  }

  tipZona(z) {
    const r = this.r, c = r.clases[z.clase] || {};
    return `<div class="pr-tz"><b><span class="pr-sw" style="background:${c.color}"></span>${esc(z.id)} · ${esc(c.nombre || z.nombre)}</b>`
      + `<div>${num(z.area_km2, 2)} km² · Δ ${num(z.cambio_dB, 1, true)} dB</div>`
      + (z.dB_antes != null ? `<div>${num(z.dB_antes, 1)} → ${num(z.dB_despues, 1)} dB</div>` : "")
      + (z.confianza ? `<div>Confianza ${esc(z.confianza)}</div>` : "")
      + `<small>Clic para ver la ficha</small></div>`;
  }

  // ------------------------------------------------------------ estado de capas
  ponerBase(k) {
    this.capasBase[this.base]?.remove();
    this.base = k;
    if (this.capasBase[k]) this.capasBase[k].addTo(this.map).bringToBack();
  }

  ponerFondo(f) { this.fondo = f; this.actualizar(); }
  ponerVisible(k, v) { this.visibles[k] = v; this.actualizar(); }
  ponerOpacidad(v) {
    this.opacidad = v;
    for (const k of ["clases", "diferencia", "densidad"]) this.capas[k]?.setOpacity(v);
    this.recorte.forEach((c) => c.options.pane === "clases" && c.setOpacity(v));
  }
  ponerFiltro(fn) { this.filtro = fn; this.actualizar(); }

  actualizar() {
    const on = (c, v) => c && (v ? c.addTo(this.map) : c.remove());
    const f = this.fondo;
    on(this.capas.antesA, f === "antes" || f === "comparar");
    on(this.capas.despuesA, f === "despues");
    on(this.capas.despuesB, f === "comparar");
    on(this.capas.clases, this.visibles.clases);
    on(this.capas.diferencia, this.visibles.diferencia);
    on(this.capas.densidad, this.visibles.densidad);
    this.zonasGrupo.clearLayers();
    if (this.visibles.zonas && this.r) {
      for (const z of this.r.zonas) if (this.filtro(z)) this.zonasGrupo.addLayer(this.poligonos.get(z.id));
    }
    this.swipeEl.hidden = f !== "comparar";
    this._clip();
    this._recorteVisible();
  }

  // ------------------------------------------------------------ comparador antes / después
  _crearSwipe() {
    const d = L.DomUtil.create("div", "pr-swipe", this.el);
    d.innerHTML = `<div class="pr-swipe-linea"></div><button type="button" class="pr-swipe-asa" aria-label="Mover el comparador">⇆</button>`
      + `<span class="pr-swipe-et pr-swipe-a">ANTES</span><span class="pr-swipe-et pr-swipe-b">DESPUÉS</span>`;
    d.hidden = true;
    this.swipeEl = d;
    L.DomEvent.disableClickPropagation(d);
    L.DomEvent.disableScrollPropagation(d);
    const asa = d.querySelector(".pr-swipe-asa");
    const mover = (e) => {
      const r = this.el.getBoundingClientRect();
      this.swipe = Math.min(0.98, Math.max(0.02, (e.clientX - r.left) / r.width));
      this._clip();
    };
    asa.addEventListener("pointerdown", (e) => {
      asa.setPointerCapture(e.pointerId);
      this.map.dragging.disable();
      const up = () => { this.map.dragging.enable(); asa.removeEventListener("pointermove", mover); };
      asa.addEventListener("pointermove", mover);
      asa.addEventListener("pointerup", up, { once: true });
    });
    asa.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        this.swipe = Math.min(0.98, Math.max(0.02, this.swipe + (e.key === "ArrowLeft" ? -0.03 : 0.03)));
        this._clip();
      }
    });
  }

  _clip() {
    const pane = this.map.getPane("radarB");
    if (this.fondo !== "comparar") { pane.style.clip = ""; return; }
    const tam = this.map.getSize();
    const nw = this.map.containerPointToLayerPoint([0, 0]);
    const se = this.map.containerPointToLayerPoint(tam);
    const x = this.map.containerPointToLayerPoint([tam.x * this.swipe, 0]).x;
    pane.style.clip = `rect(${nw.y}px, ${se.x}px, ${se.y}px, ${x}px)`;
    this.swipeEl.style.left = `${this.swipe * 100}%`;
  }

  // ------------------------------------------------------------ lectura de valores
  valorEn(latlng) {
    const v = this.val, r = this.r;
    if (!v || !r) return null;
    const [[s, w], [n, e]] = r.bounds;
    const fy = (n - latlng.lat) / (n - s), fx = (latlng.lng - w) / (e - w);
    if (fy < 0 || fy >= 1 || fx < 0 || fx >= 1) return null;
    const m = r.valores;
    const fila = Math.floor((fy * m.filas_ventana) / m.factor), col = Math.floor((fx * m.columnas_ventana) / m.factor);
    if (fila >= m.filas || col >= m.columnas) return null;
    const N = m.filas * m.columnas, i = fila * m.columnas + col;
    const q = (k) => { const x = v[k * N + i]; return x === 0 ? null : (x - 1) * 0.2 - 40; };
    const d8 = v[2 * N + i], d = d8 === 128 ? null : (d8 > 127 ? d8 - 256 : d8) / 10;
    const fr = v[3 * N + i];
    const antes = q(0), despues = q(1);
    if (antes === null && despues === null) return null;
    return { antes, despues, cambio: d, frac: fr === 255 ? null : fr / 250, clase: CLAVES_CLASE[v[4 * N + i]] || null, celda_m: m.resolucion_m };
  }

  htmlValor(ll, x) {
    const r = this.r, c = x.clase ? r.clases[x.clase] : null;
    const cob = (db) => {
      if (db === null || !r.coberturas) return "";
      const cortes = r.parametros.cortes_cobertura_dB || [r.parametros.agua_dB, -9, -3];
      const k = r.estadisticas.coberturas?.orden?.[cortes.filter((t) => db >= t).length];
      return k ? ` <span class="pr-mut">(${esc(r.coberturas[k].nombre.toLowerCase())})</span>` : "";
    };
    return `<div class="pr-lect"><b>${ll.lat.toFixed(4)}, ${ll.lng.toFixed(4)}</b>`
      + `<div>Antes: ${num(x.antes, 1)} dB${cob(x.antes)}</div>`
      + `<div>Después: ${num(x.despues, 1)} dB${cob(x.despues)}</div>`
      + `<div>Cambio corregido: <b>${num(x.cambio, 1, true)} dB</b></div>`
      + (x.frac !== null ? `<div>Píxeles con cambio en la celda: ${num(100 * x.frac, 1)} %</div>` : "")
      + (c ? `<div><span class="pr-sw" style="background:${c.color}"></span>${esc(c.nombre)}</div>` : "")
      + `<small>Celda de ${num(x.celda_m, 0)} m</small></div>`;
  }

  _mover(e) {
    if (this._raf) return;
    this._raf = requestAnimationFrame(() => {
      this._raf = null;
      const x = this.valorEn(e.latlng);
      this.alLeer?.(x ? { ...x, lat: e.latlng.lat, lng: e.latlng.lng } : null);
      const sobreZona = e.originalEvent.target?.classList?.contains("leaflet-interactive");
      if (x && !sobreZona && !this.el.classList.contains("pr-sin-tip")) mostrarTip(this.htmlValor(e.latlng, x), e.originalEvent.clientX, e.originalEvent.clientY);
      else if (!sobreZona) ocultarTip();
    });
  }

  _clic(e) {
    const x = this.valorEn(e.latlng);
    if (!x) return;
    const ll = e.latlng;
    L.popup({ className: "pr-popup", maxWidth: 280 }).setLatLng(ll).setContent(this.htmlValor(ll, x)
      + `<div class="pr-pop-links"><a target="_blank" rel="noopener" href="https://www.google.com/maps/@${ll.lat.toFixed(5)},${ll.lng.toFixed(5)},3000m/data=!3m1!1e3">Ver satélite (Google)</a>`
      + `<button type="button" class="pr-copiar" data-copiar="${ll.lat.toFixed(5)}, ${ll.lng.toFixed(5)}">Copiar coordenadas</button></div>`).openOn(this.map);
    // Leaflet corta la propagación de los clics del popup: el botón necesita su propio manejador
    const b = this.map.getContainer().querySelector(".pr-popup .pr-copiar");
    b?.addEventListener("click", () => copiar(b));
  }

  // ------------------------------------------------------------ zonas
  seleccionar(z) {
    for (const [id, p] of this.poligonos) {
      const col = this.r.clases[this.r.zonas.find((q) => q.id === id)?.clase]?.color;
      p.setStyle(id === z?.id ? { weight: 3.5, fillOpacity: 0.18, color: "#ffffff" } : { weight: 1.6, fillOpacity: 0.08, color: col });
    }
    this._quitarRecorte();
    if (!z) return;
    const p = this.poligonos.get(z.id);
    if (p && !this.zonasGrupo.hasLayer(p) && this.visibles.zonas) this.zonasGrupo.addLayer(p);
    p?.bringToFront();
    if (z.recorte) {
      const b = z.recorte.bounds, base = `${this.carpeta}zonas/${z.id}`;
      this.recorte = [
        L.imageOverlay(`${base}_antes.webp`, b, { pane: "radarA", interactive: false, className: "pr-rec-antes" }),
        L.imageOverlay(`${base}_despues.webp`, b, { pane: "radarA", interactive: false, className: "pr-rec-despA" }),
        L.imageOverlay(`${base}_despues.webp`, b, { pane: "radarB", interactive: false, className: "pr-rec-despB" }),
        L.imageOverlay(`${base}_cambio.png`, b, { pane: "clases", interactive: false, opacity: this.opacidad, className: "pr-rec-cambio" }),
      ];
      this._recorteVisible();
    }
    this.map.flyToBounds(z.recorte ? z.recorte.bounds : z.bounds, { padding: [30, 30], duration: 0.7, maxZoom: 14 });
  }

  _recorteVisible() {
    if (!this.recorte.length) return;
    const [a, dA, dB, c] = this.recorte, f = this.fondo;
    const on = (l, v) => (v ? l.addTo(this.map) : l.remove());
    on(a, f === "antes" || f === "comparar");
    on(dA, f === "despues");
    on(dB, f === "comparar");
    on(c, this.visibles.clases);
  }

  _quitarRecorte() {
    this.recorte.forEach((l) => l.remove());
    this.recorte = [];
  }

  verTodo() { if (this.r) this.map.flyToBounds(this.r.bounds, { padding: [16, 16], duration: 0.6 }); }
}
