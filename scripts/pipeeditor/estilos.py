"""«Mis estilos» y los últimos ajustes usados, guardados en JSON. Sin Maya.

Un estilo es una combinación de ajustes (tipo, perfil, grosor, material,
conectores...) con un nombre, para reutilizarla en otras escenas.
"""

import json
import os

from pipeeditor import construir

# Estilos que vienen de serie: se ven en la lista pero no se pueden borrar.
DE_SERIE = {
    "Cable de lámpara": {"tipo": "cable", "perfil_cable": "doble", "grosor": 0.6, "holgura": 0.15,
                         "conector_inicio": "clavija", "material_cuerpo": "pvc_blanco",
                         "material_piezas": "pvc_blanco", "material_metal": "laton", "rigidez": 0.15},
    "Tendido eléctrico": {"tipo": "cable", "perfil_cable": "redondo", "grosor": 2.5, "holgura": 0.04,
                          "salida": 0.0, "material_cuerpo": "goma_negra", "rigidez": 0.6},
    "Cuerda de puerto": {"tipo": "cable", "perfil_cable": "trenzado", "grosor": 4.0, "holgura": 0.2,
                         "lados": 8, "conector_fin": "grillete", "material_cuerpo": "canamo",
                         "material_piezas": "oxido", "material_metal": "oxido", "rigidez": 0.1,
                         "ondulacion": 0.2},
    "Manguera de jardín": {"tipo": "cable", "perfil_cable": "corrugado", "grosor": 2.5, "holgura": 0.3,
                           "material_cuerpo": "manguera_naranja", "rigidez": 0.4, "ondulacion": 0.5},
    "Mazo de cables": {"tipo": "cable", "perfil_cable": "redondo", "grosor": 0.8, "haz": 7, "torsion": 0.5,
                       "separacion_bridas_haz": 25.0, "holgura": 0.1, "material_cuerpo": "goma_negra"},
    "Teléfono antiguo": {"tipo": "cable", "perfil_cable": "espiral", "grosor": 1.2, "holgura": 0.25,
                         "material_cuerpo": "plastico_negro"},
    "Fontanería de cobre": {"tipo": "tuberia", "perfil_tuberia": "redonda", "grosor": 2.2, "radio_codo": 1.5,
                            "norma": "cobre", "codo": "pieza", "material_cuerpo": "cobre",
                            "material_piezas": "cobre", "material_metal": "laton", "soportes_auto": True},
    "Tubería industrial": {"tipo": "tuberia", "perfil_tuberia": "redonda", "grosor": 16.83, "radio_codo": 1.5,
                           "norma": "acero", "codo": "soldado", "separacion_bridas": 600.0, "soportes_auto": True,
                           "extremos": "brida", "material_cuerpo": "hierro_pintado",
                           "material_piezas": "hierro_pintado", "material_metal": "acero_galvanizado"},
    "Conducto de ventilación": {"tipo": "tuberia", "perfil_tuberia": "cuadrada", "grosor": 30.0,
                                "radio_codo": 0.6, "separacion_soportes": 150.0,
                                "material_cuerpo": "acero_galvanizado", "material_piezas": "acero"},
    "Tubo flexible": {"tipo": "tuberia", "perfil_tuberia": "corrugada", "grosor": 5.0, "recorrido": "libre",
                      "material_cuerpo": "aluminio", "material_piezas": "acero"},
}

TUBERIA_POR_DEFECTO = {"grosor": 6.0, "lados": 16, "salida": 6.0}

CLAVES_VALIDAS = set(construir.POR_DEFECTO) | {"material_cuerpo", "material_piezas", "material_metal"}


def limpiar(ajustes):
    return {k: v for k, v in ajustes.items() if k in CLAVES_VALIDAS}


class Estilos(object):
    def __init__(self, carpeta):
        self.carpeta = carpeta
        self.ruta = os.path.join(carpeta, "estilos.json")
        self.ruta_ultimos = os.path.join(carpeta, "ultimos.json")

    def _leer(self, ruta):
        try:
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)
            return datos if isinstance(datos, dict) else {}
        except (OSError, ValueError):
            return {}

    def _escribir(self, ruta, datos):
        os.makedirs(self.carpeta, exist_ok=True)
        temporal = ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(temporal, ruta)

    def propios(self):
        return self._leer(self.ruta)

    def nombres(self, tipo=None):
        """De serie primero y luego los propios, filtrados por tipo si se pide."""
        todos = list(DE_SERIE.items()) + sorted(self.propios().items())
        return [n for n, a in todos if tipo is None or a.get("tipo", "cable") == tipo]

    def es_de_serie(self, nombre):
        return nombre in DE_SERIE and nombre not in self.propios()

    def cargar(self, nombre):
        propios = self.propios()
        if nombre in propios:
            return dict(propios[nombre])
        return dict(DE_SERIE.get(nombre, {}))

    def guardar(self, nombre, ajustes):
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("nombre vacío")
        datos = self.propios()
        datos[nombre] = limpiar(ajustes)
        self._escribir(self.ruta, datos)

    def borrar(self, nombre):
        datos = self.propios()
        if nombre in datos:
            del datos[nombre]
            self._escribir(self.ruta, datos)
            return True
        return False

    # --- últimos ajustes usados, por tipo ---------------------------------------------
    def ultimos(self, tipo):
        base = construir.ajustes(tipo=tipo)
        if tipo == "tuberia":
            base.update(TUBERIA_POR_DEFECTO)
        base.update(limpiar(self._leer(self.ruta_ultimos).get(tipo, {})))
        base["tipo"] = tipo
        return base

    def recordar(self, ajustes):
        datos = self._leer(self.ruta_ultimos)
        datos[ajustes.get("tipo", "cable")] = limpiar(ajustes)
        try:
            self._escribir(self.ruta_ultimos, datos)
        except OSError:
            pass
