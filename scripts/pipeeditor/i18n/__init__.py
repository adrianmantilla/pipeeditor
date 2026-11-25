"""Textos de la interfaz, separados del código para poder traducirlos.

Cada idioma es un archivo JSON en esta carpeta (``es.json``, ``en.json``...).
Si falta una clave en el idioma elegido, se usa el español.
El idioma se elige en el menú PipeEditor > Idioma (se guarda en las
preferencias de Maya) o con la variable de entorno ``PIPEEDITOR_IDIOMA``,
que manda sobre el menú.
"""

import json
import os

_CARPETA = os.path.dirname(os.path.abspath(__file__))
IDIOMA_BASE = "es"
_cache = {}
_idioma = os.environ.get("PIPEEDITOR_IDIOMA", IDIOMA_BASE)


def _cargar(idioma):
    if idioma not in _cache:
        ruta = os.path.join(_CARPETA, idioma + ".json")
        try:
            with open(ruta, encoding="utf-8") as f:
                _cache[idioma] = json.load(f)
        except (OSError, ValueError):
            _cache[idioma] = {}
    return _cache[idioma]


def idiomas():
    """Idiomas disponibles (los archivos JSON de esta carpeta)."""
    return sorted(os.path.splitext(n)[0] for n in os.listdir(_CARPETA) if n.endswith(".json"))


def idioma():
    return _idioma


def por_entorno():
    return bool(os.environ.get("PIPEEDITOR_IDIOMA"))


def usar_idioma(idioma):
    global _idioma
    _idioma = idioma


def claves(idioma=IDIOMA_BASE):
    return set(_cargar(idioma))


def t(clave, **valores):
    """Devuelve el texto de ``clave`` en el idioma activo, con ``valores`` sustituidos."""
    texto = _cargar(_idioma).get(clave) or _cargar(IDIOMA_BASE).get(clave) or clave
    try:
        return texto.format(**valores)
    except (KeyError, IndexError):
        return texto
