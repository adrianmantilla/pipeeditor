# Cambios

Las escenas guardadas con una versión anterior se abren igual que se hicieron: PipeEditor guarda en cada nodo la versión de sus datos y, al abrir, mantiene los valores con los que se crearon.

## 1.1.0

### Cables
- **Reposo físico**: si el cable toca el suelo o un objeto de apoyo, se asienta de verdad. Se tumba en el suelo con pocas curvas amplias, no atraviesa mesas ni postes, cae por el borde de una mesa si un extremo está encima y conserva su longitud. Sin contactos sigue siendo la catenaria exacta.
- **Rigidez, ondulación y semilla**: cuánto se deja doblar el cable, la memoria de bobina y otra variante con la misma forma general.
- **Ganchos**: puntos por los que el cable pasa deslizando, sin atarse.
- **Haz suelto**: los cables de un haz sin bridas cuelgan cada uno por su cuenta, sin atravesarse (variación de longitud entre ellos).
- **Perfiles**: el cable de lámpara es un ocho de una sola funda y la cuerda tiene tres cabos con sus fibras.
- **Conectores** nuevos: aislador de porcelana. El grillete tiene orejeta y guardacabos.
- Eje Z arriba.

### Tuberías
- **Medidas normalizadas**: acero (DN) y cobre (EN 1057).
- **Codos** de radio largo (1,5 diámetros) y soldados con cordón.
- **Recorrido «Junto a las superficies»** (nuevo, por defecto): de una pared al suelo baja por la pared y sigue por el suelo. **«Esquivando objetos»** rodea solo el obstáculo, sin separarse de la pared.
- **Tuberías en paralelo** (rack), apiladas a lo largo de la pared.
- **Soportes** a tamaño real (abrazadera, varilla, tuerca y placa) y separación según el diámetro.

### Mallas y materiales
- Mallas cerradas con aristas duras y pliegue para subdividir, UV a escala real (1 unidad = 10 cm) y anillos según la curvatura.
- Las piezas de metal van en su propia malla, con su material.

### Otros
- Aviso en la ventana si el Maya no trae numpy (sin reposo físico).
- `herramientas/render_referencia.py`: la misma escena con Arnold para comparar versiones.

## 1.0.0

Primera versión: cables con catenaria, tuberías en ángulo recto, conectores, perfiles, haces, estilos, materiales para Arnold y horneado.
