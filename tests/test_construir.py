import unittest

import comun
from pipeeditor import construir as c
from pipeeditor import perfiles, piezas, vec

A = [c.Anclaje((0, 200, 0), (1, 0, 0)), c.Anclaje((400, 150, 100), (-1, 0, 0))]
P = [c.Anclaje((0, 100, 0), (0, 0, 1)), c.Anclaje((300, 250, 200), (0, 0, 1))]


class Cables(unittest.TestCase):
    def test_todos_los_perfiles(self):
        for perfil in perfiles.PERFILES_CABLE:
            with self.subTest(perfil=perfil):
                r = c.construir({"perfil_cable": perfil}, A)
                comun.comprobar_malla(self, r.cuerpo)
                self.assertGreater(r.cuerpo.num_caras, 0)
                self.assertLess(r.triangulos(), 200000)

    def test_conectores(self):
        for con in piezas.CONECTORES:
            with self.subTest(conector=con):
                r = c.construir({"conector_inicio": con, "conector_fin": con}, A)
                comun.comprobar_malla(self, r.piezas)
                if con == "rollo":  # el rollo es cable: va en el cuerpo
                    comun.comprobar_malla(self, r.cuerpo)
                    sin = c.construir({}, A)
                    self.assertGreater(r.cuerpo.num_caras, sin.cuerpo.num_caras * 2)
                elif con in ("ninguno", "propio"):
                    self.assertTrue(r.piezas.vacia())
                else:
                    self.assertFalse(r.piezas.vacia())

    def test_conector_propio(self):
        from pipeeditor import malla as ml
        propio = ml.cilindro(1, 0, 5, 6)
        r = c.construir({"conector_inicio": "propio"}, A, malla_propia=propio)
        self.assertFalse(r.piezas.vacia())
        # el cable empieza donde acaba el conector (5 unidades sobre la normal)
        self.assertAlmostEqual(r.curva[0][0], 5.0, places=6)

    def test_salida_recta(self):
        r = c.construir({"salida": 10.0}, A)
        self.assertEqual(r.curva[0], (0.0, 200.0, 0.0))
        self.assertAlmostEqual(r.curva[1][1], 200.0, places=6)  # sale en horizontal
        self.assertGreater(r.curva[1][0], 0)

    def test_piezas_a_lo_largo(self):
        for pieza in piezas.PIEZAS_CABLE[1:]:
            r = c.construir({"pieza": pieza, "separacion_piezas": 50}, A)
            comun.comprobar_malla(self, r.piezas)
            self.assertFalse(r.piezas.vacia())

    def test_haz(self):
        uno = c.construir({}, A)
        siete = c.construir({"haz": 7, "torsion": 1.0, "separacion_bridas_haz": 40}, A)
        self.assertGreater(siete.cuerpo.num_caras, uno.cuerpo.num_caras * 6)
        self.assertFalse(siete.piezas.vacia())

    def test_posiciones_haz(self):
        for n in (1, 2, 7, 12, 19):
            pos = perfiles.posiciones_haz(n, 2.0)
            self.assertEqual(len(pos), n)
            for i in range(n):
                for j in range(i + 1, n):
                    self.assertGreater(vec.distancia((pos[i][0], pos[i][1], 0), (pos[j][0], pos[j][1], 0)), 1.0)

    def test_longitud_fija_se_tensa(self):
        anclajes = [c.Anclaje((0, 100, 0), (1, 0, 0), longitud=150), c.Anclaje((400, 100, 0), (-1, 0, 0))]
        r = c.construir({"modo_tension": "longitud", "salida": 0}, anclajes)
        self.assertEqual(r.tensos, 1)
        r = c.construir({"modo_tension": "holgura", "salida": 0}, anclajes)
        self.assertEqual(r.tensos, 0)

    def test_varios_anclajes(self):
        anclajes = A[:1] + [c.Anclaje((200, 180, 50), (0, 1, 0), factor=2.0)] + A[1:]
        r = c.construir({}, anclajes)
        self.assertEqual(len(r.longitudes), 2)
        self.assertTrue(any(vec.distancia(p, (200, 180, 50)) < 1e-6 for p in r.curva))

    def test_suelo(self):
        r = c.construir({"holgura": 2.0, "altura_suelo": 100.0, "grosor": 2.0}, A)
        self.assertGreaterEqual(min(p[1] for p in r.curva), 101.0 - 1e-6)

    def test_desde_ruta(self):
        ruta = [(0, 0, 0), (100, 0, 0), (100, 0, 100)]
        r = c.construir({}, ruta=ruta, ruta_lineal=True)
        self.assertGreater(len(r.curva), 3)
        comun.comprobar_malla(self, r.cuerpo)

    def test_un_anclaje_no_hace_nada(self):
        r = c.construir({}, A[:1])
        self.assertTrue(r.cuerpo.vacia())


class Tuberias(unittest.TestCase):
    def test_todos_los_perfiles(self):
        for perfil in perfiles.PERFILES_TUBERIA:
            for extremos in piezas.EXTREMOS_TUBERIA:
                with self.subTest(perfil=perfil, extremos=extremos):
                    r = c.construir({"tipo": "tuberia", "perfil_tuberia": perfil, "grosor": 6, "pared": 0.5,
                                     "extremos": extremos, "separacion_bridas": 80, "codo": "pieza"}, P)
                    comun.comprobar_malla(self, r.cuerpo)
                    comun.comprobar_malla(self, r.piezas)

    def test_hueca(self):
        cerrada = c.construir({"tipo": "tuberia", "grosor": 6, "extremos": "tapon", "pared": 0.5}, P)
        hueca = c.construir({"tipo": "tuberia", "grosor": 6, "extremos": "abiertos", "pared": 0.5}, P)
        self.assertGreater(len(hueca.cuerpo.vertices), len(cerrada.cuerpo.vertices))

    def test_recorrido_en_angulo_recto(self):
        r = c.construir({"tipo": "tuberia", "grosor": 4, "radio_codo": 0}, P)
        for a, b in zip(r.curva, r.curva[1:]):
            distintos = sum(1 for i in range(3) if abs(a[i] - b[i]) > 1e-6)
            self.assertEqual(distintos, 1)

    def test_salida_por_la_normal(self):
        r = c.construir({"tipo": "tuberia", "grosor": 4, "salida": 20, "radio_codo": 0}, P)
        self.assertEqual(r.curva[0], (0.0, 100.0, 0.0))
        self.assertEqual(r.curva[1], (0.0, 100.0, 20.0))

    def test_soportes(self):
        pared = lambda p, t: ((p[0], p[1], -30.0), (0.0, 0.0, 1.0))  # noqa: E731
        sin = c.construir({"tipo": "tuberia", "grosor": 4}, P, cercano=pared)
        con = c.construir({"tipo": "tuberia", "grosor": 4, "separacion_soportes": 50,
                           "alcance_soportes": 1000}, P, cercano=pared)
        self.assertTrue(sin.piezas.vacia())
        self.assertFalse(con.piezas.vacia())
        comun.comprobar_malla(self, con.piezas)

    def test_soportes_fuera_de_alcance(self):
        lejos = lambda p, t: ((p[0], p[1], -5000.0), (0.0, 0.0, 1.0))  # noqa: E731
        r = c.construir({"tipo": "tuberia", "grosor": 4, "separacion_soportes": 50, "alcance_soportes": 60},
                        P, cercano=lejos)
        self.assertTrue(r.piezas.vacia())

    def test_desde_curva_suave(self):
        ruta = [(x, 0.0, (x / 10.0) ** 2) for x in range(0, 101, 5)]
        r = c.construir({"tipo": "tuberia", "grosor": 4}, ruta=ruta, ruta_lineal=False)
        comun.comprobar_malla(self, r.cuerpo)
        self.assertEqual(len(r.curva), len(ruta))


if __name__ == "__main__":
    unittest.main()
