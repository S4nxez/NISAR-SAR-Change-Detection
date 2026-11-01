#!/usr/bin/env python3
"""
nisar_cambio.py - Detecta cambios entre dos escenas NISAR (antes / despues) y genera
los ficheros que muestra la web (frontend/nisar.html y frontend/prueba.html).

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

Ademas calcula: histogramas de brillo de cada fecha, matriz de transicion entre
"coberturas radar" (agua / liso / vegetacion / muy brillante), balance de agua,
correlacion entre fechas, una rejilla de valores para consultar con el raton
(valores.bin.gz), un mapa de densidad de cambio y el contorno de cada zona.

Uso:
  python nisar_cambio.py ESCENA_ANTES ESCENA_DESPUES --id peru_oct2026 \
      --titulo "Amazonia peruana" --salida ../frontend/public/data/nisar
  (ESCENA_* = carpeta *_completo o su .zip, generados por nisar_escena.py)
"""
import argparse
import datetime as dt
import gzip
import json
import math
import os
import re
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as nd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nisar_comun import Escena, contornos, db_a_q, filtrar_speckle, q_a_db, reducir, utm_a_latlon  # noqa: E402

CLASES = {
    1: {"clave": "agua_nueva", "nombre": "Agua nueva", "color": "#3d8bff",
        "lectura": "Superficie que pasa a reflejar como agua lisa: posible inundación o crecida."},
    2: {"clave": "agua_desaparece", "nombre": "Agua que desaparece", "color": "#e4b65c",
        "lectura": "Superficie que deja de ser agua: retirada de una crecida o lago que mengua."},
    3: {"clave": "descenso", "nombre": "Descenso del eco", "color": "#e47759",
        "lectura": "Menos retrodispersión: posible tala, cosecha o suelo más seco."},
    4: {"clave": "aumento", "nombre": "Aumento del eco", "color": "#68b6a3",
        "lectura": "Más retrodispersión: vegetación que crece, estructuras o suelo más húmedo."},
}
# "Coberturas radar": lectura aproximada del brillo HH en banda L. No es un mapa de usos del suelo.
CORTE_LISO, CORTE_BRILLANTE = -9.0, -3.0
COBERTURAS = [
    {"clave": "agua", "nombre": "Agua lisa", "color": "#3d8bff",
     "lectura": "Muy oscuro: el radar rebota lejos como en un espejo. Ríos, lagos, zonas inundadas sin vegetación."},
    {"clave": "liso", "nombre": "Superficie lisa o vegetación baja", "color": "#c9a96e",
     "lectura": "Oscuro: suelo desnudo, pastos, cultivos bajos, arena o carreteras."},
    {"clave": "vegetacion", "nombre": "Vegetación densa", "color": "#4f9d69",
     "lectura": "Gris medio: bosque o cultivos altos; la banda L entra en la copa y rebota en las ramas."},
    {"clave": "brillante", "nombre": "Muy brillante", "color": "#f2f2f2",
     "lectura": "Muy claro: edificios, bosque inundado (doble rebote agua-tronco) o laderas de cara al radar."},
]
FRANJA = 1024
HALO = 4
MAX_ZONAS = 500


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


def cobertura(db, agua):
    """0 agua, 1 liso, 2 vegetacion, 3 muy brillante (NaN -> 3, filtrar con la mascara)."""
    return np.digitize(db, [agua, CORTE_LISO, CORTE_BRILLANTE]).astype(np.uint8)


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


def png_densidad(frac, ruta, tope=0.3):
    """Fraccion de pixeles con cambio por celda: transparente -> amarillo -> rojo."""
    ok = np.isfinite(frac) & (frac >= 0.02)
    t = np.clip(np.nan_to_num(frac) / tope, 0, 1)
    a, b = np.array(_rgb("#ffd166"), np.float32), np.array(_rgb("#ef476f"), np.float32)
    rgba = np.zeros(frac.shape + (4,), np.uint8)
    rgba[..., :3] = (a + (b - a) * t[..., None]).astype(np.uint8)
    rgba[..., 3] = np.where(ok, (70 + 175 * t).astype(np.uint8), 0)
    Image.fromarray(rgba, "RGBA").save(ruta, optimize=True)


def percentil_hist(conteos, bordes, p):
    c = np.cumsum(conteos)
    if c[-1] == 0:
        return float("nan")
    i = int(np.searchsorted(c, p * c[-1]))
    return float(bordes[min(i + 1, len(bordes) - 1)])


def es(v, d=1, signo=False):
    """Numero con formato espanol (1 234,5)."""
    t = f"{v:+,.{d}f}" if signo else f"{v:,.{d}f}"
    return t.replace(",", " ").replace(".", ",").replace("-", "−")


def plural(n, uno, varios):
    return f"{n} {uno if n == 1 else varios}"


def confianza(area_km2, cambio_abs, umbral):
    if area_km2 >= 0.5 and cambio_abs >= 2 * umbral:
        return "alta"
    if area_km2 >= 0.1 and cambio_abs >= 1.25 * umbral:
        return "media"
    return "baja"


def texto_resumen(r):
    """Parrafos en lenguaje llano a partir del resumen (los usan la web y el informe)."""
    e, p = r["estadisticas"], r["parametros"]
    pc = e["por_clase"]
    cambio_km2 = sum(v["km2"] for v in pc.values())
    cambio_pct = sum(v["pct"] for v in pc.values())
    dias = r["escena"].get("dias")
    orbita = {"Descending": "descendente", "Ascending": "ascendente"}.get(str(r.get("direccion")), str(r.get("direccion")).lower())
    t = []
    t.append(f"Entre el {r['antes']['fecha']} y el {r['despues']['fecha']}"
             + (f" ({plural(dias, 'día', 'días')})" if dias is not None else "")
             + f" se han comparado {es(e['area_valida_km2'], 0)} km² con datos válidos en las dos fechas"
             + (f" (pista {r['pista']}, frame {r['frame']}, órbita {orbita})" if r.get("pista") else "")
             + ", con el radar NISAR en banda L, polarización HH, a 20 m.")
    t.append(f"Antes de comparar se ha quitado un desplazamiento global de {es(p['desplazamiento_global_dB'], 2, True)} dB, "
             "que afecta a toda la escena por igual (humedad general o calibración). "
             f"Después, el {es(cambio_pct, 2)} % del área ({es(cambio_km2, 1)} km²) cambia más de ±{es(p['umbral_dB'], 1)} dB. "
             f"Agrupado, eso da {plural(e['zonas_total'], 'zona', 'zonas')} de al menos {es(p['area_min_km2'], 2)} km² "
             f"que suman {es(sum(e['zonas_km2_por_clase'].values()), 1)} km².")
    orden = sorted(pc.items(), key=lambda kv: -kv[1]["km2"])
    if orden and orden[0][1]["km2"] > 0:
        k, v = orden[0]
        t.append(f"La clase con más superficie es «{r['clases'][k]['nombre']}» ({es(v['km2'], 1)} km², "
                 f"{plural(e['zonas_por_clase'][k], 'zona', 'zonas')}). {r['clases'][k]['lectura']}")
    if r["zonas"]:
        z = r["zonas"][0]
        t.append(f"La zona más grande ({z['id']}) es de tipo «{z['nombre']}»: {es(z['area_km2'], 2)} km² con un cambio medio de "
                 f"{es(z['cambio_dB'], 1, True)} dB (de {es(z['dB_antes'], 1)} a {es(z['dB_despues'], 1)} dB), "
                 f"centrada en {z['lat']:.4f}, {z['lng']:.4f}. Confianza {z['confianza']}.")
    a = e["agua"]
    t.append(f"La superficie con aspecto de agua pasa de {es(a['antes_km2'], 1)} a {es(a['despues_km2'], 1)} km² "
             f"({es(a['despues_km2'] - a['antes_km2'], 1, True)} km²): {es(a['nueva_km2'], 1)} km² se vuelven agua y "
             f"{es(a['perdida_km2'], 1)} km² dejan de serlo.")
    rr = e["correlacion"]
    lect = ("muy parecidas: la mayor parte de la escena no cambia" if rr >= 0.85 else
            "bastante parecidas, con cambios repartidos" if rr >= 0.6 else
            "poco parecidas: hay mucho cambio o ruido entre fechas")
    t.append(f"La correlación entre las dos imágenes es {es(rr, 2)}, es decir, son {lect}.")
    if r.get("simulado"):
        t.append("AVISO: la segunda fecha de este par es simulada; los cambios se han inyectado a propósito para validar el método.")
    t.append("Un cambio de radar es una señal, no una prueba: conviene contrastarlo con imagen óptica o conocimiento del terreno.")
    return t


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
    ap.add_argument("--sin-indice", action="store_true", help="no anadir el par a pares.json")
    a = ap.parse_args()

    A, B = Escena(a.antes), Escena(a.despues)
    for E_ in (A, B):   # pista / frame / direccion desde el nombre del granulo si faltan en los metadatos
        m = re.search(r"GCOV_\d{3}_(\d{3})_([AD])_(\d{3})_", str(E_.resumen.get("granuleId") or E_.resumen.get("archivo") or ""))
        if m:
            E_.resumen.setdefault("trackNumber", int(m.group(1)))
            E_.resumen.setdefault("frameNumber", int(m.group(3)))
            E_.resumen.setdefault("orbitPassDirection", "Ascending" if m.group(2) == "A" else "Descending")
    (r0, r1, c0, c1), (orow, oc) = alinear(A, B)
    print(f"Antes {A.fecha}  Despues {B.fecha}  ventana comun filas {r0}-{r1} columnas {c0}-{c1}", flush=True)
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
    print(f"Desplazamiento global: {despl:+.2f} dB", flush=True)

    # ---- pasada 2: clases, reducciones y estadisticas
    # factor de reduccion de las imagenes: el lado mayor queda en ~2000-4000 px
    G = int(min(8, max(2, 2 ** np.ceil(np.log2(max(H, W) / 2500)))))   # fondos (160 m en una escena NISAR)
    F = max(2, G // 2)                                                    # capa de cambio y zonas (80 m)
    V = 2 * G                                                             # rejilla de consulta (320 m)
    Hr, Wr = H // F, W // F
    frac = np.zeros((5, Hr, Wr), np.float32)
    validr = np.zeros((Hr, Wr), np.float32)
    dmean = np.full((Hr, Wr), np.nan, np.float32)
    fa_r = np.full((Hr, Wr), np.nan, np.float32)
    fb_r = np.full((Hr, Wr), np.nan, np.float32)
    fa_g = np.full((H // G, W // G), np.nan, np.float32)
    fb_g = np.full((H // G, W // G), np.nan, np.float32)
    d_g = np.full((H // G, W // G), np.nan, np.float32)
    dh_bins = np.arange(-15, 15.01, 0.5)
    dh = np.zeros(len(dh_bins) - 1, np.int64)
    hb_bins = np.arange(-30, 5.01, 0.5)
    h_antes = np.zeros(len(hb_bins) - 1, np.int64)
    h_desp = np.zeros(len(hb_bins) - 1, np.int64)
    trans = np.zeros(16, np.int64)
    sx = sy = sxx = syy = sxy = sd = sdd = 0.0
    conteo = np.zeros(5, np.int64)
    paso = FRANJA // G * G
    for s in range(0, H // G * G, paso):
        e = min(H // G * G, s + paso)
        fa, fb, ok = preparar(qA, qB, s, e)
        cls, d = clasificar(fa, fb, ok, despl, a.umbral, a.agua)
        d[~ok] = np.nan
        conteo += np.bincount(cls[ok], minlength=5)
        x, y, dd = fa[ok].astype(np.float64), fb[ok].astype(np.float64), d[ok].astype(np.float64)
        sx, sy, sxx, syy, sxy = sx + x.sum(), sy + y.sum(), sxx + (x * x).sum(), syy + (y * y).sum(), sxy + (x * y).sum()
        sd, sdd = sd + dd.sum(), sdd + (dd * dd).sum()
        dh += np.histogram(np.clip(dd, -14.99, 14.99), dh_bins)[0]
        h_antes += np.histogram(np.clip(x, -29.99, 4.99), hb_bins)[0]
        h_desp += np.histogram(np.clip(y, -29.99, 4.99), hb_bins)[0]
        trans += np.bincount((cobertura(fa[ok], a.agua) * 4 + cobertura(fb[ok], a.agua)).astype(np.int64), minlength=16)
        sr = slice(s // F, e // F)
        validr[sr] = reducir(ok, F)[:, :Wr]
        for k in range(1, 5):
            frac[k, sr] = reducir(cls == k, F)[:, :Wr]
        dmean[sr] = reducir(d, F)[:, :Wr]
        fa_r[sr] = reducir(np.where(ok, fa, np.nan), F)[:, :Wr]
        fb_r[sr] = reducir(np.where(ok, fb, np.nan), F)[:, :Wr]
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
    lado_r_km = abs(A.dx) * F / 1000
    min_px = max(1, int(round(a.area_min / px_r_km2)))
    zonas = []
    limpio = np.zeros_like(cls_r)
    print("Agrupando zonas...", flush=True)
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
            za, zb, zd = fa_r[sl][m], fb_r[sl][m], dmean[sl][m]
            fa_ok, fb_ok = za[np.isfinite(za)], zb[np.isfinite(zb)]
            mp = np.pad(m, 1)
            centro = mp[1:-1, 1:-1]
            bordes = int((centro & ~mp[:-2, 1:-1]).sum() + (centro & ~mp[2:, 1:-1]).sum()
                         + (centro & ~mp[1:-1, :-2]).sum() + (centro & ~mp[1:-1, 2:]).sum())
            with np.errstate(invalid="ignore"):
                zonas.append({
                    "clase": k, "px": int(tam[i]), "cy": cy, "cx": cx, "_sl": sl, "_m": m,
                    "bbox": [sl[0].start * F, sl[0].stop * F, sl[1].start * F, sl[1].stop * F],
                    "d_media": float(np.nanmean(zd)),
                    "d_ext": float(np.nanmin(zd) if k in (1, 3) else np.nanmax(zd)),
                    "a_media": float(np.mean(fa_ok)) if fa_ok.size else float("nan"),
                    "b_media": float(np.mean(fb_ok)) if fb_ok.size else float("nan"),
                    "agua_a": float(np.mean(fa_ok < a.agua)) if fa_ok.size else 0.0,
                    "agua_b": float(np.mean(fb_ok < a.agua)) if fb_ok.size else 0.0,
                    "cob_a": int(np.bincount(cobertura(fa_ok, a.agua), minlength=4).argmax()) if fa_ok.size else 0,
                    "cob_b": int(np.bincount(cobertura(fb_ok, a.agua), minlength=4).argmax()) if fb_ok.size else 0,
                    "perimetro_km": bordes * lado_r_km})
    zonas.sort(key=lambda z: -z["px"])

    def ll(fila, col):   # pixel de la ventana comun -> lat, lon
        x = A.x0 + (c0 + col) * A.dx
        y = A.y0 + (r0 + fila) * A.dy
        return utm_a_latlon(x, y, A.epsg)

    os.makedirs(os.path.join(a.salida, a.id, "zonas"), exist_ok=True)
    out = os.path.join(a.salida, a.id)
    print("Escribiendo imagenes...", flush=True)
    # escala de grises comun a las dos fechas, ajustada a la escena (percentiles 2-98 de "antes")
    vmin, vmax = (float(v) for v in np.nanpercentile(fa_g, [2, 98]))
    escala = {"vmin": round(vmin, 1), "vmax": round(vmax, 1)}
    png_gris(fa_g, os.path.join(out, "antes.webp"), **escala)
    png_gris(fb_g, os.path.join(out, "despues.webp"), **escala)
    png_clases(limpio, os.path.join(out, "cambio.png"))
    png_diferencia(d_g, os.path.join(out, "diferencia.webp"))

    # ---- rejilla de consulta (V) y densidad de cambio
    rv = V // F
    Hv, Wv = Hr // rv, Wr // rv
    with np.errstate(invalid="ignore", divide="ignore"):
        valido_v = reducir(validr, rv)[:Hv, :Wv]
        fr_cls = np.stack([reducir(frac[k], rv)[:Hv, :Wv] for k in range(1, 5)])
        fr_cls = fr_cls / np.where(valido_v > 0, valido_v, np.nan)
        chg_v = np.nansum(fr_cls, axis=0)
    hay = valido_v > 0
    chg_v[~hay] = np.nan
    cls_v = (np.nan_to_num(fr_cls, nan=-1).argmax(axis=0) + 1).astype(np.uint8)
    cls_v[~(hay & (np.nan_to_num(chg_v) > 0))] = 0
    fa_v = reducir(fa_g, 2)[:Hv, :Wv]
    fb_v = reducir(fb_g, 2)[:Hv, :Wv]
    d_v = reducir(d_g, 2)[:Hv, :Wv]
    dq = np.where(np.isfinite(d_v), np.clip(np.rint(np.nan_to_num(d_v) * 10), -127, 127), -128).astype(np.int8)
    cq = np.where(np.isfinite(chg_v), np.clip(np.rint(np.nan_to_num(chg_v) * 250), 0, 250), 255).astype(np.uint8)
    capas = [db_a_q(fa_v), db_a_q(fb_v), dq.view(np.uint8), cq, cls_v]
    with gzip.open(os.path.join(out, "valores.bin.gz"), "wb", compresslevel=6) as fh:
        for c in capas:
            fh.write(np.ascontiguousarray(c).tobytes())
    png_densidad(chg_v, os.path.join(out, "densidad.png"))

    # ---- lista de zonas (recortes a 20 m de las mayores, contorno de las MAX_ZONAS primeras)
    print("Recortes y contornos de zonas...", flush=True)
    lista = []
    R = 256  # medio lado del recorte (512 px = 10,2 km)
    for j, z in enumerate(zonas[:MAX_ZONAS]):
        lat, lon = ll(z["cy"], z["cx"])
        s_, n_ = ll(z["bbox"][1], z["bbox"][2]), ll(z["bbox"][0], z["bbox"][3])
        area = z["px"] * px_r_km2
        per = z["perimetro_km"]
        item = {"id": f"z{j + 1:03d}", "clase": CLASES[z["clase"]]["clave"],
                "nombre": CLASES[z["clase"]]["nombre"], "lat": round(lat, 5), "lng": round(lon, 5),
                "area_km2": round(area, 3), "cambio_dB": round(z["d_media"], 2),
                "cambio_max_dB": round(z["d_ext"], 2),
                "dB_antes": round(z["a_media"], 2), "dB_despues": round(z["b_media"], 2),
                "pct_agua_antes": round(100 * z["agua_a"], 1), "pct_agua_despues": round(100 * z["agua_b"], 1),
                "cobertura_antes": COBERTURAS[z["cob_a"]]["clave"], "cobertura_despues": COBERTURAS[z["cob_b"]]["clave"],
                "perimetro_km": round(per, 2),
                "compacidad": round(min(1.0, 4 * math.pi * area / per ** 2), 3) if per > 0 else None,
                "confianza": confianza(area, abs(z["d_media"]), a.umbral),
                "bounds": [[round(min(s_[0], n_[0]), 5), round(min(s_[1], n_[1]), 5)],
                           [round(max(s_[0], n_[0]), 5), round(max(s_[1], n_[1]), 5)]]}
        # contorno real de la zona (bordes de los bloques de 80 m, simplificado): [[exterior, huecos...], ...]
        m, sl = z["_m"], z["_sl"]
        item["contorno"] = [[[[round(v, 5) for v in ll((sl[0].start + p[0]) * F, (sl[1].start + p[1]) * F)] for p in anillo]
                             for anillo in poli] for poli in contornos(m, eps=0.6, max_vertices=600)]
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
    n = float(n_ok)
    var_x, var_y = sxx / n - (sx / n) ** 2, syy / n - (sy / n) ** 2
    corr = (sxy / n - sx / n * sy / n) / math.sqrt(max(1e-12, var_x * var_y))
    # |cambio| con la resolucion fina de la pasada 1 (0,05 dB), ya sin el desplazamiento global
    centros = np.abs(bins[:-1] + 0.025 - despl)
    orden_abs = np.argsort(centros)
    abs_h, abs_bins = hist[orden_abs], np.concatenate([[0.0], centros[orden_abs]])
    t_km2 = (trans * px_km2).reshape(4, 4)
    try:
        dias = (dt.date.fromisoformat(B.fecha) - dt.date.fromisoformat(A.fecha)).days
    except ValueError:
        dias = None
    resumen = {
        "id": a.id,
        "titulo": a.titulo or a.id,
        "simulado": bool(a.simulado),
        "nota": a.nota,
        "generado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sensor": "NISAR L-SAR (banda L), producto L2 GCOV, polarización HH",
        "antes": {"fecha": A.fecha, "granulo": A.resumen.get("granuleId") or A.resumen.get("archivo"),
                  "inicio": str(A.resumen.get("zeroDopplerStartTime", ""))},
        "despues": {"fecha": B.fecha, "granulo": B.resumen.get("granuleId") or B.resumen.get("archivo"),
                    "inicio": str(B.resumen.get("zeroDopplerStartTime", ""))},
        "pista": A.resumen.get("trackNumber"), "frame": A.resumen.get("frameNumber"),
        "direccion": A.resumen.get("orbitPassDirection"),
        "escena": {"dias": dias, "mirada": A.resumen.get("lookDirection"),
                   "polarizaciones_antes": sorted(A.resumen.get("bandas", {}).keys()),
                   "polarizaciones_despues": sorted(B.resumen.get("bandas", {}).keys()),
                   "pixel_m": abs(A.dx), "epsg": A.epsg, "filas": H, "columnas": W,
                   "area_ventana_km2": round(H * W * px_km2, 1)},
        "bounds": [[round(min(lats), 5), round(min(lons), 5)], [round(max(lats), 5), round(max(lons), 5)]],
        "centro": [round(float(np.mean(lats)), 4), round(float(np.mean(lons)), 4)],
        "imagenes": {"antes": "antes.webp", "despues": "despues.webp", "cambio": "cambio.png",
                     "diferencia": "diferencia.webp", "densidad": "densidad.png",
                     "resolucion_m": {"fondo": abs(A.dx) * G, "cambio": abs(A.dx) * F, "densidad": abs(A.dx) * V},
                     "escala_gris_dB": escala},
        "valores": {"archivo": "valores.bin.gz", "filas": Hv, "columnas": Wv, "factor": V,
                    "filas_ventana": H, "columnas_ventana": W, "resolucion_m": abs(A.dx) * V,
                    "capas": ["q_antes", "q_despues", "cambio_dB_x10_int8", "frac_cambio_x250", "clase"],
                    "codificacion": "q: dB = (q-1)*0.2 - 40, 0 = sin dato; cambio int8 -128 = sin dato; frac 255 = sin dato"},
        "parametros": {"umbral_dB": a.umbral, "agua_dB": a.agua, "filtro_px": 5, "area_min_km2": a.area_min,
                       "desplazamiento_global_dB": round(despl, 2),
                       "cortes_cobertura_dB": [a.agua, CORTE_LISO, CORTE_BRILLANTE]},
        "estadisticas": {
            "area_valida_km2": round(area_valida, 1),
            "por_clase": {CLASES[k]["clave"]: {"km2": round(float(conteo[k]) * px_km2, 2),
                                               "pct": round(100.0 * float(conteo[k]) / n_ok, 3)} for k in CLASES},
            "estable_pct": round(100.0 * float(conteo[0]) / n_ok, 3),
            "zonas_total": len(zonas),
            "zonas_por_clase": {CLASES[k]["clave"]: sum(1 for z in zonas if z["clase"] == k) for k in CLASES},
            "zonas_km2_por_clase": {CLASES[k]["clave"]: round(sum(z["px"] for z in zonas if z["clase"] == k) * px_r_km2, 2)
                                    for k in CLASES},
            "histograma_cambio": {"bordes_dB": [float(dh_bins[0]), float(dh_bins[-1]), 0.5], "conteos": dh.tolist()},
            "histograma_antes": {"bordes_dB": [float(hb_bins[0]), float(hb_bins[-1]), 0.5], "conteos": h_antes.tolist()},
            "histograma_despues": {"bordes_dB": [float(hb_bins[0]), float(hb_bins[-1]), 0.5], "conteos": h_desp.tolist()},
            "brillo": {"media_antes_dB": round(sx / n, 2), "media_despues_dB": round(sy / n, 2),
                       "desviacion_antes_dB": round(math.sqrt(max(0.0, var_x)), 2),
                       "desviacion_despues_dB": round(math.sqrt(max(0.0, var_y)), 2),
                       "mediana_antes_dB": round(percentil_hist(h_antes, hb_bins, 0.5), 2),
                       "mediana_despues_dB": round(percentil_hist(h_desp, hb_bins, 0.5), 2)},
            "cambio": {"media_dB": round(sd / n, 3), "desviacion_dB": round(math.sqrt(max(0.0, sdd / n - (sd / n) ** 2)), 3),
                       "p50_abs_dB": round(percentil_hist(abs_h, abs_bins, 0.5), 2),
                       "p90_abs_dB": round(percentil_hist(abs_h, abs_bins, 0.9), 2),
                       "p99_abs_dB": round(percentil_hist(abs_h, abs_bins, 0.99), 2)},
            "correlacion": round(float(corr), 4),
            "coberturas": {"orden": [c["clave"] for c in COBERTURAS],
                           "matriz_km2": [[round(float(v), 2) for v in fila] for fila in t_km2],
                           "antes_km2": [round(float(v), 2) for v in t_km2.sum(1)],
                           "despues_km2": [round(float(v), 2) for v in t_km2.sum(0)]},
            "agua": {"antes_km2": round(float(t_km2[0].sum()), 2), "despues_km2": round(float(t_km2[:, 0].sum()), 2),
                     "estable_km2": round(float(t_km2[0, 0]), 2),
                     "nueva_km2": round(float(t_km2[1:, 0].sum()), 2), "perdida_km2": round(float(t_km2[0, 1:].sum()), 2)},
        },
        "clases": {CLASES[k]["clave"]: {"nombre": c["nombre"], "color": c["color"], "lectura": c["lectura"]}
                   for k, c in CLASES.items()},
        "coberturas": {c["clave"]: {"nombre": c["nombre"], "color": c["color"], "lectura": c["lectura"]} for c in COBERTURAS},
        "zonas": lista,
    }
    resumen["resumen_texto"] = texto_resumen(resumen)
    with open(os.path.join(out, "cambio.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, separators=(",", ":"))

    if not a.sin_indice:
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
    print(f"OK -> {out}  ({len(zonas)} zonas)", flush=True)


if __name__ == "__main__":
    main()
