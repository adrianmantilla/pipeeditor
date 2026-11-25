"""Escena de referencia de PipeEditor renderizada con Arnold (herramienta de desarrollo).

Sirve para comparar versiones a simple vista: la misma escena, la misma
cámara y la misma luz en cada versión del plugin.

    mayapy herramientas/render_referencia.py carpeta_de_salida [nombre]

Guarda ``<nombre>.ma`` y ``<nombre>.png`` (1280×720) en la carpeta. Si un
ajuste no existe en la versión del plugin que se prueba (versiones antiguas),
se salta sin fallar, para poder renderizar la misma escena antes y después.
"""

import os
import subprocess
import sys
import time
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))


def poner(cmds, n, ajustes):
    for atributo, valor in ajustes.items():
        try:
            if isinstance(valor, str):
                from pipeeditor import nodo
                valor = list(nodo.ENUMS[atributo]).index(valor)
            cmds.setAttr("{}.{}".format(n, atributo), valor)
        except Exception:  # ajuste que esta versión no tiene
            print("  (sin «{}» en esta versión)".format(atributo))


def crear(cmds, escena, anclajes, ajustes, extra=None, apoyos=()):
    base = {k: v for k, v in ajustes.items()}
    g = escena.crear(anclajes, base)
    n = escena.nodo_de(g)
    if extra:
        poner(cmds, n, extra)
    if apoyos:
        escena.poner_apoyos([n], list(apoyos))
    return n


def material_simple(cmds, nombre, color, rugosidad=0.6):
    m = cmds.shadingNode("standardSurface", asShader=True, name=nombre)
    cmds.setAttr(m + ".baseColor", *color, type="double3")
    cmds.setAttr(m + ".specularRoughness", rugosidad)
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=nombre + "SG")
    cmds.connectAttr(m + ".outColor", sg + ".surfaceShader")
    return sg


def construir_escena(cmds, escena):
    cmds.file(new=True, force=True)
    suelo = cmds.polyPlane(width=1400, height=1000, subdivisionsX=1, subdivisionsY=1, name="suelo")[0]
    pared = cmds.polyCube(width=1400, height=500, depth=20, name="pared")[0]
    cmds.move(0, 250, -400, pared)
    mesa = cmds.polyCube(width=220, height=8, depth=110, name="mesa")[0]
    cmds.move(-200, 76, 0, mesa)
    patas = []
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = cmds.polyCube(width=6, height=72, depth=6, name="pata")[0]
            cmds.move(-200 + sx * 100, 36, sz * 47, p)
            patas.append(p)
    postes = []
    for i, x in enumerate((150, 520)):
        p = cmds.polyCylinder(radius=7, height=300, subdivisionsAxis=24, name="poste{}".format(i + 1))[0]
        cmds.move(x, 150, 120, p)
        postes.append(p)
    pilar = cmds.polyCube(width=50, height=500, depth=50, name="pilar")[0]
    cmds.move(330, 250, -330, pilar)
    gris = material_simple(cmds, "hormigon", (0.42, 0.41, 0.39), 0.8)
    madera = material_simple(cmds, "madera", (0.36, 0.22, 0.12), 0.55)
    cmds.sets([suelo, pared, pilar] + postes, edit=True, forceElement=gris)
    cmds.sets([mesa] + patas, edit=True, forceElement=madera)

    objetos = [suelo, pared, mesa, pilar] + patas + postes
    # Cable de lámpara: del enchufe de la pared a la mesa, cae por el borde y se tumba en el suelo.
    crear(cmds, escena, [((-520, 30, -389), (0, 0, 1), pared), ((-170, 80.5, 10), (0, 1, 0), mesa)],
          {"tipo": "cable", "perfil_cable": "doble", "grosor": 0.7, "holgura": 0.9, "conector_inicio": "clavija",
           "material_cuerpo": "pvc_blanco", "material_piezas": "pvc_blanco"},
          {"rigidez": 0.15, "ondulacion": 0.4, "semilla": 3}, apoyos=[mesa] + patas)
    # Manguera: de un grifo en la pared, casi toda en el suelo.
    crear(cmds, escena, [((-20, 90, -389), (0, 0, 1), pared), ((60, 1.25, 330), (0, 0, 1), None)],
          {"tipo": "cable", "perfil_cable": "corrugado", "grosor": 2.5, "holgura": 0.8,
           "material_cuerpo": "manguera_naranja"},
          {"rigidez": 0.4, "ondulacion": 0.7, "semilla": 5})
    # Cuerda de puerto entre los dos postes, con grillete.
    crear(cmds, escena, [((150, 270, 128), (1, 0, 0), postes[0]), ((520, 230, 128), (-1, 0, 0), postes[1])],
          {"tipo": "cable", "perfil_cable": "trenzado", "grosor": 4.0, "holgura": 0.12, "lados": 8,
           "conector_fin": "grillete", "material_cuerpo": "canamo", "material_piezas": "acero_galvanizado",
           "material_metal": "acero_galvanizado"},
          {"rigidez": 0.1})
    # Haz de cables sueltos del poste al suelo.
    crear(cmds, escena, [((150, 200, 128), (0, 0, 1), postes[0]), ((260, 1.0, 380), (0, 0, 1), None)],
          {"tipo": "cable", "grosor": 1.2, "haz": 5, "holgura": 0.45, "material_cuerpo": "goma_negra"},
          {"variacion": 0.7, "rigidez": 0.35, "semilla": 2})
    # Tendido eléctrico entre lo alto de los postes, sobre aisladores.
    crear(cmds, escena, [((150, 300, 120), (0, 1, 0), postes[0]), ((520, 300, 120), (0, 1, 0), postes[1])],
          {"tipo": "cable", "grosor": 1.6, "holgura": 0.03, "salida": 0.0, "conector_inicio": "aislador",
           "conector_fin": "aislador", "material_piezas": "pvc_blanco", "material_metal": "acero_galvanizado"})
    # Rack de tres tuberías de acero por la pared, que esquiva el pilar.
    crear(cmds, escena, [((-600, 380, -385), (0, 0, 1), pared), ((600, 380, -385), (0, 0, 1), pared)],
          {"tipo": "tuberia", "grosor": 6.03, "material_cuerpo": "hierro_pintado",
           "material_piezas": "hierro_pintado", "extremos": "brida", "salida": 25.0},
          {"norma": "acero", "tubos": 3, "separacionTubos": 12.0, "codo": "soldado", "recorrido": "esquivar",
           "soportesAuto": True, "separacionSoportes": 150.0}, apoyos=[pared, pilar])
    # Tubería de cobre que baja de la pared al suelo.
    crear(cmds, escena, [((450, 300, -389), (0, 0, 1), pared), ((620, 0, -200), (0, 1, 0), None)],
          {"tipo": "tuberia", "grosor": 2.2, "codo": "pieza", "material_cuerpo": "cobre",
           "material_piezas": "cobre", "separacion_soportes": 80.0},
          {"norma": "cobre"}, apoyos=[pared])
    del objetos

    # Cámara y luces.
    cam, forma = cmds.camera(name="camReferencia", focalLength=35)
    cmds.setAttr(forma + ".focalLength", 28)
    cmds.xform(cam, worldSpace=True, translation=(40, 260, 980))
    cmds.viewLookAt(forma, position=(20, 150, -150))
    cmds.setAttr(forma + ".renderable", 1)
    for c in cmds.ls(type="camera"):
        if c != forma:
            cmds.setAttr(c + ".renderable", 0)
    return cam, forma


def luces(cmds):
    cmds.loadPlugin("mtoa", quiet=True)
    import mtoa.core as core
    core.createOptions()
    cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
    cielo = cmds.shadingNode("aiSkyDomeLight", asLight=True, name="cielo")
    cmds.setAttr(cielo + ".intensity", 0.6)
    sol = cmds.directionalLight(name="sol", intensity=2.5)
    sol_t = cmds.listRelatives(sol, parent=True)[0]
    cmds.xform(sol_t, worldSpace=True, rotation=(-50, 30, 0))
    try:
        cmds.setAttr(sol + ".aiAngle", 2.0)
    except Exception:
        pass
    cmds.setAttr("defaultArnoldRenderOptions.AASamples", 5)
    cmds.setAttr("defaultArnoldRenderOptions.GIDiffuseSamples", 2)
    cmds.setAttr("defaultResolution.width", 1280)
    cmds.setAttr("defaultResolution.height", 720)
    cmds.setAttr("defaultResolution.deviceAspectRatio", 1280 / 720.0)


def renderizar(cmds, camara, png):
    """Exporta la escena a .ass y la renderiza con kick (sin interfaz)."""
    ass = os.path.splitext(png)[0] + ".ass"
    cmds.arnoldExportAss(filename=ass, cam=camara, mask=255, lightLinks=True, shadowLinks=True)
    raiz_mtoa = os.path.dirname(os.path.dirname(cmds.pluginInfo("mtoa", query=True, path=True)))
    for posible in (raiz_mtoa, os.path.dirname(raiz_mtoa), os.path.dirname(os.path.dirname(raiz_mtoa))):
        kick = os.path.join(posible, "bin", "kick" + (".exe" if os.name == "nt" else ""))
        if os.path.exists(kick):
            break
    else:
        raise RuntimeError("no encuentro kick junto a mtoa ({})".format(raiz_mtoa))
    sombras = os.path.join(os.path.dirname(kick), "..", "shaders")
    limpiar_ass(ass)
    exr = os.path.splitext(png)[0] + ".exr"
    # -sl: sin licencia (marca de agua), suficiente para comparar versiones.
    orden = [kick, "-i", ass, "-o", exr, "-r", "1280", "720", "-dw", "-dp", "-sl", "-v", "1", "-l", sombras]
    print(" ".join(orden))
    t = time.time()
    subprocess.check_call(orden)
    print("Render en {:.0f} s".format(time.time() - t))
    a_png(os.path.dirname(kick), exr, png)
    print("Imagen:", png)


def limpiar_ass(ass):
    """Quita el denoiser de la salida: sin licencia, kick no lo carga."""
    with open(ass) as f:
        lineas = f.readlines()
    limpias = [l for l in lineas if "defaultArnoldDenoiser" not in l]
    if len(limpias) != len(lineas):
        with open(ass, "w") as f:
            f.writelines(limpias)


def a_png(bin_arnold, exr, png):
    """Convierte el EXR lineal a PNG sRGB con oiiotool (viene con Arnold)."""
    oiio = os.path.join(bin_arnold, "oiiotool" + (".exe" if os.name == "nt" else ""))
    if os.path.exists(oiio):
        subprocess.check_call([oiio, exr, "--ch", "R,G,B", "--colorconvert", "linear", "sRGB", "-o", png])
        return
    print("Sin oiiotool: queda solo el EXR", exr)


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    carpeta = sys.argv[1]
    nombre = sys.argv[2] if len(sys.argv) > 2 else "referencia"
    os.makedirs(carpeta, exist_ok=True)
    cmds.loadPlugin(os.path.join(RAIZ, "plug-ins", "pipeeditor_plugin.py"))
    from pipeeditor import escena
    import pipeeditor
    print("PipeEditor", pipeeditor.__version__, "desde", RAIZ)
    t = time.time()
    camara, _forma = construir_escena(cmds, escena)
    luces(cmds)
    print("Escena construida en {:.1f} s".format(time.time() - t))
    ma = os.path.join(carpeta, nombre + ".ma")
    cmds.file(rename=ma)
    cmds.file(save=True, type="mayaAscii", force=True)
    renderizar(cmds, camara, os.path.join(carpeta, nombre + ".png"))
    return 0


if __name__ == "__main__":
    codigo = 2
    try:
        codigo = main()
    except Exception:
        traceback.print_exc()
        print("RESULTADO: ERROR")
    finally:
        sys.stdout.flush()
        try:
            import maya.standalone
            maya.standalone.uninitialize()
        except Exception:
            pass
        os._exit(codigo)
