"""Fase 4: viento, cadenas, guirnaldas, rollos, bandejas."""

import unittest

import comun  # noqa: F401

from pipeeditor import construir as c
from pipeeditor import vec

A = [c.Anclaje((0, 300, 0), (1, 0, 0)), c.Anclaje((500, 300, 0), (-1, 0, 0))]


class Viento(unittest.TestCase):
    def test_se_balancea_sin_estirarse(self):
        a = {"holgura": 0.1, "salida": 0.0, "apoyar_suelo": False}
        quieto = c.construir(a, A)
        movido = c.construir(dict(a, viento=0.8, direccion_viento=90.0, _tiempo=1.0), A)
        medio_q = min(quieto.curva, key=lambda p: abs(p[0] - 250))
        medio_m = min(movido.curva, key=lambda p: abs(p[0] - 250))
        self.assertGreater(medio_m[2], 10.0)  # se va hacia +Z, adonde sopla
        self.assertGreater(medio_m[1], medio_q[1])  # al balancearse sube
        self.assertAlmostEqual(quieto.longitud, movido.longitud, delta=quieto.longitud * 0.01)
        self.assertLess(vec.distancia(movido.curva[0], quieto.curva[0]), 1e-6)

    def test_cambia_con_el_tiempo_y_no_con_viento_a_favor(self):
        a = {"holgura": 0.1, "salida": 0.0, "apoyar_suelo": False, "viento": 0.8, "direccion_viento": 90.0}
        t0 = c.construir(dict(a, _tiempo=0.0), A).curva
        t1 = c.construir(dict(a, _tiempo=0.7), A).curva
        self.assertNotEqual(t0, t1)
        a_favor = c.construir(dict(a, direccion_viento=0.0, _tiempo=0.7), A).curva
        quieto = c.construir(dict(a, viento=0.0), A).curva
        self.assertLess(max(abs(p[2]) for p in a_favor), 1e-6)
        self.assertEqual(len(a_favor), len(quieto))

    def test_la_cache_no_repite_el_reposo_por_el_tiempo(self):
        cache = {"firma_apoyos": "nada"}
        a = {"holgura": 0.6, "salida": 0.0, "viento": 0.5}
        c.construir(dict(a, _tiempo=0.0), [c.Anclaje((0, 100, 0), (1, 0, 0)), c.Anclaje((400, 100, 0), (-1, 0, 0))],
                    cache=cache)
        clave = cache["clave"]
        c.construir(dict(a, _tiempo=2.0), [c.Anclaje((0, 100, 0), (1, 0, 0)), c.Anclaje((400, 100, 0), (-1, 0, 0))],
                    cache=cache)
        self.assertEqual(cache["clave"], clave)


if __name__ == "__main__":
    unittest.main()
