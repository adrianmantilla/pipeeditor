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
3. En **Recorrido** elige *En Z*, *En L* o *En línea recta*.
4. Pon **Bridas cada** 100 cm y **Soportes cada** 80 cm.
5. Selecciona la tubería y la pared y pulsa **Paredes para los soportes**: las abrazaderas se estiran hasta la pared.

También puedes seleccionar una fila de aristas de un modelo (por ejemplo, el borde de un tejado) y pulsar **Desde aristas**.

## Trucos

- **Varios a la vez**: selecciona varios cables y cambia un ajuste; cambia en todos.
- **Un tramo más flojo**: selecciona su anclaje y sube *Holgura de este tramo* en el Channel Box.
- **Para animar**: pon *Al mover un extremo* en **Longitud fija**; al separar los extremos el cable se tensa.
- **Muchos cables entre dos paneles**: selecciona varias caras de un objeto y varias del otro y pulsa **Entre dos grupos**. Para que sea un mazo, usa *Cables en el haz*.
- **Tu propio conector**: modela una pieza con el eje Y hacia donde sale el cable, selecciona el cable y la pieza y pulsa **Usar el objeto seleccionado como conector**.
- **Estilos**: cuando tengas una combinación que te guste, pulsa **Guardar** junto a *Estilo*.

## Antes de entregar o compartir una escena

Usa **PipeEditor → Hornear todos los de la escena**. Los cables pasan a ser mallas normales de Maya y la escena se abre en cualquier ordenador, tenga o no PipeEditor. Después ya no se pueden editar con la ventana, así que guarda antes una copia si quieres seguir cambiándolos.
