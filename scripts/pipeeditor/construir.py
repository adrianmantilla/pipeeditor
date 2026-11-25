"""Construye un cable o una tubería completos a partir de sus ajustes. Sin Maya.

El nodo de Maya reúne los datos (anclajes, curva, objetos de apoyo) y llama a
``construir``; aquí está toda la lógica, para poder probarla fuera de Maya.
"""

import math

from pipeeditor import apoyo, catenaria, perfiles, piezas, reposo, trazado, vec
from pipeeditor import malla as ml

TIPOS = ("cable", "tuberia")
MODOS_TENSION = ("holgura", "longitud")
CODOS = ("curvado", "pieza")
EJES = ("y", "z")

POR_DEFECTO = {
    "tipo": "cable",
    # comunes
    "grosor": 2.0,               # diámetro, en unidades de la escena (cm)
    "lados": 8,
    "segmentos_metro": 24,
    "salida": 4.0,
    "apoyar_suelo": True,
    "altura_suelo": 0.0,
    "arriba": "y",               # eje vertical de la escena
    # reposo físico (cables)
    "reposo": True,
    "rigidez": 0.3,              # 0 = cuerda floja, 1 = cable duro
    "ondulacion": 0.0,           # memoria de bobina: ondas laterales
    "variacion": 0.0,            # diferencias de holgura entre cables de un haz
    "semilla": 0,
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

    def __init__(self, posicion, normal=(0.0, 1.0, 0.0), factor=1.0, longitud=0.0, desliza=False):
        self.posicion = tuple(posicion)
        self.normal = vec.unitario(normal)
        self.factor = factor
        self.longitud = longitud  # longitud fija del tramo que empieza aquí (0 = sin fijar)
        self.desliza = desliza    # punto intermedio por el que el cable pasa sin atarse (gancho)


class Resultado(object):
    def __init__(self):
        self.cuerpo = ml.Malla()
        self.piezas = ml.Malla()
        self.curva = []
        self.longitud = 0.0
        self.caida = 0.0
        self.tensos = 0
        self.longitudes = []
        self.reposado = False
        self.hilos = []  # recorrido de cada cable de un haz suelto

    def triangulos(self):
        return self.cuerpo.triangulos() + self.piezas.triangulos()


def ajustes(**cambios):
    a = dict(POR_DEFECTO)
    a.update(cambios)
    return a


def construir(a, anclajes=(), ruta=None, ruta_lineal=False, bajar=None, cercano=None, malla_propia=None,
              empujar=None):
    """Devuelve un ``Resultado``.

    ``anclajes``: lista de ``Anclaje`` (al menos dos), o vacía si hay ``ruta``.
    ``ruta``: puntos de una curva; ``ruta_lineal`` si la curva es de grado 1
    (sus esquinas se redondean).
    ``bajar(x, y, z)``: altura de la superficie bajo ese punto, o None.
    ``cercano(punto, tangente)``: (punto, normal) de la superficie más cercana, o None.
    ``empujar(P, radio)``: saca de los objetos de apoyo los puntos del array
    ``P`` (N×3); devuelve (P corregido, máscara de contacto). Ver ``reposo``.

    Con ``arriba = "z"`` todo llega y sale en coordenadas de la escena; por
    dentro se trabaja siempre con Y hacia arriba.
    """
    a = ajustes(**a)
    if a["arriba"] == "z":
        return _con_z_arriba(a, list(anclajes), ruta, ruta_lineal, bajar, cercano, malla_propia, empujar)
    if a["tipo"] == "tuberia":
        return _tuberia(a, list(anclajes), ruta, ruta_lineal, cercano)
    return _cable(a, list(anclajes), ruta, ruta_lineal, bajar, malla_propia, empujar)


# --- eje vertical Z -------------------------------------------------------------------

def _a_interno(p):
    return (p[0], p[2], -p[1])


def _a_escena(p):
    return (p[0], -p[2], p[1])


def _con_z_arriba(a, anclajes, ruta, ruta_lineal, bajar, cercano, malla_propia, empujar):
    b = dict(a, arriba="y")
    anclajes = [Anclaje(_a_interno(x.posicion), _a_interno(x.normal), x.factor, x.longitud, x.desliza)
                for x in anclajes]
    ruta = [_a_interno(p) for p in ruta] if ruta is not None else None
    bajar_i = (lambda x, y, z: bajar(*_a_escena((x, y, z)))) if bajar is not None else None
    cercano_i = None
    if cercano is not None:
        def cercano_i(p, t):
            golpe = cercano(_a_escena(p), _a_escena(t))
            if golpe is None:
                return None
            return _a_interno(golpe[0]), _a_interno(golpe[1])
    empujar_i = None
    if empujar is not None:
        def empujar_i(P, radio):
            import numpy as np
            P = np.asarray(P, dtype=float)
            fuera = np.stack([P[:, 0], -P[:, 2], P[:, 1]], axis=1)
            Q, contacto = empujar(fuera, radio)
            Q = np.asarray(Q, dtype=float)
            return np.stack([Q[:, 0], Q[:, 2], -Q[:, 1]], axis=1), contacto
    res = construir(b, anclajes, ruta, ruta_lineal, bajar_i, cercano_i, malla_propia, empujar_i)
    res.cuerpo.vertices = [_a_escena(p) for p in res.cuerpo.vertices]
    res.piezas.vertices = [_a_escena(p) for p in res.piezas.vertices]
    res.curva = [_a_escena(p) for p in res.curva]
    res.hilos = [[_a_escena(p) for p in h] for h in res.hilos]
    return res


# --- cables ---------------------------------------------------------------------------

def _segmentos(longitud, a):
    return max(8, int(math.ceil(longitud / 100.0 * a["segmentos_metro"])))


def _cable(a, anclajes, ruta, ruta_lineal, bajar, malla_propia, empujar=None):
    res = Resultado()
    r = max(a["grosor"], 1e-4) / 2.0
    cantidad = max(1, int(a["haz"]))
    r_total = perfiles.radio_haz(cantidad, r)
    inicio = piezas.conector(a["conector_inicio"], r_total, malla_propia)
    fin = piezas.conector(a["conector_fin"], r_total, malla_propia)
    suelo = a["altura_suelo"] if a["apoyar_suelo"] else None
    # Haz suelto: cada cable cuelga por su cuenta (sin bridas que los aten).
    suelto = (cantidad > 1 and a["separacion_bridas_haz"] <= 0 and a["reposo"] and reposo.disponible()
              and ruta is None)

    if ruta is not None and len(ruta) >= 2:
        camino = [tuple(p) for p in ruta]
        if ruta_lineal:
            camino, _ = trazado.redondear(camino, r_total * 3.0, pasos=6)
        t0 = vec.unitario(vec.resta(camino[1], camino[0]))
        t1 = vec.unitario(vec.resta(camino[-2], camino[-1]))
        marco_ini = vec.marco_desde_eje(vec.resta(camino[0], vec.escala(t0, inicio.largo)), t0)
        marco_fin = vec.marco_desde_eje(vec.resta(camino[-1], vec.escala(t1, fin.largo)), t1)
        res.longitudes = [vec.longitud_polilinea(camino)]
    elif len(anclajes) >= 2 and suelto:
        res.hilos = _haz_suelto(a, anclajes, inicio, fin, r, suelo, bajar, empujar, res)
        camino = res.hilos[0]
        marco_ini = vec.marco_desde_eje(anclajes[0].posicion, anclajes[0].normal)
        marco_fin = vec.marco_desde_eje(anclajes[-1].posicion, anclajes[-1].normal)
    elif len(anclajes) >= 2:
        camino, marco_ini, marco_fin = _camino_colgante(a, anclajes, inicio, fin, r_total, suelo, bajar, res,
                                                        empujar)
    else:
        return res

    # Anillos según la curvatura: densos en las curvas, pocos en las rectas.
    paso_max = 100.0 / max(1, a["segmentos_metro"])
    paso_min = min(r * 0.3, paso_max)
    camino = trazado.adaptativo(camino, paso_max, 6.0, paso_min)
    res.hilos = [trazado.adaptativo(h, paso_max, 6.0, paso_min) for h in res.hilos]
    if res.hilos:
        res.hilos[0] = camino
    res.curva = camino
    res.longitud = vec.longitud_polilinea(camino)
    if res.hilos:
        for h in res.hilos:
            res.cuerpo.anadir(perfiles.cuerpo_cable(h, r, a["perfil_cable"], a["lados"], 1, 0.0))
    else:
        res.cuerpo = perfiles.cuerpo_cable(camino, r, a["perfil_cable"], a["lados"], cantidad, a["torsion"])
    if not inicio.malla.vacia():
        res.piezas.anadir(inicio.malla, marco_ini)
    if not fin.malla.vacia():
        res.piezas.anadir(fin.malla, marco_fin)
    margen = max(inicio.largo, fin.largo) + a["salida"] + r_total * 4
    if a["pieza"] != "ninguna" and a["separacion_piezas"] > 0:
        modelo = piezas.pieza_cable(a["pieza"], r if res.hilos else r_total)
        for h in (res.hilos or [camino]):
            for p, t, _s in trazado.uniforme(h, a["separacion_piezas"], margen=margen):
                res.piezas.anadir(modelo, vec.marco_desde_eje(p, t))
    if cantidad > 1 and a["separacion_bridas_haz"] > 0:
        modelo = piezas.brida_haz(r_total)
        for p, t, _s in trazado.uniforme(camino, a["separacion_bridas_haz"], margen=margen):
            res.piezas.anadir(modelo, vec.marco_desde_eje(p, t))
    return res


def _extremos(a, anclajes, inicio, fin):
    """Punta del conector (c) y fin de la salida recta (s) en cada extremo."""
    primero, ultimo = anclajes[0], anclajes[-1]
    salida = max(0.0, a["salida"])
    c0 = vec.suma(primero.posicion, vec.escala(primero.normal, inicio.largo))
    c1 = vec.suma(ultimo.posicion, vec.escala(ultimo.normal, fin.largo))
    s0 = vec.suma(c0, vec.escala(primero.normal, salida))
    s1 = vec.suma(c1, vec.escala(ultimo.normal, salida))
    return c0, s0, s1, c1, salida


def _largo_tramo(a, anclaje, p, q, factor=1.0):
    if a["modo_tension"] == "longitud" and anclaje.longitud > 0:
        return anclaje.longitud * factor
    return catenaria.longitud_con_holgura(p, q, a["holgura"] * anclaje.factor * factor)


def _catenarias(a, anclajes, paradas, r, suelo, bajar, res, factor=1.0, contar=True):
    """Catenaria apoyada de cada tramo, su longitud y si toca algo."""
    tramos, largos, toca = [], [], False
    for i in range(len(paradas) - 1):
        p, q = paradas[i], paradas[i + 1]
        largo = _largo_tramo(a, anclajes[i], p, q, factor)
        if contar and catenaria.esta_tenso(p, q, largo):
            res.tensos += 1
        libre = catenaria.puntos(p, q, largo, _segmentos(largo, a))
        tramo = apoyo.apoyar_tramo(libre, r, suelo, bajar)
        if any(abs(u[1] - v[1]) > 1e-9 for u, v in zip(libre, tramo)):
            toca = True
        tramos.append(tramo)
        largos.append(largo)
    return tramos, largos, toca


def _toca_objetos(empujar, tramos, r):
    if empujar is None:
        return False
    import numpy as np
    P = np.array([p for t in tramos for p in t], dtype=float)
    _Q, contacto = empujar(P, r)
    return bool(np.any(contacto))


def _reposar(a, anclajes, tramos, largos, c0, c1, salida, r, suelo, empujar, semilla, otros=()):
    """Cadena para el reposo a partir de las catenarias apoyadas, y su resultado."""
    total = sum(largos)
    paso = max(total / 180.0, r * 1.5)
    puntos, rest, fijos, ganchos = [], [], [], []
    if salida > 0:
        puntos.append(c0)
        rest.append(vec.distancia(c0, tramos[0][0]))
        fijos.append(0)
    amplitud = r * (0.08 + 6.0 * max(0.0, a["ondulacion"]))
    for i, (tramo, largo) in enumerate(zip(tramos, largos)):
        partes = max(3, int(round(largo / paso)))
        ini = reposo.repartir(tramo, partes)
        ini = reposo.ondulacion(ini, amplitud, semilla * 7919 + i, r * 70.0)
        if i == 0:
            fijos.append(len(puntos))
            puntos.append(tuple(ini[0]))
        puntos.extend(tuple(p) for p in ini[1:])
        rest.extend([largo / partes] * partes)
        fin_tramo = len(puntos) - 1
        if i == len(tramos) - 1:
            fijos.append(fin_tramo)
        elif anclajes[i + 1].desliza:
            ganchos.append(tramo[-1])
        else:
            fijos.append(fin_tramo)
    if salida > 0:
        rest.append(vec.distancia(puntos[-1], c1))
        puntos.append(c1)
        fijos.append(len(puntos) - 1)
    cadena = reposo.Cadena(puntos, rest, fijos, ganchos)
    x = reposo.reposar(cadena, r, suelo=suelo, empujar=empujar, rigidez=a["rigidez"], otros=otros)
    return [tuple(float(c) for c in p) for p in x]


def _camino_colgante(a, anclajes, inicio, fin, r, suelo, bajar, res, empujar=None):
    """Catenarias entre anclajes, con la salida recta y los conectores de los extremos.

    Si el cable toca el suelo u otro objeto, o pasa por un gancho, se busca
    su reposo físico (ver ``reposo``); si cuelga libre, la catenaria es exacta.
    """
    primero, ultimo = anclajes[0], anclajes[-1]
    c0, s0, s1, c1, salida = _extremos(a, anclajes, inicio, fin)
    paradas = [s0] + [x.posicion for x in anclajes[1:-1]] + [s1]
    tramos, largos, toca = _catenarias(a, anclajes, paradas, r, suelo, bajar, res)
    ganchos = any(x.desliza for x in anclajes[1:-1])
    usar = a["reposo"] and reposo.disponible() and (toca or ganchos or _toca_objetos(empujar, tramos, r))
    if usar:
        camino = _reposar(a, anclajes, tramos, largos, c0, c1, salida, r, suelo, empujar, a["semilla"])
        res.reposado = True
        res.longitudes = largos
        for t in tramos:
            res.caida = max(res.caida, catenaria.caida(t))
        camino = _sobre_suelo(trazado.suavizar(camino), suelo, r)
    else:
        camino = [c0] if salida > 0 else []
        for i, tramo in enumerate(tramos):
            res.caida = max(res.caida, catenaria.caida(tramo))
            res.longitudes.append(vec.longitud_polilinea(tramo))
            camino.extend(tramo if i == 0 else tramo[1:])
        if salida > 0:
            camino.append(c1)
            radio = min(salida * 0.9, reposo.radio_minimo(r, a["rigidez"]))
            esquinas = {1, len(camino) - 2}
            camino, _ = trazado.redondear(camino, radio, pasos=5, solo=esquinas)
    camino = trazado.limpiar_repetidos(camino)
    marco_ini = vec.marco_desde_eje(primero.posicion, primero.normal)
    marco_fin = vec.marco_desde_eje(ultimo.posicion, ultimo.normal)
    return camino, marco_ini, marco_fin


def _haz_suelto(a, anclajes, inicio, fin, r, suelo, bajar, empujar, res):
    """Cada cable del haz con su propio recorrido, sin atravesar a los demás."""
    import random
    cantidad = max(1, int(a["haz"]))
    c0, s0, s1, c1, salida = _extremos(a, anclajes, inicio, fin)
    direccion = vec.resta(anclajes[-1].posicion, anclajes[0].posicion)
    lado = vec.cruz(direccion, (0.0, 1.0, 0.0))
    lado = vec.unitario(lado, (1.0, 0.0, 0.0))
    arriba = vec.unitario(vec.cruz(lado, direccion), (0.0, 1.0, 0.0))
    azar = random.Random(int(a["semilla"]) * 31 + 7)
    hilos = []
    for k, (x0, y0) in enumerate(perfiles.posiciones_haz(cantidad, 2.0 * r * 1.05)):
        o = vec.suma(vec.escala(lado, x0), vec.escala(arriba, y0))
        factor = 1.0 + max(0.0, a["variacion"]) * (azar.random() - 0.5) * 0.8
        paradas = [vec.suma(s0, o)] + [vec.suma(x.posicion, o) for x in anclajes[1:-1]] + [vec.suma(s1, o)]
        tramos, largos, _toca = _catenarias(a, anclajes, paradas, r, suelo, bajar, res, factor, contar=k == 0)
        if k == 0:
            res.longitudes = largos
            for t in tramos:
                res.caida = max(res.caida, catenaria.caida(t))
        camino = _reposar(a, anclajes, tramos, largos, vec.suma(c0, o), vec.suma(c1, o), salida, r, suelo,
                          empujar, a["semilla"] + k * 101, otros=hilos)
        hilos.append(camino)
    res.reposado = True
    return [trazado.limpiar_repetidos(_sobre_suelo(trazado.suavizar(h), suelo, r)) for h in hilos]


def _sobre_suelo(camino, suelo, r):
    if suelo is None:
        return camino
    return [(p[0], max(p[1], suelo + r), p[2]) for p in camino]


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
