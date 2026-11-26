"""Vectores 3D como tuplas (x, y, z). Sin Maya, para poder probarlo todo fuera."""

import math


def suma(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def resta(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def escala(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def punto(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def largo(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def distancia(a, b):
    return largo(resta(a, b))


def unitario(a, defecto=(0.0, 1.0, 0.0)):
    n = largo(a)
    if n < 1e-12:
        return defecto
    return (a[0] / n, a[1] / n, a[2] / n)


def mezcla(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def perpendicular(v):
    """Un vector unitario perpendicular a ``v``, preferiblemente horizontal."""
    v = unitario(v)
    candidato = cruz(v, (0.0, 1.0, 0.0))
    if largo(candidato) < 1e-6:
        candidato = cruz(v, (1.0, 0.0, 0.0))
    return unitario(candidato)


def girar(v, eje, angulo):
    """Gira ``v`` alrededor de ``eje`` (unitario) ``angulo`` radianes (Rodrigues)."""
    c, s = math.cos(angulo), math.sin(angulo)
    termino = escala(eje, punto(eje, v) * (1 - c))
    return suma(suma(escala(v, c), escala(cruz(eje, v), s)), termino)


def longitud_polilinea(puntos):
    return sum(distancia(puntos[i - 1], puntos[i]) for i in range(1, len(puntos)))


def acumulada(puntos):
    """Distancia recorrida hasta cada punto de la polilínea."""
    s, total = [0.0], 0.0
    for i in range(1, len(puntos)):
        total += distancia(puntos[i - 1], puntos[i])
        s.append(total)
    return s


def matriz(origen, eje_x, eje_y, eje_z):
    """Matriz 4x4 (filas) que lleva coordenadas locales a mundo."""
    return (eje_x, eje_y, eje_z, origen)


def aplicar(m, p):
    x, y, z = p
    ex, ey, ez, o = m
    return (o[0] + ex[0] * x + ey[0] * y + ez[0] * z,
            o[1] + ex[1] * x + ey[1] * y + ez[1] * z,
            o[2] + ex[2] * x + ey[2] * y + ez[2] * z)


def marco_desde_eje(origen, eje_y, referencia=None):
    """Matriz con Y = ``eje_y``; X lo más parecido posible a ``referencia``."""
    y = unitario(eje_y)
    if referencia is not None:
        x = resta(referencia, escala(y, punto(referencia, y)))
        x = unitario(x) if largo(x) > 1e-6 else perpendicular(y)
    else:
        x = perpendicular(y)
    z = unitario(cruz(x, y))
    return matriz(origen, x, y, z)
