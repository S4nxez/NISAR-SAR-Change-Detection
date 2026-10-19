"""
Utilidades comunes del procesado NISAR.

Formato "escena" (lo que produce nisar_escena.py, carpeta o .zip):
  resumen.json             metadatos, georreferencia UTM y estadisticas
  HHHH_fFF_cCC.npz         teselas: q (uint8), r0, c0
Cuantizacion de cada pixel: q = 0 sin dato; dB = (q - 1) * PASO + DB_MIN
"""
import io
import json
import math
import os
import zipfile

import numpy as np

DB_MIN = -40.0
PASO = 0.2


# ---------------------------------------------------------------- dB <-> q
def db_a_q(db):
    """dB (float, NaN = sin dato) -> uint8 cuantizado (0 = sin dato)."""
    db = np.asarray(db, dtype=np.float32)
    ok = np.isfinite(db)
    q = np.zeros(db.shape, np.uint8)
    q[ok] = np.clip(np.rint((db[ok] - DB_MIN) / PASO) + 1, 1, 255).astype(np.uint8)
    return q


def q_a_db(q):
    """uint8 cuantizado -> dB float32 (NaN donde q == 0)."""
    q = np.asarray(q)
    db = (q.astype(np.float32) - 1.0) * PASO + DB_MIN
    db[q == 0] = np.nan
    return db


def lineal_a_db(a):
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 10.0 * np.log10(np.asarray(a, dtype=np.float32))
    db[~np.isfinite(db)] = np.nan
    return db


# ---------------------------------------------------------------- filtros
def media_movil(a, k):
    """Media k x k (k impar) con suma acumulada; bordes con ventana recortada. a sin NaN."""
    r = k // 2
    p = np.pad(a.astype(np.float64), ((r + 1, r), (r + 1, r)), mode="constant")
    p[0, :] = 0
    p[:, 0] = 0
    s = p.cumsum(0).cumsum(1)
    return (s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k])


def filtrar_speckle(db, k=5):
    """Media en potencia lineal sobre ventana k x k ignorando NaN. Devuelve dB."""
    ok = np.isfinite(db)
    lin = np.where(ok, np.power(10.0, np.where(ok, db, 0) / 10.0), 0.0)
    suma = media_movil(lin, k)
    n = media_movil(ok.astype(np.float64), k)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 10.0 * np.log10(suma / n)
    out[~ok] = np.nan
    return out.astype(np.float32)


def reducir(a, f, modo="media"):
    """Reduce un array 2D por bloques f x f ignorando NaN (media o fraccion de True)."""
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    b = a[:h, :w].reshape(h // f, f, w // f, f)
    if a.dtype == bool:
        return b.mean(axis=(1, 3))
    with np.errstate(invalid="ignore"):
        cnt = np.isfinite(b).sum(axis=(1, 3))
        s = np.nansum(b, axis=(1, 3))
        return np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan).astype(np.float32)


# ---------------------------------------------------------------- UTM -> lat/lon (WGS84)
def utm_a_latlon(x, y, epsg):
    """Convierte coordenadas UTM (EPSG 326xx norte / 327xx sur) a (lat, lon) en grados."""
    zona = epsg % 100
    sur = 32700 < epsg < 32800
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    k0 = 0.9996
    x = x - 500000.0
    y = y - 10000000.0 if sur else y
    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
         + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
         + (151 * e1 ** 3 / 96) * math.sin(6 * mu))
    ep2 = e2 / (1 - e2)
    c1 = ep2 * math.cos(p) ** 2
    t1 = math.tan(p) ** 2
    n1 = a / math.sqrt(1 - e2 * math.sin(p) ** 2)
    r1 = a * (1 - e2) / (1 - e2 * math.sin(p) ** 2) ** 1.5
    d = x / (n1 * k0)
    lat = p - (n1 * math.tan(p) / r1) * (d * d / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * ep2) * d ** 4 / 24
                                         + (61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * ep2 - 3 * c1 * c1) * d ** 6 / 720)
    lon = (d - (1 + 2 * t1 + c1) * d ** 3 / 6
           + (5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * ep2 + 24 * t1 * t1) * d ** 5 / 120) / math.cos(p)
    return math.degrees(lat), (zona - 1) * 6 - 180 + 3 + math.degrees(lon)


# ---------------------------------------------------------------- escenas
class Escena:
    """Lee una escena (carpeta o .zip) generada por nisar_escena.py."""

    def __init__(self, ruta, banda="HHHH"):
        self.ruta = ruta
        self.banda = banda
        self._zip = zipfile.ZipFile(ruta) if ruta.lower().endswith(".zip") else None
        self.resumen = json.loads(self._leer("resumen.json"))
        g = self.resumen["geo"]
        self.alto, self.ancho = int(g["alto"]), int(g["ancho"])
        self.dx, self.dy = float(g["dx"]), float(g["dy"])
        # x0/y0 = esquina superior izquierda. Las escenas de analizar_nisar.py (v1) guardaban
        # el centro del primer pixel: se corrige medio pixel.
        medio = 0.0 if g.get("origen") == "esquina" else 0.5
        self.x0 = float(g["x0"]) - medio * self.dx
        self.y0 = float(g["y0"]) - medio * self.dy
        self.epsg = int(self.resumen.get("epsg", 32718))
        self.teselas = [t for t in self.resumen["teselas"]
                        if t.get("banda", "HHHH") == banda and t["validos"] > 0]

    def _leer(self, nombre):
        if self._zip:
            return self._zip.read(nombre)
        with open(os.path.join(self.ruta, nombre), "rb") as fh:
            return fh.read()

    @property
    def fecha(self):
        return str(self.resumen.get("zeroDopplerStartTime", ""))[:10]

    def mosaico_q(self):
        """Imagen completa cuantizada (uint8, alto x ancho). ~270 MB para una escena NISAR."""
        m = np.zeros((self.alto, self.ancho), np.uint8)
        for t in self.teselas:
            nombre = f"{self.banda}_f{t['fila']:02d}_c{t['col']:02d}.npz"
            d = np.load(io.BytesIO(self._leer(nombre)))
            q = d["q"]
            r0, c0 = int(d["r0"]), int(d["c0"])
            m[r0:r0 + q.shape[0], c0:c0 + q.shape[1]] = q
        return m

    def pixel_a_latlon(self, fila, col):
        x = self.x0 + (col + 0.5) * self.dx
        y = self.y0 + (fila + 0.5) * self.dy
        return utm_a_latlon(x, y, self.epsg)


def guardar_escena(carpeta, resumen, mosaico_q, tesela=2048, banda="HHHH", zip_final=True):
    """Escribe un mosaico cuantizado en formato escena (teselas + resumen.json)."""
    os.makedirs(carpeta, exist_ok=True)
    H, W = mosaico_q.shape
    teselas = []
    for ti in range(-(-H // tesela)):
        for tj in range(-(-W // tesela)):
            r0, c0 = ti * tesela, tj * tesela
            q = mosaico_q[r0:r0 + tesela, c0:c0 + tesela]
            n = int((q > 0).sum())
            teselas.append({"banda": banda, "fila": ti, "col": tj, "r0": r0, "c0": c0,
                            "alto": q.shape[0], "ancho": q.shape[1], "validos": n})
            if n:
                np.savez_compressed(os.path.join(carpeta, f"{banda}_f{ti:02d}_c{tj:02d}.npz"), q=q, r0=r0, c0=c0)
    resumen = dict(resumen)
    resumen["teselas"] = teselas
    resumen["tesela_px"] = tesela
    with open(os.path.join(carpeta, "resumen.json"), "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False)
    if zip_final:
        with zipfile.ZipFile(carpeta.rstrip("/\\") + ".zip", "w", zipfile.ZIP_STORED) as z:
            for fn in sorted(os.listdir(carpeta)):
                z.write(os.path.join(carpeta, fn), fn)
