"""Nodo de Maya «pipeEditorNodo»: calcula el cable o la tubería en vivo.

Entradas: las matrices de los anclajes (localizadores), una curva opcional,
las mallas de apoyo y todos los ajustes. Salidas: la malla del cuerpo, la de
las piezas y la curva central. Al mover un anclaje, Maya lo recalcula solo.
Toda la geometría la hace ``construir`` (Python puro).
"""

import math

import maya.api.OpenMaya as om

from pipeeditor import construir, piezas, perfiles
from pipeeditor import malla as ml

NOMBRE = "pipeEditorNodo"
ID = om.MTypeId(0x0007F1A0)  # rango reservado para uso local

# (atributo, clave de construir.POR_DEFECTO, tipo, opciones)
ENUMS = {
    "tipo": construir.TIPOS,
    "perfilCable": perfiles.PERFILES_CABLE,
    "modoTension": construir.MODOS_TENSION,
    "conectorInicio": piezas.CONECTORES,
    "conectorFin": piezas.CONECTORES,
    "pieza": piezas.PIEZAS_CABLE,
    "perfilTuberia": perfiles.PERFILES_TUBERIA,
    "recorrido": ("z", "l", "libre"),
    "codo": construir.CODOS,
    "extremos": piezas.EXTREMOS_TUBERIA,
}
NUMEROS = [
    # atributo, clave, tipo, mínimo, máximo suave
    ("grosor", "grosor", "d", 0.01, 50.0),
    ("lados", "lados", "i", 3, 32),
    ("segmentosMetro", "segmentos_metro", "i", 2, 100),
    ("salida", "salida", "d", 0.0, 50.0),
    ("apoyarSuelo", "apoyar_suelo", "b", None, None),
    ("alturaSuelo", "altura_suelo", "d", None, None),
    ("holgura", "holgura", "d", 0.0, 1.0),
    ("separacionPiezas", "separacion_piezas", "d", 1.0, 500.0),
    ("haz", "haz", "i", 1, 37),
    ("torsion", "torsion", "d", -10.0, 10.0),
    ("separacionBridasHaz", "separacion_bridas_haz", "d", 0.0, 500.0),
    ("radioCodo", "radio_codo", "d", 0.0, 10.0),
    ("separacionBridas", "separacion_bridas", "d", 0.0, 1000.0),
    ("pared", "pared", "d", 0.0, 10.0),
    ("separacionSoportes", "separacion_soportes", "d", 0.0, 1000.0),
    ("alcanceSoportes", "alcance_soportes", "d", 1.0, 1000.0),
]
CLAVE_DE_ENUM = {
    "tipo": "tipo", "perfilCable": "perfil_cable", "modoTension": "modo_tension",
    "conectorInicio": "conector_inicio", "conectorFin": "conector_fin", "pieza": "pieza",
    "perfilTuberia": "perfil_tuberia", "recorrido": "recorrido", "codo": "codo", "extremos": "extremos",
}
# Atributos de ajuste por orden, para la interfaz y los estilos.
AJUSTES = list(ENUMS) + [n[0] for n in NUMEROS]


def clave(atributo):
    """Clave de ``construir.POR_DEFECTO`` de un atributo del nodo."""
    if atributo in CLAVE_DE_ENUM:
        return CLAVE_DE_ENUM[atributo]
    for n in NUMEROS:
        if n[0] == atributo:
            return n[1]
    return None


def maya_useNewAPI():
    pass


class PipeEditorNodo(om.MPxNode):
    atributos = {}

    def __init__(self):
        om.MPxNode.__init__(self)

    @staticmethod
    def crear():
        return PipeEditorNodo()

    # --- definición -------------------------------------------------------------------
    @staticmethod
    def iniciar():
        A = PipeEditorNodo.atributos
        num = om.MFnNumericAttribute()
        typ = om.MFnTypedAttribute()
        mat = om.MFnMatrixAttribute()
        en = om.MFnEnumAttribute()

        A["anclas"] = mat.create("anclas", "anc", om.MFnMatrixAttribute.kDouble)
        mat.array = True
        mat.usesArrayDataBuilder = True
        A["factores"] = num.create("factores", "fac", om.MFnNumericData.kDouble, 1.0)
        num.array = True
        num.usesArrayDataBuilder = True
        A["longitudes"] = num.create("longitudes", "lon", om.MFnNumericData.kDouble, 0.0)
        num.array = True
        num.usesArrayDataBuilder = True
        A["ruta"] = typ.create("ruta", "rut", om.MFnData.kNurbsCurve)
        A["apoyos"] = typ.create("apoyos", "apo", om.MFnData.kMesh)
        typ.array = True
        typ.usesArrayDataBuilder = True
        typ.disconnectBehavior = om.MFnAttribute.kDelete
        A["conectorPropio"] = typ.create("conectorPropio", "cpr", om.MFnData.kMesh)

        for nombre, opciones in ENUMS.items():
            defecto = opciones.index(construir.POR_DEFECTO[CLAVE_DE_ENUM[nombre]])
            A[nombre] = en.create(nombre, nombre, defecto)
            for i, o in enumerate(opciones):
                en.addField(o, i)
            en.keyable = False
            en.channelBox = True
        for nombre, k, tipo, minimo, maximo in NUMEROS:
            defecto = construir.POR_DEFECTO[k]
            if tipo == "d":
                A[nombre] = num.create(nombre, nombre, om.MFnNumericData.kDouble, float(defecto))
            elif tipo == "i":
                A[nombre] = num.create(nombre, nombre, om.MFnNumericData.kInt, int(defecto))
            else:
                A[nombre] = num.create(nombre, nombre, om.MFnNumericData.kBoolean, bool(defecto))
            if minimo is not None:
                num.setMin(minimo)
            if maximo is not None and tipo != "b":
                num.setSoftMax(maximo)
            num.keyable = True

        A["cuerpo"] = typ.create("cuerpo", "cue", om.MFnData.kMesh)
        typ.writable = False
        typ.storable = False
        A["piezas"] = typ.create("piezas", "pie", om.MFnData.kMesh)
        typ.writable = False
        typ.storable = False
        A["curva"] = typ.create("curva", "cur", om.MFnData.kNurbsCurve)
        typ.writable = False
        typ.storable = False
        A["longitudesActuales"] = typ.create("longitudesActuales", "lac", om.MFnData.kDoubleArray)
        typ.writable = False
        typ.storable = False
        for nombre, corto, tipo in (("longitudTotal", "lto", om.MFnNumericData.kDouble),
                                    ("caida", "cai", om.MFnNumericData.kDouble),
                                    ("triangulos", "tri", om.MFnNumericData.kInt),
                                    ("tensos", "ten", om.MFnNumericData.kInt)):
            A[nombre] = num.create(nombre, corto, tipo, 0)
            num.writable = False
            num.storable = False

        salidas = ["cuerpo", "piezas", "curva", "longitudesActuales", "longitudTotal", "caida", "triangulos",
                   "tensos"]
        entradas = [n for n in A if n not in salidas]
        for n in entradas + salidas:
            om.MPxNode.addAttribute(A[n])
        for e in entradas:
            for s in salidas:
                om.MPxNode.attributeAffects(A[e], A[s])

    # --- cálculo ----------------------------------------------------------------------
    def compute(self, plug, datos):
        A = PipeEditorNodo.atributos
        salidas = ("cuerpo", "piezas", "curva", "longitudesActuales", "longitudTotal", "caida", "triangulos",
                   "tensos")
        if plug.isNull or om.MFnAttribute(plug.attribute()).name not in salidas:
            return None
        try:
            res = self._calcular(datos)
        except Exception as error:  # nunca tumbar Maya por un cable
            om.MGlobal.displayWarning("PipeEditor: {}".format(error))
            res = construir.Resultado()
        datos.outputValue(A["cuerpo"]).setMObject(_malla_maya(res.cuerpo))
        datos.outputValue(A["piezas"]).setMObject(_malla_maya(res.piezas))
        datos.outputValue(A["curva"]).setMObject(_curva_maya(res.curva))
        datos.outputValue(A["longitudesActuales"]).setMObject(
            om.MFnDoubleArrayData().create(om.MDoubleArray(res.longitudes)))
        datos.outputValue(A["longitudTotal"]).setDouble(res.longitud)
        datos.outputValue(A["caida"]).setDouble(res.caida)
        datos.outputValue(A["triangulos"]).setInt(res.triangulos())
        datos.outputValue(A["tensos"]).setInt(res.tensos)
        for s in salidas:
            datos.setClean(A[s])
        return self

    def _calcular(self, datos):
        A = PipeEditorNodo.atributos
        ajustes = {}
        for nombre, opciones in ENUMS.items():
            i = datos.inputValue(A[nombre]).asShort()
            ajustes[CLAVE_DE_ENUM[nombre]] = opciones[max(0, min(len(opciones) - 1, i))]
        for nombre, k, tipo, _mn, _mx in NUMEROS:
            h = datos.inputValue(A[nombre])
            ajustes[k] = h.asDouble() if tipo == "d" else (h.asInt() if tipo == "i" else h.asBool())

        factores = _valores_array(datos.inputArrayValue(A["factores"]), lambda h: h.asDouble())
        longitudes = _valores_array(datos.inputArrayValue(A["longitudes"]), lambda h: h.asDouble())
        matrices = _valores_array(datos.inputArrayValue(A["anclas"]), lambda h: h.asMatrix())
        anclajes = []
        for indice in sorted(matrices):
            m = matrices[indice]
            pos = (m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2))
            normal = (m.getElement(1, 0), m.getElement(1, 1), m.getElement(1, 2))
            anclajes.append(construir.Anclaje(pos, normal, factores.get(indice, 1.0), longitudes.get(indice, 0.0)))

        ruta, lineal = _ruta(datos.inputValue(A["ruta"]), ajustes["segmentos_metro"])
        apoyos = []
        arr = datos.inputArrayValue(A["apoyos"])
        for i in range(len(arr)):
            arr.jumpToPhysicalElement(i)
            objeto = arr.inputValue().asMesh()
            if not objeto.isNull():
                fn = om.MFnMesh(objeto)
                apoyos.append((fn, fn.autoUniformGridParams()))
        propio = None
        h = datos.inputValue(A["conectorPropio"]).asMesh()
        if not h.isNull():
            propio = _malla_python(om.MFnMesh(h))
        bajar = _bajar(apoyos) if apoyos else None
        cercano = _cercano(apoyos) if apoyos else None
        return construir.construir(ajustes, anclajes, ruta=ruta, ruta_lineal=lineal, bajar=bajar,
                                   cercano=cercano, malla_propia=propio)


def _valores_array(arr, leer):
    salida = {}
    for i in range(len(arr)):
        arr.jumpToPhysicalElement(i)
        salida[arr.elementLogicalIndex()] = leer(arr.inputValue())
    return salida


def _ruta(handle, segmentos_metro):
    objeto = handle.asNurbsCurve()
    if objeto.isNull():
        return None, False
    try:
        fn = om.MFnNurbsCurve(objeto)
    except RuntimeError:
        return None, False
    if fn.degree == 1:
        return [(p.x, p.y, p.z) for p in fn.cvPositions()], True
    largo = fn.length()
    n = max(8, int(math.ceil(largo / 100.0 * segmentos_metro * 2)))
    puntos = []
    for i in range(n + 1):
        p = fn.getPointAtParam(fn.findParamFromLength(largo * i / float(n)))
        puntos.append((p.x, p.y, p.z))
    if fn.form != om.MFnNurbsCurve.kOpen and puntos:
        puntos[-1] = puntos[0]
    return puntos, False


def _bajar(apoyos):
    abajo = om.MFloatVector(0.0, -1.0, 0.0)

    def bajar(x, y, z):
        mejor = None
        origen = om.MFloatPoint(x, y, z)
        for fn, acel in apoyos:
            golpe = fn.closestIntersection(origen, abajo, om.MSpace.kObject, 1e7, False, None, None, False, acel)
            if golpe and golpe[2] >= 0:
                altura = golpe[0].y
                if mejor is None or altura > mejor:
                    mejor = altura
        return mejor
    return bajar


def _cercano(apoyos):
    def cercano(p, _tangente):
        mejor, distancia = None, float("inf")
        punto = om.MPoint(*p)
        for fn, _acel in apoyos:
            q, n, _cara = fn.getClosestPointAndNormal(punto, om.MSpace.kObject)
            d = q.distanceTo(punto)
            if d < distancia:
                n.normalize()
                mejor, distancia = ((q.x, q.y, q.z), (n.x, n.y, n.z)), d
        return mejor
    return cercano


def _malla_python(fn):
    m = ml.Malla()
    m.vertices = [(p.x, p.y, p.z) for p in fn.getPoints()]
    cuentas, conexiones = fn.getVertices()
    i = 0
    for c in cuentas:
        caras = tuple(conexiones[i:i + c])
        m.caras.append(caras)
        m.caras_uv.append(tuple(m.uv(0.5, 0.5) for _ in caras))
        i += c
    return m


def _malla_maya(malla):
    datos = om.MFnMeshData().create()
    if malla.vacia():
        # una malla vacía válida, para que la forma no dé errores
        om.MFnMesh().create([], [], [], parent=datos)
        return datos
    vertices, cuentas, conexiones, us, vs, cuentas_uv, ids_uv = malla.para_maya()
    fn = om.MFnMesh()
    fn.create([om.MPoint(*p) for p in vertices], cuentas, conexiones, us, vs, parent=datos)
    fn.assignUVs(cuentas_uv, ids_uv)
    aristas = list(range(fn.numEdges))
    fn.setEdgeSmoothings(aristas, [True] * len(aristas))
    fn.cleanupEdgeSmoothing()
    return datos


def _curva_maya(puntos):
    datos = om.MFnNurbsCurveData().create()
    if len(puntos) < 2:
        puntos = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]
    cvs = om.MPointArray([om.MPoint(*p) for p in puntos])
    nudos = om.MDoubleArray([float(i) for i in range(len(puntos))])
    om.MFnNurbsCurve().create(cvs, nudos, 1, om.MFnNurbsCurve.kOpen, False, False, datos)
    return datos


def registrar(plugin):
    plugin.registerNode(NOMBRE, ID, PipeEditorNodo.crear, PipeEditorNodo.iniciar, om.MPxNode.kDependNode)


def desregistrar(plugin):
    plugin.deregisterNode(ID)
