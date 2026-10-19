#!/usr/bin/env python3
"""
simular_despues.py - Fabrica una escena "despues" SIMULADA a partir de una real, con cambios
conocidos, para probar el pipeline mientras no tengamos una segunda fecha real.

Cambios que mete (y guarda en simulacion.json para comprobar si se detectan):
  - un desplazamiento global de +0,8 dB y ruido independiente (como entre dos pasadas reales)
  - inundacion: bosque -> agua lisa (~ -22 dB)
  - tala: varias parcelas que bajan ~5 dB
  - lago que mengua: parte del agua pasa a tierra (~ -8 dB)
  - aumento: una zona que sube ~5 dB

Uso:
  python simular_despues.py ESCENA_ANTES --salida escenas/simulada_2026-10-17
Las posiciones por defecto son de la escena NISAR del 5 oct 2026 (track 83, frame 91);
con otra escena, pasa --auto para elegirlas automaticamente.
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy import ndimage as nd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nisar_comun import Escena, db_a_q, guardar_escena, q_a_db  # noqa: E402

# (fila, columna, radio_px) en la escena de referencia; tipo de cambio
CAMBIOS_REF = [
    ("inundacion", 7650, 9300, 160),
    ("tala", 12350, 9900, 90),
    ("tala", 12050, 10400, 70),
    ("tala", 12700, 9300, 60),
    ("lago_mengua", 4560, 5250, 120),
    ("aumento", 9000, 4500, 80),
]


def mancha(shape, cy, cx, r, rng):
    """Mascara irregular aproximadamente circular de radio r."""
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    base = ((yy - cy) ** 2 + (xx - cx) ** 2) <= r * r
    ruido = nd.gaussian_filter(rng.standard_normal(shape), r / 4)
    ruido /= ruido.std() + 1e-9
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / r
    return base & (ruido > (dist - 0.8) * 2.5)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("antes")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--fecha", default="2026-10-17")
    ap.add_argument("--auto", action="store_true", help="elegir posiciones automaticamente")
    ap.add_argument("--semilla", type=int, default=20261017)
    a = ap.parse_args()
    rng = np.random.default_rng(a.semilla)

    A = Escena(a.antes)
    q = A.mosaico_q()
    H, W = q.shape
    print(f"Escena antes {A.fecha}: {H} x {W}")
    ok = q > 0
    # ruido independiente (dB) + desplazamiento global, por franjas para no gastar memoria
    out = np.empty_like(q)
    for s in range(0, H, 1024):
        blk = q_a_db(q[s:s + 1024])
        out[s:s + 1024] = db_a_q(blk + 0.8 + rng.normal(0, 1.5, blk.shape).astype(np.float32))

    cambios = CAMBIOS_REF
    if a.auto:
        cambios = []
        tipos = ["inundacion", "tala", "tala", "aumento"]
        for t in tipos:
            while True:
                cy, cx = rng.integers(300, H - 300), rng.integers(300, W - 300)
                if ok[cy, cx] and ok[cy - 200:cy + 200, cx - 200:cx + 200].mean() > 0.99:
                    cambios.append((t, int(cy), int(cx), 100))
                    break

    verdad = []
    for tipo, cy, cx, r in cambios:
        y0, y1, x0, x1 = max(0, cy - r - 2), min(H, cy + r + 3), max(0, cx - r - 2), min(W, cx + r + 3)
        sub_shape = (y1 - y0, x1 - x0)
        m = mancha(sub_shape, cy - y0, cx - x0, r, rng) & (q[y0:y1, x0:x1] > 0)
        dbs = q_a_db(out[y0:y1, x0:x1])
        orig = q_a_db(q[y0:y1, x0:x1])
        if tipo == "inundacion":
            nuevo = rng.normal(-22, 1.5, sub_shape)
            m &= orig > -15                        # solo donde no era agua
        elif tipo == "tala":
            nuevo = dbs - 5.0
        elif tipo == "lago_mengua":
            m &= orig < -15                         # solo el agua
            nuevo = rng.normal(-8, 1.5, sub_shape)
        else:  # aumento
            nuevo = dbs + 5.0
        dbs[m] = nuevo[m]
        out[y0:y1, x0:x1] = db_a_q(dbs)
        lat, lon = A.pixel_a_latlon(cy, cx)
        verdad.append({"tipo": tipo, "fila": cy, "col": cx, "radio_px": r,
                       "area_km2": round(float(m.sum()) * abs(A.dx * A.dy) / 1e6, 2),
                       "lat": round(lat, 5), "lng": round(lon, 5)})
        print(f"  {tipo}: {verdad[-1]['area_km2']} km2 en {lat:.3f}, {lon:.3f}")

    resumen = dict(A.resumen)
    resumen.pop("teselas", None)
    resumen["zeroDopplerStartTime"] = a.fecha + "T23:23:38 (SIMULADO)"
    resumen["granuleId"] = "SIMULADO a partir de " + str(A.resumen.get("granuleId") or A.resumen.get("archivo"))
    resumen["simulado"] = True
    resumen["geo"] = {"x0": A.x0, "y0": A.y0, "dx": A.dx, "dy": A.dy, "ancho": W, "alto": H, "origen": "esquina"}
    resumen["epsg"] = A.epsg
    guardar_escena(a.salida, resumen, out)
    with open(os.path.join(a.salida, "simulacion.json"), "w", encoding="utf-8") as fh:
        json.dump({"semilla": a.semilla, "desplazamiento_dB": 0.8, "ruido_dB": 1.5, "cambios": verdad},
                  fh, ensure_ascii=False, indent=1)
    print(f"OK -> {a.salida}")


if __name__ == "__main__":
    main()
