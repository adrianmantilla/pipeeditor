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


class Accesorios(unittest.TestCase):
    def _tramo(self, accesorio_medio="ninguno", fin="ninguno", **ajustes):
        anclajes = [c.Anclaje((0, 100, 0), (1, 0, 0)),
                    c.Anclaje((300, 100, 0), (0, 1, 0), accesorio=accesorio_medio),
                    c.Anclaje((600, 100, 0), (-1, 0, 0), accesorio=fin)]
        a = dict({"tipo": "tuberia", "recorrido": "libre", "grosor": 5.0, "salida": 0.0}, **ajustes)
        return c.construir(a, anclajes)

    def test_valvulas_y_te(self):
        for tipo, clave in (("valvula_bola", "valvulas_bola"), ("valvula_compuerta", "valvulas_compuerta"),
                            ("te", "tes")):
            r = self._tramo(tipo)
            self.assertEqual(r.recuento.get(clave), 1, tipo)
            self.assertGreater(r.piezas.num_caras, 0)
            # la maneta, el volante o la salida de la te van hacia la normal del anclaje (+Y)
            self.assertGreater(max(v[1] for v in r.piezas.vertices), 100 + 2.5 * 1.6, tipo)
            cerca = [v for v in r.piezas.vertices if abs(v[0] - 300) < 30]
            self.assertTrue(cerca, tipo)

    def test_reduccion_intermedia_cambia_el_diametro(self):
        r = self._tramo("reduccion", norma="acero", grosor=6.0)
        self.assertEqual(r.recuento.get("reducciones"), 1)
        tubos = sorted(k for k in r.recuento if k.startswith("tubo_"))
        self.assertEqual(len(tubos), 2)
        gruesos = [float(k[5:]) for k in tubos]
        self.assertAlmostEqual(max(gruesos), 6.03)
        self.assertAlmostEqual(min(gruesos), 4.83)
        # antes de la reducción el cuerpo es grueso; después, fino
        antes = [abs(v[2]) for v in r.cuerpo.vertices if v[0] < 280]
        despues = [abs(v[2]) for v in r.cuerpo.vertices if v[0] > 320]
        self.assertAlmostEqual(max(antes), 6.03 / 2, delta=0.05)
        self.assertAlmostEqual(max(despues), 4.83 / 2, delta=0.05)

    def test_reduccion_en_el_extremo(self):
        r = self._tramo(fin="reduccion", extremos="tapon")
        self.assertEqual(r.recuento.get("reducciones"), 1)
        self.assertEqual(r.recuento.get("tapones"), 1)  # en el otro extremo sí hay tapón
        self.assertGreater(max(v[0] for v in r.piezas.vertices), 600.5)

    def test_recuento_de_un_cable(self):
        r = c.construir({"holgura": 0.1, "conector_inicio": "clavija", "salida": 0.0},
                        [c.Anclaje((0, 100, 0), (1, 0, 0)), c.Anclaje((300, 100, 0), (-1, 0, 0))])
        self.assertEqual(r.recuento.get("conector_clavija"), 1)
        self.assertAlmostEqual(r.recuento["cable_2.00"], r.longitud)


class ListaMateriales(unittest.TestCase):
    def test_suma_por_concepto_y_medida(self):
        from pipeeditor import lista_materiales as lm
        an = [c.Anclaje((0, 100, 0), (1, 0, 0)), c.Anclaje((300, 100, 0), (0, 1, 0), accesorio="valvula_bola"),
              c.Anclaje((600, 100, 0), (-1, 0, 0))]
        a = {"tipo": "tuberia", "recorrido": "libre", "grosor": 6.0, "norma": "acero", "salida": 0.0,
             "extremos": "tapon", "material_cuerpo": "acero", "material_piezas": "acero",
             "material_metal": "laton"}
        r1 = c.construir(a, an)
        r2 = c.construir(a, an)
        cable = c.construir({"conector_inicio": "clavija", "salida": 0.0, "material_cuerpo": "goma_negra"},
                            [c.Anclaje((0, 100, 0), (1, 0, 0)), c.Anclaje((300, 100, 0), (-1, 0, 0))])
        filas = lm.filas([("tubo_01", a, r1.recuento), ("tubo_02", a, r2.recuento),
                          ("cable_01", {"tipo": "cable", "grosor": 2.0, "material_cuerpo": "goma_negra"},
                           cable.recuento)])
        por = {f["concepto"]: f for f in filas}
        self.assertAlmostEqual(por["tubo"]["cantidad"], 12.0, places=1)  # 2 × 600 cm
        self.assertEqual(por["tubo"]["unidad"], "m")
        self.assertEqual(por["tubo"]["norma"], "acero")
        self.assertEqual(por["valvulas_bola"]["cantidad"], 2)
        self.assertEqual(por["valvulas_bola"]["material"], "laton")
        self.assertEqual(por["tapones"]["cantidad"], 4)
        self.assertEqual(por["tubo"]["elementos"], ["tubo_01", "tubo_02"])
        texto = lm.a_csv(filas, decimal=",")
        primera, segunda = texto.splitlines()[:2]
        self.assertEqual(len(primera.split(";")), 7)
        self.assertIn("12,00", texto)
