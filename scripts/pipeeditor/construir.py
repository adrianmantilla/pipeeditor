"""Construye un cable o una tubería completos a partir de sus ajustes. Sin Maya.

El nodo de Maya reúne los datos (anclajes, curva, objetos de apoyo) y llama a
``construir``; aquí está toda la lógica, para poder probarla fuera de Maya.
"""

import math

from pipeeditor import apoyo, catenaria, perfiles, piezas, trazado, vec
from pipeeditor import malla as ml

TIPOS = ("cable", "tuberia")
MODOS_TENSION = ("holgura", "longitud")
CODOS = ("curvado", "pieza")

POR_DEFECTO = {
    "tipo": "cable",
    # comunes
    "grosor": 2.0,               # diámetro, en unidades de la escena (cm)
    "lados": 8,
    "segmentos_metro": 24,
    "salida": 4.0,
    "apoyar_suelo": True,
    "altura_suelo": 0.0,
    # cables
    "perfil_cable": "redondo",
    "holgura": 0.12,
    "modo_tension": "holgura",
    "conector_inicio": "ninguno",
    "conector_fin": "ninguno",
    "pieza": "ninguna",
    "separacion_piezas": 40.0,
    "haz": 1,
    "torsion": 0.0,
    "separacion_bridas_haz": 0.0,
    # tuberías
    "perfil_tuberia": "redonda",
    "recorrido": "z",
    "radio_codo": 2.0,           # en diámetros de la tubería
    "codo": "curvado",
    "separacion_bridas": 0.0,
    "extremos": "abiertos",
    "pared": 0.0,
    "separacion_soportes": 0.0,
    "alcance_soportes": 60.0,
}


class Anclaje(object):
    """Punto de anclaje: posición, normal (por dónde sale el cable) y factor de holgura."""

    def __init__(self, posicion, normal=(0.0, 1.0, 0.0), factor=1.0, longitud=0.0):
        self.posicion = tuple(posicion)
        self.normal = vec.unitario(normal)
        self.factor = factor
        self.longitud = longitud  # longitud fija del tramo que empieza aquí (0 = sin fijar)


class Resultado(object):
    def __init__(self):
        self.cuerpo = ml.Malla()
        self.piezas = ml.Malla()
        self.curva = []
        self.longitud = 0.0
        self.caida = 0.0
        self.tensos = 0
        self.longitudes = []

    def triangulos(self):
        return self.cuerpo.triangulos() + self.piezas.triangulos()


def ajustes(**cambios):
    a = dict(POR_DEFECTO)
    a.update(cambios)
    return a


def construir(a, anclajes=(), ruta=None, ruta_lineal=False, bajar=None, cercano=None, malla_propia=None):
    """Devuelve un ``Resultado``.

    ``anclajes``: lista de ``Anclaje`` (al menos dos), o vacía si hay ``ruta``.
    ``ruta``: puntos de una curva; ``ruta_lineal`` si la curva es de grado 1
    (sus esquinas se redondean).
    ``bajar(x, y, z)``: altura de la superficie bajo ese punto, o None.
    ``cercano(punto, tangente)``: (punto, normal) de la superficie más cercana, o None.
    """
    a = ajustes(**a)
    if a["tipo"] == "tuberia":
        return _tuberia(a, list(anclajes), ruta, ruta_lineal, cercano)
    return _cable(a, list(anclajes), ruta, ruta_lineal, bajar, malla_propia)


# --- cables ---------------------------------------------------------------------------

def _segmentos(longitud, a):
    return max(8, int(math.ceil(longitud / 100.0 * a["segmentos_metro"])))


def _cable(a, anclajes, ruta, ruta_lineal, bajar, malla_propia):
    res = Resultado()
    r = max(a["grosor"], 1e-4) / 2.0
    cantidad = max(1, int(a["haz"]))
    r_total = perfiles.radio_haz(cantidad, r)
    inicio = piezas.conector(a["conector_inicio"], r_total, malla_propia)
    fin = piezas.conector(a["conector_fin"], r_total, malla_propia)
    suelo = a["altura_suelo"] if a["apoyar_suelo"] else None

    if ruta is not None and len(ruta) >= 2:
        camino = [tuple(p) for p in ruta]
        if ruta_lineal:
            camino, _ = trazado.redondear(camino, r_total * 3.0, pasos=6)
        t0 = vec.unitario(vec.resta(camino[1], camino[0]))
        t1 = vec.unitario(vec.resta(camino[-2], camino[-1]))
        marco_ini = vec.marco_desde_eje(vec.resta(camino[0], vec.escala(t0, inicio.largo)), t0)
        marco_fin = vec.marco_desde_eje(vec.resta(camino[-1], vec.escala(t1, fin.largo)), t1)
        res.longitudes = [vec.longitud_polilinea(camino)]
    elif len(anclajes) >= 2:
        camino, marco_ini, marco_fin = _camino_colgante(a, anclajes, inicio, fin, r_total, suelo, bajar, res)
    else:
        return res

    res.curva = camino
    res.longitud = vec.longitud_polilinea(camino)
    res.cuerpo = perfiles.cuerpo_cable(camino, r, a["perfil_cable"], a["lados"], cantidad, a["torsion"])
    if not inicio.malla.vacia():
        res.piezas.anadir(inicio.malla, marco_ini)
    if not fin.malla.vacia():
        res.piezas.anadir(fin.malla, marco_fin)
    margen = max(inicio.largo, fin.largo) + a["salida"] + r_total * 4
    if a["pieza"] != "ninguna" and a["separacion_piezas"] > 0:
        modelo = piezas.pieza_cable(a["pieza"], r_total)
        for p, t, _s in trazado.uniforme(camino, a["separacion_piezas"], margen=margen):
            res.piezas.anadir(modelo, vec.marco_desde_eje(p, t))
    if cantidad > 1 and a["separacion_bridas_haz"] > 0:
        modelo = piezas.brida_haz(r_total)
        for p, t, _s in trazado.uniforme(camino, a["separacion_bridas_haz"], margen=margen):
            res.piezas.anadir(modelo, vec.marco_desde_eje(p, t))
    return res


def _camino_colgante(a, anclajes, inicio, fin, r, suelo, bajar, res):
    """Catenarias entre anclajes, con la salida recta y los conectores de los extremos."""
    primero, ultimo = anclajes[0], anclajes[-1]
    salida = max(0.0, a["salida"])
    c0 = vec.suma(primero.posicion, vec.escala(primero.normal, inicio.largo))
    c1 = vec.suma(ultimo.posicion, vec.escala(ultimo.normal, fin.largo))
    s0 = vec.suma(c0, vec.escala(primero.normal, salida))
    s1 = vec.suma(c1, vec.escala(ultimo.normal, salida))
    paradas = [s0] + [x.posicion for x in anclajes[1:-1]] + [s1]

    camino = [c0] if salida > 0 else []
    for i in range(len(paradas) - 1):
        p, q = paradas[i], paradas[i + 1]
        anclaje = anclajes[i]
        if a["modo_tension"] == "longitud" and anclaje.longitud > 0:
            largo = anclaje.longitud
        else:
            largo = catenaria.longitud_con_holgura(p, q, a["holgura"] * anclaje.factor)
        if catenaria.esta_tenso(p, q, largo):
            res.tensos += 1
        tramo = catenaria.puntos(p, q, largo, _segmentos(largo, a))
        tramo = apoyo.apoyar_tramo(tramo, r, suelo, bajar)
        res.caida = max(res.caida, catenaria.caida(tramo))
        res.longitudes.append(vec.longitud_polilinea(tramo))
        camino.extend(tramo if i == 0 else tramo[1:])
    if salida > 0:
        camino.append(c1)
        radio = min(salida * 0.9, r * 6.0)
        esquinas = {1, len(camino) - 2}
        camino, _ = trazado.redondear(camino, radio, pasos=5, solo=esquinas)
    camino = trazado.limpiar_repetidos(camino)
    marco_ini = vec.marco_desde_eje(primero.posicion, primero.normal)
    marco_fin = vec.marco_desde_eje(ultimo.posicion, ultimo.normal)
    return camino, marco_ini, marco_fin


# --- tuberías -------------------------------------------------------------------------

def _tuberia(a, anclajes, ruta, ruta_lineal, cercano):
    res = Resultado()
    R = max(a["grosor"], 1e-4) / 2.0
    radio_codo = max(0.0, a["radio_codo"]) * 2.0 * R
    codos = []
    if ruta is not None and len(ruta) >= 2:
        camino = trazado.limpiar([tuple(p) for p in ruta]) if ruta_lineal else [tuple(p) for p in ruta]
        if ruta_lineal:
            camino, codos = trazado.redondear(camino, radio_codo, pasos=8)
    elif len(anclajes) >= 2:
        salida = max(0.0, a["salida"])
        primero, ultimo = anclajes[0], anclajes[-1]
        s0 = vec.suma(primero.posicion, vec.escala(primero.normal, salida))
        s1 = vec.suma(ultimo.posicion, vec.escala(ultimo.normal, salida))
        paradas = [s0] + [x.posicion for x in anclajes[1:-1]] + [s1]
        medio = trazado.recorrido_ortogonal(paradas, a["recorrido"])
        polilinea = ([primero.posicion] if salida > 0 else []) + medio + ([ultimo.posicion] if salida > 0 else [])
        polilinea = trazado.limpiar(polilinea)
        camino, codos = trazado.redondear(polilinea, radio_codo, pasos=8)
    else:
        return res
    if len(camino) < 2:
        return res
    res.curva = camino
    res.longitud = vec.longitud_polilinea(camino)
    res.longitudes = [res.longitud]
    abierta = a["extremos"] == "abiertos"
    res.cuerpo = perfiles.cuerpo_tuberia(camino, R, a["perfil_tuberia"], max(a["lados"], 8), a["pared"], abierta)
    R_fuera = R * (1.35 if a["perfil_tuberia"] == "aislada" else 1.0)

    s = vec.acumulada(camino)
    curvas = [(s[c.indice_inicio] - R_fuera * 1.6, s[c.indice_fin] + R_fuera * 1.6) for c in codos]

    def en_recta(distancia):
        return all(not (i0 <= distancia <= i1) for i0, i1 in curvas)

    # Codos de pieza: un manguito a cada lado.
    if a["codo"] == "pieza":
        m = piezas.manguito(R_fuera)
        for c in codos:
            res.piezas.anadir(m, vec.marco_desde_eje(c.inicio, c.tangente_inicio))
            res.piezas.anadir(m, vec.marco_desde_eje(c.fin, c.tangente_fin))
    # Bridas: repartidas en los tramos rectos y a los dos lados de cada codo.
    if a["separacion_bridas"] > 0:
        b = piezas.brida_tuberia(R_fuera)
        for p, t, d in trazado.uniforme(camino, a["separacion_bridas"], margen=R_fuera * 2):
            if en_recta(d):
                res.piezas.anadir(b, vec.marco_desde_eje(p, t))
        hueco = R_fuera * (1.0 if a["codo"] == "pieza" else 0.35)
        for c in codos:
            res.piezas.anadir(b, vec.marco_desde_eje(vec.resta(c.inicio, vec.escala(c.tangente_inicio, hueco)),
                                                     c.tangente_inicio))
            res.piezas.anadir(b, vec.marco_desde_eje(vec.suma(c.fin, vec.escala(c.tangente_fin, hueco)),
                                                     c.tangente_fin))
    # Fajas de la tubería aislada, cada metro.
    if a["perfil_tuberia"] == "aislada":
        f = piezas.faja(R)
        for p, t, d in trazado.uniforme(camino, 100.0, margen=R * 2):
            if en_recta(d):
                res.piezas.anadir(f, vec.marco_desde_eje(p, t))
    # Extremos.
    t0 = vec.unitario(vec.resta(camino[0], camino[1]))
    t1 = vec.unitario(vec.resta(camino[-1], camino[-2]))
    if a["extremos"] == "tapon":
        tp = piezas.tapon(R_fuera)
        res.piezas.anadir(tp, vec.marco_desde_eje(camino[0], t0))
        res.piezas.anadir(tp, vec.marco_desde_eje(camino[-1], t1))
    elif a["extremos"] == "brida":
        b = piezas.brida_tuberia(R_fuera)
        res.piezas.anadir(b, vec.marco_desde_eje(vec.suma(camino[0], vec.escala(t0, -R_fuera * 0.18)), t0))
        res.piezas.anadir(b, vec.marco_desde_eje(vec.suma(camino[-1], vec.escala(t1, -R_fuera * 0.18)), t1))
    # Soportes a la pared más cercana.
    if a["separacion_soportes"] > 0 and cercano is not None:
        for p, t, d in trazado.uniforme(camino, a["separacion_soportes"], margen=R_fuera * 3):
            if not en_recta(d):
                continue
            golpe = cercano(p, t)
            if golpe is None:
                continue
            contacto, normal = golpe
            if vec.distancia(p, contacto) > a["alcance_soportes"] + R_fuera:
                continue
            res.piezas.anadir(piezas.soporte(R_fuera, p, t, contacto, normal))
    return res
