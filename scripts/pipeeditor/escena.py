"""Crear, editar y hornear cables y tuberías en la escena de Maya.

Cada cable o tubería es un grupo con este contenido:

    cable_01                (grupo; moverlo mueve sus anclajes libres)
      cable_01_cuerpo       (malla: la sale del nodo)
      cable_01_piezas       (malla: conectores, bridas, soportes)
      cable_01_metal        (malla: las partes metálicas de las piezas)
      cable_01_curva        (curva central, oculta)
      cable_01_anclas       (localizadores que no están pegados a un objeto)

y un nodo ``pipeEditorNodo`` que lo calcula. Los anclajes pegados a un objeto
cuelgan de ese objeto y le siguen cuando se mueve.
"""

import random

import maya.api.OpenMaya as om
from maya import cmds

from pipeeditor import construir, materiales, nodo, vec

ATRIB_GRUPO = "pipeEditorNodo"
ATRIB_FACTOR = "pipeFactor"
ATRIB_LONGITUD = "pipeLongitud"
ATRIB_DESLIZA = "pipeDesliza"


# --- utilidades -----------------------------------------------------------------------

class Bloque(object):
    """Todo lo de dentro se deshace con un solo Ctrl+Z."""

    def __init__(self, nombre="PipeEditor"):
        self.nombre = nombre

    def __enter__(self):
        cmds.undoInfo(openChunk=True, chunkName=self.nombre)
        return self

    def __exit__(self, *_):
        cmds.undoInfo(closeChunk=True)
        return False


def _nombre_libre(base):
    i = 1
    while cmds.objExists("{}_{:02d}".format(base, i)):
        i += 1
    return "{}_{:02d}".format(base, i)


def _matriz_mundo(objeto):
    return om.MMatrix(cmds.xform(objeto, query=True, matrix=True, worldSpace=True))


def _orientar(objeto, posicion, normal):
    """Coloca ``objeto`` en ``posicion`` (mundo) con su eje Y en ``normal``."""
    m = vec.marco_desde_eje(posicion, normal)
    ex, ey, ez, o = m
    matriz = [ex[0], ex[1], ex[2], 0, ey[0], ey[1], ey[2], 0, ez[0], ez[1], ez[2], 0, o[0], o[1], o[2], 1]
    cmds.xform(objeto, matrix=matriz, worldSpace=True)


# --- buscar ---------------------------------------------------------------------------

def nodos():
    return cmds.ls(type=nodo.NOMBRE) or []


def nodo_de(objeto):
    """El nodo de PipeEditor de un grupo, malla, curva o anclaje; o None."""
    if not objeto or not cmds.objExists(objeto):
        return None
    if cmds.nodeType(objeto) == nodo.NOMBRE:
        return objeto
    candidatos = [objeto] + (cmds.listRelatives(objeto, shapes=True, fullPath=True) or [])
    for c in candidatos:
        for n in cmds.listConnections(c, source=True, destination=True, type=nodo.NOMBRE) or []:
            return n
    # subiendo por los padres (por ejemplo, el grupo de anclas)
    padre = cmds.listRelatives(objeto, parent=True, fullPath=True)
    if padre:
        return nodo_de(padre[0])
    return None


def nodos_seleccionados():
    salida = []
    for s in cmds.ls(selection=True, long=True, objectsOnly=True) or []:
        n = nodo_de(s)
        if n and n not in salida:
            salida.append(n)
    return salida


def grupo_de(n):
    for g in cmds.listConnections(n + ".message", destination=True, source=False) or []:
        if cmds.attributeQuery(ATRIB_GRUPO, node=g, exists=True):
            return g
    return None


def anclas_de(n):
    """Localizadores del nodo, en orden."""
    salida = []
    for i in sorted(cmds.getAttr(n + ".anclas", multiIndices=True) or []):
        fuente = cmds.listConnections("{}.anclas[{}]".format(n, i), source=True, destination=False) or []
        if fuente:
            salida.append(fuente[0])
    return salida


def es_ancla(objeto):
    return cmds.objExists(objeto) and cmds.attributeQuery(ATRIB_FACTOR, node=objeto, exists=True)


def formas_de(n):
    """(forma del cuerpo, forma de las piezas, forma de la curva)."""
    def destino(atributo):
        d = cmds.listConnections(n + "." + atributo, destination=True, source=False, shapes=True) or []
        return d[0] if d else None
    return destino("cuerpo"), destino("piezas"), destino("curva")


def forma_de(n, parte):
    """Forma de malla de ``parte`` (cuerpo, piezas o metal), o None."""
    d = cmds.listConnections(n + "." + parte, destination=True, source=False, shapes=True) or []
    return d[0] if d else None


# --- crear ----------------------------------------------------------------------------

def _crear_ancla(nombre, posicion, normal, padre, tamano):
    loc = cmds.spaceLocator(name=nombre)[0]
    if padre:
        loc = cmds.parent(loc, padre)[0]
    _orientar(loc, posicion, normal)
    forma = cmds.listRelatives(loc, shapes=True)[0]
    for eje in "XYZ":
        cmds.setAttr("{}.localScale{}".format(forma, eje), tamano)
    cmds.setAttr(forma + ".overrideEnabled", 1)
    cmds.setAttr(forma + ".overrideColor", 17)  # amarillo
    cmds.addAttr(loc, longName=ATRIB_FACTOR, niceName="Holgura de este tramo", attributeType="double",
                 defaultValue=1.0, minValue=0.0, softMaxValue=4.0, keyable=True)
    cmds.addAttr(loc, longName=ATRIB_LONGITUD, niceName="Longitud fija del tramo", attributeType="double",
                 defaultValue=0.0, minValue=0.0, keyable=False)
    _anadir_desliza(loc)
    return loc


def _anadir_desliza(loc):
    if not cmds.attributeQuery(ATRIB_DESLIZA, node=loc, exists=True):
        cmds.addAttr(loc, longName=ATRIB_DESLIZA, niceName="Pasa sin atarse (gancho)", attributeType="bool",
                     defaultValue=False, keyable=True)


def _reconectar(n, anclas):
    """Conecta ``anclas`` (en orden) a las entradas del nodo, quitando lo anterior."""
    for atributo in ("anclas", "factores", "longitudes", "deslizan"):
        for i in cmds.getAttr("{}.{}".format(n, atributo), multiIndices=True) or []:
            plug = "{}.{}[{}]".format(n, atributo, i)
            for f in cmds.listConnections(plug, source=True, destination=False, plugs=True) or []:
                cmds.disconnectAttr(f, plug)
            cmds.removeMultiInstance(plug, b=True)
    for i, a in enumerate(anclas):
        cmds.connectAttr(a + ".worldMatrix[0]", "{}.anclas[{}]".format(n, i), force=True)
        cmds.connectAttr(a + "." + ATRIB_FACTOR, "{}.factores[{}]".format(n, i), force=True)
        cmds.connectAttr(a + "." + ATRIB_LONGITUD, "{}.longitudes[{}]".format(n, i), force=True)
        _anadir_desliza(a)
        cmds.connectAttr(a + "." + ATRIB_DESLIZA, "{}.deslizan[{}]".format(n, i), force=True)


def _crear_estructura(base, ajustes):
    """Grupo, nodo, mallas y curva vacíos; devuelve (grupo, nodo)."""
    nombre = _nombre_libre(base)
    grupo = cmds.group(empty=True, name=nombre)
    cmds.addAttr(grupo, longName=ATRIB_GRUPO, attributeType="message")
    n = cmds.createNode(nodo.NOMBRE, name=nombre + "_nodo")
    cmds.connectAttr(n + ".message", grupo + "." + ATRIB_GRUPO)
    poner_ajustes([n], ajustes)
    tipo = ajustes.get("tipo", "cable")
    for parte in materiales.PARTES:
        t = cmds.createNode("transform", name="{}_{}".format(nombre, parte), parent=grupo)
        forma = cmds.createNode("mesh", name="{}_{}Shape".format(nombre, parte), parent=t)
        cmds.connectAttr("{}.{}".format(n, parte), forma + ".inMesh")
        cmds.setAttr(t + ".inheritsTransform", 0)
        for a in ("translate", "rotate", "scale"):
            cmds.setAttr("{}.{}".format(t, a), lock=True)
        defecto = materiales.POR_TIPO.get(tipo, materiales.POR_TIPO["cable"])[materiales.PARTES.index(parte)]
        materiales.asignar([forma], ajustes.get("material_" + parte) or defecto)
    t = cmds.createNode("transform", name=nombre + "_curva", parent=grupo)
    curva = cmds.createNode("nurbsCurve", name=nombre + "_curvaShape", parent=t)
    cmds.connectAttr(n + ".curva", curva + ".create")
    cmds.setAttr(t + ".inheritsTransform", 0)
    cmds.setAttr(t + ".visibility", 0)
    cmds.group(empty=True, name=nombre + "_anclas", parent=grupo)
    return grupo, n


def _tamano_ancla(ajustes):
    return max(1.0, ajustes.get("grosor", 2.0) * 1.5)


def _con_eje(ajustes):
    """Ajustes completos; si no dicen el eje vertical, el de la escena."""
    completos = dict(construir.POR_DEFECTO, **ajustes)
    if "arriba" not in ajustes:
        try:
            completos["arriba"] = "z" if cmds.upAxis(query=True, axis=True).lower() == "z" else "y"
        except (RuntimeError, AttributeError):
            pass
    return completos


def alternar_gancho(anclas):
    """Los puntos intermedios elegidos pasan a ser ganchos (el cable desliza) o vuelven a atarse."""
    anclas = [a for a in anclas if es_ancla(a)]
    if not anclas:
        return None
    _anadir_desliza(anclas[0])
    nuevo = not cmds.getAttr(anclas[0] + "." + ATRIB_DESLIZA)
    with Bloque():
        for a in anclas:
            _anadir_desliza(a)
            cmds.setAttr(a + "." + ATRIB_DESLIZA, nuevo)
    return nuevo


def crear(anclajes, ajustes, base=None):
    """Crea un cable o una tubería entre ``anclajes``.

    ``anclajes``: lista de (posición, normal, objeto al que pegarse o None).
    Devuelve el grupo creado.
    """
    ajustes = _con_eje(ajustes)
    tipo = ajustes["tipo"]
    with Bloque():
        grupo, n = _crear_estructura(base or tipo, ajustes)
        anclas = []
        for i, (pos, normal, padre) in enumerate(anclajes):
            padre = padre if padre and cmds.objExists(padre) else grupo + "|" + grupo.split("|")[-1] + "_anclas"
            anclas.append(_crear_ancla("{}_ancla_{}".format(grupo.split("|")[-1], i + 1), pos, normal, padre,
                                       _tamano_ancla(ajustes)))
        _reconectar(n, anclas)
        if tipo == "cable" and ajustes["modo_tension"] == "longitud":
            fijar_longitudes([n])
    return grupo


def crear_desde_curva(curva, ajustes, base=None):
    """Cable o tubería que sigue la curva ``curva`` (transform o forma)."""
    ajustes = _con_eje(ajustes)
    formas = cmds.listRelatives(curva, shapes=True, type="nurbsCurve", fullPath=True) or (
        [curva] if cmds.nodeType(curva) == "nurbsCurve" else [])
    if not formas:
        raise ValueError("no es una curva")
    with Bloque():
        grupo, n = _crear_estructura(base or ajustes["tipo"], ajustes)
        cmds.connectAttr(formas[0] + ".worldSpace[0]", n + ".ruta", force=True)
    return grupo


def crear_desde_aristas(aristas, ajustes, base=None):
    """Convierte las aristas en una curva (que sigue viva) y crea el cable o la tubería encima."""
    with Bloque():
        cmds.select(aristas, replace=True)
        curva = cmds.polyToCurve(form=2, degree=1, conformToSmoothMeshPreview=False)[0]
        grupo = crear_desde_curva(curva, ajustes, base)
        curva = cmds.parent(curva, grupo)[0]
        cmds.setAttr(curva + ".visibility", 0)
    return grupo


# --- anclajes a partir de la selección -----------------------------------------------

def _transform_de_forma(forma):
    return cmds.listRelatives(forma, parent=True, fullPath=True)[0]


def _puntos_de_componente(componente):
    """Lista de (posición, normal, transform) de un vértice o cara seleccionados."""
    salida = []
    lista = om.MSelectionList()
    lista.add(componente)
    camino, comp = lista.getComponent(0)
    if camino.node().hasFn(om.MFn.kTransform):
        camino.extendToShape()
    fn = om.MFnMesh(camino)
    transform = _transform_de_forma(camino.fullPathName())
    if comp.hasFn(om.MFn.kMeshVertComponent):
        for i in om.MFnSingleIndexedComponent(comp).getElements():
            p = fn.getPoint(i, om.MSpace.kWorld)
            nrm = fn.getVertexNormal(i, True, om.MSpace.kWorld)
            salida.append(((p.x, p.y, p.z), (nrm.x, nrm.y, nrm.z), transform))
    elif comp.hasFn(om.MFn.kMeshPolygonComponent):
        it = om.MItMeshPolygon(camino, comp)
        while not it.isDone():
            p = it.center(om.MSpace.kWorld)
            nrm = it.getNormal(om.MSpace.kWorld)
            salida.append(((p.x, p.y, p.z), (nrm.x, nrm.y, nrm.z), transform))
            it.next()
    return salida


def anclajes_de_seleccion(pegar=True):
    """(posición, normal, padre) de lo seleccionado, en el orden de selección."""
    salida = []
    for s in cmds.ls(orderedSelection=True, flatten=True, long=True) or []:
        if "." in s:
            if ".vtx[" in s or ".f[" in s:
                salida.extend(_puntos_de_componente(s))
            continue
        if not cmds.objectType(s, isAType="transform"):
            continue
        if es_ancla(s):
            m = _matriz_mundo(s)
            salida.append(((m.getElement(3, 0), m.getElement(3, 1), m.getElement(3, 2)),
                           (m.getElement(1, 0), m.getElement(1, 1), m.getElement(1, 2)), None))
            continue
        pos = cmds.xform(s, query=True, rotatePivot=True, worldSpace=True)
        salida.append((tuple(pos), None, s))
    # Los objetos sin normal: el cable sale en horizontal hacia el anclaje vecino.
    for i, (pos, normal, padre) in enumerate(salida):
        if normal is None:
            vecino = salida[i + 1][0] if i + 1 < len(salida) else (salida[i - 1][0] if i > 0 else None)
            d = vec.resta(vecino, pos) if vecino else (1.0, 0.0, 0.0)
            d = (d[0], 0.0, d[2]) if abs(d[0]) + abs(d[2]) > 1e-6 else (1.0, 0.0, 0.0)
            salida[i] = (pos, vec.unitario(d), padre)
    if not pegar:
        salida = [(p, n, None) for p, n, _ in salida]
    return salida


def _por_objeto(anclajes):
    grupos = {}
    orden = []
    for a in anclajes:
        clave = a[2] or ""
        if clave not in grupos:
            grupos[clave] = []
            orden.append(clave)
        grupos[clave].append(a)
    return [grupos[k] for k in orden]


def crear_entre_grupos(anclajes, ajustes, variacion=0.25, semilla=1, pegar=True):
    """Muchos cables entre dos grupos de puntos (de dos objetos distintos).

    Los puntos de cada grupo se ordenan a lo ancho para que los cables no se
    crucen, y cada cable recibe una holgura y un grosor algo distintos.
    """
    grupos = _por_objeto(anclajes)
    if len(grupos) != 2:
        mitad = len(anclajes) // 2
        grupos = [anclajes[:mitad], anclajes[mitad:]]
    a, b = grupos
    if not a or not b:
        raise ValueError("hacen falta dos grupos")
    centro_a = vec.escala([sum(c) for c in zip(*[x[0] for x in a])], 1.0 / len(a))
    centro_b = vec.escala([sum(c) for c in zip(*[x[0] for x in b])], 1.0 / len(b))
    eje = vec.unitario(vec.resta(centro_b, centro_a))
    ancho = vec.unitario(vec.cruz(eje, (0.0, 1.0, 0.0)), (1.0, 0.0, 0.0))
    a = sorted(a, key=lambda x: vec.punto(x[0], ancho))
    b = sorted(b, key=lambda x: vec.punto(x[0], ancho))
    n = min(len(a), len(b))
    if len(a) != len(b):  # se reparten los del grupo grande
        a = [a[int(i * len(a) / float(n))] for i in range(n)]
        b = [b[int(i * len(b) / float(n))] for i in range(n)]
    if not pegar:
        a = [(p, nn, None) for p, nn, _ in a]
        b = [(p, nn, None) for p, nn, _ in b]
    azar = random.Random(semilla)
    grupos_creados = []
    with Bloque():
        contenedor = cmds.group(empty=True, name=_nombre_libre("haz"))
        for i in range(n):
            propio = dict(ajustes)
            propio["holgura"] = max(0.0, ajustes.get("holgura", 0.12) * (1 + azar.uniform(-variacion, variacion) * 2))
            propio["grosor"] = max(0.05, ajustes.get("grosor", 2.0) * (1 + azar.uniform(-variacion, variacion) * 0.5))
            g = crear([a[i], b[i]], propio)
            grupos_creados.append(cmds.parent(g, contenedor)[0])
    return contenedor, grupos_creados


# --- editar ---------------------------------------------------------------------------

def poner_ajustes(nodos_, ajustes):
    """Escribe los ajustes (claves de construir.POR_DEFECTO) en los nodos."""
    for n in nodos_:
        for atributo in nodo.AJUSTES:
            k = nodo.clave(atributo)
            if k not in ajustes:
                continue
            v = ajustes[k]
            plug = "{}.{}".format(n, atributo)
            if atributo in nodo.ENUMS:
                opciones = nodo.ENUMS[atributo]
                v = opciones.index(v) if v in opciones else 0
            if cmds.getAttr(plug, lock=True) or cmds.listConnections(plug, source=True, destination=False):
                continue
            cmds.setAttr(plug, v)


def leer_ajustes(n):
    salida = {}
    for atributo in nodo.AJUSTES:
        v = cmds.getAttr("{}.{}".format(n, atributo))
        if atributo in nodo.ENUMS:
            opciones = nodo.ENUMS[atributo]
            v = opciones[max(0, min(len(opciones) - 1, int(v)))]
        salida[nodo.clave(atributo)] = v
    for parte in materiales.PARTES:
        forma = forma_de(n, parte)
        if forma:
            salida["material_" + parte] = materiales.de(forma)
    return salida


def informacion(n):
    return {
        "longitud": cmds.getAttr(n + ".longitudTotal"),
        "caida": cmds.getAttr(n + ".caida"),
        "triangulos": cmds.getAttr(n + ".triangulos"),
        "tensos": cmds.getAttr(n + ".tensos"),
        "tipo": leer_ajustes(n)["tipo"],
    }


def poner_material(nodos_, parte, nombre):
    formas = [forma_de(n, parte) for n in nodos_]
    with Bloque():
        materiales.asignar(formas, nombre)


def fijar_longitudes(nodos_):
    """Pasa a «longitud fija» guardando en cada tramo su longitud actual."""
    for n in nodos_:
        actuales = cmds.getAttr(n + ".longitudesActuales") or []
        for i, a in enumerate(anclas_de(n)[:-1]):
            if i < len(actuales):
                cmds.setAttr(a + "." + ATRIB_LONGITUD, actuales[i])
        cmds.setAttr(n + ".modoTension", construir.MODOS_TENSION.index("longitud"))


def poner_apoyos(nodos_, mallas):
    """Los cables y tuberías se apoyan en (y se sujetan a) estas mallas."""
    formas = []
    for m in mallas:
        formas.extend(cmds.listRelatives(m, shapes=True, type="mesh", fullPath=True, noIntermediate=True) or [])
    with Bloque():
        for n in nodos_:
            for i in cmds.getAttr(n + ".apoyos", multiIndices=True) or []:
                plug = "{}.apoyos[{}]".format(n, i)
                for f in cmds.listConnections(plug, source=True, destination=False, plugs=True) or []:
                    cmds.disconnectAttr(f, plug)
                cmds.removeMultiInstance(plug, b=True)
            for i, f in enumerate(formas):
                cmds.connectAttr(f + ".worldMesh[0]", "{}.apoyos[{}]".format(n, i), force=True)
    return len(formas)


def poner_conector_propio(nodos_, objeto, extremo="ambos"):
    formas = cmds.listRelatives(objeto, shapes=True, type="mesh", fullPath=True, noIntermediate=True) or []
    if not formas:
        raise ValueError("no es una malla")
    with Bloque():
        for n in nodos_:
            cmds.connectAttr(formas[0] + ".outMesh", n + ".conectorPropio", force=True)
            indice = list(nodo.ENUMS["conectorInicio"]).index("propio")
            if extremo in ("ambos", "inicio"):
                cmds.setAttr(n + ".conectorInicio", indice)
            if extremo in ("ambos", "fin"):
                cmds.setAttr(n + ".conectorFin", indice)


def insertar_punto(ancla):
    """Añade un anclaje a mitad del tramo que empieza en ``ancla``."""
    n = nodo_de(ancla)
    anclas = anclas_de(n)
    if ancla not in anclas and cmds.ls(ancla, long=True):
        largo = cmds.ls(ancla, long=True)[0]
        anclas_largo = [cmds.ls(a, long=True)[0] for a in anclas]
        if largo in anclas_largo:
            ancla = anclas[anclas_largo.index(largo)]
    i = anclas.index(ancla)
    if i >= len(anclas) - 1:
        i -= 1
    pp = tuple(cmds.xform(anclas[i], query=True, translation=True, worldSpace=True))
    qq = tuple(cmds.xform(anclas[i + 1], query=True, translation=True, worldSpace=True))
    curva = formas_de(n)[2]
    medio = vec.mezcla(pp, qq, 0.5)
    if curva:
        fn = om.MFnNurbsCurve(om.MSelectionList().add(curva).getDagPath(0))
        # punto de la curva a mitad de camino entre los dos anclajes
        t0 = fn.closestPoint(om.MPoint(*pp))[1]
        t1 = fn.closestPoint(om.MPoint(*qq))[1]
        punto = fn.getPointAtParam((t0 + t1) / 2.0, om.MSpace.kWorld)
        medio = (punto.x, punto.y, punto.z)
    grupo = grupo_de(n)
    with Bloque():
        nueva = _crear_ancla("{}_ancla_{}".format(grupo.split("|")[-1], len(anclas) + 1), medio, (0, 1, 0),
                             grupo + "|" + grupo.split("|")[-1] + "_anclas",
                             cmds.getAttr(cmds.listRelatives(ancla, shapes=True)[0] + ".localScaleX"))
        anclas.insert(i + 1, nueva)
        _reconectar(n, anclas)
    return nueva


def quitar_puntos(anclas_quitar):
    """Quita anclajes intermedios; cada cable conserva al menos dos."""
    quitadas = 0
    with Bloque():
        por_nodo = {}
        for a in anclas_quitar:
            n = nodo_de(a)
            if n:
                por_nodo.setdefault(n, []).append(cmds.ls(a, long=True)[0])
        for n, quitar in por_nodo.items():
            anclas = anclas_de(n)
            quedan = [a for a in anclas if cmds.ls(a, long=True)[0] not in quitar]
            if len(quedan) < 2:
                continue
            _reconectar(n, quedan)
            for a in anclas:
                if a not in quedan:
                    cmds.delete(a)
                    quitadas += 1
    return quitadas


def hornear(nodos_):
    """Convierte en mallas normales de Maya: quita el nodo y los anclajes."""
    hechos = []
    with Bloque("Hornear"):
        for n in nodos_:
            grupo = grupo_de(n)
            cuerpo, piezas, curva = formas_de(n)
            metal = forma_de(n, "metal")
            anclas = anclas_de(n)
            ruta = cmds.listConnections(n + ".ruta", source=True, destination=False) or []
            for forma in (cuerpo, piezas, metal, curva):
                if forma:
                    cmds.delete(forma, constructionHistory=True)
            if cmds.objExists(n):
                cmds.delete(n)
            for a in anclas:
                if cmds.objExists(a):
                    cmds.delete(a)
            for forma in (piezas, metal):
                if forma and cmds.objExists(forma) and not cmds.polyEvaluate(forma, face=True):
                    cmds.delete(_transform_de_forma(forma))
            for r in ruta:  # la curva de unas aristas se queda como curva normal
                if cmds.objExists(r):
                    cmds.delete(r, constructionHistory=True)
            if grupo and cmds.objExists(grupo):
                if cmds.attributeQuery(ATRIB_GRUPO, node=grupo, exists=True):
                    cmds.deleteAttr(grupo + "." + ATRIB_GRUPO)
                for sub in cmds.listRelatives(grupo, children=True, fullPath=True) or []:
                    if sub.endswith("_anclas") and not cmds.listRelatives(sub, children=True):
                        cmds.delete(sub)
                hechos.append(grupo)
    return hechos


def borrar(nodos_):
    with Bloque("Borrar"):
        for n in nodos_:
            grupo = grupo_de(n)
            anclas = anclas_de(n)
            for a in anclas:
                if cmds.objExists(a):
                    cmds.delete(a)
            if grupo and cmds.objExists(grupo):
                cmds.delete(grupo)
            if cmds.objExists(n):
                cmds.delete(n)


# --- clic sobre superficies -----------------------------------------------------------

def _es_de_pipeeditor(camino):
    nodo_dag = om.MDagPath(camino)
    while nodo_dag.length() > 0:
        fn = om.MFnDependencyNode(nodo_dag.node())
        if fn.hasAttribute(ATRIB_GRUPO):
            return True
        nodo_dag.pop()
    return False


def punto_en_superficie(origen, direccion):
    """(posición, normal, transform) donde el rayo toca una malla visible, o el suelo (Y = 0)."""
    mejor, distancia = None, float("inf")
    rayo_o = om.MFloatPoint(*origen)
    rayo_d = om.MFloatVector(*direccion)
    it = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kMesh)
    while not it.isDone():
        camino = it.getPath()
        it.next()
        if not camino.isVisible() or om.MFnDagNode(camino).isIntermediateObject:
            continue
        if _es_de_pipeeditor(camino):
            continue
        fn = om.MFnMesh(camino)
        corte = fn.closestIntersection(rayo_o, rayo_d, om.MSpace.kWorld, 1e7, False)
        if corte and corte[2] >= 0 and 0 < corte[1] < distancia:
            p = corte[0]
            normal = fn.getPolygonNormal(corte[2], om.MSpace.kWorld)
            if vec.punto((normal.x, normal.y, normal.z), direccion) > 0:
                normal = -normal
            transform = om.MDagPath(camino)
            transform.pop()
            mejor = ((p.x, p.y, p.z), (normal.x, normal.y, normal.z), transform.fullPathName())
            distancia = corte[1]
    if mejor is None and direccion[1] < -1e-6:
        t = -origen[1] / direccion[1]
        mejor = ((origen[0] + direccion[0] * t, 0.0, origen[2] + direccion[2] * t), (0.0, 1.0, 0.0), None)
    return mejor


def rayo_del_visor(x, y):
    """((origen), (dirección)) en mundo del píxel (x, y) del visor activo (API 1, como Árboles)."""
    import maya.OpenMaya as om1
    import maya.OpenMayaUI as omui1
    origen, direccion = om1.MPoint(), om1.MVector()
    omui1.M3dView.active3dView().viewToWorld(int(x), int(y), origen, direccion)
    return (origen.x, origen.y, origen.z), (direccion.x, direccion.y, direccion.z)


CONTEXTO = "pipeEditorClic"


class Herramienta(object):
    """Cada clic añade un anclaje al cable en curso. Ctrl+clic empieza otro; Q termina."""

    def __init__(self, obtener_ajustes, pegar=lambda: True, al_crear=None):
        self.obtener_ajustes = obtener_ajustes
        self.pegar = pegar
        self.al_crear = al_crear
        self.pendiente = None
        self.grupo = None

    def activar(self):
        if cmds.draggerContext(CONTEXTO, exists=True):
            cmds.deleteUI(CONTEXTO)
        cmds.draggerContext(CONTEXTO, pressCommand=self._pulsar, space="screen", cursor="crossHair",
                            name=CONTEXTO, undoMode="step")
        cmds.setToolTo(CONTEXTO)

    def _pulsar(self):
        x, y, _ = cmds.draggerContext(CONTEXTO, query=True, anchorPoint=True)
        modificador = cmds.draggerContext(CONTEXTO, query=True, modifier=True)
        golpe = punto_en_superficie(*rayo_del_visor(x, y))
        if golpe is None:
            return
        pos, normal, padre = golpe
        if not self.pegar():
            padre = None
        if modificador == "ctrl":
            self.pendiente, self.grupo = None, None
        n = nodo_de(self.grupo) if self.grupo and cmds.objExists(self.grupo) else None
        if n is None:
            self.grupo = None
        if self.grupo is None and self.pendiente is None:
            self.pendiente = (pos, normal, padre)
            cmds.inViewMessage(amg=_texto("clic_falta_uno"), pos="topCenter", fade=True)
            return
        if self.grupo is None:
            self.grupo = crear([self.pendiente, (pos, normal, padre)], self.obtener_ajustes())
            self.pendiente = None
            if self.al_crear:
                self.al_crear(self.grupo)
            return
        with Bloque():
            anclas = anclas_de(n)
            grupo = grupo_de(n)
            nueva = _crear_ancla("{}_ancla_{}".format(grupo.split("|")[-1], len(anclas) + 1), pos, normal,
                                 padre or grupo + "|" + grupo.split("|")[-1] + "_anclas",
                                 cmds.getAttr(cmds.listRelatives(anclas[-1], shapes=True)[0] + ".localScaleX"))
            _reconectar(n, anclas + [nueva])


def soltar_herramienta():
    if not cmds.about(batch=True) and cmds.currentCtx() == CONTEXTO:
        cmds.setToolTo("selectSuperContext")


def _texto(clave):
    from pipeeditor.i18n import t
    return t(clave)


# --- aviso al guardar -----------------------------------------------------------------

def cuantos_vivos():
    return len(nodos())
