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
