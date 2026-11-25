"""Tuberías: normas, pendiente, soportes hacia el techo y señales."""

import unittest

import comun  # noqa: F401

from pipeeditor import construir as c
from pipeeditor import trazado, vec

PARED = [c.Anclaje((0, 150, 0), (0, 0, 1)), c.Anclaje((300, 0, 50), (0, 1, 0))]


class Normas(unittest.TestCase):
    def test_todas_las_normas_tienen_medidas(self):
        for norma in c.NORMAS[1:]:
            d, pared = c.medida_normalizada(norma, 5.0)
            self.assertTrue(0 < pared < d / 4, norma)

    def test_ansi_y_desague(self):
        self.assertAlmostEqual(c.medida_normalizada("ansi", 11.0)[0], 11.43)
        self.assertAlmostEqual(c.medida_normalizada("desague", 11.0)[0], 11.0)
        r = c.construir({"tipo": "tuberia", "norma": "multicapa", "grosor": 2.5}, PARED)
        self.assertGreater(r.cuerpo.num_caras, 0)


class Pendiente(unittest.TestCase):
    def test_baja_hacia_el_final_sin_mover_los_extremos(self):
        P = [(0, 100, 0), (10, 100, 0), (200, 100, 0), (200, 0, 0), (300, 0, 0)]
        Q = trazado.con_pendiente(P, 0.02)
        self.assertEqual(Q[0], P[0])
        self.assertEqual(Q[-1], P[-1])
        self.assertAlmostEqual(Q[2][1], 100 - 0.02 * 200)
        self.assertAlmostEqual(Q[3][1], 0 + 0.02 * 100)  # el último tramo también baja hacia el final
        self.assertEqual((Q[2][0], Q[2][2]), (Q[3][0], Q[3][2]))  # la bajante sigue vertical

    def test_sin_tramo_vertical_no_cambia(self):
        P = [(0, 100, 0), (100, 100, 0), (100, 100, 100)]
        self.assertEqual(trazado.con_pendiente(P, 0.02), P)

    def test_en_la_tuberia(self):
        llano = c.construir({"tipo": "tuberia", "recorrido": "z"}, PARED)
        inclinada = c.construir({"tipo": "tuberia", "recorrido": "z", "pendiente": 0.02}, PARED)
        self.assertNotEqual(llano.curva, inclinada.curva)
        self.assertLess(vec.distancia(inclinada.curva[0], llano.curva[0]), 1e-6)
        self.assertLess(vec.distancia(inclinada.curva[-1], llano.curva[-1]), 1e-6)


class Soportes(unittest.TestCase):
    def test_colgados_del_techo(self):
        pedidos = []

        def cercano(p, t, direccion=None):
            pedidos.append(direccion)
            if direccion is None:
                return (p[0], p[1], p[2] - 10.0), (0.0, 0.0, 1.0)
            return (p[0], 280.0, p[2]), (0.0, -1.0, 0.0)

        tramo = [c.Anclaje((0, 200, 0), (1, 0, 0)), c.Anclaje((400, 200, 0), (-1, 0, 0))]
        a = {"tipo": "tuberia", "recorrido": "libre", "separacion_soportes": 100.0, "alcance_soportes": 120.0}
        pared = c.construir(a, tramo, cercano=cercano)
        techo = c.construir(dict(a, soportes_hacia="techo"), tramo, cercano=cercano)
        self.assertIn((0.0, 1.0, 0.0), pedidos)
        self.assertGreater(max(v[1] for v in techo.piezas.vertices), 279.0)
        self.assertLess(max(v[1] for v in pared.piezas.vertices), 230.0)


class Senales(unittest.TestCase):
    def test_flechas_y_bandas(self):
        tramo = [c.Anclaje((0, 100, 0), (1, 0, 0)), c.Anclaje((1000, 100, 0), (-1, 0, 0))]
        a = {"tipo": "tuberia", "recorrido": "libre", "grosor": 10.0}
        nada = c.construir(a, tramo)
        flechas = c.construir(dict(a, senales="flecha"), tramo)
        las_dos = c.construir(dict(a, senales="flecha_y_banda"), tramo)
        self.assertEqual(nada.piezas.num_caras, 0)
        self.assertGreater(flechas.piezas.num_caras, 0)
        self.assertGreater(las_dos.piezas.num_caras, flechas.piezas.num_caras)
        # las flechas van encima de la tubería, pegadas a ella
        self.assertLess(max(v[1] for v in flechas.piezas.vertices), 100 + 5.0 * 1.05 + 0.2)


if __name__ == "__main__":
    unittest.main()
