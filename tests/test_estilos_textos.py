import json
import os
import re
import shutil
import tempfile
import unittest

import comun
from pipeeditor import construir, estilos, materiales_datos, perfiles, piezas
from pipeeditor.i18n import claves, t


class Estilos(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.e = estilos.Estilos(self.carpeta)

    def tearDown(self):
        shutil.rmtree(self.carpeta)

    def test_de_serie_validos(self):
        for nombre, a in estilos.DE_SERIE.items():
            self.assertTrue(set(a) <= estilos.CLAVES_VALIDAS, nombre)
            ajustes = construir.ajustes(**{k: v for k, v in a.items() if k in construir.POR_DEFECTO})
            if ajustes["tipo"] == "cable":
                self.assertIn(ajustes["perfil_cable"], perfiles.PERFILES_CABLE)
            else:
                self.assertIn(ajustes["perfil_tuberia"], perfiles.PERFILES_TUBERIA)
            for parte in ("material_cuerpo", "material_piezas", "material_metal"):
                if parte in a:
                    self.assertIn(a[parte], materiales_datos.MATERIALES)

    def test_guardar_cargar_borrar(self):
        self.e.guardar("Mío", {"tipo": "cable", "grosor": 3.0, "basura": 1})
        self.assertEqual(self.e.cargar("Mío"), {"tipo": "cable", "grosor": 3.0})
        self.assertIn("Mío", self.e.nombres("cable"))
        self.assertNotIn("Mío", self.e.nombres("tuberia"))
        self.assertTrue(self.e.borrar("Mío"))
        self.assertFalse(self.e.borrar("Cable de lámpara"))

    def test_ultimos(self):
        self.assertEqual(self.e.ultimos("tuberia")["grosor"], 6.0)
        self.e.recordar({"tipo": "cable", "grosor": 7.5})
        self.assertEqual(self.e.ultimos("cable")["grosor"], 7.5)

    def test_json_roto(self):
        with open(os.path.join(self.carpeta, "estilos.json"), "w") as f:
            f.write("{roto")
        self.assertEqual(self.e.propios(), {})


class Textos(unittest.TestCase):
    def test_claves_usadas_existen(self):
        carpeta = os.path.join(comun.SCRIPTS, "pipeeditor")
        usadas = set()
        for nombre in os.listdir(carpeta):
            if nombre.endswith(".py"):
                with open(os.path.join(carpeta, nombre), encoding="utf-8") as f:
                    usadas |= set(re.findall(r'\bt\("([a-z0-9_]+)"\s*[,)]', f.read()))
        with open(os.path.join(comun.SCRIPTS, "AEpipeEditorNodoTemplate.mel"), encoding="utf-8") as f:
            usadas |= set(re.findall(r'pipeEditorTexto\("([a-z0-9_]+)"\)', f.read()))
        from pipeeditor import ventana_campos
        for clave, control, opciones, _tipos, seccion in ventana_campos.CAMPOS:
            usadas |= {"campo_" + clave, "campo_" + clave + "_ayuda", "seccion_" + seccion}
            if control == "lista":
                for o in opciones:
                    prefijo = "opcion_conector_" if clave.startswith("conector") else "opcion_" + clave + "_"
                    usadas.add(prefijo + o)
        for s in ventana_campos.SECCIONES:
            usadas.add("seccion_" + s)
        for tipo in construir.TIPOS:
            usadas |= {"tipo_" + tipo, "nuevo_" + tipo}
        for n in materiales_datos.MATERIALES:
            usadas.add("material_" + n)
        for k in ("crear_clic", "crear_seleccion", "crear_grupos", "crear_aristas", "crear_curva",
                  "insertar_punto", "quitar_punto", "seleccionar_anclas", "seleccionar_cuerpo", "hornear",
                  "borrar"):
            usadas |= {k, k + "_ayuda"}
        usadas |= {"editando_uno", "editando_varios", "material_cuerpo", "material_piezas", "material_metal"}
        faltan = sorted(usadas - claves())
        self.assertEqual(faltan, [])

    def test_formato(self):
        self.assertEqual(t("creados_haz", n=3), "3 cables creados.")
        self.assertEqual(t("no_existe"), "no_existe")

    def test_json_valido(self):
        with open(os.path.join(comun.SCRIPTS, "pipeeditor", "i18n", "es.json"), encoding="utf-8") as f:
            datos = json.load(f)
        self.assertTrue(all(isinstance(v, str) and v for v in datos.values()))

    def test_listas_coinciden(self):
        self.assertIn("propio", piezas.CONECTORES)
        self.assertEqual(set(materiales_datos.POR_TIPO), set(construir.TIPOS))


if __name__ == "__main__":
    unittest.main()
