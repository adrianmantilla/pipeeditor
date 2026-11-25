"""Ventana de PipeEditor (Qt). No usa Maya directamente: habla con un «servicio».

El servicio (``interfaz_maya.ServicioMaya`` en Maya, uno falso en las pruebas)
crea, lee y cambia cables y tuberías. Si hay cables seleccionados, los cambios
de la ventana se les aplican al momento; si no, son los ajustes para los
siguientes que se creen.
"""

from pipeeditor import construir, ventana_campos
from pipeeditor import materiales_datos as materiales
from pipeeditor.i18n import t
from pipeeditor.qt import QtCore, QtWidgets

CAMPOS = ventana_campos.CAMPOS
SECCIONES = ventana_campos.SECCIONES


def _miles(n):
    return "{:,}".format(int(n)).replace(",", ".")


def _metros(cm):
    return "{:.2f} m".format(cm / 100.0).replace(".", ",")


class VentanaPipeEditor(QtWidgets.QWidget):
    def __init__(self, servicio, padre=None):
        QtWidgets.QWidget.__init__(self, padre)
        self.setObjectName("PipeEditorVentana")
        self.setWindowTitle("PipeEditor")
        self.servicio = servicio
        self.tipo = "cable"
        self.nuevos = {"cable": servicio.ultimos("cable"), "tuberia": servicio.ultimos("tuberia")}
        self.editando = []
        self._cargando = False
        self.controles = {}
        self.filas = {}
        self._construir()
        self.refrescar()

    # --- construcción -----------------------------------------------------------------
    def _construir(self):
        raiz = QtWidgets.QVBoxLayout(self)
        raiz.setContentsMargins(6, 6, 6, 6)
        raiz.setSpacing(6)

        tipos = QtWidgets.QHBoxLayout()
        tipos.setSpacing(0)
        self.botones_tipo = {}
        for tipo in construir.TIPOS:
            b = QtWidgets.QPushButton(t("tipo_" + tipo))
            b.setCheckable(True)
            b.setMinimumHeight(30)
            b.setStyleSheet("QPushButton:checked { background-color: #5285a6; color: white; font-weight: bold; }")
            b.clicked.connect(lambda _=False, tipo=tipo: self.cambiar_tipo(tipo))
            tipos.addWidget(b)
            self.botones_tipo[tipo] = b
        raiz.addLayout(tipos)

        crear = QtWidgets.QGroupBox(t("seccion_crear"))
        rejilla = QtWidgets.QGridLayout(crear)
        rejilla.setSpacing(4)
        self.botones_crear = {}
        for i, (clave, funcion) in enumerate((("crear_clic", self._crear_clic),
                                              ("crear_seleccion", self._crear_seleccion),
                                              ("crear_grupos", self._crear_grupos),
                                              ("crear_aristas", self._crear_aristas),
                                              ("crear_curva", self._crear_curva))):
            b = QtWidgets.QPushButton(t(clave))
            b.setToolTip(t(clave + "_ayuda"))
            b.clicked.connect(funcion)
            rejilla.addWidget(b, i // 2, i % 2)
            self.botones_crear[clave] = b
        self.pegar = QtWidgets.QCheckBox(t("pegar_objetos"))
        self.pegar.setToolTip(t("pegar_objetos_ayuda"))
        self.pegar.setChecked(True)
        rejilla.addWidget(self.pegar, 3, 0, 1, 2)
        raiz.addWidget(crear)

        estilo = QtWidgets.QHBoxLayout()
        estilo.addWidget(QtWidgets.QLabel(t("estilo")))
        self.lista_estilos = QtWidgets.QComboBox()
        self.lista_estilos.setMinimumContentsLength(14)
        self.lista_estilos.activated.connect(self._aplicar_estilo)
        estilo.addWidget(self.lista_estilos, 1)
        self.boton_guardar_estilo = QtWidgets.QPushButton(t("estilo_guardar"))
        self.boton_guardar_estilo.clicked.connect(self._guardar_estilo)
        estilo.addWidget(self.boton_guardar_estilo)
        self.boton_borrar_estilo = QtWidgets.QPushButton(t("estilo_borrar"))
        self.boton_borrar_estilo.clicked.connect(self._borrar_estilo)
        estilo.addWidget(self.boton_borrar_estilo)
        raiz.addLayout(estilo)

        self.cabecera = QtWidgets.QLabel()
        self.cabecera.setWordWrap(True)
        self.cabecera.setStyleSheet("font-weight: bold; padding: 2px 0;")
        raiz.addWidget(self.cabecera)

        desplazable = QtWidgets.QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QtWidgets.QFrame.NoFrame)
        contenido = QtWidgets.QWidget()
        columna = QtWidgets.QVBoxLayout(contenido)
        columna.setContentsMargins(0, 0, 0, 0)
        self.secciones = {}
        formularios = {}
        for s in SECCIONES:
            caja = QtWidgets.QGroupBox(t("seccion_" + s))
            form = QtWidgets.QFormLayout(caja)
            form.setLabelAlignment(QtCore.Qt.AlignRight)
            columna.addWidget(caja)
            self.secciones[s] = caja
            formularios[s] = form
        for clave, control, opciones, tipos, seccion in CAMPOS:
            w = self._control(clave, control, opciones)
            etiqueta = QtWidgets.QLabel(t("campo_" + clave))
            etiqueta.setToolTip(t("campo_" + clave + "_ayuda"))
            w.setToolTip(t("campo_" + clave + "_ayuda"))
            formularios[seccion].addRow(etiqueta, w)
            self.controles[clave] = (w, control)
            self.filas[clave] = (etiqueta, w, tipos)
        # botones dentro de las secciones
        self.boton_apoyos = QtWidgets.QPushButton(t("apoyos"))
        self.boton_apoyos.setToolTip(t("apoyos_ayuda"))
        self.boton_apoyos.clicked.connect(self._apoyos)
        formularios["caida"].addRow(self.boton_apoyos)
        self.boton_paredes = QtWidgets.QPushButton(t("paredes"))
        self.boton_paredes.setToolTip(t("paredes_ayuda"))
        self.boton_paredes.clicked.connect(self._apoyos)
        formularios["a_lo_largo"].addRow(self.boton_paredes)
        self.boton_conector = QtWidgets.QPushButton(t("conector_propio"))
        self.boton_conector.setToolTip(t("conector_propio_ayuda"))
        self.boton_conector.clicked.connect(self._conector_propio)
        formularios["extremos"].addRow(self.boton_conector)
        # materiales
        self.material_cuerpo = QtWidgets.QComboBox()
        self.material_piezas = QtWidgets.QComboBox()
        for combo, parte in ((self.material_cuerpo, "cuerpo"), (self.material_piezas, "piezas")):
            combo.activated.connect(lambda _i, combo=combo, parte=parte: self._material(parte, combo))
            formularios["material"].addRow(QtWidgets.QLabel(t("material_" + parte)), combo)
        columna.addStretch(1)
        desplazable.setWidget(contenido)
        raiz.addWidget(desplazable, 1)

        editar = QtWidgets.QGroupBox(t("seccion_editar"))
        filas = QtWidgets.QGridLayout(editar)
        filas.setSpacing(4)
        self.botones_editar = {}
        for i, (clave, funcion) in enumerate((("insertar_punto", self.servicio.insertar_punto),
                                              ("quitar_punto", self.servicio.quitar_puntos),
                                              ("seleccionar_anclas", self.servicio.seleccionar_anclas),
                                              ("seleccionar_cuerpo", self.servicio.seleccionar_cuerpos),
                                              ("hornear", self._hornear),
                                              ("borrar", self.servicio.borrar))):
            b = QtWidgets.QPushButton(t(clave))
            b.setToolTip(t(clave + "_ayuda"))
            b.clicked.connect(lambda _=False, f=funcion: self._accion(f))
            filas.addWidget(b, i // 3, i % 3)
            self.botones_editar[clave] = b
        raiz.addWidget(editar)

        self.estado = QtWidgets.QLabel()
        self.estado.setWordWrap(True)
        raiz.addWidget(self.estado)

    def _control(self, clave, control, opciones):
        if control == "lista":
            w = QtWidgets.QComboBox()
            for o in opciones:
                w.addItem(t("opcion_" + clave + "_" + o) if clave not in ("conector_inicio", "conector_fin")
                          else t("opcion_conector_" + o), o)
            w.activated.connect(lambda _i, clave=clave: self._cambio(clave))
        elif control == "casilla":
            w = QtWidgets.QCheckBox()
            w.toggled.connect(lambda _v, clave=clave: self._cambio(clave))
        else:
            minimo, maximo, decimales, paso, sufijo = opciones
            if control == "entero":
                w = QtWidgets.QSpinBox()
                w.setRange(int(minimo), int(maximo))
            else:
                w = QtWidgets.QDoubleSpinBox()
                w.setRange(minimo, maximo)
                w.setDecimals(decimales)
            w.setSingleStep(paso)
            w.setSuffix(sufijo)
            w.setKeyboardTracking(False)
            w.valueChanged.connect(lambda _v, clave=clave: self._cambio(clave))
        return w

    # --- valores de los controles -----------------------------------------------------
    def valor(self, clave):
        w, control = self.controles[clave]
        if control == "lista":
            return w.currentData()
        if control == "casilla":
            return w.isChecked()
        if control == "porcentaje":
            return w.value() / 100.0
        if control == "entero":
            return int(w.value())
        return float(w.value())

    def poner_valor(self, clave, v):
        w, control = self.controles[clave]
        w.blockSignals(True)
        try:
            if control == "lista":
                i = w.findData(v)
                w.setCurrentIndex(max(0, i))
            elif control == "casilla":
                w.setChecked(bool(v))
            elif control == "porcentaje":
                w.setValue(float(v) * 100.0)
            else:
                w.setValue(v)
        finally:
            w.blockSignals(False)

    def ajustes_actuales(self):
        a = dict(self.nuevos[self.tipo])
        for clave in self.controles:
            a[clave] = self.valor(clave)
        a["tipo"] = self.tipo
        a["material_cuerpo"] = self.material_cuerpo.currentData()
        a["material_piezas"] = self.material_piezas.currentData()
        return a

    # --- estado -----------------------------------------------------------------------
    def refrescar(self):
        """Lee la selección: si hay cables, la ventana los edita."""
        self.editando = self.servicio.seleccion()
        if self.editando:
            ajustes = self.servicio.leer(self.editando[0])
            self.tipo = ajustes.get("tipo", "cable")
        else:
            ajustes = self.nuevos[self.tipo]
        self._mostrar(ajustes)
        self._estado()

    def cambiar_tipo(self, tipo):
        if self.editando:
            self.servicio.escribir(self.editando, {"tipo": tipo})
            self.tipo = tipo
            self.refrescar()
            return
        self.tipo = tipo
        self._mostrar(self.nuevos[tipo])
        self._estado()

    def _mostrar(self, ajustes):
        self._cargando = True
        try:
            for tipo, b in self.botones_tipo.items():
                b.setChecked(tipo == self.tipo)
            for clave in self.controles:
                if clave in ajustes:
                    self.poner_valor(clave, ajustes[clave])
            for clave, (etiqueta, w, tipos) in self.filas.items():
                visible = self.tipo in tipos
                etiqueta.setVisible(visible)
                w.setVisible(visible)
            self.secciones["haz"].setVisible(self.tipo == "cable")
            self.secciones["recorrido"].setVisible(self.tipo == "tuberia")
            self.boton_apoyos.setVisible(self.tipo == "cable")
            self.boton_paredes.setVisible(self.tipo == "tuberia")
            self.boton_conector.setVisible(self.tipo == "cable")
            self.botones_crear["crear_grupos"].setVisible(self.tipo == "cable")
            self._llenar_materiales(ajustes)
            self._llenar_estilos()
            self._ajustar_dependientes()
        finally:
            self._cargando = False

    def _llenar_materiales(self, ajustes):
        cuerpo_def, piezas_def = materiales.POR_TIPO[self.tipo]
        listas = ((self.material_cuerpo, materiales.CABLE if self.tipo == "cable" else materiales.TUBERIA,
                   ajustes.get("material_cuerpo") or cuerpo_def),
                  (self.material_piezas, materiales.PIEZAS, ajustes.get("material_piezas") or piezas_def))
        for combo, nombres, actual in listas:
            combo.blockSignals(True)
            combo.clear()
            for n in nombres:
                combo.addItem(t("material_" + n), n)
            if combo.findData(actual) < 0 and actual in materiales.MATERIALES:
                combo.addItem(t("material_" + actual), actual)
            combo.setCurrentIndex(max(0, combo.findData(actual)))
            combo.blockSignals(False)

    def _llenar_estilos(self):
        self.lista_estilos.blockSignals(True)
        self.lista_estilos.clear()
        self.lista_estilos.addItem(t("estilo_elige"), None)
        for n in self.servicio.estilos.nombres(self.tipo):
            self.lista_estilos.addItem(n, n)
        self.lista_estilos.setCurrentIndex(0)
        self.lista_estilos.blockSignals(False)

    def _ajustar_dependientes(self):
        """Activa o apaga controles que solo tienen sentido con otros."""
        def activo(clave, si):
            etiqueta, w, _tipos = self.filas[clave]
            etiqueta.setEnabled(si)
            w.setEnabled(si)
        activo("holgura", self.valor("modo_tension") == "holgura")
        activo("altura_suelo", self.valor("apoyar_suelo"))
        activo("separacion_piezas", self.valor("pieza") != "ninguna")
        haz = self.valor("haz") > 1
        activo("torsion", haz)
        activo("separacion_bridas_haz", haz)
        activo("pared", self.valor("extremos") == "abiertos")
        activo("alcance_soportes", self.valor("separacion_soportes") > 0)

    def _estado(self):
        if self.editando:
            info = self.servicio.informacion(self.editando)
            self.cabecera.setText(t("editando_" + ("uno" if len(self.editando) == 1 else "varios"),
                                    n=len(self.editando)))
            texto = t("estado_info", longitud=_metros(info["longitud"]), triangulos=_miles(info["triangulos"]))
            if info.get("caida"):
                texto += " · " + t("estado_caida", caida=_metros(info["caida"]))
            if info.get("tensos"):
                texto += "\n" + t("estado_tenso", n=info["tensos"])
            self.estado.setText(texto)
        else:
            self.cabecera.setText(t("nuevo_" + self.tipo))
            self.estado.setText(t("estado_sin_seleccion"))
        for b in self.botones_editar.values():
            b.setEnabled(bool(self.editando))

    # --- cambios ----------------------------------------------------------------------
    def _cambio(self, clave):
        if self._cargando:
            return
        v = self.valor(clave)
        self._ajustar_dependientes()
        self.nuevos[self.tipo][clave] = v
        if self.editando:
            if clave == "modo_tension" and v == "longitud":
                self.servicio.fijar_longitudes(self.editando)
            else:
                self.servicio.escribir(self.editando, {clave: v})
            self._estado()
        else:
            self.servicio.recordar(self.ajustes_actuales())

    def _material(self, parte, combo):
        nombre = combo.currentData()
        self.nuevos[self.tipo]["material_" + parte] = nombre
        if self.editando:
            self.servicio.material(self.editando, parte, nombre)
        else:
            self.servicio.recordar(self.ajustes_actuales())

    def _aplicar_estilo(self, indice):
        nombre = self.lista_estilos.itemData(indice)
        if not nombre:
            return
        estilo = self.servicio.estilos.cargar(nombre)
        tipo = estilo.get("tipo", self.tipo)
        if self.editando:
            self.servicio.escribir(self.editando, estilo)
            for parte in ("cuerpo", "piezas"):
                if estilo.get("material_" + parte):
                    self.servicio.material(self.editando, parte, estilo["material_" + parte])
            self.refrescar()
        else:
            self.tipo = tipo
            self.nuevos[tipo].update(estilo)
            self._mostrar(self.nuevos[tipo])
            self.servicio.recordar(self.ajustes_actuales())
        self._mensaje(t("estilo_aplicado", nombre=nombre))

    def _guardar_estilo(self):
        nombre, ok = QtWidgets.QInputDialog.getText(self, t("estilo_guardar_titulo"), t("estilo_guardar_texto"))
        if ok and nombre.strip():
            self.servicio.estilos.guardar(nombre.strip(), self.ajustes_actuales())
            self._llenar_estilos()
            self._mensaje(t("estilo_guardado", nombre=nombre.strip()))

    def _borrar_estilo(self):
        nombre = self.lista_estilos.currentData()
        if not nombre:
            self._mensaje(t("estilo_borrar_elige"))
            return
        if self.servicio.estilos.borrar(nombre):
            self._llenar_estilos()
            self._mensaje(t("estilo_borrado", nombre=nombre))
        else:
            self._mensaje(t("estilo_de_serie"))

    # --- acciones ---------------------------------------------------------------------
    def _accion(self, funcion, *argumentos):
        try:
            resultado = funcion(*argumentos)
        except Exception as error:  # se muestra al usuario, nunca un error mudo
            self._mensaje(t("error", texto=str(error)))
            return None
        self.refrescar()
        if isinstance(resultado, str):
            self._mensaje(resultado)
        return resultado

    def _crear_clic(self):
        self._accion(self.servicio.crear_clic, self.ajustes_actuales, self.pegar.isChecked)

    def _crear_seleccion(self):
        self._accion(self.servicio.crear_seleccion, self.ajustes_actuales(), self.pegar.isChecked())

    def _crear_grupos(self):
        self._accion(self.servicio.crear_grupos, self.ajustes_actuales(), self.pegar.isChecked())

    def _crear_aristas(self):
        self._accion(self.servicio.crear_aristas, self.ajustes_actuales())

    def _crear_curva(self):
        self._accion(self.servicio.crear_curva, self.ajustes_actuales())

    def _apoyos(self):
        self._accion(self.servicio.apoyos)

    def _conector_propio(self):
        self._accion(self.servicio.conector_propio)

    def _hornear(self):
        return self.servicio.hornear()

    def _mensaje(self, texto):
        self.estado.setText(texto)
        self.servicio.mensaje(texto)
