// Página de pruebas: subir dos pasadas NISAR, seguir el procesado y explorar el resultado.
//   prueba.html               subir y analizar
//   prueba.html#t=<trabajo>   abrir un trabajo del servidor
//   prueba.html#ej=<id>       abrir un ejemplo incluido (frontend/public/data/nisar/<id>)
import * as api from "./api.js";
import { barrasH, barrasV, dispersion, histograma } from "./graficas.js";
import { Mapa } from "./mapa.js";
import { $, $$, activarTips, bytes, comprobarPar, copiar, dias, duracion, esc, fechaLarga, info, leerNombre, num, POLS } from "./util.js";

const EJEMPLOS = "./public/data/nisar/";
const ORDEN_CONF = { alta: 3, media: 2, baja: 1 };

const est = {
  servidor: false,
  slots: { antes: nuevoSlot(), despues: nuevoSlot() },
  sondeo: null,
  r: null,
  base: "",
  mapa: null,
  zonaSel: null,
  mostrar: 40,
};

function nuevoSlot() {
  return { fichero: null, nombre: null, meta: null, subida: null, estado: "vacio", error: null, xhr: null, enviados: 0, total: 0, t0: 0 };
}

// ================================================================ servidor
async function comprobarServidor() {
  const el = $("#srv-estado"), txt = $("#srv-texto");
  try {
    const s = await api.estado();
    est.servidor = true;
    el.classList.remove("is-off");
    txt.textContent = s.ocupado ? "SERVICIO OCUPADO · PROCESANDO" : `SERVICIO LISTO${s.h5py ? "" : " · SIN h5py"}`;
    el.dataset.tip = `Servicio de procesado activo.\nEspacio libre: ${bytes(s.libre_bytes)}\nLímite por fichero: ${bytes(s.limite_bytes)}`
      + (s.h5py ? "" : "\nFalta h5py: solo podrá procesar escenas .zip, no .h5.");
    $("#sin-servidor").hidden = true;
  } catch {
    est.servidor = false;
    el.classList.add("is-off");
    txt.textContent = "SIN SERVICIO DE PROCESADO";
    $("#sin-servidor").hidden = false;
  }
  actualizarAnalizar();
}

async function cargarHistorial() {
  const ul = $("#historial");
  if (!est.servidor) { ul.innerHTML = `<li class="pr-mut">Requiere el servicio de procesado.</li>`; return; }
  try {
    const { trabajos } = await api.trabajos();
    ul.innerHTML = trabajos.length ? trabajos.slice(0, 12).map((t) => `<li><a href="#t=${esc(t.id)}">${esc(t.titulo)}</a>`
      + `<span class="pr-estado pr-estado-${esc(t.estado)}">${esc({ terminado: "listo", procesando: `${Math.round(100 * t.progreso)} %`, en_cola: "en cola", error: "error" }[t.estado] || t.estado)}</span></li>`).join("")
      : `<li class="pr-mut">Todavía no hay análisis.</li>`;
  } catch (e) { ul.innerHTML = `<li class="pr-mut">${esc(e.message)}</li>`; }
}

async function cargarEjemplos() {
  const ul = $("#ejemplos");
  try {
    const r = await fetch(EJEMPLOS + "pares.json");
    const { pares } = await r.json();
    ul.innerHTML = pares.map((p) => `<li><a href="#ej=${esc(p.id)}">${esc(p.titulo)}</a><span class="pr-mut">${esc(p.antes)} → ${esc(p.despues)}${p.simulado ? " · simulado" : ""}</span></li>`).join("");
  } catch { ul.innerHTML = `<li class="pr-mut">No hay ejemplos en public/data/nisar.</li>`; }
}

// ================================================================ carga de ficheros
function prepararDrops() {
  for (const drop of $$(".pr-drop")) {
    const slot = drop.dataset.slot, input = $("input", drop);
    drop.addEventListener("click", (e) => { if (!e.target.closest("button,a")) input.click(); });
    drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
    input.addEventListener("change", () => input.files[0] && elegir(slot, input.files[0]));
    drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("is-over"); });
    drop.addEventListener("dragleave", () => drop.classList.remove("is-over"));
    drop.addEventListener("drop", (e) => {
      e.preventDefault();
      drop.classList.remove("is-over");
      const fs = [...e.dataTransfer.files];
      if (fs.length === 2) {
        // dos ficheros a la vez: se ordenan por la fecha del nombre
        const [a, b] = fs.map((f) => ({ f, m: leerNombre(f.name) })).sort((x, y) => (x.m?.fecha || "").localeCompare(y.m?.fecha || ""));
        elegir("antes", a.f); elegir("despues", b.f);
      } else if (fs[0]) elegir(slot, fs[0]);
    });
  }
  $("#intercambiar").addEventListener("click", () => {
    const { antes, despues } = est.slots;
    if (antes.estado === "subiendo" || despues.estado === "subiendo") return;
    est.slots = { antes: despues, despues: antes };
    pintarSlot("antes"); pintarSlot("despues"); pintarComprobaciones();
  });
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => e.preventDefault());
}

function elegir(slot, fichero) {
  const s = est.slots[slot];
  s.xhr?.cancelar();
  const ext = fichero.name.toLowerCase().split(".").pop();
  Object.assign(s, nuevoSlot(), { fichero, nombre: fichero.name, meta: leerNombre(fichero.name), total: fichero.size });
  if (!["h5", "zip"].includes(ext)) {
    s.estado = "error";
    s.error = "Formato no admitido. Sube el .h5 de NISAR GCOV o una escena .zip.";
  } else if (!est.servidor) {
    s.estado = "error";
    s.error = "No hay servicio de procesado: arranca processing/servidor.py.";
  } else {
    subirSlot(slot);
  }
  pintarSlot(slot);
  pintarComprobaciones();
}

function subirSlot(slot) {
  const s = est.slots[slot];
  s.estado = "subiendo";
  s.t0 = performance.now();
  s.xhr = api.subir(s.fichero, (env, tot) => {
    s.enviados = env;
    s.total = tot;
    pintarProgresoSlot(slot);
  });
  s.xhr.promesa.then((reg) => {
    if (est.slots[slot] !== s) return;
    s.subida = reg;
    s.meta = { ...(s.meta || {}), ...(reg.meta || {}) };
    s.estado = "listo";
    s.avisos = reg.avisos || [];
  }).catch((e) => {
    if (est.slots[slot] !== s) return;
    s.estado = "error";
    s.error = e.message;
  }).finally(() => {
    if (est.slots[slot] !== s) return;
    s.xhr = null;
    pintarSlot(slot);
    pintarComprobaciones();
  });
}

function pintarSlot(slot) {
  const s = est.slots[slot], drop = $(`.pr-drop[data-slot="${slot}"]`);
  const vacio = $(".pr-drop-vacio", drop), infoEl = $(".pr-drop-info", drop);
  drop.classList.toggle("is-lleno", s.estado !== "vacio");
  drop.classList.toggle("is-error", s.estado === "error");
  drop.classList.toggle("is-listo", s.estado === "listo");
  vacio.hidden = s.estado !== "vacio";
  infoEl.hidden = s.estado === "vacio";
  if (s.estado === "vacio") return;
  const m = s.meta || {};
  const tipo = s.nombre.toLowerCase().endsWith(".zip") ? "Escena convertida (.zip)" : "NISAR L2 GCOV (.h5)";
  const filas = [
    ["Fecha", m.fecha ? `${fechaLarga(m.fecha)}${m.hora ? ` · ${m.hora}` : ""}` : "—"],
    ["Pista / frame", m.pista != null ? `${m.pista} / ${m.frame}` : "—"],
    ["Órbita", m.direccion ? { Ascending: "ascendente", Descending: "descendente" }[m.direccion] || m.direccion : "—"],
    ["Polarización", m.polarizaciones?.length ? m.polarizaciones.map((p) => p.slice(0, 2)).join(", ") : (POLS[m.polarizacion] || m.polarizacion || "—")],
  ];
  if (m.ciclo != null) filas.push(["Ciclo", m.ciclo]);
  infoEl.innerHTML = `<div class="pr-fich"><strong title="${esc(s.nombre)}">${esc(s.nombre)}</strong><span>${tipo} · ${bytes(s.total)}</span></div>`
    + `<dl class="pr-meta">${filas.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`
    + `<div class="pr-barra"><span></span></div><p class="pr-drop-estado"></p>`
    + (s.avisos?.length ? `<p class="pr-warn">${s.avisos.map(esc).join("<br>")}</p>` : "")
    + `<button type="button" class="pr-btn pr-btn-mini pr-quitar" data-tip="Quitar este fichero">✕</button>`;
  $(".pr-quitar", infoEl).addEventListener("click", (e) => {
    e.stopPropagation();
    s.xhr?.cancelar();
    est.slots[slot] = nuevoSlot();
    $("input", drop).value = "";
    pintarSlot(slot); pintarComprobaciones();
  });
  pintarProgresoSlot(slot);
}

function pintarProgresoSlot(slot) {
  const s = est.slots[slot], drop = $(`.pr-drop[data-slot="${slot}"]`);
  const barra = $(".pr-barra span", drop), txt = $(".pr-drop-estado", drop);
  if (!barra) return;
  if (s.estado === "subiendo") {
    const f = s.total ? s.enviados / s.total : 0;
    const seg = (performance.now() - s.t0) / 1000, vel = s.enviados / Math.max(seg, 0.1);
    barra.style.width = `${(100 * f).toFixed(1)}%`;
    txt.textContent = f >= 1 ? "Comprobando el fichero en el servidor…"
      : `Subiendo ${num(100 * f, 0)} % · ${bytes(vel)}/s · quedan ${duracion((s.total - s.enviados) / Math.max(vel, 1))}`;
  } else if (s.estado === "listo") {
    barra.style.width = "100%";
    txt.textContent = "✓ Subido y comprobado";
  } else if (s.estado === "error") {
    barra.style.width = "0";
    txt.textContent = `✕ ${s.error}`;
  }
}

function pintarComprobaciones() {
  const { antes, despues } = est.slots;
  const ul = $("#comprobaciones");
  const lista = comprobarPar(antes.meta, despues.meta);
  ul.innerHTML = lista.map((c) => `<li class="${c.ok === true ? "ok" : c.ok === false ? "ko" : "na"}">${c.ok === true ? "✓" : c.ok === false ? "✕" : "?"} ${esc(c.texto)}</li>`).join("");
  if (antes.meta?.polarizacion && despues.meta?.polarizacion && antes.meta.polarizacion !== despues.meta.polarizacion) {
    ul.innerHTML += `<li class="na">? Modos de polarización distintos (${esc(antes.meta.polarizacion)} / ${esc(despues.meta.polarizacion)}): se compara solo HH.</li>`;
  }
  actualizarAnalizar(lista);
}

function actualizarAnalizar(lista = comprobarPar(est.slots.antes.meta, est.slots.despues.meta)) {
  const { antes, despues } = est.slots;
  const btn = $("#analizar"), nota = $("#analizar-nota");
  const grave = lista.find((c) => c.grave);
  let msg = "";
  if (!est.servidor) msg = "Necesitas el servicio de procesado (processing/servidor.py).";
  else if (antes.estado === "vacio" || despues.estado === "vacio") msg = "Sube las dos pasadas para empezar.";
  else if (antes.estado === "subiendo" || despues.estado === "subiendo") msg = "Esperando a que terminen las subidas…";
  else if (antes.estado === "error" || despues.estado === "error") msg = "Hay un fichero con error: cámbialo.";
  else if (grave) msg = grave.texto;
  btn.disabled = Boolean(msg);
  const h5 = [antes, despues].filter((s) => s.subida?.tipo === "h5").length;
  nota.textContent = msg || (h5 ? `Listo. Convertir ${h5 === 1 ? "el .h5" : "los dos .h5"} lleva varios minutos por fichero.` : "Listo para analizar.");
}

async function analizar() {
  const btn = $("#analizar");
  btn.disabled = true;
  try {
    const t = await api.crearTrabajo({
      antes: est.slots.antes.subida.id, despues: est.slots.despues.subida.id,
      umbral: +$("#op-umbral").value, agua: +$("#op-agua").value, area_min: +$("#op-area").value,
      titulo: $("#op-titulo").value.trim(),
    });
    location.hash = `t=${t.id}`;
  } catch (e) {
    $("#analizar-nota").textContent = e.message;
    btn.disabled = false;
  }
}

// ================================================================ progreso
function seguir(id) {
  clearTimeout(est.sondeo);
  $("#progreso").hidden = false;
  $("#resultado").hidden = true;
  $("#prog-error").hidden = true;
  $("#progreso").scrollIntoView({ behavior: "smooth", block: "start" });
  const paso = async () => {
    let t;
    try { t = await api.trabajo(id); } catch (e) {
      $("#prog-titulo").textContent = "No se encuentra el trabajo";
      $("#prog-error").hidden = false;
      $("#prog-error").textContent = e.message;
      return;
    }
    pintarProgreso(t);
    if (t.estado === "terminado") {
      $("#progreso").hidden = true;
      cargarHistorial();
      abrirResultado(api.url(`trabajos/${t.id}/`), true);
    } else if (t.estado !== "error") {
      est.sondeo = setTimeout(paso, 1000);
    } else {
      cargarHistorial();
    }
  };
  paso();
}

function pintarProgreso(t) {
  $("#prog-titulo").textContent = t.estado === "error" ? "El procesado ha fallado" : t.estado === "en_cola" ? "En cola…" : `Procesando: ${t.titulo}`;
  $("#prog-barra").style.width = `${(100 * (t.progreso || 0)).toFixed(1)}%`;
  const ini = Date.parse(t.inicio || t.creado), fin = t.terminado ? Date.parse(t.terminado) : Date.now();
  $("#prog-tiempo").textContent = `${num(100 * (t.progreso || 0), 0)} % · ${duracion((fin - ini) / 1000)}`;
  const icono = { pendiente: "○", procesando: "◐", hecho: "✓", omitido: "✓", error: "✕" };
  $("#prog-pasos").innerHTML = t.pasos.map((p) => `<li class="pr-paso is-${p.estado}"><span class="pr-paso-ico">${icono[p.estado] || "○"}</span>`
    + `<div><strong>${esc(p.nombre)}</strong><span class="pr-mut">${esc(p.detalle || { pendiente: "pendiente", procesando: "en curso", hecho: "hecho", omitido: "no hace falta", error: "error" }[p.estado])}</span>`
    + `<div class="pr-barra"><span style="width:${(100 * (p.estado === "omitido" ? 1 : p.progreso)).toFixed(1)}%"></span></div></div></li>`).join("");
  const log = $("#prog-log");
  log.textContent = (t.registro || []).join("\n");
  log.scrollTop = log.scrollHeight;
  if (t.estado === "error") {
    $("#prog-error").hidden = false;
    $("#prog-error").textContent = t.mensaje;
  }
}

// ================================================================ resultado
async function abrirResultado(base, esTrabajo) {
  $("#resultado").hidden = false;
  $("#res-titulo").textContent = "Cargando resultado…";
  let r;
  try {
    const resp = await fetch(base + "cambio.json", { cache: "no-store" });
    if (!resp.ok) throw new Error(`No se encuentra ${base}cambio.json`);
    r = await resp.json();
  } catch (e) {
    $("#res-titulo").textContent = e.message;
    return;
  }
  let valores = null;
  if (r.valores) {
    try { valores = await api.valores(base + r.valores.archivo); } catch { /* sin lectura de valores */ }
  }
  est.r = r;
  est.base = base;
  est.zonaSel = null;
  est.mostrar = 40;
  pintarCabecera(r, base, esTrabajo);
  pintarKpis(r);
  pintarResumen(r);
  if (!est.mapa) {
    est.mapa = new Mapa($("#map"), {
      alSeleccionar: (z) => seleccionarZona(z),
      alLeer: (x) => pintarLectura(x),
    });
  }
  est.mapa.cargar(r, base, valores);
  pintarLeyenda(r);
  prepararFiltros(r);
  pintarZonas();
  pintarGraficas(r);
  pintarMetodo(r);
  $("#detalle").hidden = true;
  $("#resultado").scrollIntoView({ behavior: "smooth", block: "start" });
}

function pintarCabecera(r, base, esTrabajo) {
  $("#res-eyebrow").textContent = esTrabajo ? "RESULTADO DEL ANÁLISIS" : "EJEMPLO INCLUIDO";
  $("#res-titulo").textContent = r.titulo;
  const d = r.escena?.dias ?? dias(r.antes.fecha, r.despues.fecha);
  $("#res-sub").textContent = `${fechaLarga(r.antes.fecha)} → ${fechaLarga(r.despues.fecha)}${d != null ? ` (${d} días)` : ""}`
    + (r.pista != null ? ` · pista ${r.pista}, frame ${r.frame}` : "") + ` · umbral ±${num(r.parametros.umbral_dB, 1)} dB`;
  const enlaces = [
    ["informe.html", "Informe", "Informe completo imprimible (guárdalo como PDF desde el navegador)", true],
    ["zonas.geojson", "GeoJSON", "Contornos de las zonas con todos sus datos, para QGIS, geojson.io o Google Earth"],
    ["zonas.csv", "CSV", "Tabla de zonas para Excel (separador ;)"],
    ["informe.md", "Markdown", "El informe en texto Markdown"],
    ["cambio.json", "JSON", "Todos los resultados en bruto"],
  ];
  $("#res-descargas").innerHTML = enlaces.map(([f, t, tip, pri]) =>
    `<a class="pr-btn ${pri ? "pr-btn-pri" : "pr-btn-sec"}" href="${esc(base + f)}" ${pri ? 'target="_blank" rel="noopener"' : "download"} data-tip="${esc(tip)}">${t}</a>`).join("")
    + `<button type="button" class="pr-btn pr-btn-sec" id="nuevo" data-tip="Volver a la carga de ficheros">Nuevo análisis</button>`;
  $("#nuevo").addEventListener("click", () => { location.hash = ""; $("#carga").scrollIntoView({ behavior: "smooth" }); });
  const nota = $("#res-nota");
  nota.hidden = !(r.simulado || r.nota);
  nota.innerHTML = `<strong>${r.simulado ? "Datos simulados." : "Nota."}</strong> ${esc(r.nota || "La segunda fecha es simulada.")}`;
}

function pintarKpis(r) {
  const e = r.estadisticas, p = r.parametros;
  const cambio = Object.values(e.por_clase).reduce((a, v) => a + v.km2, 0);
  const pct = Object.values(e.por_clase).reduce((a, v) => a + v.pct, 0);
  const zkm = Object.values(e.zonas_km2_por_clase || {}).reduce((a, v) => a + v, 0);
  const ag = e.agua;
  const k = [
    ["ÁREA ANALIZADA", `${num(e.area_valida_km2, 0)}`, "km² con datos en las dos fechas", "Superficie donde las dos pasadas tienen señal válida. Los bordes sin datos y las zonas muy oscuras (sombra de radar) quedan fuera."],
    ["ÁREA CON CAMBIO", `${num(cambio, 1)}`, `km² · ${num(pct, 2)} % del área`, `Píxeles de 20 m cuyo brillo sube o baja más de ${num(p.umbral_dB, 1)} dB tras corregir el desplazamiento global.`],
    ["ZONAS", `${e.zonas_total}`, `${num(zkm, 1)} km² agrupados`, `Manchas conexas de cambio de al menos ${num(p.area_min_km2, 2)} km². Las más pequeñas se descartan como ruido.`],
    ["DÍAS ENTRE PASADAS", `${r.escena?.dias ?? dias(r.antes.fecha, r.despues.fecha) ?? "—"}`, `${r.antes.fecha} → ${r.despues.fecha}`, "NISAR repite la misma pista cada 12 días."],
    ["DESPLAZAMIENTO GLOBAL", `${num(p.desplazamiento_global_dB, 2, true)}`, "dB restados a toda la escena", "Mediana de la diferencia entre fechas. Un cambio de humedad general o de calibración sube o baja toda la imagen; se quita para que solo queden cambios locales."],
  ];
  if (e.correlacion != null) k.push(["CORRELACIÓN", num(e.correlacion, 2), e.correlacion >= 0.85 ? "imágenes muy parecidas" : e.correlacion >= 0.6 ? "parecidas" : "poco parecidas", "Correlación de Pearson entre el brillo de las dos fechas, píxel a píxel. 1 = idénticas."]);
  if (ag) k.push(["AGUA", `${num(ag.antes_km2, 0)} → ${num(ag.despues_km2, 0)}`, `km² · +${num(ag.nueva_km2, 1)} / −${num(ag.perdida_km2, 1)}`, `Superficie con brillo de agua lisa (< ${num(p.agua_dB, 1)} dB) en cada fecha, y cuánta aparece y desaparece.`]);
  if (e.cambio) k.push(["CAMBIO TÍPICO", `${num(e.cambio.p90_abs_dB, 1)} dB`, `el 90 % de los píxeles cambia menos`, `Percentiles del cambio absoluto: 50 % < ${num(e.cambio.p50_abs_dB, 2)} dB, 90 % < ${num(e.cambio.p90_abs_dB, 2)} dB, 99 % < ${num(e.cambio.p99_abs_dB, 2)} dB. Desviación ${num(e.cambio.desviacion_dB, 2)} dB.`]);
  $("#res-kpis").innerHTML = k.map(([t, v, s, tip]) => `<article class="stat-card" tabindex="0" data-tip="${esc(tip)}"><span class="stat-label">${t} ${info(tip).replace("tabindex=\"0\" ", "")}</span><strong>${esc(v)}</strong><span class="stat-foot">${esc(s)}</span></article>`).join("");
}

function pintarResumen(r) {
  const t = r.resumen_texto || [`Entre el ${r.antes.fecha} y el ${r.despues.fecha} se han detectado ${r.estadisticas.zonas_total} zonas de cambio.`];
  $("#res-texto").innerHTML = t.map((p) => `<p${p.startsWith("AVISO") ? ' class="pr-warn"' : ""}>${esc(p)}</p>`).join("");
}

function pintarLeyenda(r) {
  const e = r.estadisticas;
  $("#leyenda").innerHTML = Object.entries(r.clases).map(([k, c]) => `<button type="button" class="pr-chip is-on" data-clase="${k}" data-tip="${esc(c.lectura)}\n${num(e.por_clase[k].km2, 2)} km² · ${e.zonas_por_clase?.[k] ?? "—"} zonas\nClic para mostrar u ocultar sus zonas">`
    + `<span class="pr-sw" style="background:${c.color}"></span>${esc(c.nombre)}</button>`).join("")
    + `<span class="pr-leyenda-dif" data-tip="Capa Diferencia: azul = el eco baja, rojo = sube, blanco = sin cambio"><i></i> −8 dB · 0 · +8 dB</span>`;
  for (const b of $$(".pr-chip", $("#leyenda"))) {
    b.addEventListener("click", () => { b.classList.toggle("is-on"); aplicarFiltros(); });
  }
}

// ---------------------------------------------------------------- zonas
function prepararFiltros(r) {
  $("#f-clase").innerHTML = `<option value="">Todas las clases</option>` + Object.entries(r.clases).map(([k, c]) => `<option value="${k}">${esc(c.nombre)}</option>`).join("");
  $("#f-conf").value = "";
  $("#f-orden").value = "area";
  $("#f-conf").disabled = !r.zonas.some((z) => z.confianza);
}

function zonasFiltradas() {
  const r = est.r;
  const clase = $("#f-clase").value, conf = $("#f-conf").value, orden = $("#f-orden").value;
  const activas = new Set($$(".pr-chip.is-on", $("#leyenda")).map((b) => b.dataset.clase));
  let zs = r.zonas.filter((z) => activas.has(z.clase) && (!clase || z.clase === clase)
    && (!conf || (ORDEN_CONF[z.confianza] || 0) >= ORDEN_CONF[conf]));
  if (orden === "cambio") zs = [...zs].sort((a, b) => Math.abs(b.cambio_dB) - Math.abs(a.cambio_dB));
  else if (orden === "id") zs = [...zs].sort((a, b) => a.id.localeCompare(b.id));
  return zs;
}

function aplicarFiltros() {
  const zs = new Set(zonasFiltradas().map((z) => z.id));
  est.mapa.ponerFiltro((z) => zs.has(z.id));
  est.mostrar = 40;
  pintarZonas();
}

function pintarZonas() {
  const r = est.r, zs = zonasFiltradas();
  const tot = r.estadisticas.zonas_total;
  $("#zonas-cuenta").textContent = zs.length === r.zonas.length ? `${zs.length}${tot > r.zonas.length ? ` de ${tot}` : ""}` : `${zs.length} / ${r.zonas.length}`;
  $("#zonas-cuenta").dataset.tip = tot > r.zonas.length ? `Se listan las ${r.zonas.length} zonas mayores de ${tot}.` : "Zonas que cumplen los filtros";
  const lista = $("#zonas");
  if (!zs.length) { lista.innerHTML = `<p class="pr-vacio">Ninguna zona con estos filtros.</p>`; $("#zonas-mas").hidden = true; return; }
  lista.innerHTML = zs.slice(0, est.mostrar).map((z) => {
    const c = r.clases[z.clase] || {};
    const sel = est.zonaSel?.id === z.id ? " is-sel" : "";
    return `<button type="button" role="listitem" class="pr-zona${sel}" data-id="${esc(z.id)}" data-tip="${esc(c.lectura || "")}">`
      + `<span class="pr-zona-id">${esc(z.id.replace("z", ""))}</span>`
      + `<span class="pr-zona-main"><strong><span class="pr-sw" style="background:${c.color}"></span>${esc(c.nombre || z.nombre)}</strong>`
      + `<small>${num(z.area_km2, 2)} km²${z.dB_antes != null ? ` · ${num(z.dB_antes, 1)} → ${num(z.dB_despues, 1)} dB` : ""}</small></span>`
      + `<span class="pr-zona-val"><b style="color:${c.color}">${num(z.cambio_dB, 1, true)} dB</b>${z.confianza ? `<small class="pr-conf pr-conf-${esc(z.confianza)}">${esc(z.confianza)}</small>` : ""}</span></button>`;
  }).join("");
  $("#zonas-mas").hidden = zs.length <= est.mostrar;
  $("#zonas-mas").textContent = `Mostrar más (${zs.length - est.mostrar})`;
}

function seleccionarZona(z) {
  est.zonaSel = z;
  for (const b of $$(".pr-zona")) b.classList.toggle("is-sel", b.dataset.id === z?.id);
  est.mapa.seleccionar(z);
  pintarDetalle(z);
}

function pintarDetalle(z) {
  const det = $("#detalle");
  if (!z) { det.hidden = true; return; }
  const r = est.r, c = r.clases[z.clase] || {}, cob = r.coberturas || {};
  det.hidden = false;
  $("#det-titulo").innerHTML = `<span class="pr-sw" style="background:${c.color}"></span>${esc(z.id)} · ${esc(c.nombre || z.nombre)}`;
  const f = (k, v, tip) => `<div class="pr-dato" ${tip ? `data-tip="${esc(tip)}"` : ""}><span>${k}</span><b>${v}</b></div>`;
  const d = [
    f("Área", `${num(z.area_km2, 3)} km²`, `${num(z.area_km2 * 100, 1)} hectáreas`),
    f("Cambio medio", `${num(z.cambio_dB, 1, true)} dB`, "Media del cambio corregido dentro de la zona"),
    z.cambio_max_dB != null && f("Cambio extremo", `${num(z.cambio_max_dB, 1, true)} dB`, "Bloque de 80 m con el cambio más fuerte"),
    z.dB_antes != null && f("Brillo", `${num(z.dB_antes, 1)} → ${num(z.dB_despues, 1)} dB`, "Brillo radar medio de la zona antes y después"),
    z.pct_agua_antes != null && f("Agua", `${num(z.pct_agua_antes, 0)} % → ${num(z.pct_agua_despues, 0)} %`, `Parte de la zona con brillo de agua (< ${num(r.parametros.agua_dB, 1)} dB)`),
    z.cobertura_antes && f("Superficie", `${esc(cob[z.cobertura_antes]?.nombre || z.cobertura_antes)} → ${esc(cob[z.cobertura_despues]?.nombre || z.cobertura_despues)}`, "Tipo de superficie dominante según el brillo radar"),
    z.perimetro_km != null && f("Perímetro", `${num(z.perimetro_km, 1)} km`),
    z.compacidad != null && f("Compacidad", num(z.compacidad, 2), "1 = círculo perfecto; valores bajos = forma alargada o irregular (ríos, carreteras, bordes de parcela)"),
    z.confianza && f("Confianza", `<span class="pr-conf pr-conf-${esc(z.confianza)}">${esc(z.confianza)}</span>`, `Alta: ≥ 0,5 km² y |Δ| ≥ ${num(2 * r.parametros.umbral_dB, 1)} dB. Media: ≥ 0,1 km² y |Δ| ≥ ${num(1.25 * r.parametros.umbral_dB, 2)} dB. Baja: el resto.`),
    f("Centro", `${z.lat.toFixed(5)}, ${z.lng.toFixed(5)}`),
  ].filter(Boolean).join("");
  const gm = `https://www.google.com/maps/@${z.lat},${z.lng},${Math.max(1500, Math.round(Math.sqrt(z.area_km2) * 4000))}m/data=!3m1!1e3`;
  $("#det-datos").innerHTML = `<p class="pr-lectura-zona">${esc(c.lectura || "")}</p><div class="pr-datos">${d}</div>`
    + `<div class="pr-det-links"><a class="pr-btn pr-btn-sec" target="_blank" rel="noopener" href="${gm}" data-tip="Abrir la zona en Google Maps (vista satélite) para contrastar con imagen óptica">Ver en satélite ↗</a>`
    + `<button type="button" class="pr-btn pr-btn-sec pr-copiar" data-copiar="${z.lat.toFixed(5)}, ${z.lng.toFixed(5)}">Copiar coordenadas</button>`
    + `<button type="button" class="pr-btn pr-btn-sec" id="det-sat" data-tip="Poner el mapa base en satélite y quitar el radar">Comparar con satélite</button></div>`;
  $("#det-sat").addEventListener("click", () => {
    $("#mapa-base").value = "satelite";
    est.mapa.ponerBase("satelite");
    ponerFondo("ninguno");
    $("#map").scrollIntoView({ behavior: "smooth", block: "center" });
  });
  const rc = $("#det-recorte");
  if (z.recorte) {
    const b = `${est.base}zonas/${z.id}`;
    rc.innerHTML = `<div class="pr-comp" style="--x:50%"><img src="${b}_antes.webp" alt="Antes"><img class="pr-comp-b" src="${b}_despues.webp" alt="Después">`
      + `<img class="pr-comp-c" src="${b}_cambio.png" alt="" hidden><span class="pr-comp-et a">ANTES</span><span class="pr-comp-et b">DESPUÉS</span>`
      + `<input type="range" min="0" max="100" value="50" aria-label="Comparar antes y después"></div>`
      + `<label class="pr-mut"><input type="checkbox" class="pr-comp-ver"> Superponer clases de cambio</label>`
      + `<p class="pr-mut">Recorte de ${num(z.recorte.lado_km, 1)} km a resolución completa (20 m). Arrastra para comparar.</p>`;
    const comp = $(".pr-comp", rc);
    $("input[type=range]", comp).addEventListener("input", (e) => comp.style.setProperty("--x", `${e.target.value}%`));
    $(".pr-comp-ver", rc).addEventListener("change", (e) => { $(".pr-comp-c", comp).hidden = !e.target.checked; });
  } else {
    rc.innerHTML = `<p class="pr-vacio">Esta zona no tiene recorte a 20 m (solo se generan para las 12 mayores). Usa el mapa: con el ratón encima ves los valores.</p>`;
  }
  det.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ---------------------------------------------------------------- lectura bajo el mapa
function pintarLectura(x) {
  const el = $("#lectura");
  if (!x) { el.textContent = "Pasa el ratón por el mapa para leer el brillo de cada fecha y el cambio. Haz clic para fijar el valor."; return; }
  const c = x.clase ? est.r.clases[x.clase] : null;
  el.innerHTML = `<b>${x.lat.toFixed(4)}, ${x.lng.toFixed(4)}</b> · antes ${num(x.antes, 1)} dB · después ${num(x.despues, 1)} dB · `
    + `cambio <b>${num(x.cambio, 1, true)} dB</b>${x.frac != null ? ` · ${num(100 * x.frac, 1)} % de píxeles con cambio` : ""}`
    + (c ? ` · <span class="pr-sw" style="background:${c.color}"></span>${esc(c.nombre)}` : "");
}

// ---------------------------------------------------------------- gráficas
function pintarGraficas(r) {
  const e = r.estadisticas, p = r.parametros, U = p.umbral_dB;
  barrasH($("#g-clases"), Object.entries(r.clases).map(([k, c]) => ({
    etq: c.nombre, valor: e.por_clase[k].km2, color: c.color,
    tip: `<b>${esc(c.nombre)}</b><div>${num(e.por_clase[k].km2, 2)} km² (${num(e.por_clase[k].pct, 3)} % del área)</div>`
      + `<div>${e.zonas_por_clase?.[k] ?? "—"} zonas · ${num(e.zonas_km2_por_clase?.[k], 2)} km² en zonas</div><small>${esc(c.lectura)}</small>`,
  })), { unidad: "km²", dec: 2 });

  const hc = e.histograma_cambio;
  histograma($("#g-hist"), {
    bordes: hc.bordes_dB, ejeX: "cambio de brillo (dB)",
    series: [{ nombre: "Píxeles", color: "#7d8b97", conteos: hc.conteos, colorBin: (x) => (x < -U ? r.clases.descenso.color : x > U ? r.clases.aumento.color : "#5b6b77") }],
    lineas: [{ x: -U, color: r.clases.descenso.color, etq: `−${num(U, 1)}` }, { x: U, color: r.clases.aumento.color, etq: `+${num(U, 1)}` }],
    formatoTip: (a, b, s) => `<b>${num(a, 1)} a ${num(b, 1)} dB</b><div>${num(s[0].valor, 3)} % de los píxeles</div><div>${num(s[0].conteo * (r.escena?.pixel_m || 20) ** 2 / 1e6, 1)} km²</div>`
      + `<small>${a >= U ? "Por encima del umbral: el eco sube" : b <= -U ? "Por debajo del umbral: el eco baja" : "Dentro del umbral: sin cambio"}</small>`,
  });

  if (e.histograma_antes) {
    histograma($("#g-brillo"), {
      bordes: e.histograma_antes.bordes_dB, ejeX: "brillo radar HH (dB)",
      series: [{ nombre: `Antes (${r.antes.fecha})`, color: "#72b8d0", conteos: e.histograma_antes.conteos, tipo: "linea" },
        { nombre: `Después (${r.despues.fecha})`, color: "#e4b65c", conteos: e.histograma_despues.conteos, tipo: "linea" }],
      lineas: [{ x: p.agua_dB, color: "#3d8bff", etq: "agua" }],
    });
  } else $("#g-brillo").innerHTML = `<p class="pr-vacio">Este resultado se generó con una versión anterior del pipeline.</p>`;

  if (e.agua) {
    const a = e.agua;
    barrasV($("#g-agua"), {
      categorias: ["Agua antes", "Agua después", "Se mantiene", "Aparece", "Desaparece"],
      series: [{ nombre: "km²", color: "#3d8bff", valores: [a.antes_km2, a.despues_km2, a.estable_km2, a.nueva_km2, a.perdida_km2] }],
      unidad: "km²",
      tips: (i) => [
        `<b>Agua antes</b><div>${num(a.antes_km2, 1)} km² con brillo &lt; ${num(p.agua_dB, 1)} dB</div>`,
        `<b>Agua después</b><div>${num(a.despues_km2, 1)} km² (${num(a.despues_km2 - a.antes_km2, 1, true)} km²)</div>`,
        `<b>Se mantiene</b><div>${num(a.estable_km2, 1)} km² son agua en las dos fechas</div>`,
        `<b>Aparece</b><div>${num(a.nueva_km2, 1)} km² se vuelven agua: crecidas, encharcamientos</div>`,
        `<b>Desaparece</b><div>${num(a.perdida_km2, 1)} km² dejan de ser agua: retirada, o agua con viento que se vuelve rugosa</div>`][i],
    });
  } else $("#g-agua").innerHTML = `<p class="pr-vacio">Sin datos de agua en este resultado.</p>`;

  pintarMatriz(r);

  dispersion($("#g-zonas"), {
    puntos: r.zonas.map((z) => ({
      x: z.area_km2, y: z.cambio_dB, color: r.clases[z.clase]?.color, r: z.confianza === "alta" ? 6 : z.confianza === "media" ? 4.5 : 3.5, z,
      tip: `<b>${esc(z.id)} · ${esc(r.clases[z.clase]?.nombre)}</b><div>${num(z.area_km2, 2)} km² · ${num(z.cambio_dB, 1, true)} dB</div>${z.confianza ? `<div>Confianza ${esc(z.confianza)}</div>` : ""}<small>Clic para abrir la ficha</small>`,
    })),
    logX: true, ejeX: "área de la zona (km², escala logarítmica)", ejeY: "cambio medio (dB)",
    lineasY: [{ y: U, color: "#68b6a3" }, { y: -U, color: "#e47759" }],
    alClic: (pt) => { seleccionarZona(pt.z); $("#map").scrollIntoView({ behavior: "smooth", block: "center" }); },
  });
}

function pintarMatriz(r) {
  const cm = r.estadisticas.coberturas, el = $("#g-matriz");
  if (!cm || !r.coberturas) { el.innerHTML = `<p class="pr-vacio">Este resultado no incluye la matriz de coberturas.</p>`; return; }
  const ks = cm.orden, M = cm.matriz_km2, cob = r.coberturas;
  const fuera = M.flatMap((f, i) => f.filter((_, j) => i !== j)), max = Math.max(...fuera, 1e-9);
  const tot = M.flat().reduce((a, b) => a + b, 0) || 1;
  let h = `<table class="pr-matriz"><thead><tr><th>Antes ↓ · Después →</th>${ks.map((k) => `<th data-tip="${esc(cob[k].lectura)}"><span class="pr-sw" style="background:${cob[k].color}"></span>${esc(cob[k].nombre)}</th>`).join("")}<th>Total antes</th></tr></thead><tbody>`;
  ks.forEach((ka, i) => {
    h += `<tr><th data-tip="${esc(cob[ka].lectura)}"><span class="pr-sw" style="background:${cob[ka].color}"></span>${esc(cob[ka].nombre)}</th>`;
    ks.forEach((kb, j) => {
      const v = M[i][j], diag = i === j;
      const a = diag ? 0.06 : 0.1 + 0.7 * Math.sqrt(v / max);
      const tip = diag ? `${cob[ka].nombre}: se mantiene\n${num(v, 1)} km² (${num((100 * v) / tot, 2)} %)`
        : `${cob[ka].nombre} → ${cob[kb].nombre}\n${num(v, 2)} km² (${num((100 * v) / tot, 3)} % del área)`;
      h += `<td class="${diag ? "diag" : ""}" style="background:rgba(228,182,92,${a.toFixed(2)})" data-tip="${esc(tip)}">${num(v, v < 10 ? 2 : 1)}</td>`;
    });
    h += `<td class="tot">${num(cm.antes_km2[i], 1)}</td></tr>`;
  });
  h += `<tr><th>Total después</th>${cm.despues_km2.map((v, j) => `<td class="tot" data-tip="Diferencia con antes: ${num(v - cm.antes_km2[j], 1, true)} km²">${num(v, 1)}</td>`).join("")}<td></td></tr></tbody></table>`;
  const cortes = r.parametros.cortes_cobertura_dB;
  if (cortes) h += `<p class="pr-mut">Cortes: agua &lt; ${num(cortes[0], 1)} dB ≤ liso &lt; ${num(cortes[1], 1)} dB ≤ vegetación &lt; ${num(cortes[2], 1)} dB ≤ muy brillante.</p>`;
  el.innerHTML = h;
}

function pintarMetodo(r) {
  const p = r.parametros, im = r.imagenes, U = p.umbral_dB;
  $("#met-texto").innerHTML = `<ol class="pr-pasos-met">
    <li><b>Filtro de speckle.</b> Media ${p.filtro_px || 5}×${p.filtro_px || 5} en potencia lineal (unos 100 m) para quitar el granulado típico del radar.</li>
    <li><b>Diferencia.</b> Brillo de después menos brillo de antes, en dB, píxel a píxel a 20 m.</li>
    <li><b>Desplazamiento global.</b> Se resta la mediana de la diferencia (${num(p.desplazamiento_global_dB, 2, true)} dB): la humedad general o la calibración mueven toda la escena y no son cambios locales.</li>
    <li><b>Clases.</b> |Δ| &gt; ${num(U, 1)} dB es cambio. «Agua nueva» y «agua que desaparece» exigen además cruzar el umbral de agua (${num(p.agua_dB, 1)} dB).</li>
    <li><b>Zonas.</b> Clase dominante en bloques de ${num(im.resolucion_m?.cambio || 80, 0)} m, agrupada en manchas de al menos ${num(p.area_min_km2, 2)} km².</li>
  </ol>
  <p class="pr-mut"><b>Límites.</b> Solo polarización HH. Umbrales fijos (el de agua falla en desiertos y con viento). Sin corrección de pendiente: en montaña aparecen falsos cambios. Un cambio de radar es una señal, no una prueba: contrástalo con imagen óptica (botón «Comparar con satélite» en cada zona).</p>`;
  const esc_ = r.escena || {};
  const filas = [
    ["Sensor", r.sensor],
    ["Pista / frame", r.pista != null ? `${r.pista} / ${r.frame}` : "—"],
    ["Órbita / mirada", `${{ Ascending: "ascendente", Descending: "descendente" }[r.direccion] || r.direccion || "—"} / ${{ Left: "izquierda", Right: "derecha" }[esc_.mirada] || esc_.mirada || "—"}`],
    ["Polarizaciones en los datos", esc_.polarizaciones_antes ? `${esc_.polarizaciones_antes.join(", ")} / ${esc_.polarizaciones_despues.join(", ")}` : "—"],
    ["Gránulo antes", r.antes.granulo], ["Gránulo después", r.despues.granulo],
    ["Píxel / proyección", esc_.pixel_m ? `${esc_.pixel_m} m / EPSG:${esc_.epsg}` : "20 m"],
    ["Tamaño de la ventana", esc_.filas ? `${num(esc_.filas, 0)} × ${num(esc_.columnas, 0)} px (${num(esc_.area_ventana_km2, 0)} km²)` : "—"],
    ["Resolución de capas", im.resolucion_m ? `fondo ${im.resolucion_m.fondo} m · cambio ${im.resolucion_m.cambio} m${im.resolucion_m.densidad ? ` · consulta ${im.resolucion_m.densidad} m` : ""}` : "—"],
    ["Escala de gris", im.escala_gris_dB ? `${num(im.escala_gris_dB.vmin, 1)} a ${num(im.escala_gris_dB.vmax, 1)} dB` : "—"],
    ["Generado", r.generado],
  ];
  $("#met-ficha").innerHTML = filas.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v ?? "—")}</td></tr>`).join("");
}

// ================================================================ controles del mapa
function ponerFondo(f) {
  for (const b of $$(".pr-seg button")) b.classList.toggle("is-on", b.dataset.fondo === f);
  est.mapa?.ponerFondo(f);
}

function prepararControles() {
  for (const b of $$(".pr-seg button")) b.addEventListener("click", () => ponerFondo(b.dataset.fondo));
  for (const c of $$("[data-capa]")) c.addEventListener("change", () => est.mapa?.ponerVisible(c.dataset.capa, c.checked));
  $("#opacidad").addEventListener("input", (e) => est.mapa?.ponerOpacidad(e.target.value / 100));
  $("#mapa-base").addEventListener("change", (e) => est.mapa?.ponerBase(e.target.value));
  $("#ver-todo").addEventListener("click", () => est.mapa?.verTodo());
  for (const id of ["#f-clase", "#f-conf", "#f-orden"]) $(id).addEventListener("change", aplicarFiltros);
  $("#zonas").addEventListener("click", (e) => {
    const b = e.target.closest(".pr-zona");
    if (b) seleccionarZona(est.r.zonas.find((z) => z.id === b.dataset.id));
  });
  $("#zonas-mas").addEventListener("click", () => { est.mostrar += 40; pintarZonas(); });
  $("#det-cerrar").addEventListener("click", () => seleccionarZona(null));
  document.addEventListener("click", async (e) => {
    const b = e.target.closest(".pr-copiar");
    if (b && !b.closest(".leaflet-popup")) await copiar(b);
  });
  const salida = (id, f) => { const i = $(id); const o = $(`output[for="${id.slice(1)}"]`); const up = () => { o.textContent = f(+i.value); }; i.addEventListener("input", up); up(); };
  salida("#op-umbral", (v) => `${num(v, 1)} dB`);
  salida("#op-agua", (v) => `${num(v, 1)} dB`);
  $("#analizar").addEventListener("click", analizar);
}

// ================================================================ rutas
function ruta() {
  const h = new URLSearchParams(location.hash.slice(1));
  clearTimeout(est.sondeo);
  if (h.get("t")) {
    if (!est.servidor) { $("#resultado").hidden = true; return; }
    seguir(h.get("t"));
  } else if (h.get("ej")) {
    $("#progreso").hidden = true;
    abrirResultado(`${EJEMPLOS}${encodeURIComponent(h.get("ej"))}/`, false);
  } else {
    $("#progreso").hidden = true;
    $("#resultado").hidden = true;
  }
}

async function iniciar() {
  activarTips(document);
  const barra = $(".topbar");
  const compacta = () => barra.classList.toggle("is-compact", scrollY > 12);
  window.addEventListener("scroll", compacta, { passive: true });
  compacta();
  prepararDrops();
  prepararControles();
  await comprobarServidor();
  cargarHistorial();
  cargarEjemplos();
  window.addEventListener("hashchange", ruta);
  let redim;
  window.addEventListener("resize", () => {
    clearTimeout(redim);
    redim = setTimeout(() => est.r && !$("#resultado").hidden && pintarGraficas(est.r), 250);
  });
  ruta();
  setInterval(async () => { const antes = est.servidor; await comprobarServidor(); if (antes !== est.servidor) cargarHistorial(); }, 15000);
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
else iniciar();

