# Guía rápida de PipeEditor

## Un cable entre dos objetos en 30 segundos

1. Menú **PipeEditor → Abrir PipeEditor…** y deja la ventana a un lado.
2. Pulsa **Cables** arriba.
3. Selecciona dos objetos (o dos caras, o dos vértices) y pulsa **Entre los seleccionados**.
4. Mueve la **Holgura**: el cable cuelga más o menos.
5. Mueve uno de los objetos: el cable le sigue.

## Dibujar con clics

1. Pulsa **Clic en el visor**.
2. Haz clic sobre una superficie y luego sobre otra: sale el primer tramo.
3. Cada clic más añade otro punto. **Ctrl+clic** empieza un cable nuevo. **Ctrl+Z** quita el último punto.
4. Pulsa **Q** para volver a la herramienta de selección.

Los puntos son localizadores amarillos. Si «Pegar los extremos a los objetos» está marcado, cuelgan del objeto donde hiciste clic.

## Una tubería por una pared

1. Pulsa **Tuberías** arriba.
2. Haz clic en la pared donde empieza y donde acaba. La tubería sale recta de la pared y va en ángulo recto.
3. En **Recorrido**, *Junto a las superficies* va pegada a la pared y al suelo. *Esquivando objetos* rodea lo que elijas como apoyo (por ejemplo, un pilar) sin separarse de la pared.
4. En **Medidas** elige *Acero* o *Cobre* para que el grosor sea una medida comercial.
5. Marca **Separación según el diámetro** para los soportes.
6. Selecciona la tubería y la pared y pulsa **Apoyar en los objetos seleccionados**: las abrazaderas se estiran hasta la pared.
7. Para varias en paralelo, sube **Tuberías en paralelo**.

8. **Válvulas y tes**: selecciona un anclaje de la tubería (con **Insertar punto** añades uno) y elige en **Accesorio en el punto**. Para una rama, selecciona el anclaje y después adónde va, y pulsa **Derivar (te)**.
9. **Desagüe**: sube la **Pendiente** (1 a 2 %). Baja desde el primer anclaje hacia el último.
10. **Lista de materiales**: menú **PipeEditor → Lista de materiales (CSV)…**.

También puedes seleccionar una fila de aristas de un modelo (por ejemplo, el borde de un tejado) y pulsar **Desde aristas**.

## Un cable que se asienta

1. Selecciona el cable y los objetos sobre los que cae (mesa, suelo, cajas) y pulsa **Apoyar en los objetos seleccionados**.
2. Con **Reposo físico** marcado (viene así), el cable se tumba encima, cae por los bordes y no atraviesa nada.
3. **Rigidez**: baja para un cable de lámpara blando, sube para una manguera gruesa.
4. **Ondulación** le da memoria de bobina; **Semilla** prueba otra variante con la misma forma general.
5. **Un cable encima de otro**: selecciona el de arriba, después el de abajo, y pulsa **Apoyar en los objetos seleccionados**.
6. Para que el cable pase por un punto sin atarse (un clavo, una argolla), selecciona ese anclaje y pulsa **Gancho**.

## Trucos

- **Varios a la vez**: selecciona varios cables y cambia un ajuste; cambia en todos.
- **Un tramo más flojo**: selecciona su anclaje y sube *Holgura de este tramo* en el Channel Box.
- **Para animar**: pon *Al mover un extremo* en **Longitud fija**; al separar los extremos el cable se tensa.
- **Viento**: sube *Viento* en *Reposo y naturalidad* y dale a reproducir: los cables que cuelgan se balancean.
- **Guirnalda o cadena**: elige el estilo *Guirnalda de luces* o *Cadena*. Con *Luz cálida* en las piezas metálicas, PipeEditor añade una luz de malla de Arnold (`cable_NN_luz`) para que las bombillas iluminen la escena; su exposición se ajusta en el Attribute Editor de esa luz.
- **Cientos de cables**: selecciónalos y pulsa **Render como curva**; Arnold los pinta como curvas y la escena pesa mucho menos.
- **Muchos cables entre dos paneles**: selecciona varias caras de un objeto y varias del otro y pulsa **Entre dos grupos**. Para que sea un mazo, usa *Cables en el haz*.
- **Tu propio conector**: modela una pieza con el eje Y hacia donde sale el cable, selecciona el cable y la pieza y pulsa **Usar el objeto seleccionado como conector**.
- **Escena pesada**: cuando un cable esté como quieres, pulsa **Asentar y fijar**. Deja de calcularse y la escena va más ligera.
- **Estilos**: cuando tengas una combinación que te guste, pulsa **Guardar** junto a *Estilo*.

## Antes de entregar o compartir una escena

Para llevar los cables a otro programa, usa **PipeEditor → Exportar horneado (USD, FBX u OBJ)…**.


Para mandarla a render a otro ordenador, usa **PipeEditor → Guardar una copia horneada…**: guarda una copia con todo convertido en mallas normales y tu escena sigue igual, editable.

Si prefieres convertir la tuya, usa **PipeEditor → Hornear todos los de la escena**. Los cables pasan a ser mallas normales de Maya y la escena se abre en cualquier ordenador, tenga o no PipeEditor. Después ya no se pueden editar con la ventana, así que guarda antes una copia si quieres seguir cambiándolos.
