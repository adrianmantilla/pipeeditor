"""Mallas sencillas en listas de Python, listas para pasar a ``MFnMesh.create``.

``Malla`` guarda vértices, caras (índices de vértice), UV y, por cada cara,
los índices de UV. Los vértices de la costura se comparten; solo las UV se
duplican, así no aparecen aristas abiertas ni sombreados raros.
"""

import math

from pipeeditor import vec


class Malla(object):
    def __init__(self):
        self.vertices = []
        self.caras = []
        self.uvs = []
        self.caras_uv = []

    # --- construir -----------------------------------------------------------------
    def vertice(self, p):
        self.vertices.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.vertices) - 1

    def uv(self, u, v):
        self.uvs.append((float(u), float(v)))
        return len(self.uvs) - 1

    def cara(self, indices, indices_uv):
        if len(indices) < 3 or len(set(indices)) < 3:
            return
        self.caras.append(tuple(indices))
        self.caras_uv.append(tuple(indices_uv))

    def anadir(self, otra, transformacion=None):
        base_v, base_uv = len(self.vertices), len(self.uvs)
        if transformacion is None:
            self.vertices.extend(otra.vertices)
        else:
            self.vertices.extend(vec.aplicar(transformacion, p) for p in otra.vertices)
        self.uvs.extend(otra.uvs)
        self.caras.extend(tuple(i + base_v for i in c) for c in otra.caras)
        self.caras_uv.extend(tuple(i + base_uv for i in c) for c in otra.caras_uv)
        return self

    # --- consultar -----------------------------------------------------------------
    @property
    def num_caras(self):
        return len(self.caras)

    def triangulos(self):
        return sum(len(c) - 2 for c in self.caras)

    def vacia(self):
        return not self.caras

    def para_maya(self):
        """(vértices, cuentas, conexiones, us, vs, cuentas_uv, ids_uv) para MFnMesh."""
        cuentas = [len(c) for c in self.caras]
        conexiones = [i for c in self.caras for i in c]
        us = [u for u, _ in self.uvs]
        vs = [v for _, v in self.uvs]
        ids_uv = [i for c in self.caras_uv for i in c]
        return self.vertices, cuentas, conexiones, us, vs, cuentas, ids_uv

    def caja(self):
        if not self.vertices:
            return (0, 0, 0), (0, 0, 0)
        xs, ys, zs = zip(*self.vertices)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def unir(mallas):
    total = Malla()
    for m in mallas:
        if m is not None:
            total.anadir(m)
    return total


# --- barrido de un perfil a lo largo de una curva ------------------------------------

def barrer(centros, marcos, anillo, tapas=True, escala_v=1.0, invertir=False):
    """Barre un perfil cerrado a lo largo de ``centros``.

    ``anillo(i)`` devuelve el perfil del punto ``i`` como lista de (x, y) en el
    plano (normal, binormal) del marco. Todos los anillos tienen los mismos
    puntos. ``escala_v``: unidades de longitud por cada 1 de V.
    """
    m = Malla()
    n = len(centros)
    if n < 2:
        return m
    perfiles = [anillo(i) for i in range(n)]
    lados = len(perfiles[0])
    if lados < 3:
        return m
    s = vec.acumulada(centros)
    filas = []
    for i in range(n):
        _t, nn, bb = marcos[i]
        c = centros[i]
        fila = []
        for x, y in perfiles[i]:
            fila.append(m.vertice(vec.suma(c, vec.suma(vec.escala(nn, x), vec.escala(bb, y)))))
        filas.append(fila)
    uv_filas = []
    for i in range(n):
        v = s[i] / escala_v if escala_v else 0.0
        uv_filas.append([m.uv(k / float(lados), v) for k in range(lados + 1)])
    for i in range(n - 1):
        for k in range(lados):
            k2 = (k + 1) % lados
            caras = [filas[i][k], filas[i][k2], filas[i + 1][k2], filas[i + 1][k]]
            uvs = [uv_filas[i][k], uv_filas[i][k + 1], uv_filas[i + 1][k + 1], uv_filas[i + 1][k]]
            if invertir:
                caras.reverse()
                uvs.reverse()
            m.cara(caras, uvs)
    if tapas:
        _tapa(m, filas[0], perfiles[0], centros[0], marcos[0], invertir)
        _tapa(m, filas[-1], perfiles[-1], centros[-1], marcos[-1], not invertir)
    return m


def _tapa(m, fila, perfil, centro, marco, al_reves):
    """Tapa plana en abanico, con UV planas.

    Usa sus propios vértices (copias del borde) para que el borde quede con
    arista dura: así todas las aristas de la malla pueden ser suaves.
    """
    radio = max(max(abs(x), abs(y)) for x, y in perfil) or 1.0
    fila = [m.vertice(m.vertices[i]) for i in fila]
    medio = m.vertice(centro)
    uv_medio = m.uv(0.5, 0.5)
    uvs = [m.uv(0.5 + 0.5 * x / radio, 0.5 + 0.5 * y / radio) for x, y in perfil]
    lados = len(fila)
    for k in range(lados):
        k2 = (k + 1) % lados
        caras = [medio, fila[k2], fila[k]]
        ids = [uv_medio, uvs[k2], uvs[k]]
        if al_reves:
            caras.reverse()
            ids.reverse()
        m.cara(caras, ids)


def anillo_entre(m, fila_fuera, fila_dentro, perfil_fuera, al_reves):
    """Corona entre dos anillos (borde de una tubería hueca)."""
    radio = max(max(abs(x), abs(y)) for x, y in perfil_fuera) or 1.0
    fila_fuera = [m.vertice(m.vertices[i]) for i in fila_fuera]
    fila_dentro = [m.vertice(m.vertices[i]) for i in fila_dentro]
    lados = len(fila_fuera)
    uv_f = [m.uv(0.5 + 0.5 * math.cos(2 * math.pi * k / lados), 0.5 + 0.5 * math.sin(2 * math.pi * k / lados))
            for k in range(lados)]
    uv_d = [m.uv(0.5 + 0.35 * math.cos(2 * math.pi * k / lados), 0.5 + 0.35 * math.sin(2 * math.pi * k / lados))
            for k in range(lados)]
    for k in range(lados):
        k2 = (k + 1) % lados
        caras = [fila_fuera[k], fila_fuera[k2], fila_dentro[k2], fila_dentro[k]]
        ids = [uv_f[k], uv_f[k2], uv_d[k2], uv_d[k]]
        if al_reves:
            caras.reverse()
            ids.reverse()
        m.cara(caras, ids)
    return radio


# --- perfiles -------------------------------------------------------------------------

def circulo(radio, lados, giro=0.0, achatado=1.0):
    return [(radio * math.cos(giro + 2 * math.pi * k / lados),
             radio * achatado * math.sin(giro + 2 * math.pi * k / lados)) for k in range(lados)]


def cuadrado_redondeado(lado, radio_esquina, puntos_esquina=3):
    """Cuadrado de lado ``lado`` con esquinas redondeadas, centrado."""
    h = lado / 2.0
    r = min(radio_esquina, h * 0.95)
    salida = []
    centros = [(h - r, h - r), (-h + r, h - r), (-h + r, -h + r), (h - r, -h + r)]
    for e, (cx, cy) in enumerate(centros):
        for k in range(puntos_esquina + 1):
            a = math.pi / 2.0 * (e + k / float(puntos_esquina))
            salida.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return salida


# --- primitivas para piezas (en local: eje Y = dirección del cable) --------------------

def cilindro(radio, y0, y1, lados=12, tapas=True, radio_final=None, desplazamiento=(0.0, 0.0)):
    centros = [(desplazamiento[0], y0, desplazamiento[1]), (desplazamiento[0], y1, desplazamiento[1])]
    marcos = [((0, 1, 0), (1, 0, 0), (0, 0, -1))] * 2
    rf = radio if radio_final is None else radio_final
    return barrer(centros, marcos, lambda i: circulo(radio if i == 0 else rf, lados), tapas=tapas,
                  escala_v=2 * math.pi * radio)


def toro(radio_mayor, radio_menor, segmentos=16, lados=8, arco=2 * math.pi, inicio=0.0):
    """Toro (o trozo de toro) en el plano XZ, centrado en el origen, eje Y."""
    cerrado = arco >= 2 * math.pi - 1e-6
    pasos = segmentos if cerrado else max(2, segmentos)
    centros, marcos = [], []
    total = pasos + (1 if not cerrado else 1)
    for i in range(total):
        a = inicio + arco * i / float(pasos)
        c = (radio_mayor * math.cos(a), 0.0, radio_mayor * math.sin(a))
        t = (-math.sin(a), 0.0, math.cos(a))
        nn = (math.cos(a), 0.0, math.sin(a))
        bb = vec.cruz(t, nn)
        centros.append(c)
        marcos.append((t, nn, bb))
    return barrer(centros, marcos, lambda i: circulo(radio_menor, lados), tapas=not cerrado,
                  escala_v=2 * math.pi * radio_menor)


def caja(ancho, alto, fondo, centro=(0.0, 0.0, 0.0)):
    m = Malla()
    hx, hy, hz = ancho / 2.0, alto / 2.0, fondo / 2.0
    cx, cy, cz = centro
    esquinas = [(cx + sx * hx, cy + sy * hy, cz + sz * hz)
                for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    # índice = (sx>0)*4 + (sy>0)*2 + (sz>0); cada cara con sus vértices (aristas duras)
    caras = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for c in caras:
        ids = [m.uv(0, 0), m.uv(1, 0), m.uv(1, 1), m.uv(0, 1)]
        m.cara([m.vertice(esquinas[i]) for i in c], ids)
    return m


def girada(malla, eje, angulo):
    """Copia de ``malla`` girada alrededor de ``eje`` (por el origen)."""
    eje = vec.unitario(eje)
    nueva = Malla()
    nueva.vertices = [vec.girar(p, eje, angulo) for p in malla.vertices]
    nueva.caras = list(malla.caras)
    nueva.uvs = list(malla.uvs)
    nueva.caras_uv = list(malla.caras_uv)
    return nueva


def movida(malla, desplazamiento):
    nueva = Malla()
    nueva.vertices = [vec.suma(p, desplazamiento) for p in malla.vertices]
    nueva.caras = list(malla.caras)
    nueva.uvs = list(malla.uvs)
    nueva.caras_uv = list(malla.caras_uv)
    return nueva
