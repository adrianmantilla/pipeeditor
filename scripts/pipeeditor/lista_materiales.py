"""Lista de materiales (sin Maya): metros de tubo y de cable, codos, bridas, válvulas...

Cada nodo da su ``recuento`` (ver ``construir.Resultado.contar``) y aquí se
suman por concepto, medida y material para guardarlos en un CSV que se abre
en una hoja de cálculo.
"""

import csv
import io

from pipeeditor.i18n import t

# Conceptos que se cuentan en piezas (el resto son metros).
_PIEZAS = ("codos", "bridas", "manguitos", "soportes", "tapones", "reducciones", "tes", "valvulas_bola",
           "valvulas_compuerta", "bridas_haz")


def filas(elementos):
    """Filas sumadas de la lista de materiales.

    ``elementos``: lista de (nombre, ajustes, recuento). Devuelve una lista de
    diccionarios con concepto, medida, norma, material, cantidad, unidad y
    elementos (nombres separados por comas), ordenada por concepto y medida.
    """
    suma = {}
    for nombre, ajustes, recuento in elementos:
        tipo = ajustes.get("tipo", "cable")
        norma = ajustes.get("norma", "libre") if tipo == "tuberia" else ""
        grosor = float(ajustes.get("grosor", 0.0))
        for clave, cantidad in sorted(recuento.items()):
            if not cantidad:
                continue
            base, _sep, medida = clave.partition("_")
            if base in ("tubo", "cable", "codos") and medida:
                concepto, medida = base, float(medida)
            else:
                concepto, medida = clave, grosor
            material = ajustes.get("material_metal" if concepto in ("soportes", "valvulas_bola",
                                                                    "valvulas_compuerta") else
                                   "material_cuerpo" if concepto in ("tubo", "cable") else "material_piezas", "")
            llave = (concepto, round(medida, 2), norma if concepto in ("tubo", "codos") else "", material or "")
            fila = suma.setdefault(llave, {"cantidad": 0.0, "elementos": []})
            fila["cantidad"] += cantidad
            if nombre not in fila["elementos"]:
                fila["elementos"].append(nombre)
    salida = []
    for (concepto, medida, norma, material), datos in sorted(suma.items()):
        metros = concepto in ("tubo", "cable")
        salida.append({
            "concepto": concepto,
            "medida": medida,
            "norma": norma,
            "material": material,
            "cantidad": round(datos["cantidad"] / 100.0, 2) if metros else int(round(datos["cantidad"])),
            "unidad": "m" if metros else "ud",
            "elementos": datos["elementos"],
        })
    return salida


def _nombre_concepto(concepto):
    if concepto.startswith("conector_"):
        return t("bom_conector", tipo=t("opcion_conector_" + concepto[9:]))
    if concepto.startswith("pieza_"):
        return t("opcion_pieza_" + concepto[6:])
    return t("bom_" + concepto)


def a_csv(filas_, decimal=None):
    """Texto CSV (separado por punto y coma) con una fila de títulos."""
    decimal = decimal or t("bom_decimal")

    def numero(x):
        texto = ("{:.2f}".format(x) if isinstance(x, float) else str(x))
        return texto.replace(".", decimal)

    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\n")
    escritor.writerow([t("bom_col_concepto"), t("bom_col_medida"), t("bom_col_norma"), t("bom_col_material"),
                       t("bom_col_cantidad"), t("bom_col_unidad"), t("bom_col_elementos")])
    for f in filas_:
        escritor.writerow([
            _nombre_concepto(f["concepto"]),
            numero(f["medida"]) + " cm",
            t("opcion_norma_" + f["norma"]) if f["norma"] else "",
            t("material_" + f["material"]) if f["material"] else "",
            numero(f["cantidad"]),
            f["unidad"],
            ", ".join(f["elementos"]),
        ])
    return salida.getvalue()
