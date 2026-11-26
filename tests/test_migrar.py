"""Escenas de versiones anteriores salen igual que entonces."""

import unittest

import comun  # noqa: F401

from pipeeditor import construir as c


class Migrar(unittest.TestCase):
    def test_version_0_sin_reposo_y_en_z(self):
        a = c.migrar(c.ajustes(), 0)
        self.assertFalse(a["reposo"])
        self.assertEqual(a["recorrido"], "z")

    def test_version_actual_no_cambia(self):
        base = c.ajustes()
        self.assertEqual(c.migrar(base, c.VERSION_DATOS), base)

    def test_respeta_lo_elegido(self):
        a = c.migrar(c.ajustes(recorrido="esquivar"), 0)
        self.assertEqual(a["recorrido"], "esquivar")

    def test_no_modifica_el_original(self):
        base = c.ajustes()
        c.migrar(base, 0)
        self.assertTrue(base["reposo"])
