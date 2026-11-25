"""Lista de materiales de PipeEditor (sin Maya): colores y cuáles se ofrecen para cada cosa."""

# nombre: (color base, metal, rugosidad, brillo de capa)
MATERIALES = {
    "goma_negra": ((0.025, 0.025, 0.027), 0.0, 0.55, 0.0),
    "pvc_blanco": ((0.78, 0.78, 0.76), 0.0, 0.35, 0.0),
    "pvc_rojo": ((0.55, 0.04, 0.03), 0.0, 0.35, 0.0),
    "pvc_amarillo": ((0.75, 0.55, 0.03), 0.0, 0.35, 0.0),
    "nailon_azul": ((0.03, 0.12, 0.45), 0.0, 0.45, 0.0),
    "canamo": ((0.42, 0.32, 0.18), 0.0, 0.85, 0.0),
    "manguera_naranja": ((0.75, 0.22, 0.03), 0.0, 0.4, 0.0),
    "cobre": ((0.93, 0.55, 0.38), 1.0, 0.32, 0.0),
    "acero": ((0.62, 0.62, 0.64), 1.0, 0.35, 0.0),
    "acero_galvanizado": ((0.72, 0.73, 0.74), 1.0, 0.5, 0.0),
    "oxido": ((0.33, 0.13, 0.05), 0.15, 0.85, 0.0),
    "hierro_pintado": ((0.12, 0.25, 0.18), 0.0, 0.72, 0.0),
    "pvc_gris": ((0.35, 0.36, 0.37), 0.0, 0.4, 0.0),
    "aluminio": ((0.85, 0.86, 0.88), 1.0, 0.28, 0.0),
    "plastico_negro": ((0.03, 0.03, 0.03), 0.0, 0.3, 0.0),
    "laton": ((0.91, 0.71, 0.38), 1.0, 0.3, 0.0),
}
# Partes de cada cable o tubería con su propio material.
PARTES = ("cuerpo", "piezas", "metal")
# material por defecto de cada parte (cuerpo, piezas, metal)
POR_TIPO = {
    "cable": ("goma_negra", "plastico_negro", "acero"),
    "tuberia": ("cobre", "acero", "acero_galvanizado"),
}
CABLE = ("goma_negra", "pvc_blanco", "pvc_rojo", "pvc_amarillo", "nailon_azul", "canamo", "manguera_naranja",
         "cobre", "acero")
TUBERIA = ("cobre", "pvc_gris", "pvc_blanco", "hierro_pintado", "acero_galvanizado", "aluminio", "oxido",
           "acero")
PIEZAS = ("plastico_negro", "acero", "acero_galvanizado", "cobre", "oxido", "pvc_blanco")
METAL = ("acero", "acero_galvanizado", "laton", "cobre", "aluminio", "oxido")
LISTA = {"piezas": PIEZAS, "metal": METAL}
