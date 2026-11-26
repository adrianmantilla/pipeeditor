"""Materiales listos para Arnold: OpenPBR en Maya 2026 y 2027, standardSurface si no hay.

Cada material se crea una sola vez por escena (``pipeEditor_<nombre>``) y se
comparte entre todos los cables y tuberías que lo usan.
"""

from maya import cmds

from pipeeditor import materiales_datos as datos

PREFIJO = "pipeEditor_"

MATERIALES = datos.MATERIALES
POR_TIPO = datos.POR_TIPO
CABLE = datos.CABLE
TUBERIA = datos.TUBERIA
PIEZAS = datos.PIEZAS
METAL = datos.METAL
EMISION = datos.EMISION
PARTES = datos.PARTES


def _tipo():
    try:
        return "openPBRSurface" if "openPBRSurface" in (cmds.allNodeTypes() or []) else "standardSurface"
    except (RuntimeError, AttributeError):
        return "standardSurface"


def _poner(material, tipo, base, metal, rugosidad, capa):
    if tipo == "openPBRSurface":
        nombres = {"color": "baseColor", "metal": "baseMetalness", "rug": "specularRoughness",
                   "capa": "coatWeight"}
    else:
        nombres = {"color": "baseColor", "metal": "metalness", "rug": "specularRoughness", "capa": "coat"}
    cmds.setAttr(material + "." + nombres["color"], *base, type="double3")
    cmds.setAttr(material + "." + nombres["metal"], metal)
    cmds.setAttr(material + "." + nombres["rug"], rugosidad)
    cmds.setAttr(material + "." + nombres["capa"], capa)


def _emision(material, tipo, color, intensidad):
    """El material da luz (bombillas): en Arnold ilumina la escena."""
    if tipo == "openPBRSurface":
        cmds.setAttr(material + ".emissionColor", *color, type="double3")
        cmds.setAttr(material + ".emissionLuminance", 1000.0 * intensidad)
    else:
        cmds.setAttr(material + ".emissionColor", *color, type="double3")
        cmds.setAttr(material + ".emission", 4.0 * intensidad)


def grupo(nombre):
    """Grupo de sombreado del material ``nombre``; lo crea si no existe."""
    if nombre not in MATERIALES:
        nombre = "goma_negra"
    material = PREFIJO + nombre
    sg = material + "SG"
    if cmds.objExists(sg) and cmds.objExists(material):
        return sg
    tipo = _tipo()
    if not cmds.objExists(material):
        material = cmds.shadingNode(tipo, asShader=True, name=material)
        _poner(material, tipo, *MATERIALES[nombre])
        if nombre in datos.EMISION:
            _emision(material, tipo, *datos.EMISION[nombre])
    if not cmds.objExists(sg):
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg)
    if not cmds.isConnected(material + ".outColor", sg + ".surfaceShader"):
        cmds.connectAttr(material + ".outColor", sg + ".surfaceShader", force=True)
    return sg


def asignar(formas, nombre):
    formas = [f for f in formas if f and cmds.objExists(f)]
    if formas:
        cmds.sets(formas, edit=True, forceElement=grupo(nombre))


def de(forma):
    """Nombre del material de PipeEditor asignado a ``forma``, o None."""
    for sg in cmds.listConnections(forma, type="shadingEngine") or []:
        for m in cmds.listConnections(sg + ".surfaceShader") or []:
            if m.startswith(PREFIJO):
                return m[len(PREFIJO):]
    return None
