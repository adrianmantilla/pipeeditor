"""Piezas sencillas que acompañan a cables y tuberías.

Todas se modelan en local con el eje Y en la dirección del cable y se escalan
con el radio ``r`` del cable o de la tubería. Los conectores empiezan en el
anclaje (Y = 0) y el cable sale por ``largo`` (Y = largo).
"""

import math

from pipeeditor import malla as ml
from pipeeditor import vec

CONECTORES = ("ninguno", "clavija", "jack", "terminal", "gancho", "grillete", "propio", "aislador", "rollo")
PIEZAS_CABLE = ("ninguna", "brida", "anillo", "etiqueta", "bombilla")
EXTREMOS_TUBERIA = ("abiertos", "tapon", "brida")
SENALES = ("ninguna", "flecha", "banda", "flecha_y_banda")
# Accesorios que se ponen en un anclaje de una tubería.
ACCESORIOS = ("ninguno", "valvula_bola", "valvula_compuerta", "te", "reduccion")

_EJE_X = vec.matriz((0.0, 0.0, 0.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))  # Y local -> X


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
            m.anadir(ml.metal(ml.cilindro(0.32 * r, -4.0 * r, 0.0, 8, desplazamiento=(lado * 1.2 * r, 0.0))))
        return Conector(m, 9.0 * r)
    if tipo == "jack":
        m.anadir(ml.metal(ml.cilindro(0.55 * r, -3.0 * r, 0.0, 8)))
        m.anadir(ml.metal(ml.cilindro(1.9 * r, 0.0, 1.2 * r, 14)))
        m.anadir(ml.cilindro(1.5 * r, 1.2 * r, 7.0 * r, 14))
        m.anadir(ml.cilindro(1.2 * r, 7.0 * r, 9.5 * r, 10, radio_final=1.05 * r))
        return Conector(m, 9.5 * r)
    if tipo == "terminal":
        m.anadir(ml.metal(ml.movida(ml.toro(1.6 * r, 0.45 * r, 14, 6), (0.0, 0.45 * r, 0.0))))
        m.anadir(ml.metal(ml.cilindro(1.3 * r, 0.9 * r, 2.6 * r, 10)))
        m.anadir(ml.cilindro(1.45 * r, 2.6 * r, 4.5 * r, 10, radio_final=1.1 * r))
        return Conector(m, 4.5 * r)
    if tipo == "gancho":
        aro = ml.toro(2.6 * r, 0.6 * r, 18, 8, arco=math.radians(290), inicio=math.radians(-55))
        # el toro está en XZ; se pone vertical (plano XY) y colgando bajo el anclaje
        aro = ml.girada(aro, (1, 0, 0), math.pi / 2)
        m.anadir(ml.metal(ml.movida(aro, (0.0, -2.6 * r, 0.0))))
        m.anadir(ml.metal(ml.cilindro(0.6 * r, 0.0, 3.5 * r, 8)))
        return Conector(m, 3.5 * r)
    if tipo == "grillete":
        # Orejeta en la superficie, grillete en D con su perno y guardacabos
        # donde se ata la cuerda (el ojo de la cuerda abraza el grillete).
        m.anadir(ml.metal(ml.caja(0.55 * r, 3.0 * r, 3.4 * r, centro=(0.0, 1.5 * r, 0.0))))
        m.anadir(ml.metal(ml.caja(2.4 * r, 0.35 * r, 4.2 * r, centro=(0.0, 0.175 * r, 0.0))))
        perno = ml.girada(ml.cilindro(0.42 * r, -1.75 * r, 1.75 * r, 8), (0, 0, 1), math.pi / 2)
        m.anadir(ml.metal(ml.movida(perno, (0.0, 2.2 * r, 0.0))))
        for lado in (-1, 1):
            m.anadir(ml.metal(ml.cilindro(0.42 * r, 2.2 * r, 5.0 * r, 8, desplazamiento=(lado * 1.1 * r, 0.0))))
            m.anadir(ml.metal(ml.cilindro(0.62 * r, 1.95 * r, 2.45 * r, 8, desplazamiento=(lado * 1.6 * r, 0.0))))
        arco = ml.girada(ml.toro(1.1 * r, 0.42 * r, 12, 8, arco=math.pi, inicio=0.0), (1, 0, 0), -math.pi / 2)
        m.anadir(ml.metal(ml.movida(arco, (0.0, 5.0 * r, 0.0))))
        ojo = ml.girada(ml.toro(1.3 * r, 0.3 * r, 16, 6), (0, 0, 1), math.pi / 2)
        m.anadir(ml.metal(ml.movida(ojo, (0.0, 6.7 * r, 0.0))))
        return Conector(m, 8.0 * r)
    if tipo == "aislador":
        # Aislador de porcelana sobre su perno; el cable se ata arriba.
        R = max(4.0 * r, 6.0)
        m.anadir(ml.metal(ml.cilindro(0.18 * R, 0.0, 0.9 * R, 8)))
        y = 0.9 * R
        for k in range(3):
            m.anadir(ml.cilindro(R * (1.0 - 0.12 * k), y, y + 0.18 * R, 18, radio_final=R * 0.55))
            m.anadir(ml.cilindro(R * 0.45, y + 0.18 * R, y + 0.42 * R, 12))
            y += 0.42 * R
        m.anadir(ml.cilindro(R * 0.5, y, y + 0.35 * R, 12, radio_final=R * 0.38))
        return Conector(m, y + 0.35 * R)
    if tipo == "rollo":
        camino, largo = camino_rollo(r)
        return Conector(m, largo)  # la malla la hace construir, con el perfil del cable
    if tipo == "propio" and propia is not None and not propia.vacia():
        _minimo, maximo = propia.caja()
        return Conector(propia, max(0.0, maximo[1]))
    return Conector(m, 0.0)


def camino_rollo(r, vueltas=4):
    """Rollo de cable tumbado alrededor del anclaje (eje Y): espiras apiladas y la
    punta que sale por el centro, arriba. Devuelve (puntos, largo)."""
    R = max(14.0 * r, 8.0)
    paso = 2.1 * r
    puntos = []
    pasos = 24
    for k in range(vueltas * pasos + 1):
        a = 2 * math.pi * k / pasos
        puntos.append((R * math.cos(a), r + paso * k / pasos, R * math.sin(a)))
    arriba = puntos[-1][1] + r * 2.0
    # la punta entra hacia el centro y sale hacia arriba
    for k in range(1, 7):
        u = k / 6.0
        puntos.append((R * (1.0 - u), arriba * (0.85 + 0.15 * u), 0.0))
    largo = arriba + r * 3.0
    puntos.append((0.0, largo, 0.0))
    return puntos, largo


def pieza_cable(tipo, r):
    """Pieza que se repite a lo largo de un cable (centrada en el origen)."""
    m = ml.Malla()
    if tipo == "brida":
        m.anadir(ml.toro(r * 1.08, r * 0.14, 14, 4))
        m.anadir(ml.caja(r * 0.9, r * 0.5, r * 0.6, centro=(r * 1.35, 0.0, 0.0)))
    elif tipo == "anillo":
        m.anadir(ml.metal(ml.toro(r * 1.15, r * 0.25, 14, 6)))
    elif tipo == "etiqueta":
        m.anadir(ml.cilindro(r * 1.12, -r * 1.2, r * 1.2, 12))
        m.anadir(ml.caja(r * 0.15, r * 2.4, r * 3.2, centro=(r * 1.2, 0.0, r * 2.4)))
    elif tipo == "bombilla":
        m.anadir(bombilla(r))
    return m


def bombilla(r):
    """Portalámparas y bombilla de guirnalda colgando hacia +Y (se coloca con Y hacia abajo).

    A tamaño real (en cm): la bombilla mide unos 4,5 cm. El cristal va en la
    malla de metal, para darle su propio material (por ejemplo, «Luz cálida»).
    """
    m = ml.Malla()
    m.anadir(ml.toro(r * 1.1, max(r * 0.3, 0.12), 12, 5))                    # abrazadera al cable
    m.anadir(ml.cilindro(0.35, r, r + 1.0, 8))                                 # rabillo
    m.anadir(ml.cilindro(1.25, r + 1.0, r + 3.8, 16, radio_final=1.1))         # portalámparas
    cristal = ml.Malla()
    perfil = [(0.0, 0.0), (0.9, 0.0), (1.35, 0.6), (2.15, 1.9), (2.3, 2.9), (2.0, 3.9), (1.2, 4.6), (0.0, 4.8)]
    centros = [(0.0, r + 3.6 + y, 0.0) for _x, y in perfil]
    marcos = [((0, 1, 0), (1, 0, 0), (0, 0, -1))] * len(perfil)
    cristal.anadir(ml.barrer(centros, marcos, lambda i: ml.circulo(max(perfil[i][0], 0.05), 16), tapas=True))
    m.anadir(ml.metal(cristal))
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
        m.anadir(ml.metal(ml.cilindro(R * 0.13, -R * 0.3, R * 0.3, 6,
                                      desplazamiento=(R * 1.42 * math.cos(a), R * 1.42 * math.sin(a)))))
    return m


def manguito(R, largo=None):
    largo = largo if largo is not None else R * 1.3
    return ml.cilindro(R * 1.16, -largo / 2.0, largo / 2.0, 16)


def cordon(R):
    """Cordón de soldadura alrededor de la tubería."""
    return ml.metal(ml.toro(R * 1.03, R * 0.07, 20, 5))


def faja(R):
    """Faja de la tubería aislada."""
    return ml.cilindro(R * 1.42, -R * 0.12, R * 0.12, 16)


def tapon(R):
    """Tapón al final de la tubería (sale hacia +Y)."""
    m = ml.cilindro(R * 1.12, -R * 0.3, R * 0.5, 16)
    m.anadir(ml.cilindro(R * 0.6, R * 0.5, R * 0.75, 6))
    return m


def largo_flecha(R):
    return max(R * 8.0, 15.0)


def flecha(R):
    """Flecha de sentido pegada a la tubería (apunta a +Y, centrada en X+)."""
    largo = largo_flecha(R)
    grueso = max(R * 0.02, 0.03)
    radio = R * 1.004

    def arco(mitad):
        pasos = 6
        fuera = [(radio + grueso, -mitad + 2 * mitad * k / pasos) for k in range(pasos + 1)]
        dentro = [(radio, mitad - 2 * mitad * k / pasos) for k in range(pasos + 1)]
        return [(r * math.cos(a), -r * math.sin(a)) for r, a in fuera + dentro]

    cuerpo, cabeza = math.radians(18.0), math.radians(42.0)
    y0, y1, y2 = -largo / 2.0, largo * 0.1, largo / 2.0
    centros = [(0.0, y0, 0.0), (0.0, y1, 0.0), (0.0, y1, 0.0), (0.0, y2, 0.0)]
    anchos = [cuerpo, cuerpo, cabeza, math.radians(0.5)]
    marcos = [((0, 1, 0), (1, 0, 0), (0, 0, -1))] * 4
    return ml.barrer(centros, marcos, lambda i: arco(anchos[i]), tapas=True)


def banda(R):
    """Banda de color alrededor de la tubería, para identificar el fluido."""
    ancho = min(max(2.0 * R, 5.0), 25.0)
    return ml.cilindro(R * 1.012, -ancho / 2.0, ancho / 2.0, 24)


def valvula_bola(R):
    """Válvula de bola: cuerpo abombado, tuercas y maneta. Eje de la tubería en Y; la maneta, hacia +X."""
    m = ml.Malla()
    m.anadir(ml.metal(ml.cilindro(R * 1.25, -R * 1.4, 0.0, 20, radio_final=R * 1.75)))
    m.anadir(ml.metal(ml.cilindro(R * 1.75, 0.0, R * 1.4, 20, radio_final=R * 1.25)))
    for signo in (-1.0, 1.0):
        y0, y1 = sorted((signo * R * 1.35, signo * R * 2.2))
        m.anadir(ml.metal(ml.cilindro(R * 1.38, y0, y1, 6)))
    m.anadir(ml.metal(ml.cilindro(R * 0.3, R * 1.5, R * 2.5, 10)), _EJE_X)
    # maneta: larga, plana y a lo largo de la tubería (abierta)
    m.anadir(ml.caja(R * 0.45, R * 5.0, R * 0.9, centro=(R * 2.65, R * 1.7, 0.0)))
    return m


def valvula_compuerta(R):
    """Válvula de compuerta: cuerpo, tapa, husillo y volante hacia +X."""
    m = ml.Malla()
    m.anadir(ml.metal(ml.cilindro(R * 1.45, -R * 1.2, R * 1.2, 20)))
    for signo in (-1.0, 1.0):
        y0, y1 = sorted((signo * R * 1.1, signo * R * 1.6))
        m.anadir(ml.metal(ml.cilindro(R * 1.75, y0, y1, 20)))  # bridas de la válvula
    m.anadir(ml.metal(ml.cilindro(R * 0.85, 0.0, R * 3.0, 16)), _EJE_X)
    m.anadir(ml.metal(ml.cilindro(R * 0.16, R * 3.0, R * 4.2, 8)), _EJE_X)
    volante = ml.toro(R * 1.6, R * 0.16, 24, 6)
    for k in range(3):
        a = 2 * math.pi * k / 3.0
        radio = ml.cilindro(R * 0.1, 0.0, R * 1.6, 6)
        volante.anadir(radio, vec.matriz((0.0, 0.0, 0.0), (0.0, -1.0, 0.0),
                                         (math.cos(a), 0.0, math.sin(a)), (-math.sin(a), 0.0, math.cos(a))))
    m.anadir(volante, vec.matriz((R * 4.0, 0.0, 0.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    return m


def te(R, largo_rama=None):
    """Te: cuerpo a lo largo de la tubería (Y) con su salida hacia +X, del mismo grueso."""
    largo_rama = largo_rama if largo_rama is not None else R * 2.3
    m = ml.Malla()
    m.anadir(ml.cilindro(R * 1.22, -R * 2.0, R * 2.0, 20))
    m.anadir(ml.cilindro(R * 1.22, 0.0, largo_rama, 20), _EJE_X)
    for signo in (-1.0, 1.0):  # rebordes de los tres extremos
        y0, y1 = sorted((signo * R * 1.75, signo * R * 2.05))
        m.anadir(ml.cilindro(R * 1.32, y0, y1, 20))
    m.anadir(ml.cilindro(R * 1.32, largo_rama - R * 0.3, largo_rama + R * 0.05, 20), _EJE_X)
    return m


def reduccion(R, r, largo=None):
    """Reducción concéntrica de ``R`` (en -Y) a ``r`` (en +Y), centrada en el origen."""
    largo = largo if largo is not None else max(R * 1.6, (R - r) * 3.0)
    return ml.cilindro(R * 1.12, -largo / 2.0, largo / 2.0, 20, radio_final=r * 1.12)


def accesorio(tipo, R):
    if tipo == "valvula_bola":
        return valvula_bola(R)
    if tipo == "valvula_compuerta":
        return valvula_compuerta(R)
    if tipo == "te":
        return te(R)
    return ml.Malla()


def soporte(R, origen, tangente, contacto, normal_superficie):
    """Abrazadera alrededor de la tubería con su varilla y la placa en la pared.

    Todo en coordenadas de mundo: ``origen`` es el centro de la tubería,
    ``contacto`` el punto de la pared y ``normal_superficie`` su normal.
    """
    m = ml.Malla()
    # Tamaños mínimos reales (en cm): en tuberías finas, la abrazadera, la
    # varilla y la placa no pueden encoger con el diámetro hasta no verse.
    ancho = max(R * 0.6, 2.0)
    m.anadir(ml.metal(ml.cilindro(R * 1.06 + 0.15, -ancho / 2.0, ancho / 2.0, 20)),
             vec.marco_desde_eje(origen, tangente))
    hacia = vec.resta(contacto, origen)
    distancia = vec.largo(hacia)
    if distancia > R * 1.2:
        eje = vec.unitario(hacia)
        grueso = max(R * 0.14, 0.5)
        m.anadir(ml.metal(ml.cilindro(grueso, R * 1.0, distancia, 8)), vec.marco_desde_eje(origen, eje, tangente))
        m.anadir(ml.metal(ml.cilindro(grueso * 1.7, R * 1.05, R * 1.05 + grueso * 1.6, 6)),
                 vec.marco_desde_eje(origen, eje, tangente))  # tuerca de la abrazadera
        placa = max(R * 0.55, 3.0)
        m.anadir(ml.metal(ml.cilindro(placa, 0.0, max(R * 0.16, 0.4), 12)),
                 vec.marco_desde_eje(contacto, normal_superficie, tangente))
    return m
