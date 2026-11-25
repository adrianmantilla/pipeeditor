"""Piezas sencillas que acompañan a cables y tuberías.

Todas se modelan en local con el eje Y en la dirección del cable y se escalan
con el radio ``r`` del cable o de la tubería. Los conectores empiezan en el
anclaje (Y = 0) y el cable sale por ``largo`` (Y = largo).
"""

import math

from pipeeditor import malla as ml
from pipeeditor import vec

CONECTORES = ("ninguno", "clavija", "jack", "terminal", "gancho", "grillete", "propio")
PIEZAS_CABLE = ("ninguna", "brida", "anillo", "etiqueta")
EXTREMOS_TUBERIA = ("abiertos", "tapon", "brida")


class Conector(object):
    def __init__(self, malla, largo):
        self.malla = malla
        self.largo = largo


def conector(tipo, r, propia=None):
    """Malla y largo del conector ``tipo`` para un cable de radio ``r``.

    ``propia``: malla de un objeto del usuario (para el tipo «propio»).
    """
    m = ml.Malla()
    if tipo == "clavija":
        m.anadir(ml.cilindro(2.6 * r, 0.0, 6.0 * r, 16))
        m.anadir(ml.cilindro(1.5 * r, 6.0 * r, 9.0 * r, 12, radio_final=1.15 * r))
        for lado in (-1, 1):
            m.anadir(ml.cilindro(0.32 * r, -4.0 * r, 0.0, 6, desplazamiento=(lado * 1.2 * r, 0.0)))
        return Conector(m, 9.0 * r)
    if tipo == "jack":
        m.anadir(ml.cilindro(0.55 * r, -3.0 * r, 0.0, 8))
        m.anadir(ml.cilindro(1.9 * r, 0.0, 1.2 * r, 14))
        m.anadir(ml.cilindro(1.5 * r, 1.2 * r, 7.0 * r, 14))
        m.anadir(ml.cilindro(1.2 * r, 7.0 * r, 9.5 * r, 10, radio_final=1.05 * r))
        return Conector(m, 9.5 * r)
    if tipo == "terminal":
        m.anadir(ml.movida(ml.toro(1.6 * r, 0.45 * r, 14, 6), (0.0, 0.45 * r, 0.0)))
        m.anadir(ml.cilindro(1.3 * r, 0.9 * r, 4.5 * r, 10))
        return Conector(m, 4.5 * r)
    if tipo == "gancho":
        aro = ml.toro(2.6 * r, 0.6 * r, 18, 8, arco=math.radians(290), inicio=math.radians(-55))
        # el toro está en XZ; se pone vertical (plano XY) y colgando bajo el anclaje
        aro = ml.girada(aro, (1, 0, 0), math.pi / 2)
        m.anadir(ml.movida(aro, (0.0, -2.6 * r, 0.0)))
        m.anadir(ml.cilindro(0.6 * r, 0.0, 3.5 * r, 8))
        return Conector(m, 3.5 * r)
    if tipo == "grillete":
        arco = ml.toro(2.0 * r, 0.55 * r, 12, 8, arco=math.pi, inicio=0.0)
        arco = ml.girada(arco, (1, 0, 0), -math.pi / 2)
        m.anadir(arco)
        perno = ml.girada(ml.cilindro(0.6 * r, -2.6 * r, 2.6 * r, 8), (0, 0, 1), math.pi / 2)
        m.anadir(perno)
        return Conector(m, 2.6 * r)
    if tipo == "propio" and propia is not None and not propia.vacia():
        _minimo, maximo = propia.caja()
        return Conector(propia, max(0.0, maximo[1]))
    return Conector(m, 0.0)


def pieza_cable(tipo, r):
    """Pieza que se repite a lo largo de un cable (centrada en el origen)."""
    m = ml.Malla()
    if tipo == "brida":
        m.anadir(ml.toro(r * 1.08, r * 0.14, 14, 4))
        m.anadir(ml.caja(r * 0.9, r * 0.5, r * 0.6, centro=(r * 1.35, 0.0, 0.0)))
    elif tipo == "anillo":
        m.anadir(ml.toro(r * 1.15, r * 0.25, 14, 6))
    elif tipo == "etiqueta":
        m.anadir(ml.cilindro(r * 1.12, -r * 1.2, r * 1.2, 12))
        m.anadir(ml.caja(r * 0.15, r * 2.4, r * 3.2, centro=(r * 1.2, 0.0, r * 2.4)))
    return m


def brida_haz(radio_exterior):
    """Brida de plástico que abraza un haz de cables."""
    m = ml.Malla()
    grosor = max(radio_exterior * 0.06, 0.05)
    m.anadir(ml.toro(radio_exterior + grosor, grosor, 20, 4))
    m.anadir(ml.caja(grosor * 6, grosor * 4, grosor * 4, centro=(radio_exterior + grosor * 3, 0.0, 0.0)))
    return m


# --- tuberías -------------------------------------------------------------------------

def brida_tuberia(R):
    """Brida con seis tornillos, centrada en el origen (eje Y)."""
    m = ml.Malla()
    m.anadir(ml.cilindro(R * 1.7, -R * 0.18, R * 0.18, 20))
    for k in range(6):
        a = 2 * math.pi * k / 6.0
        m.anadir(ml.cilindro(R * 0.13, -R * 0.3, R * 0.3, 6,
                             desplazamiento=(R * 1.42 * math.cos(a), R * 1.42 * math.sin(a))))
    return m


def manguito(R, largo=None):
    largo = largo if largo is not None else R * 1.3
    return ml.cilindro(R * 1.16, -largo / 2.0, largo / 2.0, 16)


def faja(R):
    """Faja de la tubería aislada."""
    return ml.cilindro(R * 1.42, -R * 0.12, R * 0.12, 16)


def tapon(R):
    """Tapón al final de la tubería (sale hacia +Y)."""
    m = ml.cilindro(R * 1.12, -R * 0.3, R * 0.5, 16)
    m.anadir(ml.cilindro(R * 0.6, R * 0.5, R * 0.75, 6))
    return m


def soporte(R, origen, tangente, contacto, normal_superficie):
    """Abrazadera alrededor de la tubería con su varilla y la placa en la pared.

    Todo en coordenadas de mundo: ``origen`` es el centro de la tubería,
    ``contacto`` el punto de la pared y ``normal_superficie`` su normal.
    """
    m = ml.Malla()
    aro = ml.toro(R * 1.12, R * 0.12, 18, 5)
    m.anadir(aro, vec.marco_desde_eje(origen, tangente))
    hacia = vec.resta(contacto, origen)
    distancia = vec.largo(hacia)
    if distancia > R * 1.2:
        eje = vec.unitario(hacia)
        varilla = ml.cilindro(R * 0.14, R * 1.12, distancia, 6)
        m.anadir(varilla, vec.marco_desde_eje(origen, eje, tangente))
        placa = ml.cilindro(R * 0.55, 0.0, R * 0.16, 10)
        m.anadir(placa, vec.marco_desde_eje(contacto, normal_superficie, tangente))
    return m
