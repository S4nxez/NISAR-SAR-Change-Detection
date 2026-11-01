"""Pruebas del pipeline NISAR sin datos reales: python -m unittest discover -s processing/tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.dirname(AQUI)
sys.path.insert(0, PROC)
from nisar_comun import (Escena, contornos, db_a_q, filtrar_speckle,  # noqa: E402
                         guardar_escena, q_a_db, utm_a_latlon)


class TestComun(unittest.TestCase):
    def test_cuantizacion_ida_y_vuelta(self):
        db = np.array([[-40.0, -15.3, 0.0], [np.nan, 10.8, -25.0]], np.float32)
        back = q_a_db(db_a_q(db))
        self.assertTrue(np.isnan(back[1, 0]))
        ok = np.isfinite(db)
        self.assertLessEqual(np.abs(back[ok] - db[ok]).max(), 0.1 + 1e-5)

    def test_filtro_conserva_media_en_zona_uniforme(self):
        db = np.full((50, 50), -6.0, np.float32)
        db[0, 0] = np.nan
        f = filtrar_speckle(db, 5)
        self.assertAlmostEqual(float(np.nanmax(np.abs(f - -6.0))), 0.0, places=4)
        self.assertTrue(np.isnan(f[0, 0]))

    def test_utm_sur(self):
        # punto de la escena real (EPSG:32718); referencia aproximada
        lat, lon = utm_a_latlon(203770 + 10, 9601190 - 10, 32718)
        self.assertAlmostEqual(lat, -3.6043, places=2)
        self.assertAlmostEqual(lon, -77.6663, places=2)

    def test_contorno_con_hueco(self):
        m = np.zeros((12, 12), bool)
        m[2:9, 2:9] = True
        m[4:7, 4:7] = False
        m[10, 10] = True
        polis = contornos(m, eps=0.1)
        self.assertEqual(len(polis), 2)                      # el cuadrado grande y el pixel suelto
        ext, hueco = polis[0]
        self.assertEqual(sorted(map(tuple, ext.tolist())), [(2, 2), (2, 9), (9, 2), (9, 9)])
        self.assertEqual(len(hueco), 4)


class TestServidor(unittest.TestCase):
    def test_metadatos_del_nombre(self):
        import servidor
        m = servidor.meta_de_nombre("NISAR_L2_PR_GCOV_032_083_D_091_2005_SHSH_A_20261005T232338_20261005T232413_P05023_N_F_J_001.h5")
        self.assertEqual((m["pista"], m["frame"], m["direccion"], m["fecha"]), (83, 91, "Descending", "2026-10-05"))
        self.assertEqual(servidor.meta_de_nombre("otra_cosa.h5"), {})


class TestCambioExtremoAExtremo(unittest.TestCase):
    def test_detecta_cambios_inyectados(self):
        rng = np.random.default_rng(1)
        H, W = 600, 700
        base = rng.normal(-6, 2, (H, W)).astype(np.float32)
        base[:, :20] = np.nan                     # borde sin datos
        base[300:330, 50:650] = rng.normal(-24, 1.5, (30, 600))   # un rio
        despues = base + 0.7 + rng.normal(0, 1.5, (H, W)).astype(np.float32)
        despues[100:160, 100:180] = rng.normal(-23, 1.5, (60, 80))   # inundacion
        despues[400:470, 400:480] -= 5                               # tala
        geo = {"x0": 300000.0, "y0": 9500000.0, "dx": 20.0, "dy": -20.0, "ancho": W, "alto": H, "origen": "esquina"}
        with tempfile.TemporaryDirectory() as tmp:
            for nombre, img, fecha in (("a", base, "2026-10-05"), ("b", despues, "2026-10-17")):
                guardar_escena(os.path.join(tmp, nombre), {"geo": geo, "epsg": 32718, "zeroDopplerStartTime": fecha},
                               db_a_q(img), tesela=256, zip_final=False)
            self.assertEqual(Escena(os.path.join(tmp, "a")).mosaico_q().shape, (H, W))
            web = os.path.join(tmp, "web")
            subprocess.run([sys.executable, os.path.join(PROC, "nisar_cambio.py"), os.path.join(tmp, "a"),
                            os.path.join(tmp, "b"), "--id", "test", "--salida", web, "--area-min", "0.1"],
                           check=True, capture_output=True)
            with open(os.path.join(web, "test", "cambio.json"), encoding="utf-8") as fh:
                c = json.load(fh)
            clases = {z["clase"] for z in c["zonas"]}
            self.assertIn("agua_nueva", clases)
            self.assertIn("descenso", clases)
            self.assertLess(abs(c["parametros"]["desplazamiento_global_dB"] - 0.95), 0.4)
            agua = c["estadisticas"]["zonas_km2_por_clase"]["agua_nueva"]
            self.assertLess(abs(agua - 60 * 80 * 4e-4), 0.6)          # 1,92 km2 inyectados
            for f in ("antes.webp", "despues.webp", "cambio.png", "diferencia.webp"):
                self.assertTrue(os.path.exists(os.path.join(web, "test", f)))
            with open(os.path.join(web, "pares.json"), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["pares"][0]["id"], "test")
            # informacion ampliada
            e = c["estadisticas"]
            self.assertGreater(e["agua"]["nueva_km2"], 1.0)
            self.assertAlmostEqual(sum(map(sum, e["coberturas"]["matriz_km2"])), e["area_valida_km2"], delta=1.0)
            self.assertGreater(e["correlacion"], 0.3)
            self.assertTrue(c["resumen_texto"])
            self.assertTrue(all(z.get("contorno") for z in c["zonas"]))
            v = c["valores"]
            import gzip
            with gzip.open(os.path.join(web, "test", v["archivo"])) as fh:
                self.assertEqual(len(fh.read()), 5 * v["filas"] * v["columnas"])
            # informes
            import nisar_informe
            nisar_informe.generar(os.path.join(web, "test"))
            for f in ("informe.html", "informe.md", "zonas.geojson", "zonas.csv"):
                self.assertTrue(os.path.exists(os.path.join(web, "test", f)))
            with open(os.path.join(web, "test", "zonas.geojson"), encoding="utf-8") as fh:
                self.assertEqual(len(json.load(fh)["features"]), len(c["zonas"]))


if __name__ == "__main__":
    unittest.main()
