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


def reposar(cadena, radio, suelo=None, empujar=None, rigidez=0.3, pasos=110, iteraciones=12, friccion=0.7):
    """Devuelve las posiciones en reposo (array N×3) de una ``Cadena``.

    ``empujar(P, radio, antes)``: saca de los objetos de apoyo los puntos de
    ``P`` (array N×3) y devuelve (P corregido, máscara de puntos en contacto).
    ``antes`` son las posiciones del paso anterior: un punto que acaba de
    entrar en un objeto sale por donde entró (así no atraviesa una mesa fina
    y sale por debajo).
    """
    return reposar_varias([cadena], radio, suelo, empujar, rigidez, pasos, iteraciones, friccion)[0]


def reposar_varias(cadenas, radio, suelo=None, empujar=None, rigidez=0.3, pasos=110, iteraciones=12,
                   friccion=0.7):
    """Reposo de varias cadenas a la vez (los cables de un haz), sin que se atraviesen entre sí.

    Se resuelven todas juntas en los mismos arrays: cuesta casi lo mismo que
    una sola. Devuelve una lista de arrays, uno por cadena.
    """
    trozos = [np.array(c.puntos, dtype=float) for c in cadenas]
    tamanos = [len(t) for t in trozos]
    if not trozos or min(tamanos) < 3:
        return trozos
    x = np.concatenate(trozos)
    n = len(x)
    inicios = np.cumsum([0] + tamanos[:-1])
    ids = np.repeat(np.arange(len(cadenas)), tamanos)
    largos = np.zeros(n - 1)
    enlace = np.ones(n - 1)   # 0 entre el final de una cadena y el principio de la siguiente
    peso = np.ones(n)
    fijos = []
    ganchos = []              # (posición, primer índice, último índice)
    for c, ini, tam in zip(cadenas, inicios, tamanos):
        largos[ini:ini + tam - 1] = c.largos
        if ini + tam - 1 < n - 1:
            enlace[ini + tam - 1] = 0.0
        fijos.extend(int(ini + f) for f in c.fijos)
        for g in c.ganchos:
            ganchos.append((np.asarray(g, dtype=float), ini, ini + tam))
    fijos = np.array(sorted(set(fijos)), dtype=int)
    peso[fijos] = 0.0
    pos_fijos = x[fijos].copy() if len(fijos) else None
    medio = float(largos[enlace > 0].mean())
    gravedad = medio * 0.01
    rmin = radio_minimo(radio, rigidez) if rigidez > 0 else 0.0
    # Distancia mínima entre i e i+2 para no doblar más que rmin (dentro de cada cadena).
    if rmin > 0:
        tramo = 0.5 * (largos[:-1] + largos[1:])
        angulo = np.minimum(tramo / rmin, math.pi * 0.95)
        dmin = 2.0 * tramo * np.cos(angulo / 2.0)
        dmin[(enlace[:-1] == 0) | (enlace[1:] == 0)] = 0.0
    else:
        dmin = None
    varias = len(cadenas) > 1
    banda = (tamanos[0], len(cadenas)) if varias and len(set(tamanos)) == 1 else None
    minimo = 2.0 * radio
    pares = np.arange(0, n - 1, 2), np.arange(1, n - 1, 2)
    xp = x.copy()

    def restricciones(cerca):
        for idx in pares:
            _distancia(x, idx, largos * 1.0, peso, enlace)
        if dmin is not None:
            _flexion(x, dmin, peso)
        if cerca is not None:
            _separar_entre(x, cerca[0], cerca[1], minimo, peso)
        if pos_fijos is not None:
            x[fijos] = pos_fijos
        for g, a, b in ganchos:
            j = a + int(np.argmin(((x[a:b] - g) ** 2).sum(axis=1)))
            if peso[j] > 0:
                x[j] = g
        if suelo is not None:
            abajo = (x[:, 1] < suelo + radio) & (peso > 0)
            x[abajo, 1] = suelo + radio

    cerca = None
    for paso in range(pasos):
        v = (x - xp) * 0.97
        xp = x.copy()
        x += v
        x[:, 1] -= gravedad * peso
        if varias and paso % 3 == 0:
            cerca = _parejas(x, ids, minimo * 1.6, banda)
        for _ in range(iteraciones):
            restricciones(cerca)
        tocan = np.zeros(n, dtype=bool)
        if suelo is not None:
            tocan |= (x[:, 1] < suelo + radio * 1.05) & (peso > 0)
        if empujar is not None:
            x2, contacto = empujar(x, radio, xp)
            x2 = np.asarray(x2, dtype=float)
            x[peso > 0] = x2[peso > 0]
            tocan |= np.asarray(contacto, dtype=bool) & (peso > 0)
            _empujar_tramos(x, xp, radio, empujar, peso, enlace)
        if tocan.any():
            # Rozamiento: lo que toca pierde casi toda su velocidad.
            xp[tocan] = x[tocan] - (x[tocan] - xp[tocan]) * (1.0 - friccion)
    # Un último ajuste sin gravedad.
    antes = x.copy()
    for _ronda in range(4 if varias else 1):
        cerca = _parejas(x, ids, minimo * 1.6, banda) if varias else None
        for _ in range(iteraciones):
            restricciones(cerca)
    if empujar is not None:
        x2, _c = empujar(x, radio, antes)
        x2 = np.asarray(x2, dtype=float)
        x[peso > 0] = x2[peso > 0]
    return [x[a:a + t].copy() for a, t in zip(inicios, tamanos)]


def _empujar_tramos(x, xp, radio, empujar, peso, enlace):
    """Mira también el centro de cada tramo: un tablero más fino que el tramo
    no se detecta con los puntos solos (los dos extremos quedan fuera)."""
    medios = 0.5 * (x[:-1] + x[1:])
    antes = 0.5 * (xp[:-1] + xp[1:])
    nuevos, contacto = empujar(medios, radio, antes)
    contacto = np.asarray(contacto, dtype=bool) & (enlace > 0)
    if not contacto.any():
        return
    delta = (np.asarray(nuevos, dtype=float) - medios) * contacto[:, None]
    mover = np.zeros_like(x)
    cuenta = np.zeros(len(x))
    np.add.at(mover, np.arange(len(x) - 1), delta)
    np.add.at(mover, np.arange(1, len(x)), delta)
    np.add.at(cuenta, np.arange(len(x) - 1), contacto * 1.0)
    np.add.at(cuenta, np.arange(1, len(x)), contacto * 1.0)
    hay = (cuenta > 0) & (peso > 0)
    x[hay] += mover[hay] / cuenta[hay][:, None]


def _distancia(x, idx, largos, peso, enlace=None):
    a, b = idx, idx + 1
    d = x[b] - x[a]
    l = np.sqrt((d * d).sum(axis=1))
    l[l < 1e-12] = 1e-12
    wa, wb = peso[a], peso[b]
    if enlace is not None:
        wa, wb = wa * enlace[a], wb * enlace[a]
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


def _parejas(x, ids, distancia, banda=None):
    """Parejas (i, j) de puntos de cadenas distintas a menos de ``distancia``.

    Con ``banda`` (cadenas del mismo tamaño, como los cables de un haz) solo
    se comparan puntos con índice parecido: mucho más rápido.
    """
    if banda is not None:
        tam, cuantas = banda
        P = x.reshape(cuantas, tam, 3)
        ii, jj = [], []
        ancho = 8
        base = np.arange(tam)
        for a in range(cuantas):
            for b in range(a + 1, cuantas):
                for desfase in range(-ancho, ancho + 1):
                    ia = base[max(0, -desfase):tam - max(0, desfase)]
                    ib = ia + desfase
                    d = P[a, ia] - P[b, ib]
                    cerca = (d * d).sum(axis=1) < distancia * distancia
                    if cerca.any():
                        ii.append(a * tam + ia[cerca])
                        jj.append(b * tam + ib[cerca])
        if not ii:
            return np.zeros(0, dtype=int), np.zeros(0, dtype=int)
        return np.concatenate(ii), np.concatenate(jj)
    d2 = ((x[:, None, :] - x[None, :, :]) ** 2).sum(axis=2)
    i, j = np.nonzero((d2 < distancia * distancia) & (ids[:, None] < ids[None, :]))
    return i, j


def _separar_entre(x, ii, jj, minimo, peso):
    if not len(ii):
        return
    d = x[ii] - x[jj]
    l = np.sqrt((d * d).sum(axis=1))
    cerca = l < minimo
    if not cerca.any():
        return
    ii, jj, d, l = ii[cerca], jj[cerca], d[cerca], np.maximum(l[cerca], 1e-9)
    wi, wj = peso[ii], peso[jj]
    w = wi + wj
    w[w == 0] = 1.0
    c = d / l[:, None] * ((minimo - l) / w)[:, None]
    delta = np.zeros_like(x)
    cuenta = np.zeros(len(x))
    np.add.at(delta, ii, c * wi[:, None])
    np.add.at(delta, jj, -c * wj[:, None])
    np.add.at(cuenta, ii, 1.0)
    np.add.at(cuenta, jj, 1.0)
    hay = cuenta > 0
    x[hay] += delta[hay] / cuenta[hay][:, None]


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
    sobre = np.clip(np.sin(np.pi * s / total), 0.0, 1.0) ** 0.5
    return p + (lado * onda_l[:, None] + arriba * onda_a[:, None]) * (amplitud * sobre)[:, None]


def ondas_suelo(puntos, largo, radio, rigidez, semilla, tocan):
    """Reparte el cable que sobra en curvas amplias donde está tumbado.

    ``puntos``: el cable ya apoyado (los puntos que bajaban del suelo o de un
    objeto se han subido encima), que mide menos que ``largo``. ``tocan``:
    qué puntos están apoyados. En cada tramo apoyado se añaden unas pocas
    curvas laterales (1 a 3 medias ondas, con una segunda onda más pequeña
    para que no sean regulares), nulas y tangentes en los extremos, con la
    amplitud justa para que el cable vuelva a medir ``largo``. Si las curvas
    doblarían más de lo que permite la rigidez, se ponen menos. Es solo el
    punto de partida del reposo: luego se relaja con todo lo demás.
    """
    p = np.array(puntos, dtype=float)
    tocan = np.asarray(tocan, dtype=bool)
    sobra = largo - _largo(p)
    if sobra <= radio * 0.1 or len(p) < 5 or not tocan.any():
        return p
    tramos = []
    i = 0
    while i < len(p):
        if tocan[i]:
            j = i
            while j + 1 < len(p) and tocan[j + 1]:
                j += 1
            if j - i >= 3:
                tramos.append((max(0, i - 1), min(len(p) - 1, j + 1)))
            i = j + 1
        else:
            i += 1
    if not tramos:
        return p
    largos = [_largo(p[a:b + 1]) for a, b in tramos]
    total = sum(largos)
    if total < 1e-9:
        return p
    rng = np.random.RandomState(int(semilla) & 0x7FFFFFFF)
    rmin = radio_minimo(radio, rigidez)
    for (a, b), lr in zip(tramos, largos):
        extra = sobra * lr / total
        seg = p[a:b + 1].copy()
        d = seg[-1] - seg[0]
        d[1] = 0.0
        if np.linalg.norm(d) < 1e-9:
            d = np.array([1.0, 0.0, 0.0])
        d /= np.linalg.norm(d)
        lado = np.cross([0.0, 1.0, 0.0], d)
        lado /= max(np.linalg.norm(lado), 1e-12)
        s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(seg[1:] - seg[:-1], axis=1))])
        u = s / max(s[-1], 1e-9)
        m = int(rng.choice([1, 2, 2, 3]))
        f1, f2, k2 = rng.rand() * 6.283, rng.rand() * 6.283, 0.25 + 0.3 * rng.rand()
        while True:
            forma = np.sin(np.pi * u) ** 2 * (np.sin(m * np.pi * u + f1) + k2 * np.sin((m + 2) * np.pi * u + f2))
            forma /= max(np.abs(forma).max(), 1e-9)
            objetivo = lr + extra
            lo, hi = 0.0, lr * 0.9
            for _ in range(40):
                amp = 0.5 * (lo + hi)
                if _largo(seg + lado * (amp * forma)[:, None]) < objetivo:
                    lo = amp
                else:
                    hi = amp
            amp = 0.5 * (lo + hi)
            # curvatura máxima aproximada de la onda frente al radio mínimo
            curva = amp * ((m + 2) * np.pi / max(lr, 1e-9)) ** 2
            if curva <= 1.0 / rmin or m == 1:
                break
            m -= 1
        p[a:b + 1] = seg + lado * (amp * forma)[:, None]
    return p


def _largo(p):
    return float(np.linalg.norm(p[1:] - p[:-1], axis=1).sum()) if len(p) > 1 else 0.0
