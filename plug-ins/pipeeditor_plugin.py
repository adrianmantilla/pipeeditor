"""Plugin de Maya para PipeEditor.

Aparece en el Plug-in Manager como «pipeeditor_plugin». Registra el nodo
«pipeEditorNodo» (el que calcula cables y tuberías en vivo) y crea el menú
PipeEditor. El instalador lo marca para que se cargue solo.
"""

import maya.api.OpenMaya as om
from maya import cmds


def maya_useNewAPI():
    pass


def initializePlugin(objeto):
    import pipeeditor
    from pipeeditor import nodo
    plugin = om.MFnPlugin(objeto, "PipeEditor", pipeeditor.__version__, "Any")
    nodo.registrar(plugin)
    try:
        from pipeeditor import interfaz_maya
        cmds.evalDeferred(interfaz_maya.iniciar, lowestPriority=True)
    except Exception as error:
        cmds.warning("PipeEditor: no se pudo crear el menú: {}".format(error))
    return plugin


def uninitializePlugin(objeto):
    plugin = om.MFnPlugin(objeto)
    try:
        from pipeeditor import interfaz_maya
        interfaz_maya.detener()
    except Exception:
        pass
    from pipeeditor import nodo
    nodo.desregistrar(plugin)
