"""Apoyar un cable que cuelga demasiado sobre el suelo o sobre objetos, sin simular.

Para cada punto del cable se busca qué hay debajo de la recta que une los dos
extremos del tramo. Si el cable baja de esa superficie, se queda encima,
tumbado. ``bajar(x, y, z)`` devuelve la altura de la primera superficie que
encuentra un rayo lanzado hacia abajo desde (x, y, z), o None.
"""

from pipeeditor import vec


def apoyar_tramo(puntos, radio, altura_suelo=None, bajar=None):
    """Devuelve los ``puntos`` del tramo levantados donde atraviesan algo.

    Los extremos nunca se mueven: son los anclajes.
    """
    if len(puntos) < 3 or (altura_suelo is None and bajar is None):
        return list(puntos)
    p, q = puntos[0], puntos[-1]
    horizontal = vec.distancia((p[0], 0, p[2]), (q[0], 0, q[2]))
    total = vec.longitud_polilinea(puntos)
    acum = 0.0
    salida = [p]
    for i in range(1, len(puntos) - 1):
        acum += vec.distancia(puntos[i - 1], puntos[i])
        r = puntos[i]
        if horizontal > 1e-9:
            u = vec.distancia((p[0], 0, p[2]), (r[0], 0, r[2])) / horizontal
        else:
            u = acum / total if total > 0 else 0.0
        u = max(0.0, min(1.0, u))
        cuerda = p[1] + (q[1] - p[1]) * u
        suelo = None
        if altura_suelo is not None and altura_suelo < cuerda:
            suelo = altura_suelo
        if bajar is not None:
            golpe = bajar(r[0], max(cuerda, r[1]) + radio * 0.5, r[2])
            if golpe is not None and (suelo is None or golpe > suelo):
                suelo = golpe
        y = r[1]
        if suelo is not None and y < suelo + radio:
            y = suelo + radio
        salida.append((r[0], y, r[2]))
    salida.append(q)
    return salida


def cajas_de_malla(puntos, triangulos, celdas=8, tamano_minimo=1.0):
    """Cajas (mínimo, máximo) que cubren la forma de una malla, no solo su caja entera.

    Una mesa da su tablero y sus patas (por debajo queda libre); una L, sus
    dos brazos. Se divide la caja de la malla en una rejilla de hasta
    ``celdas`` por eje, se marcan las celdas que tocan sus triángulos o que
    quedan dentro de ella, y se juntan en cajas grandes. ``puntos``: N×3;
    ``triangulos``: M×3 índices. Necesita numpy.
    """
    import numpy as np
    P = np.asarray(puntos, dtype=float).reshape(-1, 3)
    T = np.asarray(triangulos, dtype=int).reshape(-1, 3)
    if len(P) == 0:
        return []
    lo, hi = P.min(axis=0), P.max(axis=0)
    if len(T) == 0:
        return [(tuple(lo), tuple(hi))]
    tam = hi - lo
    n = np.maximum(1, np.minimum(celdas, np.floor(tam / max(tamano_minimo, 1e-6)).astype(int)))
    paso = np.where(tam > 0, tam / n, 1.0)
    ocupada = np.zeros(tuple(n), dtype=bool)
    # celdas que tocan cada triángulo (por su caja)
    tri = P[T]
    t_lo = np.floor((tri.min(axis=1) - lo) / paso - 1e-9).astype(int)
    t_hi = np.floor((tri.max(axis=1) - lo) / paso + 1e-9).astype(int)
    t_lo = np.clip(t_lo, 0, n - 1)
    t_hi = np.clip(t_hi, 0, n - 1)
    for a, b in zip(t_lo, t_hi):
        ocupada[a[0]:b[0] + 1, a[1]:b[1] + 1, a[2]:b[2] + 1] = True
    # celdas cuyo centro queda dentro de la malla (rayo hacia +X, cuenta de cortes)
    idx = np.stack(np.meshgrid(*[np.arange(k) for k in n], indexing="ij"), axis=-1).reshape(-1, 3)
    centros = lo + (idx + 0.5) * paso
    v0, v1, v2 = tri[:, 0], tri[:, 1], tri[:, 2]
    # proyección en el plano YZ: ¿el centro cae en el triángulo y el corte está a +X?
    for c, i in zip(centros, idx):
        if ocupada[tuple(i)]:
            continue
        y, z = c[1], c[2]
        d = (v1[:, 1] - v0[:, 1]) * (v2[:, 2] - v0[:, 2]) - (v2[:, 1] - v0[:, 1]) * (v1[:, 2] - v0[:, 2])
        valido = np.abs(d) > 1e-12
        d = np.where(valido, d, 1.0)
        u = ((v1[:, 1] - y) * (v2[:, 2] - z) - (v2[:, 1] - y) * (v1[:, 2] - z)) / d
        v = ((v2[:, 1] - y) * (v0[:, 2] - z) - (v0[:, 1] - y) * (v2[:, 2] - z)) / d
        w = 1.0 - u - v
        dentro_tri = valido & (u >= 0) & (v >= 0) & (w >= 0)
        x = u * v0[:, 0] + v * v1[:, 0] + w * v2[:, 0]
        if np.count_nonzero(dentro_tri & (x > c[0])) % 2 == 1:
            ocupada[tuple(i)] = True
    # juntar celdas en cajas grandes
    usada = np.zeros_like(ocupada)
    cajas = []
    for i in range(n[0]):
        for j in range(n[1]):
            for k in range(n[2]):
                if not ocupada[i, j, k] or usada[i, j, k]:
                    continue
                i2 = i
                while i2 + 1 < n[0] and ocupada[i2 + 1, j, k] and not usada[i2 + 1, j, k]:
                    i2 += 1
                j2 = j
                while j2 + 1 < n[1] and np.all(ocupada[i:i2 + 1, j2 + 1, k] & ~usada[i:i2 + 1, j2 + 1, k]):
                    j2 += 1
                k2 = k
                while k2 + 1 < n[2] and np.all(ocupada[i:i2 + 1, j:j2 + 1, k2 + 1]
                                               & ~usada[i:i2 + 1, j:j2 + 1, k2 + 1]):
                    k2 += 1
                usada[i:i2 + 1, j:j2 + 1, k:k2 + 1] = True
                a = lo + np.array([i, j, k]) * paso
                b = lo + np.array([i2 + 1, j2 + 1, k2 + 1]) * paso
                cajas.append((tuple(float(x) for x in a), tuple(float(x) for x in b)))
    return cajas
