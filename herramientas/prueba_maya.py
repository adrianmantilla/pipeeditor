"""Prueba de PipeEditor dentro de Maya, sin interfaz (herramienta de desarrollo).

Desde la terminal, con el mayapy de cada versión:

    /Applications/Autodesk/maya2027/Maya.app/Contents/bin/mayapy herramientas/prueba_maya.py
    "C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe" herramientas\\prueba_maya.py

No toca tus preferencias de Maya. Comprueba que el plugin carga, que el nodo
calcula cables y tuberías, que siguen a sus anclajes, los apoyos, los
conectores, insertar y quitar puntos, hornear, y que la escena se guarda y se
vuelve a abrir bien. La ventana y el clic en el visor necesitan la interfaz:
pruébalos abriendo Maya normalmente. Termina con «RESULTADO: OK» o con la
lista de fallos. Con el argumento ``--render carpeta`` guarda además una
escena de ejemplo en esa carpeta.
"""

import os
import shutil
import sys
import tempfile
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

fallos = []


def comprobar(condicion, texto):
    print(("  ok    " if condicion else "  FALLO ") + texto)
    if not condicion:
        fallos.append(texto)


def caras(forma):
    from maya import cmds
    return cmds.polyEvaluate(forma, face=True) if forma and cmds.objExists(forma) else 0


def caja_y(forma):
    from maya import cmds
    return cmds.exactWorldBoundingBox(forma)


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds

    print("Maya", cmds.about(version=True), "-", cmds.about(operatingSystem=True))
    cmds.loadPlugin(os.path.join(RAIZ, "plug-ins", "pipeeditor_plugin.py"))
    comprobar(cmds.pluginInfo("pipeeditor_plugin", query=True, loaded=True), "el plugin se carga")
    from pipeeditor import escena, interfaz_maya, materiales
    interfaz_maya.iniciar()
    for nombre in interfaz_maya.COMANDOS:
        comprobar(cmds.runTimeCommand(nombre, exists=True), "existe la orden " + nombre)
    comprobar(materiales._tipo() in ("openPBRSurface", "standardSurface"), "material: " + materiales._tipo())

    temporal = tempfile.mkdtemp()
    try:
        cmds.file(new=True, force=True)
        # --- cable entre dos postes ---
        poste_a = cmds.polyCube(width=20, height=300, depth=20, name="posteA")[0]
        cmds.move(0, 150, 0, poste_a)
        poste_b = cmds.polyCube(width=20, height=250, depth=20, name="posteB")[0]
        cmds.move(500, 125, 100, poste_b)
        grupo = escena.crear([((0, 290, 0), (1, 0, 0), poste_a), ((500, 240, 100), (-1, 0, 0), poste_b)],
                             {"tipo": "cable", "grosor": 2.0, "holgura": 0.1, "conector_inicio": "clavija",
                              "conector_fin": "gancho", "salida": 5.0})
        n = escena.nodo_de(grupo)
        comprobar(n is not None and cmds.nodeType(n) == "pipeEditorNodo", "se crea el nodo del cable")
        cuerpo, piezas, curva = escena.formas_de(n)
        comprobar(caras(cuerpo) > 100, "el cable tiene malla ({} caras)".format(caras(cuerpo)))
        comprobar(caras(piezas) > 10, "los conectores tienen malla")
        largo = cmds.getAttr(n + ".longitudTotal")
        comprobar(500 < largo < 700, "longitud razonable ({:.1f})".format(largo))
        caida = cmds.getAttr(n + ".caida")
        comprobar(caida > 10, "el cable cuelga ({:.1f} de caída)".format(caida))
        comprobar(materiales.de(cuerpo) == "goma_negra", "material del cuerpo")
        anclas = escena.anclas_de(n)
        comprobar(len(anclas) == 2, "dos anclajes")
        comprobar(cmds.listRelatives(anclas[1], parent=True)[0] == poste_b, "el anclaje cuelga del poste")

        antes = caja_y(cuerpo)
        cmds.move(0, 100, 0, poste_b, relative=True)
        despues = caja_y(cuerpo)
        comprobar(despues[4] > antes[4] + 50, "el cable sigue al poste al moverlo")
        cmds.undo()

        # holgura y longitud fija
        cmds.setAttr(n + ".holgura", 0.4)
        comprobar(cmds.getAttr(n + ".caida") > caida * 1.5, "más holgura, más caída")
        escena.fijar_longitudes([n])
        fijo = cmds.getAttr(n + ".longitudTotal")
        cmds.move(400, 0, 0, poste_b, relative=True)
        comprobar(cmds.getAttr(n + ".tensos") >= 1, "con longitud fija, al separar se tensa")
        comprobar(abs(cmds.getAttr(n + ".longitudTotal") - fijo) / fijo < 0.6, "longitud fija se mantiene")
        cmds.move(-400, 0, 0, poste_b, relative=True)
        cmds.setAttr(n + ".modoTension", 0)

        # perfiles
        for i, perfil in enumerate(("redondo", "doble", "plano", "trenzado", "corrugado", "espiral")):
            cmds.setAttr(n + ".perfilCable", i)
            comprobar(caras(cuerpo) > 50, "perfil " + perfil)
        cmds.setAttr(n + ".perfilCable", 0)

        # apoyo en un objeto y en el suelo
        mesa = cmds.polyCube(width=200, height=10, depth=200, name="mesa")[0]
        cmds.move(250, 150, 50, mesa)
        cmds.setAttr(n + ".holgura", 1.0)
        escena.poner_apoyos([n], [mesa])
        caja = caja_y(cuerpo)
        comprobar(caja[1] >= 150 - 1, "se apoya sobre la mesa (mínimo y {:.1f})".format(caja[1]))
        escena.poner_apoyos([n], [])
        cmds.setAttr(n + ".holgura", 0.1)

        # puntos intermedios
        nueva = escena.insertar_punto(anclas[0])
        comprobar(len(escena.anclas_de(n)) == 3, "insertar un punto")
        comprobar(escena.quitar_puntos([nueva]) == 1 and len(escena.anclas_de(n)) == 2, "quitar el punto")

        # conector propio
        cono = cmds.polyCone(radius=3, height=8, name="miConector")[0]
        escena.poner_conector_propio([n], cono)
        comprobar(caras(piezas) > 10, "conector propio")

        # haz
        cmds.setAttr(n + ".haz", 7)
        cmds.setAttr(n + ".separacionBridasHaz", 40)
        comprobar(caras(cuerpo) > 700, "haz de 7 cables")
        cmds.setAttr(n + ".haz", 1)

        # --- tubería en ángulo recto entre dos paredes ---
        pared = cmds.polyCube(width=600, height=400, depth=5, name="pared")[0]
        cmds.move(300, 200, -40, pared)
        tub = escena.crear([((0, 50, -37.5), (0, 0, 1), None), ((400, 300, -37.5), (0, 0, 1), None)],
                           {"tipo": "tuberia", "grosor": 8.0, "separacion_bridas": 100.0, "codo": "pieza",
                            "separacion_soportes": 80.0, "extremos": "brida"})
        nt = escena.nodo_de(tub)
        c_tub, p_tub, _ = escena.formas_de(nt)
        comprobar(caras(c_tub) > 100, "la tubería tiene malla")
        comprobar(caras(p_tub) > 100, "bridas y manguitos")
        sin_soportes = caras(p_tub)
        escena.poner_apoyos([nt], [pared])
        comprobar(caras(p_tub) > sin_soportes, "soportes a la pared")
        comprobar(materiales.de(c_tub) == "cobre", "material de la tubería")

        # --- desde una curva y desde aristas ---
        curva_usuario = cmds.curve(degree=3, point=[(0, 0, 200), (100, 50, 250), (200, 0, 300), (300, 80, 200)])
        g_curva = escena.crear_desde_curva(curva_usuario, {"tipo": "tuberia", "perfil_tuberia": "corrugada",
                                                           "grosor": 5.0})
        comprobar(caras(escena.formas_de(escena.nodo_de(g_curva))[0]) > 100, "tubería desde una curva")
        cmds.move(0, 0, 50, curva_usuario + ".cv[1]", relative=True)
        comprobar(caras(escena.formas_de(escena.nodo_de(g_curva))[0]) > 100, "sigue a la curva al editarla")
        plano = cmds.polyPlane(width=200, height=200, subdivisionsX=4, subdivisionsY=4, name="tejado")[0]
        cmds.move(0, 400, 0, plano)
        g_aristas = escena.crear_desde_aristas(["{}.e[0:3]".format(plano)], {"tipo": "tuberia", "grosor": 6.0})
        comprobar(caras(escena.formas_de(escena.nodo_de(g_aristas))[0]) > 50, "tubería desde aristas")

        # --- entre dos grupos ---
        sel = ["{}.f[1]".format(poste_a), "{}.f[3]".format(poste_a), "{}.f[1]".format(poste_b),
               "{}.f[3]".format(poste_b)]
        anclajes = []
        for s in sel:
            anclajes.extend(escena._puntos_de_componente(s))
        contenedor, creados = escena.crear_entre_grupos(anclajes, {"tipo": "cable", "grosor": 1.0})
        comprobar(len(creados) == 2, "dos cables entre dos grupos")

        # --- guardar y abrir ---
        ruta = os.path.join(temporal, "prueba_pipeeditor.ma")
        cmds.file(rename=ruta)
        cmds.file(save=True, type="mayaAscii", force=True)
        caras_antes = caras(cuerpo)
        cmds.file(new=True, force=True)
        cmds.file(ruta, open=True, force=True)
        n2 = escena.nodos()
        comprobar(len(n2) >= 6, "la escena guarda los nodos ({})".format(len(n2)))
        cuerpo2 = escena.formas_de(escena.nodo_de("cable_01"))[0]
        comprobar(caras(cuerpo2) == caras_antes, "al abrir, el cable se recalcula igual")

        # --- hornear ---
        hechos = escena.hornear([escena.nodo_de("cable_01")])
        comprobar(hechos and not cmds.ls("cable_01_nodo"), "hornear quita el nodo")
        comprobar(caras("cable_01_cuerpo") > 100, "tras hornear queda la malla")
        comprobar(not cmds.listConnections("cable_01_cuerpoShape.inMesh"), "la malla ya no depende de nada")
        escena.hornear(escena.nodos())
        comprobar(not escena.nodos(), "hornear todo")
        ruta2 = os.path.join(temporal, "horneada.ma")
        cmds.file(rename=ruta2)
        cmds.file(save=True, type="mayaAscii", force=True)
        with open(ruta2, encoding="utf-8", errors="ignore") as f:
            texto = f.read()
        comprobar("pipeEditorNodo" not in texto and "requires \"pipeeditor_plugin\"" not in texto,
                  "la escena horneada no necesita PipeEditor")

        if "--render" in sys.argv:
            destino = sys.argv[sys.argv.index("--render") + 1]
            escena_ejemplo(destino)
    finally:
        shutil.rmtree(temporal, ignore_errors=True)

    print("")
    if fallos:
        print("RESULTADO: {} FALLOS".format(len(fallos)))
        for f in fallos:
            print("  - " + f)
    else:
        print("RESULTADO: OK")


def escena_ejemplo(carpeta):
    """Una azotea con tendido, mazo de cables y tuberías, guardada en ``carpeta``."""
    from maya import cmds
    from pipeeditor import escena
    cmds.file(new=True, force=True)
    os.makedirs(carpeta, exist_ok=True)
    suelo = cmds.polyPlane(width=1400, height=900, name="azotea")[0]
    muro = cmds.polyCube(width=1400, height=350, depth=20, name="muro")[0]
    cmds.move(0, 175, -450, muro)
    postes = []
    for i, x in enumerate((-550, -50, 450)):
        p = cmds.polyCylinder(radius=8, height=420, name="poste{}".format(i + 1))[0]
        cmds.move(x, 210, 150, p)
        postes.append(p)
    for altura in (400, 380):
        anclajes = [((x, altura, 150), (0, 1, 0), p) for x, p in zip((-550, -50, 450), postes)]
        escena.crear(anclajes, {"tipo": "cable", "grosor": 1.6, "holgura": 0.05, "salida": 0.0})
    escena.crear([((-550, 300, 158), (0, 0, 1), postes[0]), ((-200, 0, 400), (0, 1, 0), None)],
                 {"tipo": "cable", "perfil_cable": "corrugado", "grosor": 2.5, "holgura": 0.6,
                  "material_cuerpo": "manguera_naranja"})
    escena.crear([((-50, 250, 158), (0, 0, 1), postes[1]), ((300, 0, 300), (0, 1, 0), None)],
                 {"tipo": "cable", "grosor": 0.8, "haz": 7, "torsion": 0.5, "separacion_bridas_haz": 30,
                  "holgura": 0.4})
    g = escena.crear([((-650, 40, -440), (0, 0, 1), muro), ((600, 260, -440), (0, 0, 1), muro)],
                     {"tipo": "tuberia", "grosor": 12.0, "separacion_bridas": 250.0, "separacion_soportes": 150.0,
                      "codo": "pieza", "material_cuerpo": "hierro_pintado", "material_piezas": "acero_galvanizado"})
    escena.poner_apoyos([escena.nodo_de(g)], [muro])
    g = escena.crear([((-400, 320, -440), (0, 0, 1), muro), ((200, 330, -440), (0, 0, 1), muro)],
                     {"tipo": "tuberia", "perfil_tuberia": "cuadrada", "grosor": 30.0, "radio_codo": 0.6,
                      "salida": 30.0, "separacion_soportes": 120.0, "material_cuerpo": "acero_galvanizado"})
    escena.poner_apoyos([escena.nodo_de(g)], [muro])
    del suelo
    ruta = os.path.join(carpeta, "ejemplo_azotea.ma")
    cmds.file(rename=ruta)
    cmds.file(save=True, type="mayaAscii", force=True)
    print("Escena de ejemplo guardada en", ruta)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("RESULTADO: ERROR")
    finally:
        try:
            import maya.standalone
            maya.standalone.uninitialize()
        except Exception:
            pass
        os._exit(0)
