"""Mallas sencillas en listas de Python, listas para pasar a ``MFnMesh.create``.

``Malla`` guarda vértices, caras (índices de vértice), UV y, por cada cara,
los índices de UV. Los vértices se comparten siempre (también en el borde de
las tapas), así la malla es cerrada y se puede suavizar (tecla 3) o
subdividir en Arnold sin que se abran grietas. Las aristas que deben verse
vivas (bordes de tapas, cantos de cajas) se guardan en ``duras``: en Maya
quedan con arista dura y con pliegue (crease), para que sigan vivas al
subdividir.

Cada cara lleva una etiqueta de material: 0 = la pieza normal, 1 = metal.

Las UV están en unidades reales: una unidad de UV son ``ESCALA_UV`` cm, igual
en todos los cables y piezas, para que una textura que se repite tenga el
mismo tamaño en todo.
"""

import math

from pipeeditor import vec

ESCALA_UV = 10.0
METAL = 1


class Malla(object):
    def __init__(self):
        self.vertices = []
        self.caras = []
        self.uvs = []
        self.caras_uv = []
        self.etiquetas = []
        self.duras = []

    # --- construir -----------------------------------------------------------------
    def vertice(self, p):
        self.vertices.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.vertices) - 1

    def uv(self, u, v):
        self.uvs.append((float(u), float(v)))
        return len(self.uvs) - 1

    def cara(self, indices, indices_uv, etiqueta=0):
        if len(indices) < 3 or len(set(indices)) < 3:
            return
        self.caras.append(tuple(indices))
        self.caras_uv.append(tuple(indices_uv))
        self.etiquetas.append(etiqueta)

    def dura(self, a, b):
        self.duras.append((a, b))

    def _etiquetas(self):
        if len(self.etiquetas) != len(self.caras):
            self.etiquetas = (list(self.etiquetas) + [0] * len(self.caras))[:len(self.caras)]
        return self.etiquetas

    def anadir(self, otra, transformacion=None):
        base_v, base_uv = len(self.vertices), len(self.uvs)
        self._etiquetas()
        if transformacion is None:
            self.vertices.extend(otra.vertices)
        else:
            self.vertices.extend(vec.aplicar(transformacion, p) for p in otra.vertices)
        self.uvs.extend(otra.uvs)
        self.caras.extend(tuple(i + base_v for i in c) for c in otra.caras)
        self.caras_uv.extend(tuple(i + base_uv for i in c) for c in otra.caras_uv)
        self.etiquetas.extend(otra._etiquetas())
        self.duras.extend((a + base_v, b + base_v) for a, b in otra.duras)
        return self

    def separar(self, etiqueta):
        """Malla nueva solo con las caras de ``etiqueta`` (y sus vértices)."""
        nueva = Malla()
        mapa_v, mapa_uv = {}, {}
        for cara, cara_uv, e in zip(self.caras, self.caras_uv, self._etiquetas()):
            if e != etiqueta:
                continue
            ids = []
            for i in cara:
                if i not in mapa_v:
                    mapa_v[i] = nueva.vertice(self.vertices[i])
                ids.append(mapa_v[i])
            ids_uv = []
            for i in cara_uv:
                if i not in mapa_uv:
                    mapa_uv[i] = nueva.uv(*self.uvs[i])
                ids_uv.append(mapa_uv[i])
            nueva.cara(ids, ids_uv, e)
        nueva.duras = [(mapa_v[a], mapa_v[b]) for a, b in self.duras if a in mapa_v and b in mapa_v]
        return nueva

    def copia(self, vertices=None):
        nueva = Malla()
        nueva.vertices = list(self.vertices) if vertices is None else vertices
        nueva.caras = list(self.caras)
        nueva.uvs = list(self.uvs)
        nueva.caras_uv = list(self.caras_uv)
        nueva.etiquetas = list(self._etiquetas())
        nueva.duras = list(self.duras)
        return nueva

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


def metal(malla):
    """La misma malla, marcada como metal."""
    malla.etiquetas = [METAL] * len(malla.caras)
    return malla


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
    perimetro = _perimetro(perfiles[0]) / ESCALA_UV
    uv_filas = []
    for i in range(n):
        v = s[i] / ESCALA_UV
        uv_filas.append([m.uv(perimetro * k / float(lados), v) for k in range(lados + 1)])
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


def _perimetro(perfil):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(perfil, perfil[1:] + perfil[:1]))


def _tapa(m, fila, perfil, centro, marco, al_reves):
    """Tapa plana: un polígono que comparte los vértices del borde, con UV planas.

    El borde se marca como arista dura (y con pliegue al subdividir).
    """
    uvs = [m.uv(0.5 + x / ESCALA_UV, 0.5 + y / ESCALA_UV) for x, y in perfil]
    caras, ids = list(fila), list(uvs)
    if not al_reves:
        caras.reverse()
        ids.reverse()
    m.cara(caras, ids)
    for k in range(len(fila)):
        m.dura(fila[k], fila[(k + 1) % len(fila)])


def anillo_entre(m, fila_fuera, fila_dentro, perfil_fuera, al_reves):
    """Corona entre dos anillos (borde de una tubería hueca)."""
    radio = max(max(abs(x), abs(y)) for x, y in perfil_fuera) or 1.0
    lados = len(fila_fuera)
    uv_f = [m.uv(0.5 + radio * math.cos(2 * math.pi * k / lados) / ESCALA_UV,
                 0.5 + radio * math.sin(2 * math.pi * k / lados) / ESCALA_UV) for k in range(lados)]
    uv_d = [m.uv(0.5 + 0.8 * radio * math.cos(2 * math.pi * k / lados) / ESCALA_UV,
                 0.5 + 0.8 * radio * math.sin(2 * math.pi * k / lados) / ESCALA_UV) for k in range(lados)]
    for k in range(lados):
        m.dura(fila_fuera[k], fila_fuera[(k + 1) % lados])
        m.dura(fila_dentro[k], fila_dentro[(k + 1) % lados])
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
    # índice = (sx>0)*4 + (sy>0)*2 + (sz>0); vértices compartidos y las 12 aristas duras
    ids_v = [m.vertice(p) for p in esquinas]
    caras = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for c in caras:
        a, b, d = esquinas[c[0]], esquinas[c[1]], esquinas[c[3]]
        ancho_c, alto_c = vec.distancia(a, b) / ESCALA_UV, vec.distancia(a, d) / ESCALA_UV
        ids = [m.uv(0, 0), m.uv(ancho_c, 0), m.uv(ancho_c, alto_c), m.uv(0, alto_c)]
        m.cara([ids_v[i] for i in c], ids)
    for i in range(8):
        for bit in (1, 2, 4):
            j = i | bit
            if j != i:
                m.dura(ids_v[i], ids_v[j])
    return m


def girada(malla, eje, angulo):
    """Copia de ``malla`` girada alrededor de ``eje`` (por el origen)."""
    eje = vec.unitario(eje)
    return malla.copia([vec.girar(p, eje, angulo) for p in malla.vertices])


def movida(malla, desplazamiento):
    return malla.copia([vec.suma(p, desplazamiento) for p in malla.vertices])
