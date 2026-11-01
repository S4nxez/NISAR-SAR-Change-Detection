// Llamadas al servicio de procesado (processing/servidor.py).
// Por defecto usa el mismo origen que la página; ?api=http://host:puerto lo cambia.

const parametro = new URLSearchParams(location.search).get("api");
export const BASE = (parametro || "").replace(/\/$/, "");

/** URL absoluta de un recurso del servicio (API o resultados en /trabajos/). */
export const url = (ruta) => `${BASE}/${ruta.replace(/^\//, "")}`;

async function json(ruta, opciones) {
  const r = await fetch(url(ruta), opciones);
  let datos = null;
  try { datos = await r.json(); } catch { /* respuesta sin JSON */ }
  if (!r.ok) throw new Error(datos?.error || `Error ${r.status} en ${ruta}`);
  return datos;
}

export const estado = () => json("api/nisar/estado");
export const trabajos = () => json("api/nisar/trabajos");
export const trabajo = (id) => json(`api/nisar/trabajos/${encodeURIComponent(id)}`);
export const crearTrabajo = (cuerpo) => json("api/nisar/trabajos", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
});

/**
 * Sube un fichero en crudo (sin multipart, para no cargarlo en memoria).
 * Devuelve { promesa, cancelar }. alProgreso(enviados, total).
 */
export function subir(fichero, alProgreso) {
  const xhr = new XMLHttpRequest();
  const promesa = new Promise((resolve, reject) => {
    xhr.open("POST", url(`api/nisar/subidas?nombre=${encodeURIComponent(fichero.name)}`));
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    xhr.upload.onprogress = (e) => e.lengthComputable && alProgreso?.(e.loaded, e.total);
    xhr.onload = () => {
      let datos = null;
      try { datos = JSON.parse(xhr.responseText); } catch { /* nada */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(datos);
      else reject(new Error(datos?.error || `Error ${xhr.status} al subir`));
    };
    xhr.onerror = () => reject(new Error("Se ha perdido la conexión con el servicio de procesado."));
    xhr.onabort = () => reject(new Error("Subida cancelada."));
    xhr.send(fichero);
  });
  return { promesa, cancelar: () => xhr.abort() };
}

/** Descarga y descomprime la rejilla de valores (valores.bin.gz). */
export async function valores(ruta) {
  const r = await fetch(ruta);
  if (!r.ok) throw new Error(`No se pudo leer ${ruta}`);
  const buf = new Uint8Array(await r.arrayBuffer());
  if (buf[0] === 0x1f && buf[1] === 0x8b && "DecompressionStream" in window) {
    const ds = new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Uint8Array(await new Response(ds).arrayBuffer());
  }
  return buf;
}
