"""Construye un cable o una tubería completos a partir de sus ajustes. Sin Maya.

El nodo de Maya reúne los datos (anclajes, curva, objetos de apoyo) y llama a
``construir``; aquí está toda la lógica, para poder probarla fuera de Maya.
"""

import math

from pipeeditor import apoyo, catenaria, perfiles, piezas, reposo, trazado, vec
from pipeeditor import malla as ml

TIPOS = ("cable", "tuberia")
MODOS_TENSION = ("holgura", "longitud")
CODOS = ("curvado", "pieza", "soldado")
EJES = ("y", "z")
SOPORTES_HACIA = ("cercana", "techo", "suelo")
NORMAS = ("libre", "acero", "cobre", "pvc", "desague", "multicapa", "ansi")

# Diámetros exteriores normalizados, en cm, con su espesor de pared.
# Acero: tubo DN (EN 10255 / ISO 65, serie media). Cobre: EN 1057.
# PVC a presión: EN 1452 (PN10). Desagüe: PVC EN 1329. Multicapa: PEX-AL-PEX.
# ANSI: acero ASME B36.10, Schedule 40 (de 1/2" a 12").
MEDIDAS = {
    "acero": ((2.13, 0.26), (2.69, 0.26), (3.37, 0.32), (4.24, 0.32), (4.83, 0.32), (6.03, 0.36),
              (7.61, 0.36), (8.89, 0.40), (11.43, 0.45), (13.97, 0.50), (16.83, 0.50), (21.91, 0.63),
              (27.30, 0.63), (32.39, 0.71)),
    "cobre": ((1.0, 0.1), (1.2, 0.1), (1.5, 0.1), (1.8, 0.1), (2.2, 0.1), (2.8, 0.12), (3.5, 0.15),
              (4.2, 0.15), (5.4, 0.2), (6.4, 0.2), (7.6, 0.2), (10.8, 0.25)),
    "pvc": ((2.5, 0.15), (3.2, 0.16), (4.0, 0.19), (5.0, 0.24), (6.3, 0.30), (7.5, 0.36), (9.0, 0.43),
            (11.0, 0.42), (12.5, 0.48), (16.0, 0.62), (20.0, 0.77), (25.0, 0.96), (31.5, 1.21)),
    "desague": ((3.2, 0.30), (4.0, 0.30), (5.0, 0.30), (7.5, 0.30), (9.0, 0.30), (11.0, 0.32), (12.5, 0.32),
                (16.0, 0.32), (20.0, 0.39)),
    "multicapa": ((1.6, 0.20), (2.0, 0.20), (2.6, 0.30), (3.2, 0.30), (4.0, 0.35), (5.0, 0.40), (6.3, 0.45)),
    "ansi": ((2.13, 0.277), (2.67, 0.287), (3.34, 0.338), (4.22, 0.356), (4.83, 0.368), (6.03, 0.391),
             (7.30, 0.516), (8.89, 0.549), (11.43, 0.602), (14.13, 0.655), (16.83, 0.711), (21.91, 0.818),
             (27.31, 0.927), (32.39, 1.031)),
}


def medida_normalizada(norma, grosor):
    """(diámetro, pared) normalizados más cercanos a ``grosor``, o None si la norma es libre."""
    tabla = MEDIDAS.get(norma)
    if not tabla:
        return None
    return min(tabla, key=lambda m: abs(math.log(max(grosor, 1e-6) / m[0])))


def separacion_soportes_auto(diametro):
    """Separación entre soportes según el diámetro (como en las tablas de montaje de acero):
    unos 1,8 m para DN15 y 5 m para DN200."""
    return 110.0 * math.sqrt(max(diametro, 0.1)) + 20.0

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
    "ondulacion": 0.2,           # memoria de bobina: ondas laterales
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
    "norma": "libre",            # medidas normalizadas: libre, acero (DN) o cobre
    "recorrido": "pegado",      # junto a las paredes y el suelo de los anclajes
    "tubos": 1,                  # varias tuberías en paralelo (rack)
    "separacion_tubos": 0.0,     # entre ejes; 0 = automática
    "radio_codo": 1.5,           # en diámetros de la tubería (1,5 = codo de radio largo)
    "codo": "curvado",
    "separacion_bridas": 0.0,
    "extremos": "abiertos",
    "pared": 0.0,
    "separacion_soportes": 0.0,
    "soportes_auto": False,      # separación de soportes según el diámetro
    "alcance_soportes": 60.0,
    "soportes_hacia": "cercana",  # superficie más cercana, o colgada del techo, o apoyada en el suelo
    "pendiente": 0.0,            # caída de los tramos horizontales (0,02 = 2 %), hacia el último anclaje
    "senales": "ninguna",        # flechas de sentido o bandas de color a lo largo
    "separacion_senales": 300.0,
}


class Anclaje(object):
    """Punto de anclaje: posición, normal (por dónde sale el cable) y factor de holgura."""

    def __init__(self, posicion, normal=(0.0, 1.0, 0.0), factor=1.0, longitud=0.0, desliza=False,
                 accesorio="ninguno"):
        self.posicion = tuple(posicion)
        self.normal = vec.unitario(normal)
        self.factor = factor
        self.longitud = longitud  # longitud fija del tramo que empieza aquí (0 = sin fijar)
        self.desliza = desliza    # punto intermedio por el que el cable pasa sin atarse (gancho)
        self.accesorio = accesorio  # tuberías: válvula, te o reducción en este punto (piezas.ACCESORIOS)


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
        self.recuento = {}  # para la lista de materiales: piezas y metros de tubo

    def contar(self, clave, cantidad=1):
        self.recuento[clave] = self.recuento.get(clave, 0) + cantidad

    def triangulos(self):
        return self.cuerpo.triangulos() + self.piezas.triangulos()


VERSION_DATOS = 1  # sube cada vez que un valor por defecto cambia lo que sale


def migrar(a, version):
    """Ajustes de un nodo guardado con una versión anterior, para que salga igual que entonces.

    Maya no guarda los atributos que están en su valor por defecto: si un
    defecto cambia, una escena antigua cambiaría al abrirla. Aquí se ponen los
    defectos que tenía cada versión.
    """
    a = dict(a)
    if version < 1:  # PipeEditor 1.0: sin reposo; las tuberías iban en Z
        a["reposo"] = False
        if a.get("recorrido") == "pegado":
            a["recorrido"] = "z"
    return a


def ajustes(**cambios):
    a = dict(POR_DEFECTO)
    a.update(cambios)
    return a


def construir(a, anclajes=(), ruta=None, ruta_lineal=False, bajar=None, cercano=None, malla_propia=None,
              empujar=None, obstaculos=(), cache=None):
    """Devuelve un ``Resultado``.

    ``anclajes``: lista de ``Anclaje`` (al menos dos), o vacía si hay ``ruta``.
    ``ruta``: puntos de una curva; ``ruta_lineal`` si la curva es de grado 1
    (sus esquinas se redondean).
    ``bajar(x, y, z)``: altura de la superficie bajo ese punto, o None.
    ``cercano(punto, tangente)``: (punto, normal) de la superficie más cercana, o None.
    ``empujar(P, radio)``: saca de los objetos de apoyo los puntos del array
    ``P`` (N×3); devuelve (P corregido, máscara de contacto). Ver ``reposo``.
    ``obstaculos``: cajas (mínimo, máximo) de los objetos que una tubería con
    recorrido «esquivar» no debe atravesar.
    ``cache``: diccionario que guarda el último recorrido de un cable (con
    ``firma_apoyos`` = lo que identifica los objetos de apoyo); si solo cambian
    ajustes que no lo mueven, no se vuelve a calcular el reposo.

    Con ``arriba = "z"`` todo llega y sale en coordenadas de la escena; por
    dentro se trabaja siempre con Y hacia arriba.
    """
    a = ajustes(**a)
    if a["arriba"] == "z":
        return _con_z_arriba(a, list(anclajes), ruta, ruta_lineal, bajar, cercano, malla_propia, empujar,
                             obstaculos, cache)
    if a["tipo"] == "tuberia":
        return _tuberia(a, list(anclajes), ruta, ruta_lineal, cercano, obstaculos)
    return _cable(a, list(anclajes), ruta, ruta_lineal, bajar, malla_propia, empujar, cache)


# --- eje vertical Z -------------------------------------------------------------------

def _a_interno(p):
    return (p[0], p[2], -p[1])


def _a_escena(p):
    return (p[0], -p[2], p[1])


def _con_z_arriba(a, anclajes, ruta, ruta_lineal, bajar, cercano, malla_propia, empujar, obstaculos=(),
                  cache=None):
    b = dict(a, arriba="y")
    if a.get("_forma"):
        guardada = forma_de_lista(a["_forma"])
        b["_forma"] = None
        if guardada is not None:
            r = Resultado()
            r.hilos = [[_a_interno(p) for p in h] for h in guardada[1]]
            b["_forma"] = forma_a_lista(r, [Anclaje(_a_interno(p)) for p in guardada[0]])
    anclajes = [Anclaje(_a_interno(x.posicion), _a_interno(x.normal), x.factor, x.longitud, x.desliza,
                        x.accesorio) for x in anclajes]
    ruta = [_a_interno(p) for p in ruta] if ruta is not None else None
    bajar_i = (lambda x, y, z: bajar(*_a_escena((x, y, z)))) if bajar is not None else None
    cercano_i = None
    if cercano is not None:
        def cercano_i(p, t, direccion=None):
            if direccion is None:
                golpe = cercano(_a_escena(p), _a_escena(t))
            else:
                golpe = cercano(_a_escena(p), _a_escena(t), _a_escena(direccion))
            if golpe is None:
                return None
            return _a_interno(golpe[0]), _a_interno(golpe[1])
    empujar_i = None
    if empujar is not None:
        def a_escena(P):
            import numpy as np
            P = np.asarray(P, dtype=float)
            return np.stack([P[:, 0], -P[:, 2], P[:, 1]], axis=1)

        def empujar_i(P, radio, antes=None):
            import numpy as np
            Q, contacto = empujar(a_escena(P), radio, None if antes is None else a_escena(antes))
            Q = np.asarray(Q, dtype=float)
            return np.stack([Q[:, 0], Q[:, 2], -Q[:, 1]], axis=1), contacto
    cajas = []
    for lo, hi in obstaculos:
        u, v = _a_interno(lo), _a_interno(hi)
        cajas.append((tuple(min(u[k], v[k]) for k in range(3)), tuple(max(u[k], v[k]) for k in range(3))))
    res = construir(b, anclajes, ruta, ruta_lineal, bajar_i, cercano_i, malla_propia, empujar_i, cajas, cache)
    res.cuerpo.vertices = [_a_escena(p) for p in res.cuerpo.vertices]
    res.piezas.vertices = [_a_escena(p) for p in res.piezas.vertices]
    res.curva = [_a_escena(p) for p in res.curva]
    res.hilos = [[_a_escena(p) for p in h] for h in res.hilos]
    return res


# --- cables ---------------------------------------------------------------------------

def _segmentos(longitud, a):
    return max(8, int(math.ceil(longitud / 100.0 * a["segmentos_metro"])))


# Ajustes que no cambian por dónde va el cable: si solo cambian estos, se
# reutiliza el recorrido ya calculado (el reposo es lo que más tarda).
_NO_CAMBIAN_RECORRIDO = ("lados", "perfil_cable", "torsion", "pieza", "separacion_piezas", "segmentos_metro",
                         "perfil_tuberia", "pared", "extremos", "separacion_bridas", "separacion_soportes",
                         "soportes_auto", "alcance_soportes", "codo", "norma", "tubos", "separacion_tubos",
                         "radio_codo", "recorrido")


def _clave(a, anclajes, cache):
    ajustes_ = tuple(sorted((k, v) for k, v in a.items() if k not in _NO_CAMBIAN_RECORRIDO))
    puntos = tuple((tuple(x.posicion), tuple(x.normal), x.factor, x.longitud, x.desliza) for x in anclajes)
    return (ajustes_, puntos, cache.get("firma_apoyos"))


def _de_cache(cache, a, anclajes, res):
    if cache is None or cache.get("clave") != _clave(a, anclajes, cache):
        return False
    for k, v in cache["res"].items():
        setattr(res, k, list(v) if isinstance(v, list) else v)
    res.hilos = [list(h) for h in cache["hilos"]]
    return True


def _a_cache(cache, a, anclajes, res, camino, marco_ini, marco_fin):
    if cache is None:
        return
    cache["clave"] = _clave(a, anclajes, cache)
    cache["camino"], cache["marco_ini"], cache["marco_fin"] = camino, marco_ini, marco_fin
    cache["hilos"] = [list(h) for h in res.hilos]
    cache["res"] = {"reposado": res.reposado, "longitudes": list(res.longitudes), "caida": res.caida,
                    "tensos": res.tensos}


def _cable(a, anclajes, ruta, ruta_lineal, bajar, malla_propia, empujar=None, cache=None):
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
    elif len(anclajes) >= 2 and _forma_valida(a.get("_forma"), anclajes, cantidad if suelto else 1):
        hilos = deformar_forma(a["_forma"], anclajes)
        camino = hilos[0]
        res.hilos = hilos if len(hilos) > 1 else []
        res.longitudes = [vec.longitud_polilinea(camino)]
        res.reposado = True
        marco_ini = vec.marco_desde_eje(anclajes[0].posicion, anclajes[0].normal)
        marco_fin = vec.marco_desde_eje(anclajes[-1].posicion, anclajes[-1].normal)
    elif len(anclajes) >= 2 and _de_cache(cache, a, anclajes, res):
        camino, marco_ini, marco_fin = cache["camino"], cache["marco_ini"], cache["marco_fin"]
    elif len(anclajes) >= 2 and suelto:
        res.hilos = _haz_suelto(a, anclajes, inicio, fin, r, suelo, bajar, empujar, res)
        camino = res.hilos[0]
        marco_ini = vec.marco_desde_eje(anclajes[0].posicion, anclajes[0].normal)
        marco_fin = vec.marco_desde_eje(anclajes[-1].posicion, anclajes[-1].normal)
        _a_cache(cache, a, anclajes, res, camino, marco_ini, marco_fin)
    elif len(anclajes) >= 2:
        camino, marco_ini, marco_fin = _camino_colgante(a, anclajes, inicio, fin, r_total, suelo, bajar, res,
                                                        empujar)
        _a_cache(cache, a, anclajes, res, camino, marco_ini, marco_fin)
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
    if res.hilos:
        res.contar("cable_{:.2f}".format(2.0 * r), sum(vec.longitud_polilinea(h) for h in res.hilos))
    else:
        res.contar("cable_{:.2f}".format(2.0 * r), res.longitud * cantidad)
    if not inicio.malla.vacia():
        res.piezas.anadir(inicio.malla, marco_ini)
        res.contar("conector_" + a["conector_inicio"])
    if not fin.malla.vacia():
        res.piezas.anadir(fin.malla, marco_fin)
        res.contar("conector_" + a["conector_fin"])
    margen = max(inicio.largo, fin.largo) + a["salida"] + r_total * 4
    if a["pieza"] != "ninguna" and a["separacion_piezas"] > 0:
        modelo = piezas.pieza_cable(a["pieza"], r if res.hilos else r_total)
        for h in (res.hilos or [camino]):
            for p, t, _s in trazado.uniforme(h, a["separacion_piezas"], margen=margen):
                res.piezas.anadir(modelo, vec.marco_desde_eje(p, t))
                res.contar("pieza_" + a["pieza"])
    if cantidad > 1 and a["separacion_bridas_haz"] > 0:
        modelo = piezas.brida_haz(r_total)
        for p, t, _s in trazado.uniforme(camino, a["separacion_bridas_haz"], margen=margen):
            res.piezas.anadir(modelo, vec.marco_desde_eje(p, t))
            res.contar("bridas_haz")
    return res


# --- forma fijada ----------------------------------------------------------------------
# «Asentar y fijar» guarda la forma del cable (y dónde estaban sus anclajes)
# en una lista de números: [nº anclajes, x y z de cada uno, nº hilos, puntos de
# cada hilo, x y z de cada punto]. Mientras esté guardada, el cable no se
# vuelve a calcular: si se mueve un anclaje, la forma se estira hasta él.

def forma_a_lista(res, anclajes):
    hilos = res.hilos or ([res.curva] if res.curva else [])
    if len(anclajes) < 2 or not hilos:
        return []
    datos = [float(len(anclajes))]
    for x in anclajes:
        datos.extend(float(c) for c in x.posicion)
    datos.append(float(len(hilos)))
    datos.extend(float(len(h)) for h in hilos)
    for h in hilos:
        for p in h:
            datos.extend(float(c) for c in p)
    return datos


def forma_de_lista(datos):
    """(anclajes, hilos) guardados, o None si la lista no es válida."""
    try:
        datos = list(datos or [])
        k = int(datos[0])
        anclas = [tuple(datos[1 + 3 * i:4 + 3 * i]) for i in range(k)]
        i = 1 + 3 * k
        h = int(datos[i])
        cuentas = [int(c) for c in datos[i + 1:i + 1 + h]]
        i += 1 + h
        hilos = []
        for c in cuentas:
            hilos.append([tuple(datos[i + 3 * j:i + 3 * j + 3]) for j in range(c)])
            i += 3 * c
        if k < 2 or not hilos or i != len(datos) or any(len(x) < 2 for x in hilos):
            return None
        return anclas, hilos
    except (IndexError, ValueError, TypeError):
        return None


def _forma_valida(forma, anclajes, hilos_esperados):
    if not forma:
        return False
    guardada = forma_de_lista(forma)
    return (guardada is not None and len(guardada[0]) == len(anclajes)
            and len(guardada[1]) == hilos_esperados)


def deformar_forma(forma, anclajes):
    """La forma guardada, estirada para que siga a los anclajes donde están ahora.

    Cada punto se mueve lo que se han movido los anclajes que tiene a los
    lados, repartido según la distancia a lo largo del cable.
    """
    anclas, hilos = forma_de_lista(forma)
    nuevas = [x.posicion for x in anclajes]
    movidos = [vec.resta(n, v) for n, v in zip(nuevas, anclas)]
    salida = []
    for h in hilos:
        s = vec.acumulada(h)
        total = s[-1] if s[-1] > 0 else 1.0
        # dónde cae cada anclaje a lo largo del hilo
        donde = [0.0]
        for v in anclas[1:-1]:
            j = min(range(len(h)), key=lambda j: vec.distancia(h[j], v))
            donde.append(max(donde[-1], s[j]))
        donde.append(total)
        nuevo = []
        tramo = 0
        for p, sp in zip(h, s):
            while tramo < len(donde) - 2 and sp > donde[tramo + 1]:
                tramo += 1
            a0, a1 = donde[tramo], donde[tramo + 1]
            u = (sp - a0) / (a1 - a0) if a1 > a0 else 0.0
            d = vec.mezcla(movidos[tramo], movidos[tramo + 1], u)
            nuevo.append(vec.suma(p, d))
        salida.append(nuevo)
    return salida


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
    """Catenaria apoyada de cada tramo, su longitud y si toca algo.

    Deja en ``_catenarias.contactos`` qué puntos de cada tramo se apoyan.
    """
    tramos, largos, toca, contactos = [], [], False, []
    for i in range(len(paradas) - 1):
        p, q = paradas[i], paradas[i + 1]
        largo = _largo_tramo(a, anclajes[i], p, q, factor)
        if contar and catenaria.esta_tenso(p, q, largo):
            res.tensos += 1
        libre = catenaria.puntos(p, q, largo, _segmentos(largo, a))
        tramo = apoyo.apoyar_tramo(libre, r, suelo, bajar)
        if any(abs(u[1] - v[1]) > 1e-9 for u, v in zip(libre, tramo)):
            toca = True
        # Extremo apoyado en una mesa: el cable va por encima hasta el borde y
        # cae por él (si no, el reposo empieza con el cable bajo el tablero).
        bajo = min(v[1] for v in libre)
        antes = _por_el_borde(p, q, r, suelo, bajar, bajo)
        despues = _por_el_borde(q, p, r, suelo, bajar, bajo)
        if antes or despues:
            toca = True
            a0 = antes[-1] if antes else p
            a1 = despues[-1] if despues else q
            resto = largo - vec.longitud_polilinea(antes) - vec.longitud_polilinea(despues)
            resto = max(resto, vec.distancia(a0, a1) * 1.01)
            medio = apoyo.apoyar_tramo(catenaria.puntos(a0, a1, resto, _segmentos(resto, a)), r, suelo, bajar)
            tramo = (antes or [p]) + medio[1:-1] + list(reversed(despues or [q]))
        # Solo lo tumbado en el suelo recibe las curvas del sobrante; sobre una
        # mesa, el sobrante cae por los bordes con el reposo.
        apoyados = [suelo is not None and v[1] <= suelo + r + 1e-6 for v in tramo]
        tramos.append(tramo)
        largos.append(largo)
        contactos.append(apoyados)
    _catenarias.contactos = contactos
    return tramos, largos, toca


def _por_el_borde(p, otro, r, suelo, bajar, bajo):
    """Camino sobre la superficie en la que se apoya ``p`` hasta su borde, hacia ``otro``.

    Devuelve [] si ``p`` no está sobre una mesa (o algo elevado) o si el cable
    no tiene que bajar de ella.
    """
    if bajar is None:
        return []
    h = bajar(p[0], p[1], p[2])
    if h is None or (suelo is not None and h <= suelo + 2.0 * r) or p[1] - h > 30.0 or bajo >= h - r:
        return []
    d = (otro[0] - p[0], 0.0, otro[2] - p[2])
    largo = math.hypot(d[0], d[2])
    if largo < 1e-6:
        return []
    d = (d[0] / largo, 0.0, d[2] / largo)
    paso = max(r, 1.0)
    t = 0.0
    while t < largo:
        t += paso
        hh = bajar(p[0] + d[0] * t, p[1], p[2] + d[2] * t)
        if hh is None or hh < h - max(2.0 * r, 1.0):
            break
    else:
        return []
    camino = [tuple(p)]
    y = h + r
    partes = max(1, int(t / max(paso * 4.0, 5.0)))
    for k in range(1, partes + 1):
        u = (t - paso) * k / float(partes)
        camino.append((p[0] + d[0] * u, y, p[2] + d[2] * u))
    fuera = t + 2.0 * r
    camino.append((p[0] + d[0] * fuera, y, p[2] + d[2] * fuera))
    return camino


def _toca_objetos(empujar, tramos, r):
    if empujar is None:
        return False
    import numpy as np
    P = np.array([p for t in tramos for p in t], dtype=float)
    _Q, contacto = empujar(P, r)
    return bool(np.any(contacto))


def _reposar(a, anclajes, tramos, largos, c0, c1, salida, r, suelo, empujar, semilla, contactos=None,
             pasos=110):
    """Reposo de un cable a partir de sus catenarias apoyadas."""
    cadena = _cadena(a, anclajes, tramos, largos, c0, c1, salida, r, semilla, contactos)
    if a.get("_borrador"):
        pasos = max(25, pasos // 3)
    x = reposo.reposar(cadena, r, suelo=suelo, empujar=empujar, rigidez=a["rigidez"], pasos=pasos)
    return [tuple(float(c) for c in p) for p in x]


def _cadena(a, anclajes, tramos, largos, c0, c1, salida, r, semilla, contactos=None, puntos_max=180):
    """Cadena de puntos para el reposo, con el cable que sobra ya repartido en el suelo."""
    total = sum(largos)
    paso = max(total / float(puntos_max), r * 1.5)
    contactos = contactos or [[False] * len(t) for t in tramos]
    puntos, rest, fijos, ganchos = [], [], [], []
    if salida > 0:
        puntos.append(c0)
        rest.append(vec.distancia(c0, tramos[0][0]))
        fijos.append(0)
    amplitud = r * (0.02 + 6.0 * max(0.0, a["ondulacion"]))
    for i, (tramo, largo) in enumerate(zip(tramos, largos)):
        partes = max(3, int(round(largo / paso)))
        # El cable que sobra se reparte en curvas amplias donde está tumbado.
        tumbado = reposo.ondas_suelo(tramo, largo, r, a["rigidez"], semilla * 7919 + i, contactos[i])
        ini = reposo.repartir(tumbado, partes)
        ini = reposo.ondulacion(ini, amplitud, semilla * 7919 + i, max(r * 70.0, largo / 3.0))
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
    return reposo.Cadena(puntos, rest, fijos, ganchos)


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
        camino = _reposar(a, anclajes, tramos, largos, c0, c1, salida, r, suelo, empujar, a["semilla"],
                          contactos=_catenarias.contactos)
        res.reposado = True
        res.longitudes = largos
        for t in tramos:
            res.caida = max(res.caida, catenaria.caida(t))
        if salida > 0:
            rmin = reposo.radio_minimo(r, a["rigidez"])
            camino = _curva_de_salida(camino, primero.normal, rmin)
            camino = list(reversed(_curva_de_salida(list(reversed(camino)), ultimo.normal, rmin)))
        camino = _fuera_de_objetos(_sobre_suelo(trazado.suavizar(camino), suelo, r), empujar, r)
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


def _curva_de_salida(camino, normal, rmin):
    """Une la salida recta del conector con el resto del cable sin esquina.

    ``camino[0]`` es la punta del conector y ``camino[1]`` el final de la
    salida recta (en la dirección ``normal``). Un cable rígido no dobla ahí en
    seco: se cambia el principio del camino por una curva (Hermite) que sale
    en la dirección de la salida y llega tangente al cable, con largo
    suficiente para no doblar más que ``rmin``.
    """
    if len(camino) < 4:
        return camino
    c0 = camino[0]
    salida = vec.distancia(c0, camino[1])
    s = vec.acumulada(camino)
    # dirección del cable justo después de la salida
    j = 2
    while j < len(camino) - 1 and s[j] - s[1] < max(salida, rmin * 0.25):
        j += 1
    t = vec.unitario(vec.resta(camino[j], camino[1]), normal)
    giro = math.acos(max(-1.0, min(1.0, vec.punto(vec.unitario(normal), t))))
    if giro < math.radians(3.0):
        return camino
    # largo de la curva: lo que hace falta para girar ``giro`` con radio rmin
    largo = salida + rmin * giro
    k = 2
    while k < len(camino) - 2 and s[k] < largo:
        k += 1
    if k >= len(camino) - 2:
        return camino
    p1 = camino[k]
    t1 = vec.unitario(vec.resta(camino[k + 1], camino[k - 1]), t)
    d = vec.distancia(c0, p1)
    m0 = vec.escala(vec.unitario(normal), d)
    m1 = vec.escala(t1, d)
    partes = max(6, int(math.ceil(giro / math.radians(3.0))))
    curva = []
    for i in range(partes):
        u = i / float(partes)
        h00, h10 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u
        h01, h11 = -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        curva.append(tuple(c0[n] * h00 + m0[n] * h10 + p1[n] * h01 + m1[n] * h11 for n in range(3)))
    return curva + list(camino[k:])


def _haz_suelto(a, anclajes, inicio, fin, r, suelo, bajar, empujar, res):
    """Cada cable del haz con su propio recorrido, sin atravesar a los demás.

    Todos parten de la forma del cable del centro (desplazada a su sitio), así
    se tumban juntos como un mazo; cada uno tiene su propia longitud
    (``variacion``) y el reposo hace que cuelguen distinto y se aparten.
    """
    import random
    cantidad = max(1, int(a["haz"]))
    c0, s0, s1, c1, salida = _extremos(a, anclajes, inicio, fin)
    direccion = vec.resta(anclajes[-1].posicion, anclajes[0].posicion)
    lado = vec.cruz(direccion, (0.0, 1.0, 0.0))
    lado = vec.unitario(lado, (1.0, 0.0, 0.0))
    arriba = vec.unitario(vec.cruz(lado, direccion), (0.0, 1.0, 0.0))
    azar = random.Random(int(a["semilla"]) * 31 + 7)
    r_total = perfiles.radio_haz(cantidad, r)
    paradas = [s0] + [x.posicion for x in anclajes[1:-1]] + [s1]
    tramos, largos, _toca = _catenarias(a, anclajes, paradas, r_total, suelo, bajar, res)
    res.longitudes = largos
    for t in tramos:
        res.caida = max(res.caida, catenaria.caida(t))
    centro = _cadena(a, anclajes, tramos, largos, c0, c1, salida, r, a["semilla"], _catenarias.contactos,
                     puntos_max=int(min(220, max(120, sum(largos) / (2.5 * r)))))
    rectos = set()
    if salida > 0:
        rectos = {0, len(centro.largos) - 1}
    holgura = max(a["holgura"], 0.0)
    cadenas = []
    for k, (x0, y0) in enumerate(perfiles.posiciones_haz(cantidad, 2.0 * r * 1.05)):
        o = vec.suma(vec.escala(lado, x0), vec.escala(arriba, y0))
        factor = 1.0 + max(0.0, a["variacion"]) * (azar.random() - 0.5) * 0.8 if k else 1.0
        escala = (1.0 + holgura * factor) / (1.0 + holgura)
        puntos = [vec.suma(p, o) for p in centro.puntos]
        rest = [l if i in rectos else l * escala for i, l in enumerate(centro.largos)]
        cadenas.append(reposo.Cadena(puntos, rest, centro.fijos, [vec.suma(g, o) for g in centro.ganchos]))
    # Todos a la vez, sin atravesarse entre sí.
    resultado = reposo.reposar_varias(cadenas, r * 1.02, suelo=suelo, empujar=empujar, rigidez=a["rigidez"],
                                      pasos=25 if a.get("_borrador") else 70)
    hilos = [[tuple(float(c) for c in p) for p in x] for x in resultado]
    res.reposado = True
    return [trazado.limpiar_repetidos(_fuera_de_objetos(_sobre_suelo(trazado.suavizar(h), suelo, r), empujar, r))
            for h in hilos]


def _fuera_de_objetos(camino, empujar, r):
    """Saca de los objetos lo que el suavizado mete en ellos (en los cantos donde el cable dobla)."""
    if empujar is None or len(camino) < 3:
        return camino
    import numpy as np
    # Más puntos donde haga falta: una cuerda larga corta la arista aunque sus extremos estén fuera.
    paso = max(r * 1.5, 0.3)
    denso = [camino[0]]
    for p, q in zip(camino, camino[1:]):
        partes = max(1, int(math.ceil(vec.distancia(p, q) / paso)))
        denso.extend(vec.mezcla(p, q, k / float(partes)) for k in range(1, partes + 1))
    P = np.array(denso, dtype=float)
    for _ in range(2):
        Q, _c = empujar(P, r)
        P[1:-1] = np.asarray(Q, dtype=float)[1:-1]
    return [tuple(float(c) for c in p) for p in P]


def _sobre_suelo(camino, suelo, r):
    if suelo is None:
        return camino
    return [(p[0], max(p[1], suelo + r), p[2]) for p in camino]


# --- tuberías -------------------------------------------------------------------------

def _tuberia(a, anclajes, ruta, ruta_lineal, cercano, obstaculos=()):
    res = Resultado()
    medida = medida_normalizada(a["norma"], a["grosor"])
    if medida is not None:
        a = dict(a, grosor=medida[0], pared=medida[1] if a["pared"] > 0 else 0.0)
    R = max(a["grosor"], 1e-4) / 2.0
    R_fuera = R * (1.35 if a["perfil_tuberia"] == "aislada" else 1.0)
    radio_codo = max(0.0, a["radio_codo"]) * 2.0 * R
    cantidad = max(1, int(a["tubos"]))
    separacion = a["separacion_tubos"] if a["separacion_tubos"] > 0 else R_fuera * 2.0 * 1.6
    desplazamientos = [(k - (cantidad - 1) / 2.0) * separacion for k in range(cantidad)]
    # Con varias tuberías, el codo de la de dentro mantiene el radio pedido.
    radio_base = radio_codo + max(abs(d) for d in desplazamientos)

    recorridos = []  # (camino, codos) de cada tubería
    if ruta is not None and len(ruta) >= 2:
        if ruta_lineal:
            polilinea = trazado.limpiar([tuple(p) for p in ruta])
            for d in desplazamientos:
                pts, radios = trazado.paralela(polilinea, d, radio_base if cantidad > 1 else radio_codo)
                recorridos.append(trazado.redondear(pts, radio_codo, pasos=14, radios=radios))
        else:
            base = [tuple(p) for p in ruta]
            marcos = trazado.marcos(base)
            for d in desplazamientos:
                pts = base if not d else [vec.suma(p, vec.escala(m[2], d)) for p, m in zip(base, marcos)]
                recorridos.append((pts, []))
    elif len(anclajes) >= 2:
        salida = max(0.0, a["salida"])
        primero, ultimo = anclajes[0], anclajes[-1]
        s0 = vec.suma(primero.posicion, vec.escala(primero.normal, salida))
        s1 = vec.suma(ultimo.posicion, vec.escala(ultimo.normal, salida))
        paradas = [s0] + [x.posicion for x in anclajes[1:-1]] + [s1]
        medio = None
        if a["recorrido"] == "esquivar" and obstaculos:
            medio = [paradas[0]]
            for p, q in zip(paradas, paradas[1:]):
                tramo = trazado.esquivar(p, q, obstaculos, R_fuera + max(separacion * (cantidad - 1) / 2.0, 0.0)
                                         + R_fuera)
                if tramo is None:
                    tramo = trazado.recorrido_ortogonal([p, q], "z")
                medio.extend(tramo[1:])
            medio = trazado.limpiar(medio)
        if medio is None and a["recorrido"] == "pegado":
            medio = [paradas[0]]
            for i, (p, q) in enumerate(zip(paradas, paradas[1:])):
                medio.extend(trazado.pegado(p, anclajes[i].normal, q, anclajes[i + 1].normal)[1:])
            medio = trazado.limpiar(medio)
        if medio is None:
            modo = a["recorrido"] if a["recorrido"] in ("z", "l", "libre") else "z"
            medio = trazado.recorrido_ortogonal(paradas, modo)
        polilinea = ([primero.posicion] if salida > 0 else []) + medio + ([ultimo.posicion] if salida > 0 else [])
        polilinea = trazado.limpiar(polilinea)
        if a["pendiente"] > 0:
            polilinea = trazado.con_pendiente(polilinea, a["pendiente"])
        # Rack de un recorrido plano junto a una pared: tuberías apiladas a lo
        # largo de la pared (no tapándose unas a otras), con los mismos codos.
        lado = trazado.normal_plano(polilinea) if cantidad > 1 else None
        if lado is not None and abs(vec.punto(lado, primero.normal)) > 0.1:
            lado = None
        for d in desplazamientos:
            pts, radios = trazado.paralela(polilinea, d, radio_base if cantidad > 1 else radio_codo, lado=lado)
            recorridos.append(trazado.redondear(pts, radio_codo, pasos=14, radios=radios))
    else:
        return res
    recorridos = [(c, k) for c, k in recorridos if len(c) >= 2]
    if not recorridos:
        return res
    con_accesorios = [x for x in anclajes if x.accesorio != "ninguno"] if ruta is None else []
    for camino, codos in recorridos:
        if con_accesorios:
            _vestir_con_accesorios(a, res, camino, codos, R, R_fuera, cercano, anclajes)
        else:
            _vestir_tuberia(a, res, camino, codos, R, R_fuera, cercano)
    medio = recorridos[len(recorridos) // 2][0]
    res.curva = medio
    res.longitud = vec.longitud_polilinea(medio)
    res.longitudes = [res.longitud]
    return res


def _radio_menor(a, R):
    """(radio, pared) de la medida siguiente más pequeña, para una reducción."""
    tabla = MEDIDAS.get(a["norma"])
    if tabla:
        menores = [m for m in tabla if m[0] / 2.0 < R * 0.98]
        if menores:
            return menores[-1][0] / 2.0, menores[-1][1] if a["pared"] > 0 else 0.0
    return R * 0.7, a["pared"] * 0.7


def _distancia_en(camino, s, p):
    """Distancia a lo largo de ``camino`` del punto más cercano a ``p``."""
    mejor, donde = float("inf"), 0.0
    for i, (u, v) in enumerate(zip(camino, camino[1:])):
        d = vec.resta(v, u)
        largo2 = vec.punto(d, d)
        t = 0.0 if largo2 < 1e-12 else max(0.0, min(1.0, vec.punto(vec.resta(p, u), d) / largo2))
        q = vec.suma(u, vec.escala(d, t))
        dist = vec.distancia(q, p)
        if dist < mejor:
            mejor, donde = dist, s[i] + t * math.sqrt(largo2)
    return donde


def _tramo(camino, codos, s, d0, d1):
    """Trozo de ``camino`` entre las distancias ``d0`` y ``d1``, con sus codos."""
    dentro = [i for i in range(len(camino)) if d0 + 1e-6 < s[i] < d1 - 1e-6]
    puntos = [trazado.en_distancia(camino, d0)[0]] + [camino[i] for i in dentro] + \
        [trazado.en_distancia(camino, d1)[0]]
    desplazar = (dentro[0] - 1) if dentro else 0
    nuevos = []
    for c in codos:
        if s[c.indice_inicio] >= d0 and s[c.indice_fin] <= d1 and dentro:
            nuevos.append(trazado.Codo(c.inicio, c.fin, c.tangente_inicio, c.tangente_fin,
                                       c.indice_inicio - desplazar, c.indice_fin - desplazar, c.angulo))
    return trazado.limpiar_repetidos(puntos), nuevos


def _vestir_con_accesorios(a, res, camino, codos, R, R_fuera, cercano, anclajes):
    """Tubería con válvulas, tes y reducciones en sus anclajes.

    Una reducción en un anclaje intermedio hace que, a partir de ahí, la
    tubería sea de la medida siguiente más pequeña. En un extremo, deja la
    salida a esa medida para seguir con otra tubería.
    """
    s = vec.acumulada(camino)
    total = s[-1]
    factor = R_fuera / R
    sitios = [(_distancia_en(camino, s, x.posicion), x) for x in anclajes]
    sitios[0] = (0.0, anclajes[0])
    sitios[-1] = (total, anclajes[-1])
    # tramos entre reducciones
    radios, cortes = [(R, a["pared"])], []
    for d, x in sorted(sitios[1:-1], key=lambda e: e[0]):
        if x.accesorio == "reduccion" and 0 < d < total:
            radios.append(_radio_menor(dict(a, pared=radios[-1][1]), radios[-1][0]))
            cortes.append(d)
    largos = [max(radios[k][0] * factor * 1.6, (radios[k][0] - radios[k + 1][0]) * factor * 3.0)
              for k in range(len(cortes))]
    inicio = 0.0
    for k in range(len(radios)):
        Rk, pared = radios[k]
        fin = cortes[k] - largos[k] / 2.0 if k < len(cortes) else total
        if fin - inicio > 1e-3:
            pts, cods = _tramo(camino, codos, s, inicio, fin)
            if len(pts) >= 2:
                ak = dict(a, grosor=2.0 * Rk, pared=pared)
                quitar = set()
                if k > 0:
                    quitar.add("inicio")
                if k < len(cortes):
                    quitar.add("fin")
                if anclajes[0].accesorio == "reduccion" and k == 0:
                    quitar.add("inicio")
                if anclajes[-1].accesorio == "reduccion" and k == len(radios) - 1:
                    quitar.add("fin")
                _vestir_tuberia(ak, res, pts, cods, Rk, Rk * factor, cercano, sin_extremos=quitar)
        if k < len(cortes):
            p, t = trazado.en_distancia(camino, cortes[k])
            res.piezas.anadir(piezas.reduccion(Rk * factor, radios[k + 1][0] * factor),
                              vec.marco_desde_eje(p, t))
            res.contar("reducciones")
            inicio = cortes[k]

    def radio_en(d):
        for k, c in enumerate(cortes):
            if d < c:
                return radios[k][0]
        return radios[-1][0]

    for d, x in sitios:
        if x.accesorio == "ninguno":
            continue
        if x.accesorio == "reduccion":
            if d <= 0.0 or d >= total:  # en un extremo: reducción hacia fuera
                Rk = radio_en(d)
                r, _pared = _radio_menor(a, Rk)
                p, t = trazado.en_distancia(camino, min(max(d, 1e-6), total))
                fuera = vec.escala(t, -1.0) if d <= 0.0 else t
                largo = max(Rk * factor * 1.6, (Rk - r) * factor * 3.0)
                res.piezas.anadir(piezas.reduccion(Rk * factor, r * factor),
                                  vec.marco_desde_eje(vec.suma(p, vec.escala(fuera, largo / 2.0)), fuera))
                res.contar("reducciones")
            continue
        p, t = trazado.en_distancia(camino, min(max(d, 1e-6), total - 1e-6))
        res.piezas.anadir(piezas.accesorio(x.accesorio, radio_en(d) * factor),
                          vec.marco_desde_eje(p, t, x.normal))
        res.contar({"te": "tes", "valvula_bola": "valvulas_bola",
                    "valvula_compuerta": "valvulas_compuerta"}.get(x.accesorio, x.accesorio))


def _vestir_tuberia(a, res, camino, codos, R, R_fuera, cercano, sin_extremos=()):
    """Cuerpo y piezas de una tubería ya trazada."""
    abierta = a["extremos"] == "abiertos"
    res.cuerpo.anadir(perfiles.cuerpo_tuberia(camino, R, a["perfil_tuberia"], max(a["lados"], 8), a["pared"],
                                              abierta))
    res.contar("tubo_{:.2f}".format(2.0 * R), vec.longitud_polilinea(camino))
    res.contar("codos_{:.2f}".format(2.0 * R), len(codos))

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
            res.contar("manguitos", 2)
    # Codos soldados: el codo es una pieza algo más gruesa, con un cordón de soldadura a cada lado.
    if a["codo"] == "soldado":
        cordon = piezas.cordon(R_fuera)
        for c in codos:
            tramo = camino[max(0, c.indice_inicio):c.indice_fin + 1]
            if len(tramo) >= 2:
                res.piezas.anadir(perfiles.cuerpo_tuberia(tramo, R_fuera * 1.045, a["perfil_tuberia"]
                                                          if a["perfil_tuberia"] != "aislada" else "redonda",
                                                          max(a["lados"], 8)))
            res.piezas.anadir(cordon, vec.marco_desde_eje(c.inicio, c.tangente_inicio))
            res.piezas.anadir(cordon, vec.marco_desde_eje(c.fin, c.tangente_fin))
    # Bridas: repartidas en los tramos rectos y a los dos lados de cada codo.
    if a["separacion_bridas"] > 0:
        b = piezas.brida_tuberia(R_fuera)
        for p, t, d in trazado.uniforme(camino, a["separacion_bridas"], margen=R_fuera * 2):
            if en_recta(d):
                res.piezas.anadir(b, vec.marco_desde_eje(p, t))
                res.contar("bridas")
        hueco = R_fuera * (1.0 if a["codo"] == "pieza" else 0.35)
        for c in codos:
            res.piezas.anadir(b, vec.marco_desde_eje(vec.resta(c.inicio, vec.escala(c.tangente_inicio, hueco)),
                                                     c.tangente_inicio))
            res.piezas.anadir(b, vec.marco_desde_eje(vec.suma(c.fin, vec.escala(c.tangente_fin, hueco)),
                                                     c.tangente_fin))
            res.contar("bridas", 2)
    # Fajas de la tubería aislada, cada metro.
    if a["perfil_tuberia"] == "aislada":
        f = piezas.faja(R)
        for p, t, d in trazado.uniforme(camino, 100.0, margen=R * 2):
            if en_recta(d):
                res.piezas.anadir(f, vec.marco_desde_eje(p, t))
    # Señales: flechas de sentido y bandas de color en los tramos rectos.
    if a["senales"] != "ninguna" and a["separacion_senales"] > 0:
        con_banda = a["senales"] in ("banda", "flecha_y_banda")
        con_flecha = a["senales"] in ("flecha", "flecha_y_banda")
        mb, mf = piezas.banda(R_fuera), piezas.flecha(R_fuera)
        ancho = min(max(2.0 * R_fuera, 5.0), 25.0)
        avance = (ancho / 2.0 + piezas.largo_flecha(R_fuera) * 0.6) if con_banda else 0.0
        arriba = (0.0, 1.0, 0.0)
        for p, t, d in trazado.uniforme(camino, a["separacion_senales"], margen=R_fuera * 6):
            if not en_recta(d):
                continue
            if con_banda:
                res.piezas.anadir(mb, vec.marco_desde_eje(p, t, arriba))
            if con_flecha and en_recta(d + avance) and d + avance < s[-1] - R_fuera * 3:
                q = trazado.en_distancia(camino, d + avance)[0] if avance else p
                res.piezas.anadir(mf, vec.marco_desde_eje(q, t, arriba))
    # Extremos.
    t0 = vec.unitario(vec.resta(camino[0], camino[1]))
    t1 = vec.unitario(vec.resta(camino[-1], camino[-2]))
    extremos = [(camino[0], t0)] if "inicio" not in sin_extremos else []
    if "fin" not in sin_extremos:
        extremos.append((camino[-1], t1))
    if a["extremos"] == "tapon":
        tp = piezas.tapon(R_fuera)
        for p, t in extremos:
            res.piezas.anadir(tp, vec.marco_desde_eje(p, t))
            res.contar("tapones")
    elif a["extremos"] == "brida":
        b = piezas.brida_tuberia(R_fuera)
        for p, t in extremos:
            res.piezas.anadir(b, vec.marco_desde_eje(vec.suma(p, vec.escala(t, -R_fuera * 0.18)), t))
            res.contar("bridas")
    # Soportes a la pared más cercana.
    separacion = separacion_soportes_auto(2.0 * R) if a["soportes_auto"] else a["separacion_soportes"]
    if separacion > 0 and cercano is not None:
        for p, t, d in trazado.uniforme(camino, separacion, margen=R_fuera * 3):
            if not en_recta(d):
                continue
            if a["soportes_hacia"] == "cercana":
                golpe = cercano(p, t)
            else:
                golpe = cercano(p, t, (0.0, 1.0, 0.0) if a["soportes_hacia"] == "techo" else (0.0, -1.0, 0.0))
            if golpe is None:
                continue
            contacto, normal = golpe
            if vec.distancia(p, contacto) > a["alcance_soportes"] + R_fuera:
                continue
            res.piezas.anadir(piezas.soporte(R_fuera, p, t, contacto, normal))
            res.contar("soportes")
    return res
