"""Cuerpos de cable y de tubería: el perfil barrido a lo largo del recorrido.

Perfiles de cable: redondo, doble (cable de lámpara), plano (cinta), trenzado
(cuerda de tres cabos), corrugado (manguera) y espiral (cable de teléfono).
Perfiles de tubería: redonda, cuadrada (conducto), corrugada (flexible) y
aislada. Las tuberías pueden ser huecas, con pared visible en los extremos.
"""

import math

from pipeeditor import malla as ml
from pipeeditor import trazado, vec

PERFILES_CABLE = ("redondo", "doble", "plano", "trenzado", "corrugado", "espiral", "cadena")
PERFILES_TUBERIA = ("redonda", "cuadrada", "corrugada", "aislada", "bandeja")

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
    if perfil == "cadena":
        return cadena(centros, radio, lados)
    detalle = {"trenzado": radio * 0.45, "corrugado": radio * 0.3, "espiral": radio * 0.6}.get(perfil)
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


def eslabon(radio_alambre, lados=8, pasos=8):
    """Eslabón de cadena (eje Y), centrado en el origen, en el plano XY.

    Medidas de una cadena corriente: luz interior de 3,5 diámetros de alambre
    de largo por 1,4 de ancho.
    """
    d = 2.0 * radio_alambre
    rc = 1.2 * d                      # radio de las curvas (al eje del alambre)
    recta = 2.1 * d                   # largo de cada lado recto
    centros, marcos = [], []

    def anadir(c, t):
        t = vec.unitario(t)
        fuera = vec.unitario((c[0], 0.0, 0.0)) if abs(c[0]) > 1e-9 else (0.0, 1.0 if c[1] > 0 else -1.0, 0.0)
        nn = vec.unitario(vec.resta(fuera, vec.escala(t, vec.punto(fuera, t))), (1.0, 0.0, 0.0))
        centros.append(c)
        marcos.append((t, nn, vec.cruz(t, nn)))

    for i in range(pasos):               # lado derecho, subiendo
        y = -recta / 2.0 + recta * i / float(pasos)
        anadir((rc, y, 0.0), (0.0, 1.0, 0.0))
    for i in range(pasos * 2):           # curva de arriba
        a = math.pi * i / float(pasos * 2)
        anadir((rc * math.cos(a), recta / 2.0 + rc * math.sin(a), 0.0), (-math.sin(a), math.cos(a), 0.0))
    for i in range(pasos):               # lado izquierdo, bajando
        y = recta / 2.0 - recta * i / float(pasos)
        anadir((-rc, y, 0.0), (0.0, -1.0, 0.0))
    for i in range(pasos * 2):           # curva de abajo
        a = math.pi + math.pi * i / float(pasos * 2)
        anadir((rc * math.cos(a), -recta / 2.0 + rc * math.sin(a), 0.0), (-math.sin(a), math.cos(a), 0.0))
    centros.append(centros[0])
    marcos.append(marcos[0])
    return ml.barrer(centros, marcos, lambda i: ml.circulo(radio_alambre, lados), tapas=False,
                     escala_v=2 * math.pi * radio_alambre)


def paso_cadena(radio_alambre):
    return 3.5 * 2.0 * radio_alambre


def cadena(centros, radio_alambre, lados=8):
    """Cadena de eslabones a lo largo de ``centros``; cada eslabón, girado 90° respecto al anterior.

    ``radio_alambre``: la mitad del grosor del cable (una cadena «de 8 mm»
    tiene alambre de 8 mm).
    """
    modelo = eslabon(radio_alambre, max(6, lados))
    paso = paso_cadena(radio_alambre)
    total = ml.Malla()
    marcos = trazado.marcos(centros)
    s = vec.acumulada(centros)
    j = 0
    for k, (p, t, d) in enumerate(trazado.uniforme(centros, paso)):
        while j < len(s) - 2 and s[j + 1] < d:
            j += 1
        lado = marcos[j][1]
        if k % 2:
            lado = vec.cruz(t, lado)
        total.anadir(modelo, vec.marco_desde_eje(p, t, lado))
    return total


def _un_cable(centros, marcos, radio, perfil, lados):
    if perfil == "doble":
        # Cable de lámpara: una sola funda en forma de 8, con el alma que une los dos conductores.
        return _tubo(centros, radio, lados, perfil=ocho(radio, max(6, lados)), marcos=marcos)
    if perfil == "plano":
        forma = [(0.32 * radio * math.cos(2 * math.pi * k / lados), radio * math.sin(2 * math.pi * k / lados))
                 for k in range(lados)]
        return _tubo(centros, radio, lados, perfil=forma, marcos=marcos)
    if perfil == "trenzado":
        return cuerda(centros, marcos, radio, lados)
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


def ocho(radio, lados):
    """Contorno en 8: dos círculos de ``radio`` (arriba y abajo) unidos por un alma estrecha."""
    d = radio * 0.95            # distancia del centro de cada conductor al eje
    w = radio * 0.42            # medio ancho del alma
    ya = d - math.sqrt(radio * radio - w * w)
    salida = []
    for centro, signo in ((d, 1.0), (-d, -1.0)):
        a0 = math.atan2((ya * signo) - centro, w * signo)
        a1 = math.atan2((ya * signo) - centro, -w * signo)
        if a1 <= a0:
            a1 += 2 * math.pi
        for k in range(lados + 1):
            a = a0 + (a1 - a0) * k / float(lados)
            salida.append((radio * math.cos(a), centro + radio * math.sin(a)))
    return salida


def cuerda(centros, marcos, radio, lados):
    """Cuerda de tres cabos que se tocan, torcidos en hélice, con las fibras de cada cabo.

    Tres cabos de radio rc tangentes entre sí y al círculo exterior: sus
    centros quedan a 0,536·R del eje y rc = 0,464·R. Una vuelta de la cuerda
    mide unas 3,5 veces su diámetro, como en una cuerda real. Las fibras
    giran al revés que los cabos.
    """
    m = ml.Malla()
    rc = radio * 0.464 * 1.04      # un poco de solape para que no se vean huecos
    eje = radio * 0.536
    vuelta = radio * 7.0
    lados_cabo = max(8, lados)
    s = vec.acumulada(centros)
    for j in range(3):
        def d(i, sd, j=j):
            a = 2 * math.pi * (sd / vuelta + j / 3.0)
            return (eje * math.cos(a), eje * math.sin(a))
        ruta = _desplazar(centros, marcos, d)
        marcos_ruta = trazado.marcos(ruta, marcos[0][1])

        def anillo(i, j=j):
            fase = 2 * math.pi * (-s[i] / (vuelta * 0.45) + j / 3.0)
            return [(rc * (1.0 + 0.05 * math.cos(6 * t + fase)) * math.cos(t),
                     rc * (1.0 + 0.05 * math.cos(6 * t + fase)) * math.sin(t))
                    for t in (2 * math.pi * k / float(lados_cabo) for k in range(lados_cabo))]
        m.anadir(ml.barrer(ruta, marcos_ruta, anillo))
    return m


# --- tuberías -------------------------------------------------------------------------

def perfil_bandeja(radio):
    """Sección en U de una bandeja portacables: ancho = grosor, alto = la mitad (máximo 10 cm), abierta hacia arriba."""
    ancho = 2.0 * radio
    alto = min(ancho * 0.5, 10.0)
    e = max(0.08, ancho * 0.012)
    a, b = -alto / 2.0, alto / 2.0
    w = ancho / 2.0
    puntos = [(a, -w), (a, w), (b, w), (b, w - e), (a + e, w - e), (a + e, -w + e), (b, -w + e), (b, -w)]
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(puntos, puntos[1:] + puntos[:1]))
    return puntos if area > 0 else list(reversed(puntos))


def cuerpo_tuberia(centros, radio, perfil="redonda", lados=16, pared=0.0, abierta=False):
    """Malla de la tubería. Si ``abierta`` y hay ``pared``, se ve hueca en los extremos."""
    if len(centros) < 2:
        return ml.Malla()
    lados = max(4, int(lados))
    if perfil == "cuadrada":
        forma = ml.cuadrado_redondeado(2.0 * radio, 0.18 * radio, max(1, lados // 8))
        interior = ml.cuadrado_redondeado(2.0 * (radio - pared), 0.12 * radio, max(1, lados // 8)) if pared else None
        radio_en = None
    elif perfil == "bandeja":
        forma, interior, radio_en = perfil_bandeja(radio), None, None
        pared = 0.0
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
