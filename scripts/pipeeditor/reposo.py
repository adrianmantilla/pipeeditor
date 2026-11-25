"""Reposo físico de un cable: dónde se queda quieto con su longitud real. Sin Maya.

La catenaria es exacta mientras el cable cuelga libre, pero no sabe qué hacer
cuando toca algo. Aquí el cable es una cadena de puntos que:

- mantiene la longitud de cada tramo (el cable no estira ni encoge),
- no se dobla más que su radio mínimo (rigidez),
- no atraviesa el suelo ni los objetos de apoyo, en ninguna dirección,
- roza con el suelo (no resbala sin fin),
- y no se mete en los otros cables del mismo haz.

Se parte de la catenaria ya apoyada y se relaja un número fijo de pasos
(integración de Verlet con restricciones de posición). No es una simulación en
el tiempo: el resultado es siempre el mismo para los mismos datos.

Necesita numpy (viene con Maya 2026 y 2027). Si no está, ``disponible()`` es
falso y PipeEditor usa la catenaria apoyada de siempre.
"""

import math

try:
    import numpy as np
except ImportError:  # pragma: no cover - Maya trae numpy
    np = None


def disponible():
    return np is not None


class Cadena(object):
    """Datos de entrada del reposo.

    ``puntos``: posiciones iniciales (lista de tuplas).
    ``largos``: longitud de reposo de cada segmento (len(puntos) - 1).
    ``fijos``: índices que no se mueven.
    ``ganchos``: posiciones por las que el cable pasa deslizando.
    """

    def __init__(self, puntos, largos, fijos=(), ganchos=()):
        self.puntos = puntos
        self.largos = largos
        self.fijos = sorted(set(fijos))
        self.ganchos = list(ganchos)


def radio_minimo(radio, rigidez):
    """Radio de curvatura mínimo del cable: de 1 a 31 veces su radio."""
    return radio * (1.0 + 30.0 * max(0.0, min(1.0, rigidez)))


def reposar(cadena, radio, suelo=None, empujar=None, rigidez=0.3, pasos=160, iteraciones=12,
            otros=(), friccion=0.7):
    """Devuelve las posiciones en reposo (array N×3).

    ``empujar(P, radio)``: saca de los objetos de apoyo los puntos de ``P``
    (array N×3) y devuelve (P corregido, máscara de puntos en contacto); o None.
    ``otros``: arrays de puntos de otros cables con los que no chocar.
    """
    x = np.array(cadena.puntos, dtype=float)
    n = len(x)
    if n < 3:
        return x
    largos = np.asarray(cadena.largos, dtype=float)
    peso = np.ones(n)
    peso[cadena.fijos] = 0.0
    fijos = np.array(cadena.fijos, dtype=int)
    pos_fijos = x[fijos].copy() if len(fijos) else None
    ganchos = np.array(cadena.ganchos, dtype=float).reshape(-1, 3)
    medio = float(largos.mean()) if len(largos) else 1.0
    gravedad = medio * 0.01
    rmin = radio_minimo(radio, rigidez) if rigidez > 0 else 0.0
    # Distancia mínima entre i e i+2 para no doblar más que rmin.
    if rmin > 0:
        tramo = 0.5 * (largos[:-1] + largos[1:])
        angulo = np.minimum(tramo / rmin, math.pi * 0.95)
        dmin = 2.0 * tramo * np.cos(angulo / 2.0)
    else:
        dmin = None
    otros = [np.asarray(o, dtype=float) for o in otros if len(o)]
    pares = np.arange(0, n - 1, 2), np.arange(1, n - 1, 2)
    xp = x.copy()
    for paso in range(pasos):
        v = (x - xp) * 0.97
        xp = x.copy()
        x = x + v
        x[:, 1] -= gravedad * peso
        for _ in range(iteraciones):
            for idx in pares:
                _distancia(x, idx, largos, peso)
            if dmin is not None:
                _flexion(x, dmin, peso)
            if pos_fijos is not None:
                x[fijos] = pos_fijos
            for g in ganchos:
                j = int(np.argmin(((x - g) ** 2).sum(axis=1)))
                if peso[j] > 0:
                    x[j] = g
            if suelo is not None:
                abajo = (x[:, 1] < suelo + radio) & (peso > 0)
                x[abajo, 1] = suelo + radio
        tocan = np.zeros(n, dtype=bool)
        if suelo is not None:
            tocan |= (x[:, 1] < suelo + radio * 1.05) & (peso > 0)
        if empujar is not None:
            x2, contacto = empujar(x, radio)
            x2 = np.asarray(x2, dtype=float)
            x2[peso == 0] = x[peso == 0]
            x = x2
            tocan |= np.asarray(contacto, dtype=bool) & (peso > 0)
        for o in otros:
            _separar(x, o, 2.0 * radio, peso)
        if tocan.any():
            # Rozamiento: lo que toca pierde casi toda su velocidad.
            xp[tocan] = x[tocan] - (x[tocan] - xp[tocan]) * (1.0 - friccion)
    # Un último ajuste de longitudes sin gravedad.
    for _ in range(iteraciones * 2):
        for idx in pares:
            _distancia(x, idx, largos, peso)
        if dmin is not None:
            _flexion(x, dmin, peso)
        if pos_fijos is not None:
            x[fijos] = pos_fijos
        if suelo is not None:
            abajo = (x[:, 1] < suelo + radio) & (peso > 0)
            x[abajo, 1] = suelo + radio
    if empujar is not None:
        x2, _c = empujar(x, radio)
        x2 = np.asarray(x2, dtype=float)
        x2[peso == 0] = x[peso == 0]
        x = x2
    return x


def _distancia(x, idx, largos, peso):
    a, b = idx, idx + 1
    d = x[b] - x[a]
    l = np.sqrt((d * d).sum(axis=1))
    l[l < 1e-12] = 1e-12
    wa, wb = peso[a], peso[b]
    w = wa + wb
    w[w == 0] = 1.0
    c = ((l - largos[a]) / l / w)[:, None] * d
    x[a] += c * wa[:, None]
    x[b] -= c * wb[:, None]


def _flexion(x, dmin, peso):
    a, b = np.arange(len(x) - 2), np.arange(2, len(x))
    d = x[b] - x[a]
    l = np.sqrt((d * d).sum(axis=1))
    corto = l < dmin
    if not corto.any():
        return
    l[l < 1e-12] = 1e-12
    wa, wb = peso[a], peso[b]
    w = wa + wb
    w[w == 0] = 1.0
    c = np.where(corto, (l - dmin) / l / w, 0.0)[:, None] * d
    delta = np.zeros_like(x)
    np.add.at(delta, a, c * wa[:, None])
    np.add.at(delta, b, -c * wb[:, None])
    x += delta


def _separar(x, otro, minimo, peso):
    d = x[:, None, :] - otro[None, :, :]
    l2 = (d * d).sum(axis=2)
    j = np.argmin(l2, axis=1)
    l = np.sqrt(l2[np.arange(len(x)), j])
    cerca = (l < minimo) & (peso > 0)
    if not cerca.any():
        return
    dd = d[np.arange(len(x)), j][cerca]
    ll = np.maximum(l[cerca], 1e-9)[:, None]
    x[cerca] += dd / ll * (minimo - ll)


# --- utilidades para preparar la cadena ------------------------------------------

def repartir(puntos, partes):
    """``partes + 1`` puntos repartidos por igual a lo largo de la polilínea."""
    p = np.asarray(puntos, dtype=float)
    seg = np.sqrt(((p[1:] - p[:-1]) ** 2).sum(axis=1))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = s[-1]
    if total < 1e-12:
        return np.repeat(p[:1], partes + 1, axis=0)
    objetivo = np.linspace(0.0, total, partes + 1)
    salida = np.empty((partes + 1, 3))
    for k in range(3):
        salida[:, k] = np.interp(objetivo, s, p[:, k])
    return salida


def ondulacion(puntos, amplitud, semilla, longitud_onda):
    """Ondas laterales suaves (memoria de bobina), nulas en los extremos."""
    p = np.asarray(puntos, dtype=float)
    if amplitud <= 0 or len(p) < 3:
        return p
    rng = np.random.RandomState(int(semilla) & 0x7FFFFFFF)
    seg = np.sqrt(((p[1:] - p[:-1]) ** 2).sum(axis=1))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = max(s[-1], 1e-9)
    t = np.gradient(p, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-12)[:, None]
    lado = np.cross(t, [0.0, 1.0, 0.0])
    largo_lado = np.linalg.norm(lado, axis=1)
    lado[largo_lado < 1e-6] = [1.0, 0.0, 0.0]
    lado /= np.maximum(np.linalg.norm(lado, axis=1), 1e-12)[:, None]
    arriba = np.cross(lado, t)
    onda_l = np.zeros(len(p))
    onda_a = np.zeros(len(p))
    for k in range(3):
        lam = longitud_onda * (0.6 + 0.8 * rng.rand())
        onda_l += np.sin(2 * math.pi * s / lam + rng.rand() * 6.283) / (k + 1)
        onda_a += np.sin(2 * math.pi * s / lam * 1.3 + rng.rand() * 6.283) / (k + 1) * 0.3
    sobre = np.sin(np.pi * s / total) ** 0.5
    return p + (lado * onda_l[:, None] + arriba * onda_a[:, None]) * (amplitud * sobre)[:, None]
