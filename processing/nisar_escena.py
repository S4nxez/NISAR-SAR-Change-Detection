#!/usr/bin/env python3
"""
nisar_escena.py - Convierte un NISAR L2 GCOV (.h5) en una "escena" lista para el pipeline.

Lee la imagen ENTERA a resolucion completa (20 m) por franjas, pasa cada pixel a dB,
lo guarda cuantizado (uint8, paso 0,2 dB) en teselas comprimidas y calcula estadisticas.

Uso:
  python nisar_escena.py ARCHIVO.h5                      -> ARCHIVO_completo/ y ARCHIVO_completo.zip
  python nisar_escena.py ARCHIVO.h5 --salida escenas/    (carpeta de destino)
  python nisar_escena.py                                 (todos los .h5 de la carpeta actual)
"""
import argparse
import glob
import json
import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nisar_comun import DB_MIN, PASO, db_a_q, lineal_a_db  # noqa: E402

GRID = "science/LSAR/GCOV/grids/frequencyA"
IDENT = "science/LSAR/identification"
BANDAS = ["HHHH", "HVHV", "VVVV", "VHVH"]
BINS = np.arange(-60.0, 30.25, 0.25)
META = ("missionId", "productType", "trackNumber", "frameNumber", "orbitPassDirection",
        "lookDirection", "absoluteOrbitNumber", "zeroDopplerStartTime", "zeroDopplerEndTime",
        "granuleId", "boundingPolygon")


def _txt(v):
    v = v[()] if hasattr(v, "shape") else v
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if isinstance(v, np.ndarray):
        return [_txt(x) for x in v.tolist()]
    return v.item() if hasattr(v, "item") else v


def procesar_banda(ds, tesela, outdir, banda):
    """Recorre la banda por franjas de 'tesela' filas, guarda teselas y devuelve estadisticas."""
    H, W = ds.shape
    hist = np.zeros(len(BINS) - 1, np.int64)
    tabla = []
    for ti in range(-(-H // tesela)):
        r0, r1 = ti * tesela, min((ti + 1) * tesela, H)
        db = lineal_a_db(ds[r0:r1, :])
        q = db_a_q(db)
        v = db[np.isfinite(db)]
        hist += np.histogram(np.clip(v, BINS[0], BINS[-1] - 1e-3), bins=BINS)[0]
        for tj in range(-(-W // tesela)):
            c0, c1 = tj * tesela, min((tj + 1) * tesela, W)
            qq = q[:, c0:c1]
            n = int((qq > 0).sum())
            fila = {"banda": banda, "fila": ti, "col": tj, "r0": r0, "c0": c0,
                    "alto": r1 - r0, "ancho": c1 - c0, "validos": n}
            if n:
                x = db[:, c0:c1][qq > 0]
                fila.update(mediana_dB=round(float(np.median(x)), 2),
                            pct_agua_probable=round(100.0 * float((x < -20).mean()), 2))
                np.savez_compressed(os.path.join(outdir, f"{banda}_f{ti:02d}_c{tj:02d}.npz"),
                                    q=qq, r0=r0, c0=c0)
            tabla.append(fila)
        print(f"  {banda}: franja {ti + 1}/{-(-H // tesela)}", flush=True)
    tot = int(hist.sum())
    cum = np.cumsum(hist) / max(tot, 1)
    pct = {f"p{p}": round(float(BINS[np.searchsorted(cum, p / 100.0)]), 2) for p in (1, 5, 25, 50, 75, 95, 99)}
    stats = {"pixeles_validos": tot, "pixeles_totales": int(H * W),
             "pct_validos": round(100.0 * tot / (H * W), 2), "percentiles_dB": pct}
    return stats, tabla


def procesar(path, tesela=2048, salida=None):
    import h5py
    base = os.path.splitext(os.path.basename(path))[0]
    destino = salida or os.path.dirname(os.path.abspath(path))
    outdir = os.path.join(destino, base + "_completo")
    os.makedirs(outdir, exist_ok=True)
    resumen = {"archivo": os.path.basename(path), "tesela_px": tesela,
               "cuantizacion": {"dB_min": DB_MIN, "paso_dB": PASO,
                                "formula": "dB = (q-1)*paso + dB_min ; q=0 sin dato"},
               "bandas": {}, "teselas": []}
    with h5py.File(path, "r") as f:
        g = f[GRID]
        for k in META:
            if k in f[IDENT]:
                resumen[k] = _txt(f[IDENT][k])
        resumen["epsg"] = int(_txt(g["projection"])) if "projection" in g else None
        x, y = g["xCoordinates"][:], g["yCoordinates"][:]
        dx, dy = float(g["xCoordinateSpacing"][()]), float(g["yCoordinateSpacing"][()])
        # xCoordinates/yCoordinates son centros de pixel; guardamos la esquina superior izquierda
        resumen["geo"] = {"x0": float(x[0]) - dx / 2, "y0": float(y[0]) - dy / 2, "dx": dx, "dy": dy,
                          "ancho": int(len(x)), "alto": int(len(y)), "origen": "esquina"}
        for b in BANDAS:
            if b in g:
                print(f"\n{base}: banda {b} {g[b].shape}")
                stats, tabla = procesar_banda(g[b], tesela, outdir, b)
                resumen["bandas"][b] = stats
                resumen["teselas"] += tabla
    with open(os.path.join(outdir, "resumen.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False)
    zpath = outdir + ".zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
        for fn in sorted(os.listdir(outdir)):
            z.write(os.path.join(outdir, fn), fn)
    print(f"OK -> {outdir}  y  {zpath} ({os.path.getsize(zpath) / 1e6:.0f} MB)")
    return outdir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivos", nargs="*", help=".h5 de NISAR GCOV (por defecto, todos los de la carpeta)")
    ap.add_argument("--tesela", type=int, default=2048)
    ap.add_argument("--salida", default=None, help="carpeta de destino (por defecto, junto al .h5)")
    a = ap.parse_args()
    archivos = a.archivos or sorted(p for p in glob.glob("*.h5") if "QA_STATS" not in p)
    if not archivos:
        sys.exit("No hay archivos .h5.")
    for p in archivos:
        procesar(p, a.tesela, a.salida)


if __name__ == "__main__":
    main()
