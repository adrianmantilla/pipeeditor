"""Utilidades de las pruebas: ruta de los scripts y comprobación de mallas."""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(RAIZ, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def comprobar_malla(prueba, m, cerrada=False):
    """Índices dentro de rango, caras sin vértices repetidos y aristas con 1 o 2 caras."""
    nv, nuv = len(m.vertices), len(m.uvs)
    prueba.assertEqual(len(m.caras), len(m.caras_uv))
    aristas = {}
    for cara, cara_uv in zip(m.caras, m.caras_uv):
        prueba.assertEqual(len(cara), len(cara_uv))
        prueba.assertGreaterEqual(len(cara), 3)
        prueba.assertEqual(len(set(cara)), len(cara))
        for i in cara:
            prueba.assertTrue(0 <= i < nv)
        for i in cara_uv:
            prueba.assertTrue(0 <= i < nuv)
        for a, b in zip(cara, cara[1:] + cara[:1]):
            clave = (min(a, b), max(a, b))
            aristas.setdefault(clave, []).append((a, b))
    for clave, usos in aristas.items():
        prueba.assertLessEqual(len(usos), 2, "arista con más de dos caras")
        if len(usos) == 2:
            prueba.assertNotEqual(usos[0], usos[1], "caras vecinas con orientación opuesta")
    for p in m.vertices:
        for c in p:
            prueba.assertTrue(c == c and abs(c) < 1e9, "coordenada no válida")
