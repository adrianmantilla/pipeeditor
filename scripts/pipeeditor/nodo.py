"""Nodo de Maya «pipeEditorNodo»: calcula el cable o la tubería en vivo.

Entradas: las matrices de los anclajes (localizadores), una curva opcional,
las mallas de apoyo y todos los ajustes. Salidas: la malla del cuerpo, la de
las piezas y la curva central. Al mover un anclaje, Maya lo recalcula solo.
Toda la geometría la hace ``construir`` (Python puro).
"""

import math

import maya.api.OpenMaya as om

from pipeeditor import construir, piezas, perfiles, trazado
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
    "recorrido": trazado.RECORRIDOS,
    "codo": construir.CODOS,
    "extremos": piezas.EXTREMOS_TUBERIA,
    "arriba": construir.EJES,
    "norma": construir.NORMAS,
}
NUMEROS = [
    # atributo, clave, tipo, mínimo, máximo suave
    ("grosor", "grosor", "d", 0.01, 50.0),
    ("lados", "lados", "i", 3, 32),
    ("segmentosMetro", "segmentos_metro", "i", 2, 100),
    ("salida", "salida", "d", 0.0, 50.0),
    ("apoyarSuelo", "apoyar_suelo", "b", None, None),
    ("alturaSuelo", "altura_suelo", "d", None, None),
    ("reposo", "reposo", "b", None, None),
    ("rigidez", "rigidez", "d", 0.0, 1.0),
    ("ondulacion", "ondulacion", "d", 0.0, 1.0),
    ("variacion", "variacion", "d", 0.0, 1.0),
    ("semilla", "semilla", "i", 0, 1000),
    ("holgura", "holgura", "d", 0.0, 1.0),
    ("separacionPiezas", "separacion_piezas", "d", 1.0, 500.0),
    ("haz", "haz", "i", 1, 37),
    ("torsion", "torsion", "d", -10.0, 10.0),
    ("separacionBridasHaz", "separacion_bridas_haz", "d", 0.0, 500.0),
    ("radioCodo", "radio_codo", "d", 0.0, 10.0),
    ("tubos", "tubos", "i", 1, 12),
    ("separacionTubos", "separacion_tubos", "d", 0.0, 200.0),
    ("separacionBridas", "separacion_bridas", "d", 0.0, 1000.0),
    ("pared", "pared", "d", 0.0, 10.0),
    ("separacionSoportes", "separacion_soportes", "d", 0.0, 1000.0),
    ("soportesAuto", "soportes_auto", "b", None, None),
    ("alcanceSoportes", "alcance_soportes", "d", 1.0, 1000.0),
]
CLAVE_DE_ENUM = {
    "tipo": "tipo", "perfilCable": "perfil_cable", "modoTension": "modo_tension",
    "conectorInicio": "conector_inicio", "conectorFin": "conector_fin", "pieza": "pieza",
    "perfilTuberia": "perfil_tuberia", "recorrido": "recorrido", "codo": "codo", "extremos": "extremos",
    "arriba": "arriba", "norma": "norma",
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
        self._cache = {}          # último recorrido calculado (ver construir.construir)
        self._borrador = False    # el último cálculo fue rápido, mientras se arrastraba
        self._vigilando = False

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
        A["deslizan"] = num.create("deslizan", "des", om.MFnNumericData.kBoolean, False)
        num.array = True
        num.usesArrayDataBuilder = True
        A["ruta"] = typ.create("ruta", "rut", om.MFnData.kNurbsCurve)
        A["apoyos"] = typ.create("apoyos", "apo", om.MFnData.kMesh)
        typ.array = True
        typ.usesArrayDataBuilder = True
        typ.disconnectBehavior = om.MFnAttribute.kDelete
        A["conectorPropio"] = typ.create("conectorPropio", "cpr", om.MFnData.kMesh)
        # Se cambia solo para recalcular con el reposo completo al soltar el ratón.
        A["refinar"] = num.create("refinar", "ref", om.MFnNumericData.kInt, 0)
        num.storable = False
        num.keyable = False
        num.hidden = True
        # Versión de los datos con la que se creó el nodo (0 = PipeEditor 1.0): ver construir.migrar.
        A["versionDatos"] = num.create("versionDatos", "vda", om.MFnNumericData.kInt, 0)
        num.keyable = False
        num.channelBox = False

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
        A["metal"] = typ.create("metal", "met", om.MFnData.kMesh)
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

        salidas = ["cuerpo", "piezas", "metal", "curva", "longitudesActuales", "longitudTotal", "caida",
                   "triangulos", "tensos"]
        entradas = [n for n in A if n not in salidas]
        for n in entradas + salidas:
            om.MPxNode.addAttribute(A[n])
        for e in entradas:
            for s in salidas:
                om.MPxNode.attributeAffects(A[e], A[s])

    # --- cálculo ----------------------------------------------------------------------
    def compute(self, plug, datos):
        A = PipeEditorNodo.atributos
        salidas = ("cuerpo", "piezas", "metal", "curva", "longitudesActuales", "longitudTotal", "caida",
                   "triangulos", "tensos")
        if plug.isNull or om.MFnAttribute(plug.attribute()).name not in salidas:
            return None
        try:
            res = self._calcular(datos, _arrastrando())
        except Exception as error:  # nunca tumbar Maya por un cable
            om.MGlobal.displayWarning("PipeEditor: {}".format(error))
            res = construir.Resultado()
        datos.outputValue(A["cuerpo"]).setMObject(_malla_maya(res.cuerpo))
        # Las escenas de antes no tienen la malla de metal: entonces va con las piezas.
        con_metal = om.MPlug(self.thisMObject(), A["metal"]).isSource
        metal = res.piezas.separar(ml.METAL) if con_metal else ml.Malla()
        piezas = res.piezas.separar(0) if con_metal else res.piezas
        datos.outputValue(A["piezas"]).setMObject(_malla_maya(piezas))
        datos.outputValue(A["metal"]).setMObject(_malla_maya(metal))
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

    def _calcular(self, datos, borrador=False):
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
        deslizan = _valores_array(datos.inputArrayValue(A["deslizan"]), lambda h: h.asBool())
        matrices = _valores_array(datos.inputArrayValue(A["anclas"]), lambda h: h.asMatrix())
        anclajes = []
        for indice in sorted(matrices):
            m = matrices[indice]
            pos = (m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2))
            normal = (m.getElement(1, 0), m.getElement(1, 1), m.getElement(1, 2))
            anclajes.append(construir.Anclaje(pos, normal, factores.get(indice, 1.0), longitudes.get(indice, 0.0),
                                              deslizan.get(indice, False)))

        ajustes = construir.migrar(ajustes, datos.inputValue(A["versionDatos"]).asInt())
        # Mientras se arrastra con el ratón, un reposo más corto; al soltar, el completo.
        self._borrador = borrador
        if borrador:
            ajustes["_borrador"] = True
            self._vigilar_al_soltar()
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
        self._cache["firma_apoyos"] = _firma(apoyos, propio)
        eje = 2 if ajustes["arriba"] == "z" else 1
        bajar = _bajar(apoyos, eje) if apoyos else None
        cercano = _cercano(apoyos) if apoyos else None
        empujar = _empujar(apoyos) if apoyos and ajustes["tipo"] == "cable" else None
        obstaculos = _cajas(apoyos) if apoyos and ajustes["tipo"] == "tuberia" else []
        return construir.construir(ajustes, anclajes, ruta=ruta, ruta_lineal=lineal, bajar=bajar,
                                   cercano=cercano, malla_propia=propio, empujar=empujar, obstaculos=obstaculos,
                                   cache=self._cache)

    def _vigilar_al_soltar(self):
        """Cuando se suelta el ratón, vuelve a calcular con el reposo completo."""
        if self._vigilando:
            return
        self._vigilando = True
        import threading
        import maya.utils

        def comprobar():
            if _arrastrando():
                threading.Timer(0.2, lambda: maya.utils.executeDeferred(comprobar)).start()
                return
            self._vigilando = False
            if self._borrador:
                try:
                    plug = om.MPlug(self.thisMObject(), PipeEditorNodo.atributos["refinar"])
                    plug.setInt(plug.asInt() + 1)
                except RuntimeError:  # el nodo ya no existe
                    pass
        threading.Timer(0.2, lambda: maya.utils.executeDeferred(comprobar)).start()


def _arrastrando():
    """¿Hay un botón del ratón pulsado en Maya con interfaz? (moviendo un anclaje, el tiempo...)."""
    if om.MGlobal.mayaState() != om.MGlobal.kInteractive:
        return False
    try:
        from pipeeditor.qt import QtCore, QtWidgets
        app = QtWidgets.QApplication.instance()
        return bool(app) and app.mouseButtons() != QtCore.Qt.NoButton
    except Exception:
        return False


def _firma(apoyos, propio):
    """Lo que identifica la forma y posición de los apoyos y del conector propio (para la caché)."""
    import hashlib
    h = hashlib.sha1()
    for fn, _acel in apoyos:
        try:
            pts = fn.getPoints(om.MSpace.kWorld)
        except RuntimeError:
            pts = fn.getPoints()
        paso = max(1, len(pts) // 2000)  # una muestra basta: mover o deformar el apoyo la cambia
        h.update(repr((len(pts), [(round(pts[i].x, 3), round(pts[i].y, 3), round(pts[i].z, 3))
                                  for i in range(0, len(pts), paso)])).encode())
    if propio is not None:
        h.update(repr(propio.vertices).encode())
    return h.hexdigest()


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


def _bajar(apoyos, eje=1):
    """Altura (en el eje vertical ``eje``) de la primera superficie bajo un punto."""
    abajo = om.MFloatVector(0.0, 0.0, -1.0) if eje == 2 else om.MFloatVector(0.0, -1.0, 0.0)

    def bajar(x, y, z):
        mejor = None
        origen = om.MFloatPoint(x, y, z)
        for fn, acel in apoyos:
            golpe = None
            # worldMesh trae la matriz del objeto: kWorld da posiciones de escena.
            for espacio in (om.MSpace.kWorld, om.MSpace.kObject):
                try:
                    try:
                        golpe = fn.closestIntersection(origen, abajo, espacio, 1e7, False, accelParams=acel)
                    except TypeError:  # versiones que no aceptan el argumento con nombre
                        golpe = fn.closestIntersection(origen, abajo, espacio, 1e7, False)
                    break
                except RuntimeError:
                    golpe = None
            if golpe and golpe[2] >= 0:
                altura = golpe[0].z if eje == 2 else golpe[0].y
                if mejor is None or altura > mejor:
                    mejor = altura
        return mejor
    return bajar


def _cercano(apoyos):
    def cercano(p, _tangente):
        mejor, distancia = None, float("inf")
        punto = om.MPoint(*p)
        for fn, _acel in apoyos:
            try:
                q, n, _cara = fn.getClosestPointAndNormal(punto, om.MSpace.kWorld)
            except RuntimeError:
                q, n, _cara = fn.getClosestPointAndNormal(punto, om.MSpace.kObject)
            d = q.distanceTo(punto)
            if d < distancia:
                n.normalize()
                mejor, distancia = ((q.x, q.y, q.z), (n.x, n.y, n.z)), d
        return mejor
    return cercano


def _cajas(apoyos):
    """Caja (mínimo, máximo) de cada malla de apoyo, en coordenadas de escena."""
    salida = []
    for fn, _acel in apoyos:
        try:
            pts = fn.getPoints(om.MSpace.kWorld)
        except RuntimeError:
            pts = fn.getPoints()
        if len(pts):
            xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
            salida.append(((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))))
    return salida


def _empujar(apoyos):
    """Saca de las mallas de apoyo los puntos del cable (para el reposo)."""
    try:
        import numpy as np
    except ImportError:
        return None
    cajas = []
    for fn, _acel in apoyos:
        try:
            pts = fn.getPoints(om.MSpace.kWorld)
        except RuntimeError:
            pts = fn.getPoints()
        P = np.array([(p.x, p.y, p.z) for p in pts], dtype=float)
        cajas.append((P.min(axis=0), P.max(axis=0)) if len(P) else None)

    def cercano(fn, punto):
        try:
            q, n, _cara = fn.getClosestPointAndNormal(punto, om.MSpace.kWorld)
        except RuntimeError:
            q, n, _cara = fn.getClosestPointAndNormal(punto, om.MSpace.kObject)
        n.normalize()
        return q, n

    def por_donde_entro(fn, acel, antes, punto):
        """Punto y normal de la superficie que cruza el tramo de ``antes`` a ``punto``."""
        d = punto - antes
        largo = d.length()
        if largo < 1e-9:
            return None
        d /= largo
        origen = om.MFloatPoint(antes.x, antes.y, antes.z)
        direccion = om.MFloatVector(d.x, d.y, d.z)
        golpe = None
        for espacio in (om.MSpace.kWorld, om.MSpace.kObject):
            try:
                try:
                    golpe = fn.closestIntersection(origen, direccion, espacio, largo * 1.001, False,
                                                   accelParams=acel)
                except TypeError:
                    golpe = fn.closestIntersection(origen, direccion, espacio, largo * 1.001, False)
                break
            except RuntimeError:
                golpe = None
        if not golpe or golpe[2] < 0:
            return None
        h = om.MPoint(golpe[0].x, golpe[0].y, golpe[0].z)
        _q, n = cercano(fn, h)
        if n * d > 0:  # la normal debe mirar hacia donde venía el punto
            n = -n
        return h, n

    def empujar(P, radio, antes=None):
        Q = np.array(P, dtype=float)
        contacto = np.zeros(len(Q), dtype=bool)
        for (fn, acel), caja in zip(apoyos, cajas):
            if caja is None:
                continue
            lo, hi = caja
            cerca = np.nonzero(np.all((Q > lo - radio) & (Q < hi + radio), axis=1))[0]
            for i in cerca:
                punto = om.MPoint(*Q[i])
                q, n = cercano(fn, punto)
                d = (punto - q) * n
                if d >= radio:
                    continue
                if d < 0 and antes is not None:
                    # Está dentro: sale por donde entró, no por la cara más cercana
                    # (si no, en una mesa fina saldría por debajo).
                    previo = om.MPoint(*antes[i])
                    qa, na = cercano(fn, previo)
                    if (previo - qa) * na >= 0:
                        cruce = por_donde_entro(fn, acel, previo, punto)
                        if cruce is not None:
                            h, nh = cruce
                            Q[i] = np.array((h.x + nh.x * radio, h.y + nh.y * radio, h.z + nh.z * radio))
                            contacto[i] = True
                            continue
                Q[i] += np.array((n.x, n.y, n.z)) * (radio - d)
                contacto[i] = True
        return Q, contacto
    return empujar


def _malla_python(fn):
    """Copia completa de una malla de Maya: vértices, caras, UV y aristas duras."""
    m = ml.Malla()
    m.vertices = [(p.x, p.y, p.z) for p in fn.getPoints()]
    cuentas, conexiones = fn.getVertices()
    try:
        us, vs = fn.getUVs()
        cuentas_uv, ids_uv = fn.getAssignedUVs()
    except RuntimeError:
        us, vs, cuentas_uv, ids_uv = [], [], [], []
    m.uvs = [(u, v) for u, v in zip(us, vs)]
    centro = None
    i = j = 0
    for k, c in enumerate(cuentas):
        caras = tuple(conexiones[i:i + c])
        if k < len(cuentas_uv) and cuentas_uv[k] == c:
            uv = tuple(ids_uv[j:j + c])
            j += c
        else:
            if centro is None:
                centro = m.uv(0.5, 0.5)
            uv = tuple(centro for _ in caras)
        m.caras.append(caras)
        m.caras_uv.append(uv)
        m.etiquetas.append(0)
        i += c
    for e in range(fn.numEdges):
        if not fn.isEdgeSmooth(e):
            m.duras.append(tuple(fn.getEdgeVertices(e)))
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
    total = fn.numEdges
    suaves = [True] * total
    duras = []
    if malla.duras:
        buscadas = set((min(a, b), max(a, b)) for a, b in malla.duras)
        for e in range(total):
            a, b = fn.getEdgeVertices(e)
            if (min(a, b), max(a, b)) in buscadas:
                suaves[e] = False
                duras.append(e)
    fn.setEdgeSmoothings(list(range(total)), suaves)
    fn.cleanupEdgeSmoothing()
    if duras:
        try:  # pliegue: la arista sigue viva al suavizar (tecla 3) o subdividir en Arnold
            fn.setCreaseEdges(duras, [2.0] * len(duras))
        except (RuntimeError, AttributeError, TypeError):
            pass
    return datos


def _curva_maya(puntos):
    """Curva central cúbica que pasa por ``puntos`` (o lineal si son muy pocos)."""
    datos = om.MFnNurbsCurveData().create()
    if len(puntos) < 2:
        puntos = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]
    if len(puntos) >= 4:
        try:
            om.MFnNurbsCurve().createWithEditPoints([om.MPoint(*p) for p in puntos], 3, om.MFnNurbsCurve.kOpen,
                                                   False, False, True, datos)
            return datos
        except (RuntimeError, TypeError):
            pass
    cvs = om.MPointArray([om.MPoint(*p) for p in puntos])
    nudos = om.MDoubleArray([float(i) for i in range(len(puntos))])
    om.MFnNurbsCurve().create(cvs, nudos, 1, om.MFnNurbsCurve.kOpen, False, False, datos)
    return datos


def registrar(plugin):
    plugin.registerNode(NOMBRE, ID, PipeEditorNodo.crear, PipeEditorNodo.iniciar, om.MPxNode.kDependNode)


def desregistrar(plugin):
    plugin.deregisterNode(ID)
