#!/usr/bin/env python3
"""
servidor.py - Servicio de procesado NISAR y web de pruebas.

Sirve la carpeta frontend/ y una API pequena que recibe las dos pasadas (antes y despues),
lanza el pipeline de esta carpeta (nisar_escena.py -> nisar_cambio.py -> nisar_informe.py)
y publica el resultado en /trabajos/<id>/.

Uso (desde la raiz del repo):
  python processing/servidor.py                 -> http://localhost:8001/prueba.html
  python processing/servidor.py --puerto 9000 --datos D:/nisar_trabajos

Solo usa la biblioteca estandar de Python mas las dependencias del pipeline
(processing/requirements.txt). Por defecto escucha solo en 127.0.0.1.

API
  GET  /api/nisar/estado                    estado del servicio
  POST /api/nisar/subidas?nombre=F.h5       cuerpo = el fichero (.h5 GCOV o escena .zip)
                                            (con clave: cabecera X-Nisar-Clave en todos los POST)
  GET  /api/nisar/subidas/<id>
  POST /api/nisar/trabajos                  JSON {antes, despues, titulo?, umbral?, agua?, area_min?}
  GET  /api/nisar/trabajos                  lista de trabajos (mas recientes primero)
  GET  /api/nisar/trabajos/<id>             estado y progreso de un trabajo
"""
import argparse
import datetime as dt
import hmac
import http.server
import json
import os
import posixpath
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
FRONT = os.path.join(RAIZ, "frontend")
sys.path.insert(0, AQUI)

PATRON = re.compile(r"NISAR_L2_\w{2}_GCOV_(?P<ciclo>\d{3})_(?P<pista>\d{3})_(?P<dir>[AD])_(?P<frame>\d{3})_"
                    r"(?P<modo>\w{4})_(?P<pol>[A-Z]{4})_\w_(?P<inicio>\d{8}T\d{6})")
FIRMA_H5 = b"\x89HDF\r\n\x1a\n"
TROZO = 8 * 1024 * 1024


def ahora():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def leer_json(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return defecto


def escribir_json(ruta, datos):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


# ---------------------------------------------------------------- metadatos
def meta_de_nombre(nombre):
    m = PATRON.search(nombre)
    if not m:
        return {}
    i = m.group("inicio")
    return {"fecha": f"{i[:4]}-{i[4:6]}-{i[6:8]}", "pista": int(m.group("pista")), "frame": int(m.group("frame")),
            "direccion": "Ascending" if m.group("dir") == "A" else "Descending", "ciclo": int(m.group("ciclo")),
            "polarizacion": m.group("pol"), "fuente": "nombre"}


def meta_de_resumen(res):
    return {"fecha": str(res.get("zeroDopplerStartTime", ""))[:10] or None, "pista": res.get("trackNumber"),
            "frame": res.get("frameNumber"), "direccion": res.get("orbitPassDirection"),
            "polarizaciones": sorted(res.get("bandas", {}).keys()), "granulo": res.get("granuleId") or res.get("archivo"),
            "ancho": res.get("geo", {}).get("ancho"), "alto": res.get("geo", {}).get("alto"),
            "epsg": res.get("epsg"), "fuente": "resumen"}


def meta_de_h5(ruta):
    try:
        import h5py
    except ImportError:
        return {}
    try:
        with h5py.File(ruta, "r") as f:
            ident = f["science/LSAR/identification"]

            def txt(k):
                if k not in ident:
                    return None
                v = ident[k][()]
                if isinstance(v, bytes):
                    return v.decode("utf-8", "replace")
                return v.item() if hasattr(v, "item") else v
            grid = f["science/LSAR/GCOV/grids/frequencyA"]
            pols = [b for b in ("HHHH", "HVHV", "VVVV", "VHVH") if b in grid]
            return {"fecha": (txt("zeroDopplerStartTime") or "")[:10] or None, "pista": txt("trackNumber"),
                    "frame": txt("frameNumber"), "direccion": txt("orbitPassDirection"),
                    "polarizaciones": pols, "granulo": txt("granuleId"), "fuente": "h5"}
    except Exception as exc:  # noqa: BLE001
        return {"error_lectura": str(exc)}


def normalizar_escena(ruta, destino):
    """Devuelve una ruta que Escena() puede abrir: zip con resumen.json en la raiz, o carpeta."""
    with zipfile.ZipFile(ruta) as z:
        nombres = z.namelist()
        if "resumen.json" in nombres:
            return ruta, json.loads(z.read("resumen.json"))
        anidados = [n for n in nombres if n.lower().endswith(".zip")]
        resumenes = [n for n in nombres if n.endswith("/resumen.json")]
        if len(resumenes) == 1:
            pref = resumenes[0][:-len("resumen.json")]
            carpeta = os.path.join(destino, os.path.basename(pref.rstrip("/")) or "escena")
            os.makedirs(carpeta, exist_ok=True)
            for n in nombres:
                if n.startswith(pref) and not n.endswith("/"):
                    with z.open(n) as src, open(os.path.join(carpeta, os.path.basename(n)), "wb") as dst:
                        shutil.copyfileobj(src, dst, TROZO)
            return carpeta, leer_json(os.path.join(carpeta, "resumen.json"), {})
        if len(anidados) == 1:
            salida = os.path.join(destino, os.path.basename(anidados[0]))
            with z.open(anidados[0]) as src, open(salida, "wb") as dst:
                shutil.copyfileobj(src, dst, TROZO)
            return normalizar_escena(salida, destino)
    raise ValueError("El .zip no contiene una escena (falta resumen.json). Genera la escena con nisar_escena.py "
                     "o sube directamente el .h5.")


# ---------------------------------------------------------------- servicio
class Servicio:
    def __init__(self, datos, conservar_h5=False):
        self.datos = os.path.abspath(datos)
        self.subidas = os.path.join(self.datos, "_subidas")
        self.escenas = os.path.join(self.datos, "_escenas")
        for d in (self.datos, self.subidas, self.escenas):
            os.makedirs(d, exist_ok=True)
        self.conservar_h5 = conservar_h5
        self.cerrojo = threading.Lock()
        self.cola = queue.Queue()
        self.actual = None
        try:
            import h5py  # noqa: F401
            self.h5py = True
        except ImportError:
            self.h5py = False
        # trabajos que quedaron a medias en una ejecucion anterior
        for t in self.listar():
            if t["estado"] in ("en_cola", "procesando"):
                t.update(estado="error", mensaje="El servidor se detuvo durante el procesado. Vuelve a lanzarlo.")
                self.guardar(t)
        threading.Thread(target=self._bucle, daemon=True).start()

    # -------- subidas
    def ruta_subida(self, sid):
        if not re.fullmatch(r"[a-z0-9-]{6,40}", sid or ""):
            raise KeyError(sid)
        return os.path.join(self.subidas, sid + ".json")

    def subida(self, sid):
        s = leer_json(self.ruta_subida(sid))
        if not s:
            raise KeyError(sid)
        return s

    def recibir(self, nombre, flujo, longitud):
        nombre = os.path.basename(nombre.replace("\\", "/"))[:200] or "fichero"
        ext = os.path.splitext(nombre)[1].lower()
        if ext not in (".h5", ".zip"):
            raise ValueError("Solo se aceptan .h5 (NISAR GCOV) o .zip (escena de nisar_escena.py).")
        libre = shutil.disk_usage(self.subidas).free
        if longitud > libre - 512 * 1024 * 1024:
            raise ValueError(f"No hay espacio en disco: el fichero ocupa {longitud / 1e9:.2f} GB y quedan {libre / 1e9:.2f} GB.")
        sid = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        ruta = os.path.join(self.subidas, sid + ext)
        restante = longitud
        with open(ruta, "wb") as fh:
            primero = True
            while restante > 0:
                trozo = flujo.read(min(TROZO, restante))
                if not trozo:
                    break
                if primero:
                    primero = False
                    if ext == ".h5" and not trozo.startswith(FIRMA_H5):
                        fh.close()
                        os.remove(ruta)
                        raise ValueError("El fichero no es un HDF5 (.h5) válido.")
                    if ext == ".zip" and not trozo.startswith(b"PK"):
                        fh.close()
                        os.remove(ruta)
                        raise ValueError("El fichero no es un .zip válido.")
                fh.write(trozo)
                restante -= len(trozo)
        if restante:
            os.remove(ruta)
            raise ValueError("La subida se cortó antes de terminar.")
        reg = {"id": sid, "nombre": nombre, "tipo": "h5" if ext == ".h5" else "escena", "bytes": longitud,
               "subido": ahora(), "ruta": ruta, "escena": None, "avisos": []}
        meta = meta_de_nombre(nombre)
        if ext == ".zip":
            try:
                ruta_esc, res = normalizar_escena(ruta, os.path.join(self.escenas, sid))
            except (ValueError, zipfile.BadZipFile) as exc:
                os.remove(ruta)
                raise ValueError(str(exc)) from exc
            reg["escena"] = ruta_esc
            meta = {**meta, **{k: v for k, v in meta_de_resumen(res).items() if v not in (None, [])}}
            if not meta_de_nombre(nombre) and res.get("archivo"):
                meta = {**meta_de_nombre(res["archivo"]), **meta}
        else:
            mh = meta_de_h5(ruta)
            if "error_lectura" in mh:
                reg["avisos"].append("No se pudieron leer los metadatos del .h5: " + mh["error_lectura"])
            meta = {**meta, **{k: v for k, v in mh.items() if v not in (None, []) and k != "error_lectura"}}
            if not self.h5py:
                reg["avisos"].append("Falta h5py en el servidor: instala processing/requirements.txt para convertir .h5.")
        if not meta.get("fecha"):
            reg["avisos"].append("No se ha podido leer la fecha de la pasada.")
        reg["meta"] = meta
        escribir_json(self.ruta_subida(sid), reg)
        return reg

    # -------- trabajos
    def ruta_trabajo(self, tid):
        if not re.fullmatch(r"[a-z0-9-]{6,40}", tid or ""):
            raise KeyError(tid)
        return os.path.join(self.datos, tid, "trabajo.json")

    def trabajo(self, tid):
        t = leer_json(self.ruta_trabajo(tid))
        if not t:
            raise KeyError(tid)
        return t

    def guardar(self, t):
        os.makedirs(os.path.join(self.datos, t["id"]), exist_ok=True)
        escribir_json(self.ruta_trabajo(t["id"]), t)

    def listar(self):
        out = []
        for d in os.listdir(self.datos):
            if d.startswith("_"):
                continue
            t = leer_json(os.path.join(self.datos, d, "trabajo.json"))
            if t:
                out.append(t)
        return sorted(out, key=lambda t: t["creado"], reverse=True)

    def crear(self, cuerpo):
        A, B = self.subida(cuerpo.get("antes")), self.subida(cuerpo.get("despues"))
        if A["id"] == B["id"]:
            raise ValueError("Antes y después son el mismo fichero.")
        ma, mb = A.get("meta", {}), B.get("meta", {})
        for k, nombre in (("pista", "pista"), ("frame", "frame"), ("direccion", "dirección de órbita")):
            if ma.get(k) is not None and mb.get(k) is not None and str(ma[k]) != str(mb[k]):
                raise ValueError(f"Las dos pasadas no comparten {nombre} ({ma[k]} frente a {mb[k]}): "
                                 "no se pueden comparar píxel a píxel.")
        if ma.get("fecha") and mb.get("fecha") and ma["fecha"] >= mb["fecha"]:
            raise ValueError(f"La fecha de «antes» ({ma['fecha']}) no es anterior a la de «después» ({mb['fecha']}).")

        def num(k, defecto, lo, hi):
            try:
                v = float(cuerpo.get(k, defecto))
            except (TypeError, ValueError):
                v = defecto
            return min(hi, max(lo, v))
        tid = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
        titulo = str(cuerpo.get("titulo") or "").strip()[:120] or (
            f"{ma.get('fecha', '?')} → {mb.get('fecha', '?')}"
            + (f" · pista {ma['pista']}, frame {ma['frame']}" if ma.get("pista") is not None else ""))
        pasos = [("escena_antes", "Preparar pasada de antes"), ("escena_despues", "Preparar pasada de después"),
                 ("comparar", "Comparar y clasificar cambios"), ("informe", "Generar informes")]
        t = {"id": tid, "titulo": titulo, "estado": "en_cola", "creado": ahora(), "terminado": None,
             "mensaje": "En cola", "progreso": 0.0,
             "parametros": {"umbral": num("umbral", 3.0, 0.5, 15), "agua": num("agua", -15.0, -30, -5),
                            "area_min": num("area_min", 0.05, 0.0, 50)},
             "antes": {"subida": A["id"], "nombre": A["nombre"], "meta": ma},
             "despues": {"subida": B["id"], "nombre": B["nombre"], "meta": mb},
             "pasos": [{"clave": k, "nombre": n, "estado": "pendiente", "progreso": 0.0} for k, n in pasos],
             "registro": [], "resultado": None}
        self.guardar(t)
        self.cola.put(tid)
        return t

    def _bucle(self):
        while True:
            tid = self.cola.get()
            try:
                self._ejecutar(self.trabajo(tid))
            except Exception:  # noqa: BLE001
                traceback.print_exc()

    def _paso(self, t, clave, **kw):
        for p in t["pasos"]:
            if p["clave"] == clave:
                p.update(kw)
        # peso de cada paso; los omitidos (escena ya convertida) no cuentan
        pesos = {"escena_antes": .3, "escena_despues": .3, "comparar": .35, "informe": .05}
        activos = [p for p in t["pasos"] if p["estado"] != "omitido"]
        total = sum(pesos[p["clave"]] for p in activos) or 1.0
        t["progreso"] = round(sum(pesos[p["clave"]] * (1.0 if p["estado"] == "hecho" else p["progreso"])
                                  for p in activos) / total, 4)
        self.guardar(t)

    def _log(self, t, linea):
        t["registro"] = (t["registro"] + [linea.rstrip()])[-60:]

    def _proceso(self, t, clave, args, progreso):
        """Ejecuta un script del pipeline y traduce su salida a progreso."""
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.Popen([sys.executable, "-u"] + args, cwd=AQUI, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace", env=env)
        ultimo = 0.0
        for linea in p.stdout:
            self._log(t, linea)
            v = progreso(linea)
            if v is not None:
                for q in t["pasos"]:
                    if q["clave"] == clave:
                        q["progreso"] = max(q["progreso"], min(1.0, v))
            if time.time() - ultimo > 0.7:
                ultimo = time.time()
                self._paso(t, clave)
        p.wait()
        self._paso(t, clave)
        if p.returncode != 0:
            ultimas = [x for x in t["registro"][-6:] if x.strip()]
            raise RuntimeError(ultimas[-1] if ultimas else f"El proceso terminó con código {p.returncode}")

    def _escena(self, t, clave, sid):
        s = self.subida(sid)
        if s.get("escena") and os.path.exists(s["escena"]):
            self._paso(t, clave, estado="omitido", progreso=1.0, detalle="ya era una escena")
            return s["escena"]
        if s["tipo"] != "h5":
            raise RuntimeError(f"La subida {s['nombre']} no es una escena válida.")
        if not self.h5py:
            raise RuntimeError("Falta h5py en el servidor: python -m pip install -r processing/requirements.txt")
        destino = os.path.join(self.escenas, sid)
        os.makedirs(destino, exist_ok=True)
        enlace = os.path.join(destino, os.path.splitext(s["nombre"])[0] + ".h5")
        if not os.path.exists(enlace):
            try:
                os.link(s["ruta"], enlace)
            except OSError:
                shutil.move(s["ruta"], enlace)
                s["ruta"] = enlace
        self._paso(t, clave, estado="procesando", detalle="convirtiendo el .h5 (lectura completa a 20 m)")
        nb = {"n": 1}

        def prog(linea):
            m = re.search(r"banda (\w{4})", linea)
            if m:
                nb["n"] = max(nb["n"], 1)
            m = re.search(r"franja (\d+)/(\d+)", linea)
            if m:
                return int(m.group(1)) / int(m.group(2))
            return None
        self._proceso(t, clave, ["nisar_escena.py", enlace, "--salida", destino], prog)
        base = os.path.splitext(os.path.basename(enlace))[0] + "_completo"
        zpath = os.path.join(destino, base + ".zip")
        if not os.path.exists(zpath):
            raise RuntimeError("nisar_escena.py no generó la escena.")
        shutil.rmtree(os.path.join(destino, base), ignore_errors=True)
        for r in {enlace, s["ruta"]}:
            if not self.conservar_h5 and os.path.exists(r):
                os.remove(r)
        s["escena"] = zpath
        escribir_json(self.ruta_subida(sid), s)
        self._paso(t, clave, estado="hecho", progreso=1.0)
        return zpath

    def _ejecutar(self, t):
        self.actual = t["id"]
        t.update(estado="procesando", mensaje="Procesando", inicio=ahora())
        self.guardar(t)
        try:
            ea = self._escena(t, "escena_antes", t["antes"]["subida"])
            eb = self._escena(t, "escena_despues", t["despues"]["subida"])
            self._paso(t, "comparar", estado="procesando")

            def prog(linea):
                m = re.search(r"pasada (\d) *: *(\d+)/(\d+)", linea)
                if m:
                    f = int(m.group(2)) / int(m.group(3))
                    return 0.05 + (0.35 * f if m.group(1) == "1" else 0.35 + 0.4 * f)
                for clave, v in (("ventana comun", .03), ("Agrupando", .8), ("Escribiendo", .85),
                                 ("Recortes", .9), ("OK ->", 1.0)):
                    if clave in linea:
                        return v
                return None
            par = t["parametros"]
            self._proceso(t, "comparar", ["nisar_cambio.py", ea, eb, "--id", t["id"], "--titulo", t["titulo"],
                                          "--salida", self.datos, "--sin-indice", "--umbral", str(par["umbral"]),
                                          "--agua", str(par["agua"]), "--area-min", str(par["area_min"])], prog)
            self._paso(t, "comparar", estado="hecho", progreso=1.0)
            self._paso(t, "informe", estado="procesando")
            import nisar_informe
            nisar_informe.generar(os.path.join(self.datos, t["id"]))
            self._paso(t, "informe", estado="hecho", progreso=1.0)
            base = f"trabajos/{t['id']}/"
            t.update(estado="terminado", mensaje="Terminado", terminado=ahora(), progreso=1.0,
                     resultado={"carpeta": base, "cambio": base + "cambio.json", "informe": base + "informe.html",
                                "geojson": base + "zonas.geojson", "csv": base + "zonas.csv", "markdown": base + "informe.md"})
        except Exception as exc:  # noqa: BLE001
            for p in t["pasos"]:
                if p["estado"] == "procesando":
                    p["estado"] = "error"
            t.update(estado="error", mensaje=str(exc), terminado=ahora())
        finally:
            self.actual = None
            self.guardar(t)


# ---------------------------------------------------------------- HTTP
class Manejador(http.server.SimpleHTTPRequestHandler):
    servicio: Servicio = None
    limite = 4 * 1024 ** 3
    cors = False
    permitir_subidas = True
    clave = ""             # si no esta vacia, las peticiones POST deben llevar la cabecera X-Nisar-Clave
    subidas_activas = threading.BoundedSemaphore(2)
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".webp": "image/webp", ".geojson": "application/geo+json", ".md": "text/markdown; charset=utf-8",
                      ".js": "text/javascript", ".json": "application/json", ".gz": "application/octet-stream"}

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=FRONT, **kw)

    def log_message(self, fmt, *args):
        if "/api/nisar/trabajos/" in (self.path or "") and self.command == "GET":
            return  # el sondeo de progreso ensucia la consola
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))

    def end_headers(self):
        if self.cors:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        if self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def translate_path(self, path):
        ruta = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        ruta = posixpath.normpath(ruta)
        partes = [p for p in ruta.split("/") if p and p not in (".", "..")]
        if partes and partes[0] == "trabajos":
            if len(partes) > 1 and partes[1].startswith("_"):
                return os.path.join(FRONT, "__no_existe__")
            base = self.servicio.datos
            partes = partes[1:]
        else:
            base = FRONT
        destino = os.path.abspath(os.path.join(base, *partes))
        if os.path.commonpath([destino, base]) != base:
            return os.path.join(FRONT, "__no_existe__")
        return destino

    def _json(self, codigo, datos):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    @staticmethod
    def _publico(reg):
        return {k: v for k, v in reg.items() if k not in ("ruta", "escena")} | {"lista": bool(reg.get("escena")) or reg["tipo"] == "h5"}

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        p = url.path.rstrip("/")
        s = self.servicio
        if p == "/api/nisar/estado":
            return self._json(200, {"ok": True, "h5py": s.h5py, "ocupado": s.actual, "en_cola": s.cola.qsize(),
                                    "requiere_clave": bool(self.clave), "subidas": self.permitir_subidas,
                                    "limite_bytes": self.limite, "libre_bytes": shutil.disk_usage(s.datos).free})
        if p == "/api/nisar/trabajos":
            return self._json(200, {"trabajos": [{k: t[k] for k in ("id", "titulo", "estado", "creado", "progreso", "mensaje")}
                                                 | {"antes": t["antes"]["meta"].get("fecha"),
                                                    "despues": t["despues"]["meta"].get("fecha")} for t in s.listar()]})
        m = re.fullmatch(r"/api/nisar/(trabajos|subidas)/([a-z0-9-]+)", p)
        if m:
            try:
                if m.group(1) == "trabajos":
                    return self._json(200, s.trabajo(m.group(2)))
                return self._json(200, self._publico(s.subida(m.group(2))))
            except KeyError:
                return self._json(404, {"error": "No existe."})
        if p.startswith("/api/"):
            return self._json(404, {"error": "Ruta desconocida."})
        if p in ("", "/"):
            self.send_response(302)
            self.send_header("Location", "/prueba.html")
            self.end_headers()
            return
        return super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlsplit(self.path)
        p = url.path.rstrip("/")
        s = self.servicio
        try:
            longitud = int(self.headers.get("Content-Length") or -1)
        except ValueError:
            longitud = -1
        if not self.permitir_subidas:
            return self._json(403, {"error": "Este servidor está abierto a la red sin clave: define NISAR_CLAVE para permitir análisis."})
        if self.clave and not hmac.compare_digest(self.headers.get("X-Nisar-Clave", ""), self.clave):
            return self._json(401, {"error": "Clave de acceso incorrecta o ausente."})
        try:
            if p == "/api/nisar/subidas":
                if longitud <= 0:
                    return self._json(411, {"error": "Falta Content-Length."})
                if longitud > self.limite:
                    return self._json(413, {"error": f"El fichero supera el límite de {self.limite / 1e9:.1f} GB."})
                nombre = urllib.parse.parse_qs(url.query).get("nombre", ["fichero"])[0]
                if not self.subidas_activas.acquire(blocking=False):
                    return self._json(429, {"error": "Ya hay dos subidas en curso. Espera a que terminen."})
                try:
                    return self._json(201, self._publico(s.recibir(nombre, self.rfile, longitud)))
                finally:
                    self.subidas_activas.release()
            if p == "/api/nisar/trabajos":
                if not 0 < longitud < 100_000:
                    return self._json(400, {"error": "Cuerpo JSON no válido."})
                cuerpo = json.loads(self.rfile.read(longitud) or b"{}")
                return self._json(201, s.crear(cuerpo))
            return self._json(404, {"error": "Ruta desconocida."})
        except KeyError:
            return self._json(404, {"error": "No existe esa subida. Vuelve a subir el fichero."})
        except (ValueError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": str(exc)})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 lo abre a la red; entonces exige --clave o NISAR_CLAVE")
    ap.add_argument("--puerto", type=int, default=8001)
    ap.add_argument("--datos", default=os.path.join(AQUI, "trabajos"), help="carpeta de subidas, escenas y resultados")
    ap.add_argument("--limite-gb", type=float, default=4.0, help="tamano maximo de cada fichero subido")
    ap.add_argument("--conservar-h5", action="store_true", help="no borrar el .h5 subido tras convertirlo")
    ap.add_argument("--cors", action="store_true", help="permitir llamadas desde otra web (Access-Control-Allow-Origin: *)")
    ap.add_argument("--clave", default=os.environ.get("NISAR_CLAVE", ""),
                    help="clave que piden las subidas y los analisis (por defecto, la variable NISAR_CLAVE)")
    a = ap.parse_args()
    Manejador.servicio = Servicio(a.datos, conservar_h5=a.conservar_h5)
    Manejador.limite = int(a.limite_gb * 1024 ** 3)
    Manejador.cors = a.cors
    Manejador.clave = a.clave.strip()
    # abierto a la red y sin clave: solo se pueden ver resultados, no lanzar analisis
    Manejador.permitir_subidas = bool(Manejador.clave) or a.host in ("127.0.0.1", "localhost", "::1")
    srv = http.server.ThreadingHTTPServer((a.host, a.puerto), Manejador)
    srv.daemon_threads = True
    print(f"Servicio NISAR en http://{'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host}:{a.puerto}/prueba.html")
    print(f"Datos en {Manejador.servicio.datos}  ·  h5py {'disponible' if Manejador.servicio.h5py else 'NO instalado'}"
          f"  ·  {'con clave' if Manejador.clave else 'sin clave'}"
          + ("" if Manejador.permitir_subidas else "  ·  SUBIDAS DESACTIVADAS (abierto a la red sin NISAR_CLAVE)"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")


if __name__ == "__main__":
    main()
