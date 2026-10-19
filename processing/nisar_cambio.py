#!/usr/bin/env python3
"""
nisar_cambio.py - Detecta cambios entre dos escenas NISAR (antes / despues) y genera
los ficheros que muestra la web (frontend/nisar.html).

Metodo (por pixel, a 20 m):
  1. Filtro de speckle: media 5x5 en potencia lineal (100 m).
  2. Diferencia d = dB_despues - dB_antes.
  3. Se resta el desplazamiento global (mediana de d): humedad o calibracion distinta
     entre fechas afectan a toda la escena y no son un cambio local.
  4. Clases (umbral U, por defecto 3 dB; agua = brillo < -15 dB):
       1 agua nueva        no era agua, ahora si, y d < -U   (posible inundacion)
       2 agua desaparece   era agua, ahora no, y d > +U       (retirada del agua)
       3 descenso          d < -U                             (posible tala, cosecha, suelo seco)
       4 aumento           d > +U                             (vegetacion, obras, suelo humedo)
  5. Se agrupan pixeles en zonas (a 80 m) y se descartan las menores de --area-min km2.

Uso:
  python nisar_cambio.py ESCENA_ANTES ESCENA_DESPUES --id peru_oct2026 \
      --titulo "Amazonia peruana" --salida ../frontend/public/data/nisar
  (ESCENA_* = carpeta *_completo o su .zip, generados por nisar_escena.py)
"""
import argparse
import datetime as dt
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as nd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nisar_comun import Escena, filtrar_speckle, q_a_db, reducir, utm_a_latlon  # noqa: E402

CLASES = {
    1: {"clave": "agua_nueva", "nombre": "Agua nueva", "color": "#3d8bff",
        "lectura": "Superficie que pasa a reflejar como agua lisa: posible inundacion o crecida."},
    2: {"clave": "agua_desaparece", "nombre": "Agua que desaparece", "color": "#e4b65c",
        "lectura": "Superficie que deja de ser agua: retirada de una crecida o lago que mengua."},
    3: {"clave": "descenso", "nombre": "Descenso del eco", "color": "#e47759",
        "lectura": "Menos retrodispersion: posible tala, cosecha o suelo mas seco."},
    4: {"clave": "aumento", "nombre": "Aumento del eco", "color": "#68b6a3",
        "lectura": "Mas retrodispersion: vegetacion que crece, estructuras o suelo mas humedo."},
}
FRANJA = 1024
HALO = 4


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def alinear(A, B):
    """Ventana comun (en pixeles de A y de B). Exige misma rejilla con desplazamiento entero."""
    if abs(A.dx - B.dx) > 1e-6 or abs(A.dy - B.dy) > 1e-6 or A.epsg != B.epsg:
        raise SystemExit("Las escenas no comparten rejilla (tamano de pixel o proyeccion distintos).")
    oc = (B.x0 - A.x0) / A.dx
    orow = (B.y0 - A.y0) / A.dy
    if abs(oc - round(oc)) > 0.01 or abs(orow - round(orow)) > 0.01:
        raise SystemExit("Las rejillas estan desplazadas una fraccion de pixel; hay que remuestrear.")
    oc, orow = int(round(oc)), int(round(orow))
    # pixel (r, c) de A  <->  pixel (r - orow, c - oc) de B
    r0, r1 = max(0, orow), min(A.alto, orow + B.alto)
    c0, c1 = max(0, oc), min(A.ancho, oc + B.ancho)
    if r1 <= r0 or c1 <= c0:
        raise SystemExit("Las escenas no se solapan.")
    return (r0, r1, c0, c1), (orow, oc)


def preparar(qA, qB, r0, r1, umbral_borde=-30.0):
    """dB filtrado de A y B en las filas [r0, r1) con halo; enmascara bordes sin senal."""
    a0, a1 = max(0, r0 - HALO), min(qA.shape[0], r1 + HALO)
    fa = filtrar_speckle(q_a_db(qA[a0:a1]))
    fb = filtrar_speckle(q_a_db(qB[a0:a1]))
    fa, fb = fa[r0 - a0:r0 - a0 + (r1 - r0)], fb[r0 - a0:r0 - a0 + (r1 - r0)]
    ok = np.isfinite(fa) & np.isfinite(fb) & (fa > umbral_borde) & (fb > umbral_borde)
    return fa, fb, ok


def clasificar(fa, fb, ok, despl, umbral, agua):
    d = fb - fa - despl
    cls = np.zeros(fa.shape, np.uint8)
    wa, wb = fa < agua, fb < agua
    cls[ok & (d < -umbral)] = 3
    cls[ok & (d > umbral)] = 4
    cls[ok & ~wa & wb & (d < -umbral)] = 1
    cls[ok & wa & ~wb & (d > umbral)] = 2
    return cls, d


def png_gris(db, ruta, vmin=-16.0, vmax=0.0):
    ok = np.isfinite(db)
    g = np.clip((np.nan_to_num(db, nan=vmin) - vmin) / (vmax - vmin), 0, 1)
    rgba = np.zeros(db.shape + (4,), np.uint8)
    rgba[..., :3] = (g * 255).astype(np.uint8)[..., None]
    rgba[..., 3] = np.where(ok, 255, 0)
    _guardar(rgba, ruta)


def _guardar(rgba, ruta):
    """WebP con perdida para fondos (10 veces mas ligero que PNG); PNG para todo lo demas."""
    im = Image.fromarray(rgba, "RGBA")
    if ruta.endswith(".webp"):
        im.save(ruta, "WEBP", quality=82, method=6)
    else:
        im.save(ruta, optimize=True)


def png_clases(cls, ruta, alfa=225):
    rgba = np.zeros(cls.shape + (4,), np.uint8)
    for k, c in CLASES.items():
        m = cls == k
        rgba[m, :3] = _rgb(c["color"])
        rgba[m, 3] = alfa
    Image.fromarray(rgba, "RGBA").save(ruta, optimize=True)


def png_diferencia(d, ruta, lim=8.0):
    ok = np.isfinite(d)
    t = np.clip(np.nan_to_num(d) / lim, -1, 1)
    rgba = np.zeros(d.shape + (4,), np.uint8)
    neg, pos = t < 0, t >= 0
    rgba[..., 0] = np.where(pos, 255, (255 * (1 + t))).astype(np.uint8)
    rgba[..., 1] = (255 * (1 - np.abs(t))).astype(np.uint8)
    rgba[..., 2] = np.where(neg, 255, (255 * (1 - t))).astype(np.uint8)
    rgba[..., 3] = np.where(ok, (40 + 200 * np.abs(t)).astype(np.uint8), 0)
    _guardar(rgba, ruta)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("antes")
    ap.add_argument("despues")
    ap.add_argument("--id", required=True, help="identificador corto, sin espacios (nombre de carpeta)")
    ap.add_argument("--titulo", default=None)
    ap.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    "..", "frontend", "public", "data", "nisar"))
    ap.add_argument("--umbral", type=float, default=3.0, help="dB de cambio para marcar un pixel")
    ap.add_argument("--agua", type=float, default=-15.0, help="dB por debajo de los cuales se considera agua")
    ap.add_argument("--area-min", type=float, default=0.05, help="km2 minimos de una zona")
    ap.add_argument("--zonas", type=int, default=12, help="zonas con recortes a 20 m")
    ap.add_argument("--simulado", action="store_true", help="marca el par como simulado en la web")
    ap.add_argument("--nota", default="", help="aviso que la web muestra junto al par")
    a = ap.parse_args()

    A, B = Escena(a.antes), Escena(a.despues)
    (r0, r1, c0, c1), (orow, oc) = alinear(A, B)
    print(f"Antes {A.fecha}  Despues {B.fecha}  ventana comun filas {r0}-{r1} columnas {c0}-{c1}")
    qA = A.mosaico_q()[r0:r1, c0:c1]
    qB = B.mosaico_q()[r0 - orow:r1 - orow, c0 - oc:c1 - oc]
    H, W = qA.shape
    px_km2 = abs(A.dx * A.dy) / 1e6

    # ---- pasada 1: desplazamiento global (mediana de la diferencia)
    bins = np.arange(-30, 30.01, 0.05)
    hist = np.zeros(len(bins) - 1, np.int64)
    n_ok = 0
    for s in range(0, H, FRANJA):
        fa, fb, ok = preparar(qA, qB, s, min(H, s + FRANJA))
        d = (fb - fa)[ok]
        n_ok += d.size
        hist += np.histogram(np.clip(d, -29.99, 29.99), bins)[0]
        print(f"  pasada 1: {min(H, s + FRANJA)}/{H}", flush=True)
    if n_ok == 0:
        raise SystemExit("No hay pixeles validos en comun.")
    cum = np.cumsum(hist) / n_ok
    despl = float(bins[np.searchsorted(cum, 0.5)] + 0.025)
    print(f"Desplazamiento global: {despl:+.2f} dB")

    # ---- pasada 2: clases y reducciones
    # factor de reduccion de las imagenes: el lado mayor queda en ~2000-4000 px
    G = int(min(8, max(2, 2 ** np.ceil(np.log2(max(H, W) / 2500)))))   # fondos (160 m en una escena NISAR)
    F = max(2, G // 2)                                                    # capa de cambio y zonas (80 m)
    Hr, Wr = H // F, W // F
    frac = np.zeros((5, Hr, Wr), np.float32)
    validr = np.zeros((Hr, Wr), np.float32)
    dmean = np.full((Hr, Wr), np.nan, np.float32)
    fa_g = np.full((H // G, W // G), np.nan, np.float32)
    fb_g = np.full((H // G, W // G), np.nan, np.float32)
    d_g = np.full((H // G, W // G), np.nan, np.float32)
    dh_bins = np.arange(-15, 15.01, 0.5)
    dh = np.zeros(len(dh_bins) - 1, np.int64)
    conteo = np.zeros(5, np.int64)
    paso = FRANJA // G * G
    for s in range(0, H // G * G, paso):
        e = min(H // G * G, s + paso)
        fa, fb, ok = preparar(qA, qB, s, e)
        cls, d = clasificar(fa, fb, ok, despl, a.umbral, a.agua)
        d[~ok] = np.nan
        conteo += np.bincount(cls[ok], minlength=5)
        dh += np.histogram(np.clip(d[ok], -14.99, 14.99), dh_bins)[0]
        sr = slice(s // F, e // F)
        validr[sr] = reducir(ok, F)[:, :Wr]
        for k in range(1, 5):
            frac[k, sr] = reducir(cls == k, F)[:, :Wr]
        dmean[sr] = reducir(d, F)[:, :Wr]
        sg = slice(s // G, e // G)
        fa_g[sg] = reducir(np.where(ok, fa, np.nan), G)[:, :W // G]
        fb_g[sg] = reducir(np.where(ok, fb, np.nan), G)[:, :W // G]
        d_g[sg] = reducir(d, G)[:, :W // G]
        print(f"  pasada 2: {e}/{H}", flush=True)

    # clase dominante a 80 m (al menos la mitad de los pixeles validos del bloque)
    with np.errstate(invalid="ignore", divide="ignore"):
        rel = frac[1:] / np.maximum(validr, 1e-6)
    best = rel.argmax(axis=0) + 1
    cls_r = np.where((rel.max(axis=0) >= 0.5) & (validr > 0.5), best, 0).astype(np.uint8)

    # zonas: componentes conexas por clase, filtradas por area
    px_r_km2 = px_km2 * F * F
    min_px = max(1, int(round(a.area_min / px_r_km2)))
    zonas = []
    limpio = np.zeros_like(cls_r)
    for k in range(1, 5):
        lab, n = nd.label(cls_r == k, structure=np.ones((3, 3)))
        if n == 0:
            continue
        tam = nd.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        objs = nd.find_objects(lab)
        for i in np.nonzero(tam >= min_px)[0]:
            sl = objs[i]
            m = lab[sl] == i + 1
            limpio[sl][m] = k
            cy, cx = nd.center_of_mass(m)
            cy, cx = (cy + sl[0].start + 0.5) * F, (cx + sl[1].start + 0.5) * F
            zonas.append({"clase": k, "px": int(tam[i]), "cy": cy, "cx": cx,
                          "bbox": [sl[0].start * F, sl[0].stop * F, sl[1].start * F, sl[1].stop * F],
                          "d_media": float(np.nanmean(dmean[sl][m]))})
    zonas.sort(key=lambda z: -z["px"])

    def ll(fila, col):   # pixel de la ventana comun -> lat, lon
        x = A.x0 + (c0 + col) * A.dx
        y = A.y0 + (r0 + fila) * A.dy
        return utm_a_latlon(x, y, A.epsg)

    os.makedirs(os.path.join(a.salida, a.id, "zonas"), exist_ok=True)
    out = os.path.join(a.salida, a.id)
    # escala de grises comun a las dos fechas, ajustada a la escena (percentiles 2-98 de "antes")
    vmin, vmax = (float(v) for v in np.nanpercentile(fa_g, [2, 98]))
    escala = {"vmin": round(vmin, 1), "vmax": round(vmax, 1)}
    png_gris(fa_g, os.path.join(out, "antes.webp"), **escala)
    png_gris(fb_g, os.path.join(out, "despues.webp"), **escala)
    png_clases(limpio, os.path.join(out, "cambio.png"))
    png_diferencia(d_g, os.path.join(out, "diferencia.webp"))

    # recortes a resolucion completa de las zonas mayores
    lista = []
    R = 256  # medio lado del recorte (512 px = 10,2 km)
    for j, z in enumerate(zonas):
        lat, lon = ll(z["cy"], z["cx"])
        s_, n_ = ll(z["bbox"][1], z["bbox"][2]), ll(z["bbox"][0], z["bbox"][3])
        item = {"id": f"z{j + 1:03d}", "clase": CLASES[z["clase"]]["clave"],
                "nombre": CLASES[z["clase"]]["nombre"], "lat": round(lat, 5), "lng": round(lon, 5),
                "area_km2": round(z["px"] * px_r_km2, 3), "cambio_dB": round(z["d_media"], 2),
                "bounds": [[round(min(s_[0], n_[0]), 5), round(min(s_[1], n_[1]), 5)],
                           [round(max(s_[0], n_[0]), 5), round(max(s_[1], n_[1]), 5)]]}
        if j < a.zonas:
            fr = int(np.clip(z["cy"] - R, 0, max(0, H - 2 * R)))
            fc = int(np.clip(z["cx"] - R, 0, max(0, W - 2 * R)))
            lo, hi = max(0, fr - HALO), min(H, fr + 2 * R + HALO)
            fa = filtrar_speckle(q_a_db(qA[lo:hi, fc:fc + 2 * R]))[fr - lo:fr - lo + 2 * R]
            fb = filtrar_speckle(q_a_db(qB[lo:hi, fc:fc + 2 * R]))[fr - lo:fr - lo + 2 * R]
            ok = np.isfinite(fa) & np.isfinite(fb) & (fa > -30) & (fb > -30)
            cls, _ = clasificar(fa, fb, ok, despl, a.umbral, a.agua)
            png_gris(q_a_db(qA[fr:fr + 2 * R, fc:fc + 2 * R]), os.path.join(out, "zonas", f"{item['id']}_antes.webp"), **escala)
            png_gris(q_a_db(qB[fr:fr + 2 * R, fc:fc + 2 * R]), os.path.join(out, "zonas", f"{item['id']}_despues.webp"), **escala)
            png_clases(cls, os.path.join(out, "zonas", f"{item['id']}_cambio.png"))
            p1, p2 = ll(fr + 2 * R, fc), ll(fr, fc + 2 * R)
            item["recorte"] = {"bounds": [[round(p1[0], 5), round(p1[1], 5)], [round(p2[0], 5), round(p2[1], 5)]],
                               "lado_km": round(2 * R * abs(A.dx) / 1000, 1)}
        lista.append(item)

    esquinas = [ll(0, 0), ll(0, W), ll(H, 0), ll(H, W)]
    lats, lons = [p[0] for p in esquinas], [p[1] for p in esquinas]
    area_valida = n_ok * px_km2
    resumen = {
        "id": a.id,
        "titulo": a.titulo or a.id,
        "simulado": bool(a.simulado),
        "nota": a.nota,
        "generado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sensor": "NISAR L-SAR (banda L), producto L2 GCOV, polarizacion HH",
        "antes": {"fecha": A.fecha, "granulo": A.resumen.get("granuleId") or A.resumen.get("archivo")},
        "despues": {"fecha": B.fecha, "granulo": B.resumen.get("granuleId") or B.resumen.get("archivo")},
        "pista": A.resumen.get("trackNumber"), "frame": A.resumen.get("frameNumber"),
        "direccion": A.resumen.get("orbitPassDirection"),
        "bounds": [[round(min(lats), 5), round(min(lons), 5)], [round(max(lats), 5), round(max(lons), 5)]],
        "centro": [round(float(np.mean(lats)), 4), round(float(np.mean(lons)), 4)],
        "imagenes": {"antes": "antes.webp", "despues": "despues.webp", "cambio": "cambio.png",
                     "diferencia": "diferencia.webp", "resolucion_m": {"fondo": abs(A.dx) * G, "cambio": abs(A.dx) * F},
                     "escala_gris_dB": escala},
        "parametros": {"umbral_dB": a.umbral, "agua_dB": a.agua, "filtro_px": 5, "area_min_km2": a.area_min,
                       "desplazamiento_global_dB": round(despl, 2)},
        "estadisticas": {
            "area_valida_km2": round(area_valida, 1),
            "por_clase": {CLASES[k]["clave"]: {"km2": round(float(conteo[k]) * px_km2, 2),
                                               "pct": round(100.0 * float(conteo[k]) / n_ok, 3)} for k in CLASES},
            "zonas_total": len(zonas),
            "zonas_km2_por_clase": {CLASES[k]["clave"]: round(sum(z["px"] for z in zonas if z["clase"] == k) * px_r_km2, 2)
                                    for k in CLASES},
            "histograma_cambio": {"bordes_dB": [float(dh_bins[0]), float(dh_bins[-1]), 0.5], "conteos": dh.tolist()},
        },
        "clases": {CLASES[k]["clave"]: {"nombre": c["nombre"], "color": c["color"], "lectura": c["lectura"]}
                   for k, c in CLASES.items()},
        "zonas": lista[:200],
    }
    with open(os.path.join(out, "cambio.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=1)

    # indice de pares para la web
    idx_path = os.path.join(a.salida, "pares.json")
    idx = {"pares": []}
    if os.path.exists(idx_path):
        with open(idx_path, encoding="utf-8") as fh:
            idx = json.load(fh)
    idx["pares"] = [p for p in idx["pares"] if p["id"] != a.id] + [{
        "id": a.id, "titulo": resumen["titulo"], "antes": A.fecha, "despues": B.fecha,
        "simulado": resumen["simulado"], "ruta": f"{a.id}/cambio.json", "centro": resumen["centro"]}]
    with open(idx_path, "w", encoding="utf-8") as fh:
        json.dump(idx, fh, ensure_ascii=False, indent=1)
    print(f"OK -> {out}  ({len(zonas)} zonas)")


if __name__ == "__main__":
    main()
