"""Une PipeEditor con Maya: menú, panel acoplable, órdenes para atajos y avisos."""

import os

import maya.api.OpenMaya as om
from maya import cmds

import pipeeditor
from pipeeditor import escena
from pipeeditor.estilos import Estilos
from pipeeditor.i18n import t
from pipeeditor.qt import QtWidgets, shiboken, sigue_vivo

CONTROL = "PipeEditorWorkspaceControl"
MENU = "PipeEditorMenu"
COMANDOS = {
    "PipeEditorAbrir": ("cmd_abrir", "mostrar()"),
    "PipeEditorCableClic": ("cmd_cable_clic", "clic('cable')"),
    "PipeEditorTuberiaClic": ("cmd_tuberia_clic", "clic('tuberia')"),
    "PipeEditorCableSeleccion": ("cmd_cable_seleccion", "entre_seleccionados('cable')"),
    "PipeEditorTuberiaSeleccion": ("cmd_tuberia_seleccion", "entre_seleccionados('tuberia')"),
    "PipeEditorHornear": ("cmd_hornear", "hornear()"),
}

_estado = {"ventana": None, "servicio": None, "trabajos": [], "avisos": []}


def carpeta_preferencias():
    return os.path.join(cmds.internalVar(userAppDir=True), "pipeeditor")


class ServicioMaya(object):
    """Lo que la ventana necesita de Maya. Cada método devuelve un texto para el usuario o None."""

    def __init__(self):
        self.estilos = Estilos(carpeta_preferencias())
        self.herramienta = None

    # lectura
    def ultimos(self, tipo):
        return self.estilos.ultimos(tipo)

    def recordar(self, ajustes):
        self.estilos.recordar(ajustes)

    def seleccion(self):
        return escena.nodos_seleccionados()

    def leer(self, n):
        return escena.leer_ajustes(n)

    def informacion(self, nodos):
        total = {"longitud": 0.0, "caida": 0.0, "triangulos": 0, "tensos": 0}
        for n in nodos:
            i = escena.informacion(n)
            total["longitud"] += i["longitud"]
            total["caida"] = max(total["caida"], i["caida"])
            total["triangulos"] += i["triangulos"]
            total["tensos"] += i["tensos"]
        return total

    # cambios
    def escribir(self, nodos, ajustes):
        with escena.Bloque():
            escena.poner_ajustes(nodos, ajustes)

    def material(self, nodos, parte, nombre):
        escena.poner_material(nodos, parte, nombre)

    def fijar_longitudes(self, nodos):
        with escena.Bloque():
            escena.fijar_longitudes(nodos)

    # crear
    def crear_clic(self, obtener_ajustes, pegar):
        self.herramienta = escena.Herramienta(obtener_ajustes, pegar, al_crear=lambda g: refrescar())
        self.herramienta.activar()
        cmds.inViewMessage(amg=t("clic_instrucciones"), pos="topCenter", fade=True, fadeStayTime=4000)
        return t("clic_instrucciones")

    def crear_seleccion(self, ajustes, pegar):
        anclajes = escena.anclajes_de_seleccion(pegar)
        if len(anclajes) < 2:
            raise ValueError(t("falta_seleccion_dos"))
        grupo = escena.crear(anclajes, ajustes)
        cmds.select(grupo)
        return t("creado", nombre=grupo)

    def crear_grupos(self, ajustes, pegar):
        anclajes = escena.anclajes_de_seleccion(True)
        if len(anclajes) < 2:
            raise ValueError(t("falta_grupos"))
        contenedor, creados = escena.crear_entre_grupos(anclajes, ajustes, pegar=pegar)
        cmds.select(contenedor)
        return t("creados_haz", n=len(creados))

    def crear_aristas(self, ajustes):
        aristas = cmds.filterExpand(selectionMask=32) or []
        if not aristas:
            raise ValueError(t("falta_aristas"))
        grupo = escena.crear_desde_aristas(aristas, ajustes)
        cmds.select(grupo)
        return t("creado", nombre=grupo)

    def crear_curva(self, ajustes):
        curvas = [c for c in cmds.ls(selection=True, long=True) or []
                  if cmds.listRelatives(c, shapes=True, type="nurbsCurve") and not escena.nodo_de(c)]
        if not curvas:
            raise ValueError(t("falta_curva"))
        grupos = [escena.crear_desde_curva(c, ajustes) for c in curvas]
        cmds.select(grupos)
        return t("creado", nombre=", ".join(grupos))

    # editar
    def _anclas_seleccionadas(self):
        return [s for s in cmds.ls(selection=True) or [] if escena.es_ancla(s)]

    def insertar_punto(self):
        anclas = self._anclas_seleccionadas()
        if not anclas:
            raise ValueError(t("falta_ancla"))
        nueva = escena.insertar_punto(anclas[0])
        cmds.select(nueva)
        return t("punto_insertado")

    def quitar_puntos(self):
        anclas = self._anclas_seleccionadas()
        if not anclas:
            raise ValueError(t("falta_ancla"))
        n = escena.quitar_puntos(anclas)
        return t("puntos_quitados", n=n)

    def seleccionar_anclas(self):
        anclas = []
        for n in self.seleccion():
            anclas.extend(escena.anclas_de(n))
        if anclas:
            cmds.select(anclas)

    def seleccionar_cuerpos(self):
        cuerpos = [escena.formas_de(n)[0] for n in self.seleccion()]
        cuerpos = [cmds.listRelatives(c, parent=True)[0] for c in cuerpos if c]
        if cuerpos:
            cmds.select(cuerpos)

    def apoyos(self):
        nodos = self.seleccion()
        mallas = [s for s in cmds.ls(selection=True, long=True, type="transform") or []
                  if not escena.nodo_de(s) and cmds.listRelatives(s, shapes=True, type="mesh")]
        if not nodos:
            raise ValueError(t("falta_cable_y_objetos"))
        cuantas = escena.poner_apoyos(nodos, mallas)
        return t("apoyos_puestos", n=cuantas)

    def conector_propio(self):
        nodos = self.seleccion()
        mallas = [s for s in cmds.ls(selection=True, long=True, type="transform") or []
                  if not escena.nodo_de(s) and cmds.listRelatives(s, shapes=True, type="mesh")]
        if not nodos or not mallas:
            raise ValueError(t("falta_cable_y_objeto"))
        escena.poner_conector_propio(nodos, mallas[0])
        return t("conector_puesto")

    def hornear(self):
        nodos = self.seleccion()
        if not nodos:
            raise ValueError(t("falta_cable"))
        hechos = escena.hornear(nodos)
        if hechos:
            cmds.select(hechos)
        return t("horneados", n=len(hechos))

    def borrar(self):
        nodos = self.seleccion()
        if nodos:
            escena.borrar(nodos)

    def mensaje(self, texto):
        if texto and not cmds.about(batch=True):
            cmds.inViewMessage(amg=texto, pos="botCenter", fade=True)


def servicio():
    if _estado["servicio"] is None:
        _estado["servicio"] = ServicioMaya()
    return _estado["servicio"]


def ventana():
    v = _estado["ventana"]
    return v if sigue_vivo(v) else None


def refrescar():
    v = ventana()
    if v is not None:
        try:
            v.refrescar()
        except RuntimeError:
            pass


# --- panel acoplable --------------------------------------------------------------------

def restaurar():
    from maya import OpenMayaUI as omui
    from pipeeditor.ventana import VentanaPipeEditor
    puntero = omui.MQtUtil.getCurrentParent()
    padre = shiboken.wrapInstance(int(puntero), QtWidgets.QWidget)
    v = ventana()
    if v is None:
        v = VentanaPipeEditor(servicio())
        _estado["ventana"] = v
    padre.layout().addWidget(v)


def mostrar():
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, restore=True, visible=True)
        if ventana() is None:
            cmds.deleteUI(CONTROL)
        else:
            refrescar()
            return ventana()
    cmds.workspaceControl(CONTROL, label="PipeEditor", retain=False, floating=True, initialWidth=380,
                          initialHeight=720, minimumWidth=300,
                          uiScript="import pipeeditor.interfaz_maya as m\nm.restaurar()",
                          closeCommand="import pipeeditor.interfaz_maya as m\nm.al_cerrar()")
    return ventana()


def al_cerrar():
    _estado["ventana"] = None


# --- órdenes ----------------------------------------------------------------------------

def _ajustes(tipo):
    v = ventana()
    if v is not None and v.tipo == tipo:
        return v.ajustes_actuales()
    return servicio().ultimos(tipo)


def clic(tipo="cable"):
    s = servicio()
    s.crear_clic(lambda: _ajustes(tipo), lambda: True)


def entre_seleccionados(tipo="cable"):
    try:
        texto = servicio().crear_seleccion(_ajustes(tipo), True)
        servicio().mensaje(texto)
    except ValueError as error:
        cmds.warning(str(error))
    refrescar()


def hornear():
    try:
        servicio().mensaje(servicio().hornear())
    except ValueError as error:
        cmds.warning(str(error))
    refrescar()


def _crear_ordenes():
    for nombre, (clave, llamada) in COMANDOS.items():
        codigo = "import pipeeditor.interfaz_maya as m\nm.{}".format(llamada)
        if cmds.runTimeCommand(nombre, exists=True):
            cmds.runTimeCommand(nombre, edit=True, command=codigo, commandLanguage="python", annotation=t(clave))
        else:
            cmds.runTimeCommand(nombre, command=codigo, commandLanguage="python", annotation=t(clave),
                                category="Custom Scripts.PipeEditor")


def _crear_menu():
    if cmds.menu(MENU, exists=True):
        cmds.deleteUI(MENU)
    cmds.menu(MENU, label="PipeEditor", parent="MayaWindow", tearOff=True)
    cmds.menuItem(label=t("menu_abrir"), command=lambda *_: mostrar())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_cable_clic"), command=lambda *_: clic("cable"))
    cmds.menuItem(label=t("menu_cable_seleccion"), command=lambda *_: entre_seleccionados("cable"))
    cmds.menuItem(label=t("menu_tuberia_clic"), command=lambda *_: clic("tuberia"))
    cmds.menuItem(label=t("menu_tuberia_seleccion"), command=lambda *_: entre_seleccionados("tuberia"))
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_hornear"), command=lambda *_: hornear())
    cmds.menuItem(label=t("menu_hornear_todo"), command=lambda *_: _hornear_todo())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_acerca", version=pipeeditor.__version__), enable=False)


def _hornear_todo():
    nodos = escena.nodos()
    if nodos:
        escena.hornear(nodos)
        servicio().mensaje(t("horneados", n=len(nodos)))
    refrescar()


def _avisar_al_guardar(*_):
    try:
        vivos = escena.cuantos_vivos()
    except Exception:
        return
    if vivos and not cmds.about(batch=True):
        cmds.inViewMessage(amg=t("aviso_guardar", n=vivos), pos="topCenter", fade=True, fadeStayTime=5000)
        om.MGlobal.displayInfo(t("aviso_guardar_texto", n=vivos))


def iniciar():
    try:
        cmds.selectPref(trackSelectionOrder=True)
    except RuntimeError:
        pass
    _crear_ordenes()
    if cmds.about(batch=True):
        return
    _crear_menu()
    _estado["trabajos"] = [cmds.scriptJob(event=["SelectionChanged", refrescar]),
                           cmds.scriptJob(event=["SceneOpened", refrescar])]
    _estado["avisos"] = [om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeSave, _avisar_al_guardar)]


def detener():
    for j in _estado["trabajos"]:
        try:
            cmds.scriptJob(kill=j, force=True)
        except RuntimeError:
            pass
    _estado["trabajos"] = []
    for a in _estado["avisos"]:
        try:
            om.MMessage.removeCallback(a)
        except RuntimeError:
            pass
    _estado["avisos"] = []
    escena.soltar_herramienta()
    if not cmds.about(batch=True):
        if cmds.workspaceControl(CONTROL, exists=True):
            cmds.deleteUI(CONTROL)
        if cmds.menu(MENU, exists=True):
            cmds.deleteUI(MENU)
    _estado["ventana"] = None
