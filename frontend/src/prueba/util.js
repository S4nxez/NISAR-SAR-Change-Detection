// Utilidades comunes de la página de pruebas: formato, nombres NISAR y tooltips.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const nf = {};
/** Número con formato español. d = decimales; signo = mostrar + en positivos. */
export function num(v, d = 1, signo = false) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const k = d + (signo ? "s" : "");
  nf[k] ??= new Intl.NumberFormat("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d, signDisplay: signo ? "exceptZero" : "auto" });
  return nf[k].format(v);
}

export function bytes(n) {
  if (!n && n !== 0) return "—";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${num(n, i >= 2 ? 1 : 0)} ${u[i]}`;
}

export function duracion(seg) {
  if (!Number.isFinite(seg) || seg < 0) return "—";
  if (seg < 60) return `${Math.round(seg)} s`;
  const m = Math.floor(seg / 60), s = Math.round(seg % 60);
  return m < 60 ? `${m} min ${s.toString().padStart(2, "0")} s` : `${Math.floor(m / 60)} h ${m % 60} min`;
}

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export function fechaLarga(iso) {
  if (!iso) return "—";
  const d = new Date(iso + "T12:00:00Z");
  return Number.isNaN(d) ? iso : d.toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

/**
 * Lee lo que dice el nombre de un fichero NISAR GCOV, p. ej.
 * NISAR_L2_PR_GCOV_032_083_D_091_2005_SHSH_A_20261005T232338_..._001.h5
 */
const PATRON = /NISAR_L2_\w{2}_GCOV_(\d{3})_(\d{3})_([AD])_(\d{3})_(\w{4})_([A-Z]{4})_\w_(\d{8})T(\d{6})/;
export function leerNombre(nombre) {
  const m = PATRON.exec(nombre || "");
  if (!m) return null;
  const f = m[7];
  return {
    ciclo: +m[1], pista: +m[2], direccion: m[3] === "A" ? "Ascending" : "Descending", frame: +m[4],
    modo: m[5], polarizacion: m[6], fecha: `${f.slice(0, 4)}-${f.slice(4, 6)}-${f.slice(6, 8)}`,
    hora: `${m[8].slice(0, 2)}:${m[8].slice(2, 4)} UTC`, fuente: "nombre",
  };
}

export const POLS = {
  SHSH: "HH (polarización simple)", DHDH: "HH + HV (doble polarización)", SHNA: "HH",
  QPQP: "cuádruple (HH, HV, VH, VV)", SVSV: "VV", DVDV: "VV + VH",
};

export function dias(a, b) {
  if (!a || !b) return null;
  return Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
}

/** Comprueba que dos pasadas se pueden comparar. Devuelve [{ok, texto, grave}]. */
export function comprobarPar(ma, mb) {
  const out = [];
  if (!ma || !mb) return out;
  for (const [k, nombre] of [["pista", "Misma pista"], ["frame", "Mismo frame"], ["direccion", "Misma dirección de órbita"]]) {
    if (ma[k] == null || mb[k] == null) out.push({ ok: null, texto: `${nombre}: no se puede saber por el nombre` });
    else if (String(ma[k]) === String(mb[k])) out.push({ ok: true, texto: `${nombre} (${ma[k]})` });
    else out.push({ ok: false, grave: true, texto: `${nombre}: ${ma[k]} frente a ${mb[k]}. Deben coincidir para comparar píxel a píxel.` });
  }
  if (ma.fecha && mb.fecha) {
    const d = dias(ma.fecha, mb.fecha);
    if (d > 0) out.push({ ok: true, texto: `Fechas en orden: ${d} días entre pasadas` });
    else if (d === 0) out.push({ ok: false, grave: true, texto: "Las dos pasadas son del mismo día" });
    else out.push({ ok: false, grave: true, texto: `«Antes» es posterior a «después» (${-d} días). Usa ⇄ para intercambiarlas.` });
  }
  return out;
}

// ---------------------------------------------------------------- tooltips
let tip;
function asegurarTip() {
  if (tip) return tip;
  tip = document.createElement("div");
  tip.className = "pr-tip";
  tip.setAttribute("role", "tooltip");
  tip.hidden = true;
  document.body.appendChild(tip);
  return tip;
}

/** Muestra un tooltip con HTML junto al punto (x, y) de la ventana. */
export function mostrarTip(html, x, y) {
  const t = asegurarTip();
  t.innerHTML = html;
  t.hidden = false;
  const r = t.getBoundingClientRect();
  let left = x + 14, top = y + 14;
  if (left + r.width > innerWidth - 8) left = x - r.width - 14;
  if (top + r.height > innerHeight - 8) top = y - r.height - 14;
  t.style.left = `${Math.max(8, left)}px`;
  t.style.top = `${Math.max(8, top)}px`;
}

export function ocultarTip() {
  if (tip) tip.hidden = true;
}

/** Activa los tooltips de todos los elementos con data-tip (texto) dentro de root. */
export function activarTips(root = document) {
  root.addEventListener("pointerover", (e) => {
    const el = e.target.closest?.("[data-tip]");
    if (!el) return;
    const r = el.getBoundingClientRect();
    mostrarTip(esc(el.dataset.tip).replace(/\n/g, "<br>"), r.left + r.width / 2 - 10, r.bottom - 6);
  });
  root.addEventListener("pointerout", (e) => {
    if (e.target.closest?.("[data-tip]")) ocultarTip();
  });
  root.addEventListener("focusin", (e) => {
    const el = e.target.closest?.("[data-tip]");
    if (!el) return;
    const r = el.getBoundingClientRect();
    mostrarTip(esc(el.dataset.tip).replace(/\n/g, "<br>"), r.left, r.bottom);
  });
  root.addEventListener("focusout", ocultarTip);
  root.addEventListener("click", (e) => { if (e.target.closest?.("[data-tip]")) ocultarTip(); });
  window.addEventListener("scroll", ocultarTip, { passive: true });
}

/** Icono ⓘ con explicación. */
export const info = (texto) => `<span class="pr-info" tabindex="0" data-tip="${esc(texto)}">i</span>`;

/** Copia texto al portapapeles y lo indica en el botón. */
export async function copiar(boton) {
  try {
    await navigator.clipboard.writeText(boton.dataset.copiar);
    boton.textContent = "✓ Copiado";
  } catch {
    boton.textContent = boton.dataset.copiar;
  }
}
