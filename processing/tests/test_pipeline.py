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
from nisar_comun import (Escena, db_a_q, filtrar_speckle, guardar_escena,  # noqa: E402
                         q_a_db, utm_a_latlon)


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


if __name__ == "__main__":
    unittest.main()
