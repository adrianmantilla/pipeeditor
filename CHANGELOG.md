# Cambios

Las escenas guardadas con una versión anterior se abren igual que se hicieron: PipeEditor guarda en cada nodo la versión de sus datos y, al abrir, mantiene los valores con los que se crearon.

## 1.3.0

### Tuberías de instalación
- **Accesorios en los anclajes** (Editar > Accesorio en el punto): válvula de bola, válvula de compuerta, te y reducción. Una reducción intermedia hace que la tubería siga con la medida siguiente más pequeña; en un extremo deja la salida más fina.
- **Derivar (te)**: selecciona un anclaje de la tubería y adónde va la rama; pone la te y crea la otra tubería, que se mueve con ese anclaje.
- **Pendiente** para desagües: los tramos horizontales bajan hacia el último anclaje y la bajante lo compensa.
- **Soportes hacia** la superficie más cercana, **colgados del techo** con varilla o **apoyados en el suelo**.
- **Señales**: flechas de sentido y bandas de color.
- **Normas** nuevas: PVC a presión (EN 1452), PVC de desagüe (EN 1329), multicapa (PEX-AL-PEX) y acero ANSI Schedule 40.
- **Esquivar la forma real**: con «Esquivando objetos», una mesa cuenta como tablero y patas, no como una caja entera; la tubería puede pasar por debajo.

### Lista de materiales
- **PipeEditor > Lista de materiales (CSV)…**: metros de tubo y de cable por diámetro, norma y material; codos, bridas, soportes, válvulas, tes, reducciones, tapones y conectores. Se abre en Excel o LibreOffice.

## 1.2.0

### Para escenas grandes
- **Asentar y fijar** (botón en Editar): guarda la forma del cable y deja de calcularla. No cambia al mover los apoyos ni al abrir la escena; si se mueve un extremo, la forma se estira hasta él. Vuelve a pulsar para soltarlo.
- **Caché**: cambiar el perfil, los lados, las piezas o la resolución no vuelve a calcular el reposo.
- **Modo borrador**: mientras arrastras un anclaje con el ratón, el reposo es más corto; al soltar se calcula entero.

### Render en otro ordenador
- **Guardar una copia horneada…** (menú PipeEditor): guarda una copia de la escena con todo horneado, que se abre en cualquier Maya sin PipeEditor (granjas de render). La escena abierta no cambia. También como orden para un atajo y desde Python: `pipeeditor.interfaz_maya.copia_horneada(ruta)`.

### Idiomas
- **Inglés**: menú PipeEditor > Idioma. Se recuerda entre sesiones; la variable `PIPEEDITOR_IDIOMA` manda sobre el menú.

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
