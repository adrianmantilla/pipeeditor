"""Cuerpos de cable y de tubería: el perfil barrido a lo largo del recorrido.

Perfiles de cable: redondo, doble (cable de lámpara), plano (cinta), trenzado
(cuerda de tres cabos), corrugado (manguera) y espiral (cable de teléfono).
Perfiles de tubería: redonda, cuadrada (conducto), corrugada (flexible) y
aislada. Las tuberías pueden ser huecas, con pared visible en los extremos.
"""

import math

from pipeeditor import malla as ml
from pipeeditor import trazado, vec

PERFILES_CABLE = ("redondo", "doble", "plano", "trenzado", "corrugado", "espiral")
PERFILES_TUBERIA = ("redonda", "cuadrada", "corrugada", "aislada")

# Puntos máximos de un recorrido para que un cable no tumbe a Maya.
MAX_PUNTOS = 6000


def _paso_seguro(centros, paso):
    total = vec.longitud_polilinea(centros)
    return max(paso, total / float(MAX_PUNTOS))


def _desplazar(centros, marcos, desplazamiento):
    """Nueva ruta: cada punto movido (x, y) en el plano (normal, binormal) del marco."""
    s = vec.acumulada(centros)
    salida = []
    for i, c in enumerate(centros):
        _t, nn, bb = marcos[i]
        x, y = desplazamiento(i, s[i])
        salida.append(vec.suma(c, vec.suma(vec.escala(nn, x), vec.escala(bb, y))))
    return salida


def _tubo(centros, radio, lados, tapas=True, perfil=None, radio_en=None, invertir=False, marcos=None):
    """Barrido simple de un círculo (o de ``perfil``) por ``centros``."""
    if len(centros) < 2:
        return ml.Malla()
    marcos = marcos or trazado.marcos(centros)
    s = vec.acumulada(centros)
    if perfil is not None:
        anillo = lambda i: perfil
    elif radio_en is not None:
        anillo = lambda i: ml.circulo(radio_en(s[i]), lados)
    else:
        fijo = ml.circulo(radio, lados)
        anillo = lambda i: fijo
    return ml.barrer(centros, marcos, anillo, tapas=tapas, escala_v=2 * math.pi * radio, invertir=invertir)


def posiciones_haz(cantidad, separacion):
    """Posiciones (x, y) de ``cantidad`` cables agrupados: uno en medio y anillos de seis."""
    if cantidad <= 1:
        return [(0.0, 0.0)]
    salida = [(0.0, 0.0)]
    anillo = 1
    while len(salida) < cantidad:
        en_anillo = 6 * anillo
        quedan = cantidad - len(salida)
        n = min(en_anillo, quedan)
        for k in range(n):
            a = 2 * math.pi * k / float(n) + (0.5 if anillo % 2 == 0 else 0.0)
            salida.append((separacion * anillo * math.cos(a), separacion * anillo * math.sin(a)))
        anillo += 1
    return salida[:cantidad]


def radio_haz(cantidad, radio):
    """Radio exterior del haz, para las bridas que lo abrazan."""
    if cantidad <= 1:
        return radio
    puntos = posiciones_haz(cantidad, 2.0 * radio * 1.02)
    return max(math.hypot(x, y) for x, y in puntos) + radio


# --- cables ---------------------------------------------------------------------------

def cuerpo_cable(centros, radio, perfil="redondo", lados=8, cantidad=1, torsion=0.0, paso=None):
    """Malla del cable (o del haz de cables) a lo largo de ``centros``.

    ``torsion``: vueltas por cada 100 unidades (1 m en centímetros) del haz.
    ``paso``: separación máxima entre anillos; por defecto, según el perfil.
    """
    if len(centros) < 2:
        return ml.Malla()
    lados = max(3, int(lados))
    detalle = {"trenzado": radio * 0.9, "corrugado": radio * 0.3, "espiral": radio * 0.6}.get(perfil)
    if cantidad > 1 and torsion:
        detalle = min(detalle or 1e9, 100.0 / max(abs(torsion), 1e-6) / 24.0)
    paso_final = paso if paso else detalle
    if paso_final:
        centros = trazado.remuestrear(centros, _paso_seguro(centros, paso_final))
    marcos = trazado.marcos(centros)
    total = ml.Malla()
    for x0, y0 in posiciones_haz(cantidad, 2.0 * radio * 1.02):
        if cantidad > 1:
            def desplazamiento(i, s, x0=x0, y0=y0):
                a = 2 * math.pi * torsion * s / 100.0
                return (x0 * math.cos(a) - y0 * math.sin(a), x0 * math.sin(a) + y0 * math.cos(a))
            ruta = _desplazar(centros, marcos, desplazamiento)
            marcos_ruta = trazado.marcos(ruta, marcos[0][1])
        else:
            ruta, marcos_ruta = centros, marcos
        total.anadir(_un_cable(ruta, marcos_ruta, radio, perfil, lados))
    return total


def _un_cable(centros, marcos, radio, perfil, lados):
    if perfil == "doble":
        m = ml.Malla()
        for lado in (-1.0, 1.0):
            ruta = _desplazar(centros, marcos, lambda i, s, lado=lado: (0.0, lado * radio * 0.98))
            m.anadir(_tubo(ruta, radio, lados, marcos=trazado.marcos(ruta, marcos[0][1])))
        return m
    if perfil == "plano":
        forma = [(0.32 * radio * math.cos(2 * math.pi * k / lados), radio * math.sin(2 * math.pi * k / lados))
                 for k in range(lados)]
        return _tubo(centros, radio, lados, perfil=forma, marcos=marcos)
    if perfil == "trenzado":
        m = ml.Malla()
        vuelta = radio * 7.0  # largo de una vuelta de la trenza
        for j in range(3):
            def d(i, s, j=j):
                a = 2 * math.pi * (s / vuelta + j / 3.0)
                return (radio * 0.5 * math.cos(a), radio * 0.5 * math.sin(a))
            ruta = _desplazar(centros, marcos, d)
            m.anadir(_tubo(ruta, radio * 0.56, max(5, lados - 2), marcos=trazado.marcos(ruta, marcos[0][1])))
        return m
    if perfil == "corrugado":
        periodo = radio * 1.2
        return _tubo(centros, radio, lados, marcos=marcos,
                     radio_en=lambda s: radio * (1.0 + 0.1 * math.cos(2 * math.pi * s / periodo)))
    if perfil == "espiral":
        alambre = radio * 0.33
        espira = radio - alambre
        paso_espira = alambre * 2.3
        s = vec.acumulada(centros)
        total = s[-1]
        vueltas = total / paso_espira
        n = max(2, min(MAX_PUNTOS, int(vueltas * 8)))
        base = [trazado.en_distancia(centros, total * k / float(n)) for k in range(n + 1)]
        ruta_base = [p for p, _ in base]
        marcos_base = trazado.marcos(ruta_base, marcos[0][1])
        ruta = []
        for k, p in enumerate(ruta_base):
            a = 2 * math.pi * vueltas * k / float(n)
            _t, nn, bb = marcos_base[k]
            ruta.append(vec.suma(p, vec.suma(vec.escala(nn, espira * math.cos(a)), vec.escala(bb, espira * math.sin(a)))))
        return _tubo(ruta, alambre, max(5, lados - 2))
    return _tubo(centros, radio, lados, marcos=marcos)


# --- tuberías -------------------------------------------------------------------------

def cuerpo_tuberia(centros, radio, perfil="redonda", lados=16, pared=0.0, abierta=False):
    """Malla de la tubería. Si ``abierta`` y hay ``pared``, se ve hueca en los extremos."""
    if len(centros) < 2:
        return ml.Malla()
    lados = max(4, int(lados))
    if perfil == "cuadrada":
        forma = ml.cuadrado_redondeado(2.0 * radio, 0.18 * radio, max(1, lados // 8))
        interior = ml.cuadrado_redondeado(2.0 * (radio - pared), 0.12 * radio, max(1, lados // 8)) if pared else None
        radio_en = None
    elif perfil == "corrugada":
        centros = trazado.remuestrear(centros, _paso_seguro(centros, radio * 0.16))
        periodo = radio * 0.7
        forma, interior = None, None
        radio_en = lambda s: radio * (1.0 + 0.09 * math.cos(2 * math.pi * s / periodo))
    else:
        forma, interior, radio_en = None, None, None
        if perfil == "aislada":
            radio = radio * 1.35
    marcos = trazado.marcos(centros)
    hueca = abierta and pared > 0 and pared < radio * 0.95
    fuera = _tubo(centros, radio, lados, tapas=not hueca, perfil=forma, radio_en=radio_en, marcos=marcos)
    if not hueca:
        return fuera
    radio_dentro = radio - pared
    perfil_dentro = interior if interior is not None else ml.circulo(radio_dentro, lados)
    dentro = _tubo(centros, radio_dentro, lados, tapas=False, perfil=perfil_dentro, invertir=True, marcos=marcos)
    m = ml.Malla()
    m.anadir(fuera)
    base = len(m.vertices)
    m.anadir(dentro)
    # Coronas en los extremos: une el primer y el último anillo de fuera y de dentro.
    filas_fuera = len(centros)
    n_lados = len(forma) if forma is not None else lados
    def fila(origen, i):
        return [origen + i * n_lados + k for k in range(n_lados)]
    perfil_fuera = forma if forma is not None else ml.circulo(radio, lados)
    ml.anillo_entre(m, fila(0, 0), fila(base, 0), perfil_fuera, al_reves=True)
    ml.anillo_entre(m, fila(0, filas_fuera - 1), fila(base, filas_fuera - 1), perfil_fuera, al_reves=False)
    return m
