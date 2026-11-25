"""Recorridos: tuberías en ángulo recto, codos redondeados, remuestreo y marcos.

Todo con tuplas, sin Maya.
"""

import math

from pipeeditor import vec

RECORRIDOS = ("z", "l", "libre", "esquivar")


def ortogonal(p, q, modo="z", tolerancia=1e-4):
    """Esquinas intermedias para ir de ``p`` a ``q`` solo por los ejes X, Y y Z.

    ``modo`` «z»: mitad del eje más largo, los otros ejes y la otra mitad.
    ``modo`` «l»: primero el eje más largo entero y después los demás.
    ``modo`` «libre»: ninguna esquina (en línea recta).
    No incluye ni ``p`` ni ``q``.
    """
    if modo == "libre":
        return []
    d = vec.resta(q, p)
    escala = max(abs(d[0]), abs(d[1]), abs(d[2]), 1e-9)
    ejes = [i for i in sorted(range(3), key=lambda i: -abs(d[i])) if abs(d[i]) > tolerancia * escala]
    if len(ejes) <= 1:
        return []
    principal, resto = ejes[0], ejes[1:]
    esquinas = []
    actual = list(p)
    if modo == "z":
        actual[principal] += d[principal] / 2.0
        esquinas.append(tuple(actual))
        for eje in resto:
            actual[eje] += d[eje]
            esquinas.append(tuple(actual))
        # la última esquina ya está alineada con q en el eje principal
    else:
        actual[principal] += d[principal]
        esquinas.append(tuple(actual))
        for eje in resto[:-1]:
            actual[eje] += d[eje]
            esquinas.append(tuple(actual))
    return esquinas


def recorrido_ortogonal(puntos, modo="z"):
    """La polilínea completa que une ``puntos`` en ángulo recto."""
    if not puntos:
        return []
    salida = [tuple(puntos[0])]
    for p, q in zip(puntos, puntos[1:]):
        salida.extend(ortogonal(p, q, modo))
        salida.append(tuple(q))
    return limpiar(salida)


def limpiar(puntos, minimo=1e-6):
    """Quita puntos repetidos y puntos intermedios que están en línea recta."""
    sin_repetir = []
    for p in puntos:
        if not sin_repetir or vec.distancia(sin_repetir[-1], p) > minimo:
            sin_repetir.append(tuple(p))
    if len(sin_repetir) < 3:
        return sin_repetir
    salida = [sin_repetir[0]]
    for i in range(1, len(sin_repetir) - 1):
        a = vec.unitario(vec.resta(sin_repetir[i], salida[-1]))
        b = vec.unitario(vec.resta(sin_repetir[i + 1], sin_repetir[i]))
        if vec.punto(a, b) < 1.0 - 1e-9:
            salida.append(sin_repetir[i])
    salida.append(sin_repetir[-1])
    return salida


class Codo(object):
    """Un codo redondeado: dónde empieza y acaba, y su dirección en cada lado."""

    def __init__(self, inicio, fin, tangente_inicio, tangente_fin, indice_inicio, indice_fin, angulo):
        self.inicio = inicio
        self.fin = fin
        self.tangente_inicio = tangente_inicio
        self.tangente_fin = tangente_fin
        self.indice_inicio = indice_inicio
        self.indice_fin = indice_fin
        self.angulo = angulo


def redondear(puntos, radio, pasos=8, solo=None, radios=None):
    """Cambia cada esquina de la polilínea por un arco de ``radio``.

    ``solo``: índices de esquina a redondear (por defecto todas).
    ``radios``: radio de cada esquina {índice: radio}, para codos concéntricos.
    Si dos codos no caben, el radio se reduce en ese codo.
    Devuelve (puntos, codos).
    """
    puntos = [tuple(p) for p in puntos]
    if len(puntos) < 3 or radio <= 0:
        return puntos, []
    salida = [puntos[0]]
    codos = []
    n = len(puntos)
    # Lo que se recorta de cada tramo no puede pasar de la mitad del tramo.
    for i in range(1, n - 1):
        a, b, c = puntos[i - 1], puntos[i], puntos[i + 1]
        if solo is not None and i not in solo:
            salida.append(b)
            continue
        u = vec.unitario(vec.resta(b, a))
        w = vec.unitario(vec.resta(c, b))
        coseno = max(-1.0, min(1.0, vec.punto(u, w)))
        giro = math.acos(coseno)
        if giro < 1e-4:
            salida.append(b)
            continue
        if giro > math.pi - 1e-3:  # vuelta atrás: no se puede redondear
            salida.append(b)
            continue
        recorte_max = min(vec.distancia(a, b) * (0.5 if i - 1 > 0 else 1.0),
                          vec.distancia(b, c) * (0.5 if i + 1 < n - 1 else 1.0))
        r = radios.get(i, radio) if radios else radio
        if r <= 0:
            salida.append(b)
            continue
        recorte = r * math.tan(giro / 2.0)
        if recorte > recorte_max:
            recorte = recorte_max * 0.999
            r = recorte / math.tan(giro / 2.0)
        inicio = vec.resta(b, vec.escala(u, recorte))
        fin = vec.suma(b, vec.escala(w, recorte))
        # Centro del arco: hacia dentro del giro.
        bisectriz = vec.unitario(vec.resta(w, u))
        centro = vec.suma(b, vec.escala(bisectriz, r / math.cos(giro / 2.0)))
        e1 = vec.resta(inicio, centro)
        normal = vec.unitario(vec.cruz(u, w))
        pasos_codo = max(2, int(math.ceil(pasos * giro / (math.pi / 2.0))))
        indice_inicio = len(salida)
        for k in range(pasos_codo + 1):
            ang = giro * k / float(pasos_codo)
            salida.append(vec.suma(centro, vec.girar(e1, normal, ang)))
        salida[-1] = fin
        codos.append(Codo(inicio, fin, u, w, indice_inicio, len(salida) - 1, giro))
    salida.append(puntos[-1])
    return limpiar_repetidos(salida), codos


def limpiar_repetidos(puntos, minimo=1e-7):
    salida = []
    for p in puntos:
        if not salida or vec.distancia(salida[-1], p) > minimo:
            salida.append(p)
    return salida


def remuestrear(puntos, paso):
    """Añade puntos para que ningún tramo mida más de ``paso``. Conserva los originales."""
    if paso <= 0 or len(puntos) < 2:
        return list(puntos)
    salida = [puntos[0]]
    for a, b in zip(puntos, puntos[1:]):
        largo = vec.distancia(a, b)
        partes = max(1, int(math.ceil(largo / paso - 1e-9)))
        for k in range(1, partes + 1):
            salida.append(vec.mezcla(a, b, k / float(partes)))
    return salida


def uniforme(puntos, separacion, desde=None, margen=0.0):
    """Posiciones y tangentes cada ``separacion`` a lo largo de la polilínea.

    ``desde``: distancia del primer punto (por defecto media separación).
    ``margen``: no se pone nada a menos de esa distancia de los extremos.
    Devuelve una lista de (posición, tangente, distancia recorrida).
    """
    if separacion <= 0 or len(puntos) < 2:
        return []
    total = vec.longitud_polilinea(puntos)
    sig = separacion / 2.0 if desde is None else desde
    sig = max(sig, margen)
    salida, acum = [], 0.0
    for a, b in zip(puntos, puntos[1:]):
        seg = vec.distancia(a, b)
        if seg < 1e-12:
            continue
        while sig <= acum + seg + 1e-9 and sig <= total - margen + 1e-9:
            u = (sig - acum) / seg
            salida.append((vec.mezcla(a, b, min(1.0, u)), vec.unitario(vec.resta(b, a)), sig))
            sig += separacion
        acum += seg
    return salida


def en_distancia(puntos, distancia):
    """(posición, tangente) a ``distancia`` del principio de la polilínea."""
    acum = 0.0
    for a, b in zip(puntos, puntos[1:]):
        seg = vec.distancia(a, b)
        if seg < 1e-12:
            continue
        if acum + seg >= distancia:
            return vec.mezcla(a, b, (distancia - acum) / seg), vec.unitario(vec.resta(b, a))
        acum += seg
    a, b = puntos[-2], puntos[-1]
    return b, vec.unitario(vec.resta(b, a))


def tangentes(puntos):
    n = len(puntos)
    if n < 2:
        return [(0.0, 1.0, 0.0)] * n
    salida = []
    for i in range(n):
        if i == 0:
            t = vec.resta(puntos[1], puntos[0])
        elif i == n - 1:
            t = vec.resta(puntos[-1], puntos[-2])
        else:
            t = vec.suma(vec.unitario(vec.resta(puntos[i], puntos[i - 1])),
                         vec.unitario(vec.resta(puntos[i + 1], puntos[i])))
            if vec.largo(t) < 1e-9:
                t = vec.resta(puntos[i + 1], puntos[i])
        salida.append(vec.unitario(t))
    return salida


def marcos(puntos, normal_inicial=None):
    """Marcos (tangente, normal, binormal) que giran lo mínimo a lo largo de la curva.

    Método de doble reflexión (Wang et al. 2008). La primera normal se elige lo
    más hacia arriba posible, para que los perfiles planos queden tumbados.
    """
    ts = tangentes(puntos)
    if not ts:
        return []
    t0 = ts[0]
    if normal_inicial is None:
        arriba = (0.0, 1.0, 0.0)
        n0 = vec.resta(arriba, vec.escala(t0, vec.punto(arriba, t0)))
        if vec.largo(n0) < 1e-6:
            n0 = vec.perpendicular(t0)
    else:
        n0 = vec.resta(normal_inicial, vec.escala(t0, vec.punto(normal_inicial, t0)))
        if vec.largo(n0) < 1e-6:
            n0 = vec.perpendicular(t0)
    n0 = vec.unitario(n0)
    salida = [(t0, n0, vec.unitario(vec.cruz(t0, n0)))]
    for i in range(1, len(puntos)):
        t_prev, r_prev, _ = salida[-1]
        v1 = vec.resta(puntos[i], puntos[i - 1])
        c1 = vec.punto(v1, v1)
        if c1 < 1e-18:
            salida.append((ts[i], r_prev, vec.unitario(vec.cruz(ts[i], r_prev))))
            continue
        r_l = vec.resta(r_prev, vec.escala(v1, 2.0 / c1 * vec.punto(v1, r_prev)))
        t_l = vec.resta(t_prev, vec.escala(v1, 2.0 / c1 * vec.punto(v1, t_prev)))
        v2 = vec.resta(ts[i], t_l)
        c2 = vec.punto(v2, v2)
        r = r_l if c2 < 1e-18 else vec.resta(r_l, vec.escala(v2, 2.0 / c2 * vec.punto(v2, r_l)))
        r = vec.unitario(vec.resta(r, vec.escala(ts[i], vec.punto(r, ts[i]))), vec.perpendicular(ts[i]))
        salida.append((ts[i], r, vec.unitario(vec.cruz(ts[i], r))))
    return salida


def suavizar(puntos, partes=2):
    """Curva de Catmull-Rom que pasa por los ``puntos``, con ``partes`` tramos entre cada par."""
    n = len(puntos)
    if n < 3 or partes < 2:
        return list(puntos)
    salida = [tuple(puntos[0])]
    for i in range(n - 1):
        p0 = puntos[i - 1] if i > 0 else vec.resta(vec.escala(puntos[0], 2.0), puntos[1])
        p1, p2 = puntos[i], puntos[i + 1]
        p3 = puntos[i + 2] if i + 2 < n else vec.resta(vec.escala(puntos[-1], 2.0), puntos[-2])
        for k in range(1, partes + 1):
            t = k / float(partes)
            t2, t3 = t * t, t * t * t
            salida.append(tuple(
                0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t2
                       + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t3) for c in range(3)))
    return salida


def adaptativo(puntos, paso_max, angulo=6.0, paso_min=0.0):
    """Puntos de la polilínea repartidos según la curvatura.

    Se queda con un punto cuando el giro acumulado desde el anterior pasa de
    ``angulo`` grados o la distancia pasa de ``paso_max``. Así hay anillos de
    sobra en las curvas y pocos en las rectas, con el mismo presupuesto.
    """
    pts = limpiar_repetidos(puntos)
    if len(pts) < 3:
        return pts
    if paso_max > 0:
        pts = remuestrear(pts, max(paso_max / 4.0, paso_min, 1e-6))
    limite = math.radians(angulo)
    salida = [pts[0]]
    giro, recorrido = 0.0, 0.0
    t_ant = vec.unitario(vec.resta(pts[1], pts[0]))
    for i in range(1, len(pts) - 1):
        recorrido += vec.distancia(pts[i - 1], pts[i])
        t = vec.unitario(vec.resta(pts[i + 1], pts[i]))
        giro += math.acos(max(-1.0, min(1.0, vec.punto(t_ant, t))))
        t_ant = t
        if (giro >= limite and recorrido >= paso_min) or (paso_max > 0 and recorrido >= paso_max - 1e-9):
            salida.append(pts[i])
            giro, recorrido = 0.0, 0.0
    salida.append(pts[-1])
    return salida



# --- recorridos que esquivan obstáculos ---------------------------------------------

def _corta(a, b, caja):
    """¿El tramo recto (en un eje) de ``a`` a ``b`` entra en la ``caja`` abierta?"""
    lo, hi = caja
    for k in range(3):
        mn, mx = min(a[k], b[k]), max(a[k], b[k])
        if mx <= lo[k] + 1e-9 or mn >= hi[k] - 1e-9:
            return False
    return True


def _dentro(p, caja):
    lo, hi = caja
    return all(lo[k] < p[k] < hi[k] for k in range(3))


def esquivar(p, q, obstaculos, holgura, penalizacion_codo=None, maximo=60):
    """Recorrido en ángulo recto de ``p`` a ``q`` que no atraviesa ``obstaculos``.

    ``obstaculos``: cajas (mínimo, máximo) de los objetos; se hinchan
    ``holgura`` (radio de la tubería más el aire que se quiere dejar). Busca
    con A* sobre una rejilla con las coordenadas de las cajas, y cada codo
    cuesta ``penalizacion_codo`` de longitud: salen pocos codos, como en una
    instalación real. Devuelve la polilínea (con ``p`` y ``q``), o None si no
    hay camino.
    """
    import heapq
    p, q = tuple(p), tuple(q)
    zona_lo = [min(p[k], q[k]) for k in range(3)]
    zona_hi = [max(p[k], q[k]) for k in range(3)]
    cajas = []
    for lo, hi in obstaculos:
        lo_h = tuple(lo[k] - holgura for k in range(3))
        hi_h = tuple(hi[k] + holgura for k in range(3))
        caja = (lo_h, hi_h)
        if _dentro(p, caja) or _dentro(q, caja):
            caja = (tuple(lo), tuple(hi))  # el extremo está pegado a este objeto: sin holgura
            if _dentro(p, caja) or _dentro(q, caja):
                continue
        cajas.append(caja)
    for lo, hi in cajas:
        for k in range(3):
            zona_lo[k] = min(zona_lo[k], lo[k])
            zona_hi[k] = max(zona_hi[k], hi[k])
    cajas = cajas[:maximo]
    if not any(_corta(a, b, c) for c in cajas for a, b in zip([p] + ortogonal(p, q, "z"),
                                                               ortogonal(p, q, "z") + [q])):
        return None  # el recorrido normal ya está libre
    ejes = []
    margen = holgura * 2.0
    for k in range(3):
        valores = {p[k], q[k]}
        for lo, hi in cajas:
            valores.add(lo[k])
            valores.add(hi[k])
            valores.add(lo[k] - margen)
            valores.add(hi[k] + margen)
        ejes.append(sorted(valores))
    indice = [{v: i for i, v in enumerate(e)} for e in ejes]
    inicio = tuple(indice[k][p[k]] for k in range(3))
    meta = tuple(indice[k][q[k]] for k in range(3))
    escala = vec.distancia(p, q) or 1.0
    codo = penalizacion_codo if penalizacion_codo is not None else max(holgura * 8.0, escala * 0.05)

    def punto_de(nodo):
        return tuple(ejes[k][nodo[k]] for k in range(3))

    def libre(a, b):
        return not any(_corta(a, b, c) for c in cajas)

    def h(nodo):
        x = punto_de(nodo)
        return sum(abs(x[k] - q[k]) for k in range(3))

    abiertos = [(h(inicio), 0.0, inicio, -1)]
    coste = {(inicio, -1): 0.0}
    padre = {}
    vistos = 0
    while abiertos:
        _f, g, nodo, direccion = heapq.heappop(abiertos)
        if nodo == meta:
            camino = [nodo]
            estado = (nodo, direccion)
            while estado in padre:
                estado = padre[estado]
                camino.append(estado[0])
            return limpiar([punto_de(n) for n in reversed(camino)])
        vistos += 1
        if vistos > 200000:
            return None
        if g > coste.get((nodo, direccion), float("inf")):
            continue
        a = punto_de(nodo)
        for eje in range(3):
            for paso in (-1, 1):
                j = nodo[eje] + paso
                if j < 0 or j >= len(ejes[eje]):
                    continue
                vecino = list(nodo)
                vecino[eje] = j
                vecino = tuple(vecino)
                b = punto_de(vecino)
                if not libre(a, b):
                    continue
                nueva_dir = eje * 2 + (paso > 0)
                if direccion >= 0 and nueva_dir // 2 == direccion // 2 and nueva_dir != direccion:
                    continue  # no dar media vuelta
                g2 = g + abs(b[eje] - a[eje]) + (codo if direccion >= 0 and nueva_dir != direccion else 0.0)
                clave = (vecino, nueva_dir)
                if g2 < coste.get(clave, float("inf")):
                    coste[clave] = g2
                    padre[clave] = (nodo, direccion)
                    heapq.heappush(abiertos, (g2 + h(vecino), g2, vecino, nueva_dir))
    return None


# --- varias tuberías en paralelo (rack) ----------------------------------------------

def _laterales(puntos, arriba=(0.0, 1.0, 0.0)):
    """Dirección lateral de cada tramo: horizontal y perpendicular al tramo.

    Los tramos verticales heredan la del tramo horizontal más cercano, así las
    tuberías de un rack siguen en fila al subir o bajar.
    """
    laterales = []
    for a, b in zip(puntos, puntos[1:]):
        d = vec.unitario(vec.resta(b, a))
        l = vec.cruz(arriba, d)
        laterales.append(vec.unitario(l) if vec.largo(l) > 1e-6 else None)
    ultimo = next((l for l in laterales if l is not None), (1.0, 0.0, 0.0))
    for i, l in enumerate(laterales):
        if l is None:
            laterales[i] = ultimo
        else:
            ultimo = l
    return laterales


def paralela(puntos, desplazamiento, radio_base, arriba=(0.0, 1.0, 0.0)):
    """Polilínea en ángulo recto desplazada ``desplazamiento`` a un lado, y el radio de cada esquina.

    Las esquinas se calculan para que los codos de todas las tuberías del rack
    sean concéntricos (mismo centro): el de fuera es más abierto.
    Devuelve (puntos, {índice de esquina: radio}).
    """
    if len(puntos) < 2:
        return list(puntos), {}
    if abs(desplazamiento) < 1e-12:
        return list(puntos), {i: radio_base for i in range(1, len(puntos) - 1)}
    laterales = _laterales(puntos, arriba)
    offs = [vec.escala(l, desplazamiento) for l in laterales]
    salida = [vec.suma(puntos[0], offs[0])]
    radios = {}
    for i in range(1, len(puntos) - 1):
        d1 = vec.unitario(vec.resta(puntos[i], puntos[i - 1]))
        d2 = vec.unitario(vec.resta(puntos[i + 1], puntos[i]))
        o1, o2 = offs[i - 1], offs[i]
        esquina = vec.suma(vec.suma(puntos[i], o1), vec.escala(d1, vec.punto(o2, d1)))
        salida.append(esquina)
        radios[i] = radio_base - vec.punto(o1, d2)
    salida.append(vec.suma(puntos[-1], offs[-1]))
    return salida, radios
