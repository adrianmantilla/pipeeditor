"""La ventana con un servicio falso (sin Maya). Se salta si no hay PySide."""

import os
import shutil
import tempfile
import unittest

import comun  # noqa: F401

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from pipeeditor.qt import QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None

from pipeeditor import construir
from pipeeditor.estilos import Estilos


class ServicioFalso(object):
    def __init__(self, carpeta):
        self.estilos = Estilos(carpeta)
        self.nodos = {}
        self.sel = []
        self.llamadas = []

    def ultimos(self, tipo):
        return self.estilos.ultimos(tipo)

    def recordar(self, ajustes):
        self.estilos.recordar(ajustes)

    def seleccion(self):
        return list(self.sel)

    def leer(self, n):
        return dict(self.nodos[n])

    def informacion(self, nodos):
        return {"longitud": 450.0, "caida": 30.0, "triangulos": 1234, "tensos": 0}

    def escribir(self, nodos, ajustes):
        for n in nodos:
            self.nodos[n].update(ajustes)
        self.llamadas.append(("escribir", tuple(nodos), dict(ajustes)))

    def material(self, nodos, parte, nombre):
        for n in nodos:
            self.nodos[n]["material_" + parte] = nombre

    def fijar_longitudes(self, nodos):
        self.llamadas.append(("fijar", tuple(nodos)))
        for n in nodos:
            self.nodos[n]["modo_tension"] = "longitud"

    def crear_seleccion(self, ajustes, pegar):
        n = "cable_{:02d}".format(len(self.nodos) + 1)
        self.nodos[n] = dict(ajustes)
        self.sel = [n]
        return "creado " + n

    def crear_clic(self, obtener, pegar):
        self.llamadas.append(("clic", obtener()["tipo"], pegar()))

    def crear_grupos(self, ajustes, pegar):
        raise ValueError("faltan grupos")

    def crear_aristas(self, ajustes):
        return None

    def crear_curva(self, ajustes):
        return None

    def __getattr__(self, nombre):  # insertar_punto, hornear, etc.
        def accion(*_a):
            self.llamadas.append((nombre,))
            return None
        return accion


@unittest.skipIf(QtWidgets is None, "sin PySide")
class Ventana(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from pipeeditor.ventana import VentanaPipeEditor
        self.carpeta = tempfile.mkdtemp()
        self.s = ServicioFalso(self.carpeta)
        self.v = VentanaPipeEditor(self.s)

    def tearDown(self):
        self.v.close()
        self.v.deleteLater()
        shutil.rmtree(self.carpeta)

    def test_empieza_en_cables(self):
        self.assertEqual(self.v.tipo, "cable")
        self.assertFalse(self.v.filas["perfil_tuberia"][1].isVisibleTo(self.v))
        self.assertTrue(self.v.filas["perfil_cable"][1].isVisibleTo(self.v))

    def test_cambiar_a_tuberias(self):
        self.v.cambiar_tipo("tuberia")
        self.assertTrue(self.v.filas["perfil_tuberia"][1].isVisibleTo(self.v))
        self.assertFalse(self.v.secciones["haz"].isVisibleTo(self.v))
        self.assertEqual(self.v.valor("grosor"), 6.0)
        self.assertEqual(self.v.ajustes_actuales()["tipo"], "tuberia")

    def test_cambio_sin_seleccion_se_recuerda(self):
        self.v.poner_valor("grosor", 4.5)
        self.v._cambio("grosor")
        self.assertEqual(self.s.ultimos("cable")["grosor"], 4.5)

    def test_crear_y_editar(self):
        self.v._crear_seleccion()
        self.assertEqual(self.v.editando, ["cable_01"])
        self.v.poner_valor("holgura", 0.3)
        self.v._cambio("holgura")
        self.assertEqual(self.s.nodos["cable_01"]["holgura"], 0.3)
        self.assertIn("1.234", self.v.estado.text())

    def test_longitud_fija(self):
        self.v._crear_seleccion()
        self.v.poner_valor("modo_tension", "longitud")
        self.v._cambio("modo_tension")
        self.assertIn(("fijar", ("cable_01",)), self.s.llamadas)
        self.assertFalse(self.v.controles["holgura"][0].isEnabled())

    def test_error_se_muestra(self):
        self.v._crear_grupos()
        self.assertIn("faltan grupos", self.v.estado.text())

    def test_estilo_de_serie(self):
        i = self.v.lista_estilos.findData("Cable de lámpara")
        self.assertGreater(i, 0)
        self.v._aplicar_estilo(i)
        self.assertEqual(self.v.valor("perfil_cable"), "doble")
        self.assertEqual(self.v.material_cuerpo.currentData(), "pvc_blanco")

    def test_estilo_de_tuberia_cambia_de_tipo(self):
        self.v.cambiar_tipo("tuberia")
        i = self.v.lista_estilos.findData("Conducto de ventilación")
        self.v._aplicar_estilo(i)
        self.assertEqual(self.v.tipo, "tuberia")
        self.assertEqual(self.v.valor("perfil_tuberia"), "cuadrada")

    def test_clic_usa_ajustes_vivos(self):
        self.v._crear_clic()
        self.assertEqual(self.s.llamadas[-1], ("clic", "cable", True))

    def test_editar_desactivado_sin_seleccion(self):
        self.assertFalse(self.v.botones_editar["hornear"].isEnabled())
        self.v._crear_seleccion()
        self.assertTrue(self.v.botones_editar["hornear"].isEnabled())

    def test_todos_los_campos_tienen_valor(self):
        a = self.v.ajustes_actuales()
        for clave in construir.POR_DEFECTO:
            self.assertIn(clave, a)


if __name__ == "__main__":
    unittest.main()
