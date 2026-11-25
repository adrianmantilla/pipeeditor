"""Perfiles realistas y tuberías normalizadas."""

import math
import unittest

import comun

from pipeeditor import construir as c
from pipeeditor import perfiles, trazado, vec
from pipeeditor import malla as ml

RECTA = [(x * 5.0, 0.0, 0.0) for x in range(41)]


class Perfiles(unittest.TestCase):
    def test_ocho_es_una_sola_funda(self):
        m = perfiles.cuerpo_cable(RECTA, 1.0, "doble", 8)
        comun.comprobar_malla(self, m)
        ancho = m.caja()[1][2] - m.caja()[0][2]
        alto = m.caja()[1][1] - m.caja()[0][1]
        self.assertAlmostEqual(max(ancho, alto), 3.9, delta=0.1)  # dos conductores de 2 de diámetro
        self.assertLess(min(ancho, alto), 2.05)

    def test_cuerda_cabos_que_se_tocan(self):
        m = perfiles.cuerpo_cable(RECTA, 2.0, "trenzado", 8)
        comun.comprobar_malla(self, m)
        # el exterior de la cuerda coincide con su radio (con 5 % de fibras)
        r_max = max(math.hypot(p[1], p[2]) for p in m.vertices)
        self.assertAlmostEqual(r_max, 2.0, delta=2.0 * 0.12)


class Tuberias(unittest.TestCase):
    A = [c.Anclaje((0, 100, 0), (0, -1, 0)), c.Anclaje((300, 250, 200), (0, -1, 0))]

    def test_medida_normalizada(self):
        self.assertEqual(c.medida_normalizada("acero", 6.0), (6.03, 0.36))
        self.assertEqual(c.medida_normalizada("cobre", 2.1), (2.2, 0.1))
        self.assertIsNone(c.medida_normalizada("libre", 6.0))

    def test_norma_cambia_el_grosor(self):
        r = c.construir({"tipo": "tuberia", "grosor": 6.0, "norma": "acero"}, self.A)
        radio = max(math.hypot(p[0] - 0.0, p[2] - 0.0) for p in r.cuerpo.vertices if abs(p[1] - 100) < 1e-6)
        self.assertAlmostEqual(radio, 6.03 / 2, places=3)

    def test_soportes_segun_diametro(self):
        self.assertAlmostEqual(c.separacion_soportes_auto(2.13), 180.0, delta=15)
        self.assertAlmostEqual(c.separacion_soportes_auto(21.9), 535.0, delta=30)

    def test_codo_soldado(self):
        libre = c.construir({"tipo": "tuberia", "codo": "curvado"}, self.A)
        soldado = c.construir({"tipo": "tuberia", "codo": "soldado"}, self.A)
        self.assertGreater(soldado.piezas.num_caras, libre.piezas.num_caras + 50)
        self.assertGreater(soldado.piezas.separar(ml.METAL).num_caras, 0)  # cordones
        comun.comprobar_malla(self, soldado.piezas)


if __name__ == "__main__":
    unittest.main()


class Recorridos(unittest.TestCase):
    def test_esquiva_una_columna(self):
        columna = ((140, -10, -20), (160, 400, 20))
        p, q = (0.0, 100.0, 0.0), (300.0, 100.0, 0.0)
        camino = trazado.esquivar(p, q, [columna], 5.0)
        self.assertIsNotNone(camino)
        self.assertEqual(camino[0], p)
        self.assertEqual(camino[-1], q)
        for a, b in zip(camino, camino[1:]):
            self.assertFalse(trazado._corta(a, b, ((135, -15, -25), (165, 405, 25))))
            # solo por los ejes
            self.assertEqual(sum(1 for k in range(3) if abs(a[k] - b[k]) > 1e-9), 1)
        self.assertLessEqual(len(camino), 6)  # pocos codos

    def test_si_no_hay_nada_en_medio_no_cambia(self):
        self.assertIsNone(trazado.esquivar((0, 0, 0), (100, 50, 0), [((500, 0, 0), (600, 10, 10))], 2.0))

    def test_tuberia_esquivando(self):
        anclas = [c.Anclaje((0, 100, 0), (1, 0, 0)), c.Anclaje((300, 100, 0), (-1, 0, 0))]
        columna = ((140, -10, -20), (160, 400, 20))
        r = c.construir({"tipo": "tuberia", "recorrido": "esquivar", "grosor": 6.0}, anclas, obstaculos=[columna])
        for p in r.cuerpo.vertices:
            dentro = all(columna[0][k] + 0.01 < p[k] < columna[1][k] - 0.01 for k in range(3))
            self.assertFalse(dentro)

    def test_rack_con_codos_concentricos(self):
        anclas = [c.Anclaje((0, 100, 0), (1, 0, 0)), c.Anclaje((300, 100, 300), (-1, 0, 0))]
        r = c.construir({"tipo": "tuberia", "tubos": 3, "grosor": 6.0, "salida": 0.0, "recorrido": "z"}, anclas)
        self.assertGreater(r.cuerpo.num_caras, 0)
        base = [(0, 0, 0), (100, 0, 0), (100, 0, 100), (200, 0, 100)]
        caminos = [trazado.paralela(base, d, 30.0) for d in (-10.0, 0.0, 10.0)]
        # la distancia entre tuberías vecinas es constante en los tramos rectos
        for (pa, _ra), (pb, _rb) in zip(caminos, caminos[1:]):
            for a, b in zip(pa, pb):
                self.assertAlmostEqual(vec.distancia(a, b), 10.0 * math.sqrt(2) if a != pa[0] and a != pa[-1]
                                       else 10.0, places=6)
        # concéntricos: los radios cambian justo lo que se separan
        radios = [rr[1] for _p, rr in caminos]
        self.assertAlmostEqual(radios[0] - radios[1], radios[1] - radios[2])
        self.assertAlmostEqual(abs(radios[0] - radios[1]), 10.0)
