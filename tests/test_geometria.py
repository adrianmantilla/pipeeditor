import math
import unittest

import comun  # noqa: F401  (añade scripts al path)
from pipeeditor import apoyo, catenaria, trazado, vec
from pipeeditor import malla as ml


class Catenaria(unittest.TestCase):
    def test_mide_lo_pedido(self):
        for p, q, largo in [((0, 0, 0), (300, 0, 0), 330), ((0, 200, 0), (400, 50, 120), 600),
                            ((0, 0, 0), (10, 300, 0), 400), ((0, 0, 0), (1000, 0, 0), 1000.5)]:
            puntos = catenaria.puntos(p, q, largo, 400)
            self.assertAlmostEqual(vec.longitud_polilinea(puntos), largo, delta=largo * 0.002)
            self.assertEqual(puntos[0], p)
            self.assertEqual(puntos[-1], q)

    def test_cuelga_hacia_abajo(self):
        puntos = catenaria.puntos((0, 100, 0), (200, 100, 0), 260, 50)
        self.assertLess(min(y for _x, y, _z in puntos), 100)
        self.assertGreater(catenaria.caida(puntos), 10)

    def test_simetrica_si_los_extremos_estan_a_la_misma_altura(self):
        puntos = catenaria.puntos((0, 0, 0), (200, 0, 0), 250, 100)
        bajo = min(puntos, key=lambda p: p[1])
        self.assertAlmostEqual(bajo[0], 100, delta=3)

    def test_tenso_es_recto(self):
        puntos = catenaria.puntos((0, 0, 0), (100, 50, 0), 50, 10)
        for p in puntos:
            self.assertAlmostEqual(p[1], p[0] * 0.5, places=6)
        self.assertTrue(catenaria.esta_tenso((0, 0, 0), (100, 0, 0), 100))

    def test_vertical_no_falla(self):
        puntos = catenaria.puntos((0, 0, 0), (0, 100, 0), 150, 10)
        self.assertEqual(len(puntos), 11)

    def test_en_el_plano_vertical(self):
        puntos = catenaria.puntos((0, 0, 0), (300, 0, 400), 600, 30)
        for x, _y, z in puntos:
            self.assertAlmostEqual(z, x * 400.0 / 300.0, places=6)

    def test_holgura(self):
        self.assertAlmostEqual(catenaria.longitud_con_holgura((0, 0, 0), (100, 0, 0), 0.1), 110.0)


class Trazado(unittest.TestCase):
    def test_ortogonal_z(self):
        camino = trazado.recorrido_ortogonal([(0, 0, 0), (100, 50, 0)], "z")
        self.assertEqual(camino, [(0, 0, 0), (50, 0, 0), (50, 50, 0), (100, 50, 0)])

    def test_ortogonal_l(self):
        camino = trazado.recorrido_ortogonal([(0, 0, 0), (100, 50, 30)], "l")
        for a, b in zip(camino, camino[1:]):
            distintos = sum(1 for i in range(3) if abs(a[i] - b[i]) > 1e-9)
            self.assertEqual(distintos, 1)
        self.assertEqual(camino[1], (100, 0, 0))

    def test_ortogonal_alineado_no_anade_esquinas(self):
        self.assertEqual(trazado.recorrido_ortogonal([(0, 0, 0), (0, 0, 80)], "z"), [(0, 0, 0), (0, 0, 80)])

    def test_cada_tramo_es_de_un_eje(self):
        camino = trazado.recorrido_ortogonal([(0, 0, 0), (100, 50, 30), (20, 80, 90)], "z")
        for a, b in zip(camino, camino[1:]):
            distintos = sum(1 for i in range(3) if abs(a[i] - b[i]) > 1e-9)
            self.assertEqual(distintos, 1)

    def test_redondear(self):
        puntos, codos = trazado.redondear([(0, 0, 0), (100, 0, 0), (100, 100, 0)], 20, pasos=8)
        self.assertEqual(len(codos), 1)
        c = codos[0]
        self.assertAlmostEqual(c.inicio[0], 80, places=6)
        self.assertAlmostEqual(c.fin[1], 20, places=6)
        self.assertAlmostEqual(math.degrees(c.angulo), 90, places=6)
        # todos los puntos del arco a 20 del centro (80, 20)
        for p in puntos[c.indice_inicio:c.indice_fin + 1]:
            self.assertAlmostEqual(vec.distancia(p, (80, 20, 0)), 20, places=5)

    def test_codos_que_no_caben_se_reducen(self):
        puntos, codos = trazado.redondear([(0, 0, 0), (10, 0, 0), (10, 10, 0), (20, 10, 0)], 50)
        self.assertEqual(len(codos), 2)
        self.assertLessEqual(codos[0].fin[1], codos[1].inicio[1] + 1e-6)

    def test_uniforme(self):
        posiciones = trazado.uniforme([(0, 0, 0), (100, 0, 0)], 25)
        self.assertEqual([round(p[0][0]) for p in posiciones], [12, 38, 62, 88])

    def test_marcos_ortonormales(self):
        puntos = catenaria.puntos((0, 0, 0), (300, 100, 200), 500, 40)
        for t, n, b in trazado.marcos(puntos):
            self.assertAlmostEqual(vec.largo(t), 1, places=6)
            self.assertAlmostEqual(vec.largo(n), 1, places=6)
            self.assertAlmostEqual(vec.punto(t, n), 0, places=6)
            self.assertAlmostEqual(vec.punto(n, b), 0, places=6)

    def test_marcos_sin_giros_bruscos(self):
        puntos, _ = trazado.redondear(trazado.recorrido_ortogonal([(0, 0, 0), (100, 80, 60)]), 10, 8)
        puntos = trazado.remuestrear(puntos, 2)
        marcos = trazado.marcos(puntos)
        for (_t1, n1, _b1), (_t2, n2, _b2) in zip(marcos, marcos[1:]):
            self.assertGreater(vec.punto(n1, n2), 0.9)


class Apoyo(unittest.TestCase):
    def test_suelo(self):
        puntos = catenaria.puntos((0, 50, 0), (200, 50, 0), 400, 80)
        apoyado = apoyo.apoyar_tramo(puntos, 1.0, altura_suelo=0.0)
        self.assertGreaterEqual(min(p[1] for p in apoyado), 1.0 - 1e-9)
        self.assertEqual(apoyado[0], puntos[0])
        self.assertEqual(apoyado[-1], puntos[-1])

    def test_objeto(self):
        puntos = catenaria.puntos((0, 100, 0), (200, 100, 0), 400, 80)
        caja = lambda x, y, z: 60.0 if 80 <= x <= 120 else None  # noqa: E731
        apoyado = apoyo.apoyar_tramo(puntos, 2.0, bajar=caja)
        for p in apoyado:
            if 80 <= p[0] <= 120:
                self.assertGreaterEqual(p[1], 62.0 - 1e-9)

    def test_sin_apoyos_no_cambia(self):
        puntos = catenaria.puntos((0, 100, 0), (200, 100, 0), 300, 20)
        self.assertEqual(apoyo.apoyar_tramo(puntos, 1.0), puntos)


class Mallas(unittest.TestCase):
    def test_cilindro(self):
        m = ml.cilindro(1, 0, 10, 8)
        comun.comprobar_malla(self, m)
        self.assertEqual(m.num_caras, 8 + 16)

    def test_toro_cerrado(self):
        comun.comprobar_malla(self, ml.toro(5, 1, 12, 6))

    def test_caja(self):
        m = ml.caja(1, 2, 3)
        comun.comprobar_malla(self, m)
        (x0, y0, z0), (x1, y1, z1) = m.caja()
        self.assertEqual((x1 - x0, y1 - y0, z1 - z0), (1, 2, 3))

    def test_tapas_hacia_fuera(self):
        m = ml.cilindro(1, 0, 10, 8)
        # la última cara (tapa final) mira hacia +Y
        a, b, c = [m.vertices[i] for i in m.caras[-1]]
        normal = vec.cruz(vec.resta(b, a), vec.resta(c, b))
        self.assertGreater(normal[1], 0)
        a, b, c = [m.vertices[i] for i in m.caras[8]]
        normal = vec.cruz(vec.resta(b, a), vec.resta(c, b))
        self.assertLess(normal[1], 0)

    def test_lados_hacia_fuera(self):
        m = ml.cilindro(1, 0, 10, 8)
        cara = m.caras[0]
        a, b, c = [m.vertices[i] for i in cara[:3]]
        normal = vec.cruz(vec.resta(b, a), vec.resta(c, b))
        centro = vec.escala([sum(v) for v in zip(*[m.vertices[i] for i in cara])], 1.0 / len(cara))
        self.assertGreater(vec.punto(normal, (centro[0], 0, centro[2])), 0)

    def test_para_maya(self):
        m = ml.cilindro(1, 0, 10, 6)
        vertices, cuentas, conexiones, us, vs, cuentas_uv, ids = m.para_maya()
        self.assertEqual(sum(cuentas), len(conexiones))
        self.assertEqual(len(ids), len(conexiones))
        self.assertEqual(len(us), len(vs))


if __name__ == "__main__":
    unittest.main()
