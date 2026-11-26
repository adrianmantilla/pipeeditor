"""Une PipeEditor con Maya: menú, panel acoplable, órdenes para atajos y avisos."""

import os

import maya.api.OpenMaya as om
from maya import cmds

import pipeeditor
from pipeeditor import escena
from pipeeditor.estilos import Estilos
from pipeeditor import i18n
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
    "PipeEditorCopiaHorneada": ("cmd_copia_horneada", "copia_horneada()"),
    "PipeEditorListaMateriales": ("cmd_lista_materiales", "lista_materiales()"),
    "PipeEditorExportar": ("cmd_exportar", "exportar()"),
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

    def reposo_disponible(self):
        from pipeeditor import reposo
        return reposo.disponible()

    def informacion(self, nodos):
        total = {"longitud": 0.0, "caida": 0.0, "triangulos": 0, "tensos": 0, "fijados": 0}
        for n in nodos:
            i = escena.informacion(n)
            total["fijados"] += 1 if escena.esta_fijado(n) else 0
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

    def alternar_gancho(self):
        anclas = self._anclas_seleccionadas()
        if not anclas:
            raise ValueError(t("falta_ancla"))
        return t("gancho_si" if escena.alternar_gancho(anclas) else "gancho_no")

    def poner_accesorio(self, tipo):
        anclas = self._anclas_seleccionadas()
        if not anclas:
            raise ValueError(t("falta_ancla_tuberia"))
        n = escena.poner_accesorio(anclas, tipo)
        if not n:
            raise ValueError(t("falta_ancla_tuberia"))
        return t("accesorio_puesto", n=n, accesorio=t("opcion_accesorio_" + tipo))

    def derivar(self):
        anclas = self._anclas_seleccionadas()
        if not anclas:
            raise ValueError(t("falta_derivar"))
        ancla = anclas[0]
        resto = [s for s in cmds.ls(orderedSelection=True, long=True) or []
                 if cmds.ls(s, long=True) != cmds.ls(ancla, long=True)]
        if not resto:
            raise ValueError(t("falta_derivar"))
        cmds.select(resto)
        destinos = escena.anclajes_de_seleccion(pegar=True)
        if not destinos:
            raise ValueError(t("falta_derivar"))
        objeto = "." not in resto[-1] and not escena.es_ancla(resto[-1])
        grupo = escena.derivar(ancla, destinos[-1], mirar_a_la_te=objeto)
        cmds.select(grupo)
        return t("derivada", nombre=grupo.split("|")[-1])

    def alternar_curva_arnold(self):
        nodos = self.seleccion()
        hecho = escena.alternar_curva_arnold(nodos) if nodos else None
        if hecho is None:
            raise ValueError(t("falta_arnold"))
        return t("curva_si" if hecho else "curva_no")

    def alternar_fijado(self):
        nodos = self.seleccion()
        hecho = escena.alternar_fijado(nodos) if nodos else None
        if hecho is None:
            raise ValueError(t("falta_cable_vivo"))
        return t("fijado_si" if hecho else "fijado_no")

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
        nodos, mallas = escena.reparto_apoyos(cmds.ls(orderedSelection=True, long=True) or [])
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


def copia_horneada(ruta=None):
    """Guarda una copia de la escena con todo horneado (para render en otro ordenador)."""
    if ruta is None:
        actual = cmds.file(query=True, sceneName=True)
        base, ext = os.path.splitext(actual) if actual else ("", ".ma")
        propuesta = base + "_horneada" + (ext or ".ma") if base else ""
        elegida = cmds.fileDialog2(fileMode=0, caption=t("menu_copia_horneada"), startingDirectory=propuesta,
                                   fileFilter="Maya ASCII (*.ma);;Maya Binary (*.mb)")
        if not elegida:
            return None
        ruta = elegida[0]
    try:
        n = escena.guardar_copia_horneada(ruta)
    except RuntimeError as error:
        cmds.warning("PipeEditor: {}".format(error))
        return None
    om.MGlobal.displayInfo(t("copia_horneada_hecha", n=n, ruta=ruta))
    servicio().mensaje(t("copia_horneada_hecha", n=n, ruta=os.path.basename(ruta)))
    refrescar()
    return ruta


def lista_materiales(ruta=None):
    """Guarda en CSV la lista de materiales de lo seleccionado, o de toda la escena."""
    nodos = escena.nodos_seleccionados() or escena.nodos()
    if not nodos:
        cmds.warning(t("falta_cable"))
        return None
    if ruta is None:
        actual = cmds.file(query=True, sceneName=True)
        propuesta = (os.path.splitext(actual)[0] + "_materiales.csv") if actual else ""
        elegida = cmds.fileDialog2(fileMode=0, caption=t("menu_lista_materiales"), startingDirectory=propuesta,
                                   fileFilter="CSV (*.csv)")
        if not elegida:
            return None
        ruta = elegida[0]
    filas = escena.lista_materiales(nodos, ruta)
    om.MGlobal.displayInfo(t("lista_materiales_hecha", n=len(filas), ruta=ruta))
    servicio().mensaje(t("lista_materiales_hecha", n=len(filas), ruta=os.path.basename(ruta)))
    return ruta


def exportar(ruta=None):
    """Exporta lo seleccionado (o toda la escena) horneado a USD, FBX u OBJ."""
    nodos = escena.nodos_seleccionados() or escena.nodos()
    if not nodos:
        cmds.warning(t("falta_cable"))
        return None
    if ruta is None:
        elegida = cmds.fileDialog2(fileMode=0, caption=t("menu_exportar"),
                                   fileFilter="USD (*.usd *.usda *.usdc);;FBX (*.fbx);;OBJ (*.obj)")
        if not elegida:
            return None
        ruta = elegida[0]
    try:
        n = escena.exportar_horneado(nodos, ruta)
    except (RuntimeError, ValueError) as error:
        cmds.warning("PipeEditor: {}".format(error))
        return None
    om.MGlobal.displayInfo(t("exportado", n=n, ruta=ruta))
    servicio().mensaje(t("exportado", n=n, ruta=os.path.basename(ruta)))
    return ruta


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
    cmds.menuItem(label=t("menu_copia_horneada"), command=lambda *_: copia_horneada())
    cmds.menuItem(label=t("menu_lista_materiales"), command=lambda *_: lista_materiales())
    cmds.menuItem(label=t("menu_exportar"), command=lambda *_: exportar())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_idioma"), subMenu=True)
    cmds.radioMenuItemCollection()
    for idioma in i18n.idiomas():
        cmds.menuItem(label=t("idioma_" + idioma), radioButton=(idioma == i18n.idioma()),
                      enable=not i18n.por_entorno(), command=lambda *_, i=idioma: cambiar_idioma(i))
    cmds.setParent("..", menu=True)
    cmds.menuItem(label=t("menu_acerca", version=pipeeditor.__version__), enable=False)


OPCION_IDIOMA = "PipeEditorIdioma"


def _idioma_guardado():
    if not i18n.por_entorno() and cmds.optionVar(exists=OPCION_IDIOMA):
        i18n.usar_idioma(cmds.optionVar(query=OPCION_IDIOMA))


def cambiar_idioma(idioma):
    """Cambia el idioma de la interfaz y lo recuerda para las próximas veces."""
    cmds.optionVar(stringValue=(OPCION_IDIOMA, idioma))
    i18n.usar_idioma(idioma)
    abierta = cmds.workspaceControl(CONTROL, exists=True)
    if abierta:
        cmds.deleteUI(CONTROL)
        _estado["ventana"] = None
    _crear_ordenes()
    _crear_menu()
    if abierta:
        mostrar()
    om.MGlobal.displayInfo("PipeEditor: " + t("idioma_cambiado"))


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


def _al_abrir():
    try:
        n = escena.migrar_escena()
        if n:
            om.MGlobal.displayInfo(t("escena_migrada", n=n))
    except Exception as error:  # nunca impedir abrir una escena
        om.MGlobal.displayWarning("PipeEditor: {}".format(error))
    refrescar()


def iniciar():
    try:
        cmds.selectPref(trackSelectionOrder=True)
    except RuntimeError:
        pass
    _idioma_guardado()
    _crear_ordenes()
    if cmds.about(batch=True):
        return
    _crear_menu()
    _estado["trabajos"] = [cmds.scriptJob(event=["SelectionChanged", refrescar]),
                           cmds.scriptJob(event=["SceneOpened", _al_abrir])]
    _al_abrir()
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
