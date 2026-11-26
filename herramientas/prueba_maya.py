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

import math
import os
import shutil
import sys
import tempfile
import time
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


def puntos_curva(forma, cuantos=400):
    """Puntos repartidos a lo largo de la curva central (sobre la curva, no sus CV)."""
    import maya.api.OpenMaya as om
    camino = om.MSelectionList().add(forma).getDagPath(0)
    fn = om.MFnNurbsCurve(camino)
    largo = fn.length()
    salida = []
    for k in range(cuantos + 1):
        u = fn.findParamFromLength(largo * k / float(cuantos))
        p = fn.getPointAtParam(u, om.MSpace.kWorld)
        salida.append((p.x, p.y, p.z))
    return salida


def malla_fn(forma):
    import maya.api.OpenMaya as om
    return om.MFnMesh(om.MSelectionList().add(forma).getDagPath(0))


def bordes_abiertos(forma):
    """Aristas con una sola cara: grietas que se abren al suavizar."""
    import maya.api.OpenMaya as om
    it = om.MItMeshEdge(om.MSelectionList().add(forma).getDagPath(0))
    abiertas = 0
    while not it.isDone():
        if it.numConnectedFaces() < 2:
            abiertas += 1
        it.next()
    return abiertas


def caja_forma(objeto):
    """Caja de la malla sola: la del transform incluye los anclajes que cuelgan de él."""
    from maya import cmds
    return cmds.exactWorldBoundingBox(cmds.listRelatives(objeto, shapes=True, fullPath=True)[0])


def nodo_enums():
    from pipeeditor import nodo
    return nodo.ENUMS


def dentro_de(puntos, caja, margen=0.3):
    (x0, y0, z0, x1, y1, z1) = caja
    return [p for p in puntos if x0 + margen < p[0] < x1 - margen and y0 + margen < p[1] < y1 - margen
            and z0 + margen < p[2] < z1 - margen]


def ms_recalculo(n, atributo="semilla"):
    """Milisegundos que tarda el nodo en recalcular tras un cambio."""
    import time
    from maya import cmds
    v = cmds.getAttr(n + "." + atributo)
    t = time.time()
    cmds.setAttr(n + "." + atributo, v + 1)
    cmds.getAttr(n + ".longitudTotal")
    cmds.polyEvaluate(cmds.listConnections(n + ".cuerpo", shapes=True)[0], face=True)
    ms = (time.time() - t) * 1000.0
    cmds.setAttr(n + "." + atributo, v)
    return ms


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
        cmds.move(0, 200, 0, poste_b, relative=True)
        despues = caja_y(cuerpo)
        comprobar(despues[4] > antes[4] + 100, "el cable sigue al poste al moverlo ({:.0f} -> {:.0f})".format(
            antes[4], despues[4]))
        cmds.move(0, -200, 0, poste_b, relative=True)

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
        puntos = puntos_curva(curva)
        encima = [p[1] for p in puntos if 170 < p[0] < 330 and -40 < p[2] < 140]
        comprobar(caras(cuerpo) > 100 and encima and min(encima) >= 155 - 0.1,
                  "se apoya sobre la mesa (mínimo y sobre la mesa {:.1f}, {} puntos de {})".format(
                      min(encima) if encima else -1, len(encima), len(puntos)))
        metidos = dentro_de(puntos, caja_forma(mesa), margen=0.5)
        comprobar(not metidos, "no atraviesa la mesa ({} puntos dentro)".format(len(metidos)))
        fuera = [p[1] for p in puntos if p[0] < 120 or p[0] > 380]
        comprobar(fuera and min(fuera) >= -0.1, "y fuera de la mesa, sobre el suelo")
        escena.poner_apoyos([n], [])
        cmds.setAttr(n + ".holgura", 0.1)

        # lámpara sobre la mesa enchufada a la pared: cae por el borde, no sube por debajo del tablero
        mesa2 = cmds.polyCube(width=220, height=8, depth=110, name="mesaLampara")[0]
        cmds.move(-200, 76, 600, mesa2)
        enchufe = cmds.polyCube(width=300, height=200, depth=10, name="paredLampara")[0]
        cmds.move(-500, 100, 205, enchufe)
        lamp = escena.crear([((-520, 30, 210.5), (0, 0, 1), enchufe), ((-170, 80.5, 610), (0, 1, 0), mesa2)],
                            {"tipo": "cable", "perfil_cable": "doble", "grosor": 0.7, "holgura": 0.9,
                             "conector_inicio": "clavija"})
        nl = escena.nodo_de(lamp)
        escena.poner_apoyos([nl], [mesa2])
        pl = puntos_curva(escena.formas_de(nl)[2])
        x0, y0, z0, x1, y1, z1 = caja_forma(mesa2)
        bajo = [p for p in pl if x0 + 1 < p[0] < x1 - 1 and z0 + 1 < p[2] < z1 - 1 and 2.0 < p[1] < y1 - 0.5]
        comprobar(not bajo, "lámpara: cae por el borde de la mesa ({} puntos bajo o dentro del tablero)".format(
            len(bajo)))

        # asentar y fijar: la forma no cambia con los ajustes; el extremo sí sigue a su anclaje
        comprobar(escena.alternar_fijado([nl]) is True and escena.esta_fijado(nl), "asentar y fijar")
        antes = puntos_curva(escena.formas_de(nl)[2], 50)
        cmds.setAttr(nl + ".rigidez", 0.9)
        despues = puntos_curva(escena.formas_de(nl)[2], 50)
        comprobar(max(math.dist(p, q) for p, q in zip(antes, despues)) < 0.5,
                  "fijado: cambiar la rigidez no cambia el cable")
        ancla_fin = escena.anclas_de(nl)[-1]
        fin_antes = cmds.xform(ancla_fin, query=True, worldSpace=True, translation=True)
        t = time.time()
        cmds.move(0, 0, 40, ancla_fin, relative=True, worldSpace=True)
        despues = puntos_curva(escena.formas_de(nl)[2], 50)
        ms = (time.time() - t) * 1000
        comprobar(math.dist(despues[-1], antes[-1]) > 30 and math.dist(despues[0], antes[0]) < 0.5,
                  "fijado: la forma sigue al extremo que se mueve ({:.0f} ms)".format(ms))
        cmds.xform(ancla_fin, worldSpace=True, translation=fin_antes)
        comprobar(escena.alternar_fijado([nl]) is False and not escena.esta_fijado(nl), "soltar la forma")
        cmds.delete(lamp, mesa2, enchufe)

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
        m_tub = escena.forma_de(nt, "metal")
        sin_soportes = caras(p_tub) + caras(m_tub)
        escena.poner_apoyos([nt], [pared])
        comprobar(caras(p_tub) + caras(m_tub) > sin_soportes, "soportes a la pared (van en la malla de metal)")
        comprobar(materiales.de(c_tub) == "cobre", "material de la tubería")

        # techo: soportes colgados con varilla (rayo hacia arriba)
        techo = cmds.polyCube(width=600, height=5, depth=200, name="techo")[0]
        cmds.move(300, 400, 0, techo)
        escena.poner_apoyos([nt], [pared, techo])
        cmds.setAttr(nt + ".soportesHacia", 1)
        cmds.setAttr(nt + ".alcanceSoportes", 400.0)
        ys = [p[1] for p in cmds.xform(m_tub + ".vtx[*]", query=True, translation=True, worldSpace=True)[1::3]]
        comprobar(ys and max(ys) > 395, "soportes colgados del techo ({:.0f})".format(max(ys) if ys else 0))
        cmds.setAttr(nt + ".soportesHacia", 0)
        escena.poner_apoyos([nt], [pared])
        cmds.delete(techo)

        # accesorios, derivación y lista de materiales
        nueva = escena.insertar_punto(escena.anclas_de(nt)[0])
        comprobar(escena.poner_accesorio([nueva], "valvula_bola") == 1, "válvula en un anclaje")
        import json as _json
        recuento = _json.loads(cmds.getAttr(nt + ".recuento"))
        comprobar(recuento.get("valvulas_bola") == 1, "la válvula sale en el recuento")
        destino = cmds.spaceLocator(name="destinoRama")[0]
        cmds.move(200, 50, 150, destino)
        rama = escena.derivar(nueva, ((200, 50, 150), (0, 0, -1), destino))
        nr = escena.nodo_de(rama)
        comprobar(nr is not None and cmds.getAttr(nueva + ".pipeAccesorio") == 3 and caras(escena.formas_de(nr)[0]) > 50,
                  "derivación con te")
        csv_ruta = os.path.join(temporal, "materiales.csv")
        filas_bom = escena.lista_materiales([nt, nr], csv_ruta)
        comprobar(os.path.exists(csv_ruta) and any(f["concepto"] == "tes" for f in filas_bom)
                  and any(f["concepto"] == "tubo" for f in filas_bom), "lista de materiales en CSV")
        escena.borrar([nt])
        comprobar(cmds.objExists(nr) and len(escena.anclas_de(nr)) == 2, "borrar la tubería deja viva la rama")
        escena.borrar([nr])
        cmds.delete(destino)
        tub = escena.crear([((0, 50, -37.5), (0, 0, 1), None), ((400, 300, -37.5), (0, 0, 1), None)],
                           {"tipo": "tuberia", "grosor": 8.0, "separacion_bridas": 100.0, "codo": "pieza",
                            "separacion_soportes": 80.0, "extremos": "brida"})
        nt = escena.nodo_de(tub)
        escena.poner_apoyos([nt], [pared])

        # --- desde una curva y desde aristas ---
        curva_usuario = cmds.curve(degree=3, point=[(0, 0, 200), (100, 50, 250), (200, 0, 300), (300, 80, 200)])
        g_curva = escena.crear_desde_curva(curva_usuario, {"tipo": "tuberia", "perfil_tuberia": "corrugada",
                                                           "grosor": 5.0})
        comprobar(caras(escena.formas_de(escena.nodo_de(g_curva))[0]) > 100, "tubería desde una curva")
        cmds.move(0, 0, 50, curva_usuario + ".cv[1]", relative=True)
        comprobar(caras(escena.formas_de(escena.nodo_de(g_curva))[0]) > 100, "sigue a la curva al editarla")
        tejado = cmds.polyCube(width=200, height=50, depth=200, name="tejado")[0]
        cmds.move(0, 400, 0, tejado)
        borde = cmds.ls(cmds.polyListComponentConversion(tejado + ".f[1]", toEdge=True), flatten=True)
        g_aristas = escena.crear_desde_aristas(borde, {"tipo": "tuberia", "grosor": 6.0})
        comprobar(caras(escena.formas_de(escena.nodo_de(g_aristas))[0]) > 50, "tubería desde aristas")

        # --- entre dos grupos ---
        sel = ["{}.f[1]".format(poste_a), "{}.f[3]".format(poste_a), "{}.f[1]".format(poste_b),
               "{}.f[3]".format(poste_b)]
        anclajes = []
        for s in sel:
            anclajes.extend(escena._puntos_de_componente(s))
        contenedor, creados = escena.crear_entre_grupos(anclajes, {"tipo": "cable", "grosor": 1.0})
        comprobar(len(creados) == 2, "dos cables entre dos grupos")

        # --- calidad de lo generado (v1.1) ---
        pruebas_calidad(cmds, escena, materiales, n)
        cmds.select(clear=True)

        # --- escenas de la versión 1.0 (sin versión de datos) ---
        from pipeeditor import construir
        comprobar(cmds.getAttr(n + ".versionDatos") == construir.VERSION_DATOS, "los nodos nuevos guardan su versión")
        viejo = escena.crear([((0, 50, 300), (0, 0, 1), None), ((300, 0, 500), (0, 1, 0), None)],
                             {"tipo": "tuberia", "grosor": 4.0})
        nv = escena.nodo_de(viejo)
        cmds.setAttr(nv + ".versionDatos", 0)
        cmds.setAttr(nv + ".recorrido", list(nodo_enums()["recorrido"]).index("pegado"))
        migrados = escena.migrar_escena()
        ajustes_viejo = escena.leer_ajustes(nv)
        comprobar(migrados == 1 and ajustes_viejo["recorrido"] == "z" and not ajustes_viejo["reposo"]
                  and cmds.getAttr(nv + ".versionDatos") == construir.VERSION_DATOS,
                  "una escena de la 1.0 se mantiene como era (recorrido en Z, sin reposo)")
        cmds.delete(viejo)

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

        # --- copia horneada para render en otro ordenador ---
        copia = os.path.join(temporal, "copia_horneada.ma")
        hechos_copia = interfaz_maya.copia_horneada(copia)
        with open(copia, encoding="utf-8", errors="ignore") as f:
            texto_copia = f.read()
        comprobar(hechos_copia and "pipeEditorNodo" not in texto_copia and "cable_01_cuerpo" in texto_copia,
                  "copia horneada sin nodos de PipeEditor")
        comprobar(len(escena.nodos()) == len(n2) and cmds.file(query=True, sceneName=True) == ruta
                  and caras(cuerpo2) == caras_antes, "la escena abierta sigue igual tras la copia")

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
    return 1 if fallos else 0


def pruebas_calidad(cmds, escena, materiales, n):
    """Mide lo realista que es el resultado, no solo que exista."""
    cuerpo, piezas, curva = escena.formas_de(n)
    metal = escena.forma_de(n, "metal")
    print("  -- calidad --")
    caja_uv = cmds.polyEvaluate(piezas, boundingBox2d=True)
    comprobar(caja_uv[0][1] - caja_uv[0][0] > 0.05, "calidad: el conector propio conserva sus UV")
    from pipeeditor import piezas as pz
    cmds.setAttr(n + ".conectorInicio", list(pz.CONECTORES).index("clavija"))
    cmds.setAttr(n + ".conectorFin", list(pz.CONECTORES).index("gancho"))
    # malla cerrada, aristas vivas con pliegue, curva cúbica
    comprobar(bordes_abiertos(cuerpo) == 0, "calidad: el cuerpo es cerrado (se suaviza sin grietas)")
    fn = malla_fn(cuerpo)
    duras = sum(1 for e in range(fn.numEdges) if not fn.isEdgeSmooth(e))
    comprobar(duras > 0, "calidad: bordes de las tapas con arista dura ({})".format(duras))
    pliegues = cmds.polyCrease(cuerpo + ".e[*]", query=True, value=True) or []
    comprobar(any(v > 0 for v in pliegues), "calidad: bordes con pliegue para subdividir")
    comprobar(cmds.getAttr(curva + ".degree") == 3, "calidad: curva central cúbica")
    # metal aparte
    comprobar(metal and caras(metal) > 0, "calidad: las patas de la clavija van en la malla de metal")
    comprobar(metal and materiales.de(metal) == "acero", "calidad: material del metal")
    # UV a escala real: 1 unidad UV = 10 cm a lo largo
    caja_uv = cmds.polyEvaluate(cuerpo, boundingBox2d=True)
    largo = cmds.getAttr(n + ".longitudTotal")
    comprobar(abs(caja_uv[1][1] - caja_uv[1][0] - largo / 10.0) / (largo / 10.0) < 0.05,
              "calidad: UV a escala real ({:.1f} de V para {:.0f} cm)".format(caja_uv[1][1] - caja_uv[1][0], largo))
    print("  info  {:.0f} polígonos por metro de cable".format(caras(cuerpo) / max(largo, 1.0) * 100.0))

    # reposo en el suelo: el sobrante queda tumbado y la longitud se conserva
    cmds.setAttr(n + ".holgura", 0.9)
    puntos = puntos_curva(curva)
    tumbados = [p for p in puntos if p[1] < 2.5]
    comprobar(len(tumbados) > 40, "calidad: el sobrante queda tumbado en el suelo ({} de {} puntos)".format(
        len(tumbados), len(puntos)))
    comprobar(min(p[1] for p in puntos) > 0.5, "calidad: no atraviesa el suelo (mínimo {:.2f})".format(
        min(p[1] for p in puntos)))
    pedido = sum(cmds.getAttr(n + ".longitudesActuales") or [0.0]) + 2 * cmds.getAttr(n + ".salida")
    real = cmds.getAttr(n + ".longitudTotal")
    comprobar(abs(real - pedido) / pedido < 0.03, "calidad: conserva la longitud ({:.0f} de {:.0f} cm, {:+.1f} %)".format(
        real, pedido, (real - pedido) / pedido * 100.0))
    ms = ms_recalculo(n)
    comprobar(ms < 1500, "calidad: recalcula el reposo en {:.0f} ms".format(ms))
    # sin pico donde toca el suelo: giro máximo entre tramos de 2 cm
    import math
    peor = 0.0
    pts = puntos_curva(curva, 600)
    for a, b, c in zip(pts, pts[2:], pts[4:]):
        u = [b[k] - a[k] for k in range(3)]
        v = [c[k] - b[k] for k in range(3)]
        lu, lv = math.sqrt(sum(x * x for x in u)), math.sqrt(sum(x * x for x in v))
        if lu > 1e-6 and lv > 1e-6:
            peor = max(peor, math.degrees(math.acos(max(-1, min(1, sum(u[k] * v[k] for k in range(3)) / lu / lv)))))
    comprobar(peor < 35.0, "calidad: sin picos al tocar el suelo (giro máximo {:.0f}°)".format(peor))

    # un poste en medio: antes se atravesaba por los lados
    cmds.setAttr(n + ".holgura", 0.1)
    columna = cmds.polyCylinder(radius=10, height=600, subdivisionsAxis=24, name="columnaEnMedio")[0]
    medio = puntos_curva(curva)[200]
    cmds.move(medio[0], 300, medio[2], columna)
    caja = cmds.exactWorldBoundingBox(columna)
    escena.poner_apoyos([n], [columna])
    puntos = puntos_curva(curva)
    radio_col = [math.hypot(p[0] - medio[0], p[2] - medio[2]) for p in puntos]
    comprobar(min(radio_col) > 10.0 - 0.3, "calidad: no atraviesa un poste por el lado (distancia {:.1f})".format(
        min(radio_col)))
    escena.poner_apoyos([n], [])
    cmds.delete(columna)
    del caja

    # gancho: el cable pasa por el punto sin atarse
    nueva = escena.insertar_punto(escena.anclas_de(n)[0])
    escena.alternar_gancho([nueva])
    cmds.move(0, 60, 0, nueva, relative=True)
    pos = cmds.xform(nueva, query=True, worldSpace=True, translation=True)
    cerca = min(math.sqrt(sum((p[k] - pos[k]) ** 2 for k in range(3))) for p in puntos_curva(curva))
    comprobar(cerca < 2.0, "calidad: el cable pasa por el gancho ({:.2f} cm)".format(cerca))
    escena.quitar_puntos([nueva])

    # haz suelto: cada cable cuelga por su cuenta sin atravesarse
    cmds.setAttr(n + ".haz", 5)
    cmds.setAttr(n + ".separacionBridasHaz", 0)
    cmds.setAttr(n + ".variacion", 0.8)
    cmds.setAttr(n + ".holgura", 0.3)
    comprobar(bordes_abiertos(cuerpo) == 0 and caras(cuerpo) > 400, "calidad: haz suelto de 5 cables")
    ms = ms_recalculo(n)
    comprobar(ms < 4000, "calidad: el haz suelto recalcula en {:.0f} ms".format(ms))
    cmds.setAttr(n + ".haz", 1)
    cmds.setAttr(n + ".variacion", 0)
    cmds.setAttr(n + ".holgura", 0.1)

    # tuberías: rack de tres, normalizadas, esquivando una columna
    pilar = cmds.polyCube(width=40, height=500, depth=40, name="pilar")[0]
    cmds.move(800, 250, 600, pilar)
    rack = escena.crear([((600, 100, 600), (1, 0, 0), None), ((1000, 100, 600), (-1, 0, 0), None)],
                        {"tipo": "tuberia", "grosor": 6.0, "norma": "acero", "tubos": 3, "codo": "soldado",
                         "recorrido": "esquivar", "salida": 10.0})
    nr = escena.nodo_de(rack)
    escena.poner_apoyos([nr], [pilar])
    c_rack = escena.formas_de(nr)[0]
    import maya.api.OpenMaya as om
    vertices = [(p.x, p.y, p.z) for p in malla_fn(c_rack).getPoints(om.MSpace.kWorld)]
    dentro = dentro_de(vertices, cmds.exactWorldBoundingBox(pilar))
    comprobar(caras(c_rack) > 300 and not dentro, "calidad: rack de 3 tuberías que esquiva el pilar ({} vértices "
              "dentro)".format(len(dentro)))
    comprobar(bordes_abiertos(c_rack) == 0, "calidad: tuberías cerradas")
    comprobar(caras(escena.formas_de(nr)[1]) > 100, "calidad: codos soldados con cordones")

    # eje Z hacia arriba
    cmds.upAxis(axis="z", rotateView=False)
    try:
        gz = escena.crear([((0, 2000, 300), (1, 0, 0), None), ((400, 2000, 300), (-1, 0, 0), None)],
                          {"tipo": "cable", "holgura": 0.1, "apoyar_suelo": False})
        nz = escena.nodo_de(gz)
        pz = puntos_curva(escena.formas_de(nz)[2])
        comprobar(cmds.getAttr(nz + ".arriba") == 1 and min(p[2] for p in pz) < 260
                  and max(abs(p[1] - 2000) for p in pz) < 1.0, "calidad: con Z arriba cuelga hacia -Z")
        escena.borrar([nz])
    finally:
        cmds.upAxis(axis="y", rotateView=False)


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
    codigo = 2
    try:
        codigo = main()
    except Exception:
        traceback.print_exc()
        print("RESULTADO: ERROR")
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        try:
            import maya.standalone
            maya.standalone.uninitialize()
        except Exception:
            pass
        sys.stdout.flush()
        os._exit(codigo)
