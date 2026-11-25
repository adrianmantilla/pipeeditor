"""Reposo físico: contacto, longitud, rigidez, ganchos, haces y eje Z."""

import math
import unittest

import comun  # noqa: F401

from pipeeditor import construir as c
from pipeeditor import reposo, vec

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


def caja(minimo, maximo):
    """``empujar`` para una caja alineada con los ejes (como haría Maya con una malla)."""
    lo = np.array(minimo, dtype=float)
    hi = np.array(maximo, dtype=float)

    def empujar(P, radio, antes=None):
        P = np.array(P, dtype=float)
        dentro = np.all((P > lo - radio) & (P < hi + radio), axis=1)
        for i in np.nonzero(dentro)[0]:
            p = P[i]
            distancias = np.concatenate([p - (lo - radio), (hi + radio) - p])
            if antes is not None:
                # sale por la cara por la que entró (la que el punto anterior tenía fuera)
                a = np.asarray(antes[i])
                fuera = np.concatenate([a <= lo - radio, a >= hi + radio])
                if fuera.any():
                    distancias = np.where(fuera, distancias, np.inf)
            k = int(np.argmin(distancias))
            if k < 3:
                P[i, k] = lo[k] - radio
            else:
                P[i, k - 3] = hi[k - 3] + radio
        return P, dentro

    def bajar(x, y, z):
        if lo[0] <= x <= hi[0] and lo[2] <= z <= hi[2] and y >= hi[1]:
            return float(hi[1])
        return None
    empujar.bajar = bajar
    return empujar


def longitud(puntos):
    return vec.longitud_polilinea(puntos)


def angulo_maximo(puntos, paso):
    """Ángulo máximo (grados) entre tramos de ``paso`` de largo, para medir la rigidez."""
    from pipeeditor import trazado
    pts = trazado.remuestrear(trazado.limpiar_repetidos(puntos), paso)
    peor = 0.0
    for a, b, d in zip(pts, pts[1:], pts[2:]):
        u, v = vec.unitario(vec.resta(b, a)), vec.unitario(vec.resta(d, b))
        peor = max(peor, math.degrees(math.acos(max(-1.0, min(1.0, vec.punto(u, v))))))
    return peor


A = [c.Anclaje((0, 100, 0), (1, 0, 0)), c.Anclaje((400, 100, 0), (-1, 0, 0))]


@unittest.skipIf(np is None, "sin numpy")
class Reposo(unittest.TestCase):
    def test_libre_sigue_siendo_catenaria(self):
        r = c.construir({"holgura": 0.1}, A)
        self.assertFalse(r.reposado)

    def test_en_el_suelo_conserva_la_longitud(self):
        r = c.construir({"holgura": 0.5, "salida": 0.0}, A)
        self.assertTrue(r.reposado)
        esperado = 400 * 1.5
        self.assertLess(abs(longitud(r.curva) - esperado) / esperado, 0.03)
        self.assertGreaterEqual(min(p[1] for p in r.curva), 1.0 - 1e-6)
        # El sobrante queda tumbado: muchos puntos sobre el suelo.
        tumbados = [p for p in r.curva if p[1] < 1.2]
        self.assertGreater(longitud(tumbados), 100.0)

    def test_toca_el_suelo_sin_pico(self):
        r = c.construir({"holgura": 0.3, "salida": 0.0, "rigidez": 0.3}, A)
        self.assertTrue(r.reposado)
        # radio mínimo 10 (r = 1): con tramos de 2, menos de ~25 grados
        self.assertLess(angulo_maximo(r.curva, 2.0), 25.0)

    def test_antes_subia_los_puntos_y_perdia_longitud(self):
        sin = c.construir({"holgura": 0.5, "salida": 0.0, "reposo": False}, A)
        con = c.construir({"holgura": 0.5, "salida": 0.0}, A)
        esperado = 400 * 1.5
        self.assertGreater(abs(longitud(sin.curva) - esperado), abs(longitud(con.curva) - esperado))

    def test_sobre_una_mesa_no_la_atraviesa(self):
        mesa = caja((150, 40, -100), (250, 50, 100))
        r = c.construir({"holgura": 0.6, "salida": 0.0}, A, bajar=mesa.bajar, empujar=mesa)
        self.assertTrue(r.reposado)
        P = np.array(r.curva)
        dentro = np.all((P > np.array([150, 40, -100]) + 0.5) & (P < np.array([250, 50, 100]) - 0.5), axis=1)
        self.assertFalse(dentro.any(), "el cable atraviesa la mesa")
        encima = [p for p in r.curva if 160 < p[0] < 240 and abs(p[2]) < 90]
        self.assertTrue(encima)
        self.assertGreater(min(p[1] for p in encima), 50.0)

    def test_mesa_fina_no_se_atraviesa_por_debajo(self):
        # Tablero de 3 cm, más fino que los tramos del cable: antes salía por debajo.
        mesa = caja((120, 60, -60), (280, 63, 60))
        r = c.construir({"holgura": 0.9, "salida": 0.0, "grosor": 1.0}, A, bajar=mesa.bajar, empujar=mesa)
        debajo = [p for p in r.curva if 125 < p[0] < 275 and abs(p[2]) < 55 and 2.0 < p[1] < 60]
        self.assertFalse(debajo, "hay cable bajo el tablero")

    def test_suelo_pocas_curvas_amplias(self):
        # El sobrante en el suelo: pocas curvas grandes, no un muelle.
        r = c.construir({"holgura": 0.6, "salida": 0.0, "grosor": 0.7, "rigidez": 0.15}, A)
        suelo = [p for p in r.curva if p[1] < 0.5]
        zs = [p[2] for p in suelo]
        cambios = sum(1 for a, b, d in zip(zs, zs[1:], zs[2:]) if (b - a) * (d - b) < 0 and abs(b) > 1.0)
        self.assertLessEqual(cambios, 8)
        self.assertGreater(max(abs(z) for z in zs), 10.0)

    def test_poste_en_medio_por_los_lados(self):
        # Un poste vertical que la catenaria atraviesa: antes se ignoraba.
        poste = caja((195, -10, -5), (205, 300, 5))
        r = c.construir({"holgura": 0.1, "salida": 0.0}, A, empujar=poste)
        self.assertTrue(r.reposado)
        P = np.array(r.curva)
        dentro = np.all((P > np.array([195, -10, -5]) + 0.2) & (P < np.array([205, 300, 5]) - 0.2), axis=1)
        self.assertFalse(dentro.any())

    def test_gancho_reparte_la_longitud(self):
        # Mismo largo total; con gancho, el tramo largo presta cable al corto.
        anclas = [c.Anclaje((0, 200, 0), (1, 0, 0)), c.Anclaje((100, 200, 0), desliza=True),
                  c.Anclaje((400, 200, 0), (-1, 0, 0))]
        fijo = c.construir({"holgura": 0.1, "salida": 0.0, "apoyar_suelo": False},
                           [c.Anclaje(x.posicion, x.normal) for x in anclas])
        libre = c.construir({"holgura": 0.1, "salida": 0.0, "apoyar_suelo": False}, anclas)
        self.assertTrue(libre.reposado)
        self.assertFalse(fijo.reposado)
        # el punto más bajo del tramo corto baja menos o igual; el cable sigue pasando por el gancho
        distancia = min(vec.distancia(p, (100, 200, 0)) for p in libre.curva)
        self.assertLess(distancia, 1.5)

    def test_haz_suelto_sin_cruzarse(self):
        r = c.construir({"haz": 3, "grosor": 2.0, "holgura": 0.3, "variacion": 0.8, "salida": 0.0}, A)
        self.assertEqual(len(r.hilos), 3)
        for i in range(3):
            for j in range(i + 1, 3):
                a, b = np.array(r.hilos[i]), np.array(r.hilos[j])
                d = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2)).min()
                self.assertGreater(d, 2.0 * 0.85, "dos cables del haz se atraviesan")

    def test_semilla_repetible(self):
        a = {"holgura": 0.5, "ondulacion": 0.5, "semilla": 3}
        r1, r2 = c.construir(a, A), c.construir(a, A)
        self.assertEqual(r1.curva, r2.curva)
        r3 = c.construir(dict(a, semilla=4), A)
        self.assertNotEqual(r1.curva, r3.curva)

    def test_eje_z(self):
        anclas = [c.Anclaje((0, 0, 100), (1, 0, 0)), c.Anclaje((400, 0, 100), (-1, 0, 0))]
        r = c.construir({"holgura": 0.1, "arriba": "z", "apoyar_suelo": False}, anclas)
        z = [p[2] for p in r.curva]
        self.assertLess(min(z), 60.0)  # cuelga hacia -Z
        self.assertLess(max(abs(p[1]) for p in r.curva), 1e-6)

    def test_rapido(self):
        import time
        t = time.time()
        c.construir({"holgura": 0.8}, A)
        self.assertLess(time.time() - t, 1.5)


class Ondulacion(unittest.TestCase):
    @unittest.skipIf(np is None, "sin numpy")
    def test_extremos_quietos(self):
        p = [(x, 0.0, 0.0) for x in range(0, 101, 5)]
        q = reposo.ondulacion(p, 3.0, 1, 30.0)
        self.assertAlmostEqual(float(np.abs(q[0] - p[0]).max()), 0.0)
        self.assertAlmostEqual(float(np.abs(q[-1] - np.array(p[-1])).max()), 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
