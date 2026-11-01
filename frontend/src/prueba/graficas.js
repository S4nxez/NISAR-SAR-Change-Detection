// Gráficas SVG pequeñas, sin dependencias, con tooltips al pasar el ratón.
import { esc, mostrarTip, num, ocultarTip } from "./util.js";

/** Ancho del SVG = ancho real del contenedor, para que el texto no se escale. */
const ancho = (el) => Math.max(320, Math.min(1400, Math.round(el.clientWidth || 600)));
const EJE = "#93a7b3";
const REJ = "#2a3c48";

function montar(el, svg, alMover, alClic, ANCHO) {
  el.innerHTML = svg;
  const s = el.querySelector("svg");
  s.addEventListener("pointermove", (e) => {
    const r = s.getBoundingClientRect();
    const x = (e.clientX - r.left) * (ANCHO / r.width);
    const y = (e.clientY - r.top) * (s.viewBox.baseVal.height / r.height);
    const html = alMover(x, y, e.target);
    if (html) mostrarTip(html, e.clientX, e.clientY); else ocultarTip();
  });
  s.addEventListener("pointerleave", () => { ocultarTip(); s.querySelector(".g-cursor")?.setAttribute("opacity", 0); });
  if (alClic) s.addEventListener("click", (e) => alClic(e.target));
}

function ticks(min, max, n = 5) {
  const paso0 = (max - min) / n;
  const mag = 10 ** Math.floor(Math.log10(paso0 || 1));
  const paso = [1, 2, 2.5, 5, 10].map((k) => k * mag).find((k) => k >= paso0) || mag * 10;
  const out = [];
  for (let v = Math.ceil(min / paso) * paso; v <= max + 1e-9; v += paso) out.push(+v.toFixed(10));
  return out;
}

/** Barras horizontales: [{etq, valor, color, tip}] */
export function barrasH(el, items, { unidad = "", dec = 1 } = {}) {
  const ANCHO = ancho(el);
  const fila = 34, ml = 170, mr = 70, alto = items.length * fila + 10;
  const vmax = Math.max(...items.map((i) => i.valor), 1e-9);
  const w = ANCHO - ml - mr;
  let s = `<svg viewBox="0 0 ${ANCHO} ${alto}" class="g-svg" role="img">`;
  items.forEach((it, i) => {
    const y = 6 + i * fila, bw = Math.max(1, (it.valor / vmax) * w);
    s += `<g data-i="${i}" class="g-fila"><rect x="0" y="${y - 3}" width="${ANCHO}" height="${fila}" fill="transparent"/>`
      + `<text x="${ml - 10}" y="${y + 16}" text-anchor="end" fill="#edf4f7" font-size="13">${esc(it.etq)}</text>`
      + `<rect x="${ml}" y="${y + 3}" width="${bw}" height="20" rx="4" fill="${it.color}"/>`
      + `<text x="${ml + bw + 8}" y="${y + 18}" fill="${EJE}" font-size="12">${num(it.valor, dec)} ${esc(unidad)}</text></g>`;
  });
  s += "</svg>";
  montar(el, s, (x, y, t) => {
    const g = t.closest?.(".g-fila");
    return g ? items[+g.dataset.i].tip : null;
  }, null, ANCHO);
}

/**
 * Histograma o líneas sobre bins regulares.
 * series: [{nombre, color, conteos, tipo: 'barra'|'linea', colorBin?(x)}]
 */
export function histograma(el, { bordes, series, lineas = [], ejeX = "", alto = 260, porcentaje = true, formatoTip }) {
  const ANCHO = ancho(el);
  const [ini, fin, paso] = bordes;
  const n = series[0].conteos.length;
  const ml = 48, mr = 14, mt = 14, mb = 40;
  const w = ANCHO - ml - mr, h = alto - mt - mb;
  const norm = series.map((s) => {
    const t = porcentaje ? s.conteos.reduce((a, b) => a + b, 0) || 1 : 1;
    return s.conteos.map((c) => (porcentaje ? (100 * c) / t : c));
  });
  const vmax = Math.max(...norm.flat(), 1e-9);
  const X = (v) => ml + ((v - ini) / (fin - ini)) * w;
  const Y = (v) => mt + h - (v / vmax) * h;
  let s = `<svg viewBox="0 0 ${ANCHO} ${alto}" class="g-svg" role="img">`;
  for (const t of ticks(0, vmax, 4)) {
    s += `<line x1="${ml}" x2="${ml + w}" y1="${Y(t)}" y2="${Y(t)}" stroke="${REJ}"/>`
      + `<text x="${ml - 6}" y="${Y(t) + 4}" text-anchor="end" fill="${EJE}" font-size="11">${num(t, t < 1 ? 1 : 0)}${porcentaje ? "%" : ""}</text>`;
  }
  for (const t of ticks(ini, fin, 8)) {
    s += `<text x="${X(t)}" y="${mt + h + 16}" text-anchor="middle" fill="${EJE}" font-size="11">${num(t, 0)}</text>`;
  }
  s += `<text x="${ml + w / 2}" y="${alto - 4}" text-anchor="middle" fill="${EJE}" font-size="12">${esc(ejeX)}</text>`;
  series.forEach((se, k) => {
    if (se.tipo === "linea") {
      const pts = norm[k].map((v, i) => `${X(ini + (i + 0.5) * paso).toFixed(1)},${Y(v).toFixed(1)}`).join(" ");
      s += `<polyline points="${pts}" fill="none" stroke="${se.color}" stroke-width="2.2" stroke-linejoin="round"/>`;
    } else {
      norm[k].forEach((v, i) => {
        const x0 = ini + i * paso;
        const col = se.colorBin ? se.colorBin(x0 + paso / 2) : se.color;
        s += `<rect x="${X(x0) + 0.6}" y="${Y(v)}" width="${Math.max(0.6, w / n - 1.2)}" height="${mt + h - Y(v)}" fill="${col}"/>`;
      });
    }
  });
  for (const l of lineas) {
    s += `<line x1="${X(l.x)}" x2="${X(l.x)}" y1="${mt}" y2="${mt + h}" stroke="${l.color}" stroke-dasharray="5 4" stroke-width="1.5"/>`
      + `<text x="${X(l.x) + 4}" y="${mt + 12}" fill="${l.color}" font-size="11">${esc(l.etq)}</text>`;
  }
  s += `<rect class="g-cursor" x="0" y="${mt}" width="${w / n}" height="${h}" fill="#ffffff" opacity="0" pointer-events="none"/>`;
  if (series.length > 1) {
    series.forEach((se, k) => {
      s += `<rect x="${ml + w - 120}" y="${mt + 6 + k * 17}" width="11" height="11" rx="2" fill="${se.color}"/>`
        + `<text x="${ml + w - 104}" y="${mt + 16 + k * 17}" fill="#edf4f7" font-size="12">${esc(se.nombre)}</text>`;
    });
  }
  s += "</svg>";
  montar(el, s, (x) => {
    const i = Math.floor(((x - ml) / w) * n);
    const cur = el.querySelector(".g-cursor");
    if (i < 0 || i >= n) { cur.setAttribute("opacity", 0); return null; }
    cur.setAttribute("x", X(ini + i * paso));
    cur.setAttribute("opacity", 0.08);
    const a = ini + i * paso, b = a + paso;
    if (formatoTip) return formatoTip(a, b, series.map((se, k) => ({ ...se, valor: norm[k][i], conteo: se.conteos[i] })));
    return `<b>${num(a, 1)} a ${num(b, 1)} dB</b>` + series.map((se, k) =>
      `<div><span class="pr-sw" style="background:${se.color}"></span>${esc(se.nombre)}: ${num(norm[k][i], 2)}${porcentaje ? " %" : ""}</div>`).join("");
  }, null, ANCHO);
}

/** Dispersión: [{x, y, color, r, id, tip}] */
export function dispersion(el, { puntos, logX = false, ejeX = "", ejeY = "", alto = 300, lineasY = [], alClic }) {
  const ANCHO = ancho(el);
  const ml = 52, mr = 16, mt = 14, mb = 42;
  const w = ANCHO - ml - mr, h = alto - mt - mb;
  if (!puntos.length) { el.innerHTML = `<p class="pr-vacio">Sin zonas que mostrar.</p>`; return; }
  const fx = logX ? (v) => Math.log10(Math.max(v, 1e-6)) : (v) => v;
  const xs = puntos.map((p) => fx(p.x)), ys = puntos.map((p) => p.y);
  let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys, ...lineasY.map((l) => l.y)), y1 = Math.max(...ys, ...lineasY.map((l) => l.y));
  if (x1 - x0 < 1e-6) { x0 -= 0.5; x1 += 0.5; }
  const py = (y1 - y0) * 0.08 || 1;
  y0 -= py; y1 += py;
  const X = (v) => ml + ((fx(v) - x0) / (x1 - x0)) * w;
  const Y = (v) => mt + h - ((v - y0) / (y1 - y0)) * h;
  let s = `<svg viewBox="0 0 ${ANCHO} ${alto}" class="g-svg" role="img">`;
  for (const t of ticks(y0, y1, 5)) {
    s += `<line x1="${ml}" x2="${ml + w}" y1="${Y(t)}" y2="${Y(t)}" stroke="${REJ}"/>`
      + `<text x="${ml - 6}" y="${Y(t) + 4}" text-anchor="end" fill="${EJE}" font-size="11">${num(t, 0)}</text>`;
  }
  const tx = logX ? ticks(Math.floor(x0), Math.ceil(x1), 6).filter((t) => Number.isInteger(t)) : ticks(x0, x1, 6);
  for (const t of tx) {
    const v = logX ? 10 ** t : t;
    if (fx(v) < x0 || fx(v) > x1) continue;
    s += `<line x1="${X(v)}" x2="${X(v)}" y1="${mt}" y2="${mt + h}" stroke="${REJ}"/>`
      + `<text x="${X(v)}" y="${mt + h + 16}" text-anchor="middle" fill="${EJE}" font-size="11">${num(v, v < 1 ? 2 : 0)}</text>`;
  }
  for (const l of lineasY) {
    s += `<line x1="${ml}" x2="${ml + w}" y1="${Y(l.y)}" y2="${Y(l.y)}" stroke="${l.color}" stroke-dasharray="5 4"/>`;
  }
  s += `<text x="${ml + w / 2}" y="${alto - 4}" text-anchor="middle" fill="${EJE}" font-size="12">${esc(ejeX)}</text>`
    + `<text x="12" y="${mt + h / 2}" text-anchor="middle" fill="${EJE}" font-size="12" transform="rotate(-90 12 ${mt + h / 2})">${esc(ejeY)}</text>`;
  puntos.forEach((p, i) => {
    s += `<circle data-i="${i}" cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="${p.r || 4}" fill="${p.color}" fill-opacity=".75" stroke="#101b25" style="cursor:pointer"/>`;
  });
  s += "</svg>";
  montar(el, s, (x, y, t) => (t.dataset?.i ? puntos[+t.dataset.i].tip : null),
    alClic ? (t) => t.dataset?.i && alClic(puntos[+t.dataset.i]) : null, ANCHO);
}

/** Barras verticales agrupadas: categorias = etiquetas, series = [{nombre, color, valores}] */
export function barrasV(el, { categorias, series, unidad = "", alto = 260, dec = 1, tips }) {
  const ANCHO = ancho(el);
  const ml = 52, mr = 14, mt = 18, mb = 44;
  const w = ANCHO - ml - mr, h = alto - mt - mb;
  const vmax = Math.max(...series.flatMap((s) => s.valores), 1e-9);
  const Y = (v) => mt + h - (v / vmax) * h;
  const gw = w / categorias.length, bw = Math.min(46, (gw * 0.75) / series.length);
  let s = `<svg viewBox="0 0 ${ANCHO} ${alto}" class="g-svg" role="img">`;
  for (const t of ticks(0, vmax, 4)) {
    s += `<line x1="${ml}" x2="${ml + w}" y1="${Y(t)}" y2="${Y(t)}" stroke="${REJ}"/>`
      + `<text x="${ml - 6}" y="${Y(t) + 4}" text-anchor="end" fill="${EJE}" font-size="11">${num(t, t < 10 ? 1 : 0)}</text>`;
  }
  categorias.forEach((c, i) => {
    const gx = ml + i * gw + (gw - bw * series.length) / 2;
    series.forEach((se, k) => {
      const v = se.valores[i];
      s += `<rect data-i="${i}" data-k="${k}" x="${gx + k * bw}" y="${Y(v)}" width="${bw - 3}" height="${mt + h - Y(v)}" rx="3" fill="${se.color}"/>`;
    });
    s += `<text x="${ml + i * gw + gw / 2}" y="${mt + h + 16}" text-anchor="middle" fill="#edf4f7" font-size="12">${esc(c)}</text>`;
  });
  if (series.length > 1) {
    series.forEach((se, k) => {
      s += `<rect x="${ml + k * 130}" y="${alto - 14}" width="11" height="11" rx="2" fill="${se.color}"/>`
        + `<text x="${ml + 16 + k * 130}" y="${alto - 4}" fill="${EJE}" font-size="12">${esc(se.nombre)}</text>`;
    });
  }
  s += "</svg>";
  montar(el, s, (x, y, t) => {
    if (!t.dataset?.i) return null;
    const i = +t.dataset.i, k = +t.dataset.k;
    if (tips) return tips(i, k);
    return `<b>${esc(categorias[i])}</b><div>${esc(series[k].nombre)}: ${num(series[k].valores[i], dec)} ${esc(unidad)}</div>`;
  }, null, ANCHO);
}
