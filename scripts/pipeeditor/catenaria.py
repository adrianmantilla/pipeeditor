"""La curva de un cable que cuelga entre dos puntos (catenaria), en 3D y sin Maya.

La gravedad tira hacia -Y. El cable vive en el plano vertical que contiene
a los dos puntos. Se resuelve el parámetro ``a`` de la catenaria
``y = a·cosh((x - xv) / a) + c`` para que la curva mida justo ``longitud``.
"""

import math

from pipeeditor import vec

# A partir de este cociente sinh se desborda; nunca hace falta un cable tan tenso.
_LIMITE = 700.0


def longitud_con_holgura(p, q, holgura):
    """Longitud del cable si sobra ``holgura`` (0.1 = un 10 % más que la recta)."""
    return vec.distancia(p, q) * (1.0 + max(0.0, holgura))


def esta_tenso(p, q, longitud):
    return longitud <= vec.distancia(p, q) * (1.0 + 1e-6)


def resolver_a(d, h, longitud):
    """Parámetro ``a`` de la catenaria para separación horizontal ``d`` y desnivel ``h``."""
    objetivo = math.sqrt(max(longitud * longitud - h * h, 0.0))
    lo, hi = d / (2.0 * _LIMITE), 1e12
    for _ in range(200):
        a = math.sqrt(lo * hi) if lo > 0 else (lo + hi) / 2.0
        f = 2.0 * a * math.sinh(d / (2.0 * a)) - objetivo
        if f > 0:
            lo = a
        else:
            hi = a
        if hi / lo < 1.0 + 1e-12:
            break
    return math.sqrt(lo * hi)


def puntos(p, q, longitud, segmentos):
    """``segmentos + 1`` puntos de la catenaria de ``p`` a ``q``, repartidos por longitud.

    Si el cable está tenso, o los puntos están casi en vertical, sale la recta.
    """
    segmentos = max(1, int(segmentos))
    horizontal = (q[0] - p[0], 0.0, q[2] - p[2])
    d = vec.largo(horizontal)
    h = q[1] - p[1]
    if esta_tenso(p, q, longitud) or d < 1e-6 * max(1.0, abs(h)):
        return [vec.mezcla(p, q, i / float(segmentos)) for i in range(segmentos + 1)]
    eje = vec.escala(horizontal, 1.0 / d)
    a = resolver_a(d, h, longitud)
    # Vértice (punto más bajo) en coordenada horizontal xv, medida desde p.
    xv = d / 2.0 - a * math.atanh(max(-0.999999999, min(0.999999999, h / longitud)))
    c = -a * math.cosh(-xv / a)
    s0 = a * math.sinh(-xv / a)
    s1 = a * math.sinh((d - xv) / a)
    salida = []
    for i in range(segmentos + 1):
        s = s0 + (s1 - s0) * i / float(segmentos)
        x = xv + a * math.asinh(s / a)
        y = a * math.cosh((x - xv) / a) + c
        salida.append((p[0] + eje[0] * x, p[1] + y, p[2] + eje[2] * x))
    salida[0], salida[-1] = tuple(p), tuple(q)
    return salida


def caida(puntos_curva):
    """Distancia vertical máxima entre la curva y la recta que une sus extremos."""
    p, q = puntos_curva[0], puntos_curva[-1]
    total = vec.distancia((p[0], 0, p[2]), (q[0], 0, q[2]))
    mayor = 0.0
    for r in puntos_curva:
        u = vec.distancia((p[0], 0, p[2]), (r[0], 0, r[2])) / total if total > 1e-9 else 0.0
        recta = p[1] + (q[1] - p[1]) * u
        mayor = max(mayor, recta - r[1])
    return mayor
