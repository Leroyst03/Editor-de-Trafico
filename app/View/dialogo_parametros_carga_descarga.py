from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QMessageBox,
    QLabel, QInputDialog, QLineEdit
)
from PyQt5.QtCore import Qt

class DialogoParametrosCargaDescarga(QDialog):
    def __init__(self, parent=None, parametros_carga_descarga=None):
        super().__init__(parent)
        self.setWindowTitle("Parámetros Carga/Descarga")
        self.setMinimumSize(1200, 600)
        
        # Propiedades base (fijas) - ID y las 20 propiedades p_a a p_t
        self.propiedades_base = [
            "ID", "p_a", "p_b", "p_c", "p_d", "p_e", "p_f", "p_g", "p_h", "p_i", 
            "p_j", "p_k", "p_l", "p_m", "p_n", "p_o", "p_p", "p_q", "p_r", "p_s", "p_t"
        ]
        
        # Propiedades personalizadas (dinámicas) - inicialmente vacías, pero se pueden agregar
        self.propiedades_personalizadas = []
        
        # Inicializar parámetros de carga/descarga
        self.parametros_carga_descarga = parametros_carga_descarga.copy() if parametros_carga_descarga else []
        
        # EXTRAER PROPIEDADES PERSONALIZADAS DE LOS DATOS CARGADOS
        if self.parametros_carga_descarga:
            self._extraer_propiedades_personalizadas()
        
        self.setup_ui()
        self.cargar_parametros_defecto()
    
    def _extraer_propiedades_personalizadas(self):
        """Extrae propiedades personalizadas de los datos cargados"""
        propiedades_encontradas = set()
        
        for elemento in self.parametros_carga_descarga:
            if isinstance(elemento, dict):
                # Agregar todas las claves que no son propiedades base
                for clave in elemento.keys():
                    if clave not in self.propiedades_base and clave not in self.propiedades_personalizadas:
                        propiedades_encontradas.add(clave)
        
        # Agregar propiedades encontradas manteniendo el orden de aparición
        for elemento in self.parametros_carga_descarga:
            if isinstance(elemento, dict):
                for clave in elemento.keys():
                    if clave in propiedades_encontradas and clave not in self.propiedades_personalizadas:
                        self.propiedades_personalizadas.append(clave)
        
        print(f"Propiedades personalizadas extraídas: {self.propiedades_personalizadas}")
    
    def setup_ui(self):
        layout_principal = QVBoxLayout()
        
        # Información
        info_label = QLabel(
            "Cada fila representa un conjunto de parámetros de carga/descarga.\n"
            "Las columnas son propiedades fijas (ID y p_a a p_t). Puede agregar columnas personalizadas.\n"
            "Cada conjunto debe tener un ID único."
        )
        info_label.setStyleSheet("font-style: italic; color: #666;")
        layout_principal.addWidget(info_label)
        
        # Tabla para parámetros de carga/descarga
        self.tabla = QTableWidget()
        self.actualizar_columnas_tabla()
        
        # Configurar header
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout_principal.addWidget(self.tabla)
        
        # Botones para propiedades
        propiedades_layout = QHBoxLayout()
        
        self.btn_agregar_propiedad = QPushButton("Agregar Propiedad Personalizada")
        self.btn_eliminar_propiedad = QPushButton("Eliminar Propiedad Seleccionada")
        
        self.btn_agregar_propiedad.clicked.connect(self.agregar_propiedad_personalizada)
        self.btn_eliminar_propiedad.clicked.connect(self.eliminar_propiedad_personalizada)
        
        propiedades_layout.addWidget(self.btn_agregar_propiedad)
        propiedades_layout.addWidget(self.btn_eliminar_propiedad)
        propiedades_layout.addStretch()
        
        layout_principal.addLayout(propiedades_layout)
        
        # Botones para filas
        filas_layout = QHBoxLayout()
        
        self.btn_agregar_fila = QPushButton("Agregar Fila")
        self.btn_eliminar_fila = QPushButton("Eliminar Fila Seleccionada")
        
        self.btn_agregar_fila.clicked.connect(self.agregar_fila)
        self.btn_eliminar_fila.clicked.connect(self.eliminar_fila)
        
        filas_layout.addWidget(self.btn_agregar_fila)
        filas_layout.addWidget(self.btn_eliminar_fila)
        filas_layout.addStretch()
        
        layout_principal.addLayout(filas_layout)
        
        # Botones de guardar/cancelar
        botones_dialogo = QHBoxLayout()
        botones_dialogo.addStretch()
        
        self.btn_guardar = QPushButton("Guardar")
        self.btn_cancelar = QPushButton("Cancelar")
        
        self.btn_guardar.clicked.connect(self.guardar_parametros)
        self.btn_cancelar.clicked.connect(self.reject)
        
        botones_dialogo.addWidget(self.btn_guardar)
        botones_dialogo.addWidget(self.btn_cancelar)
        
        layout_principal.addLayout(botones_dialogo)
        
        self.setLayout(layout_principal)
    
    def actualizar_columnas_tabla(self):
        """Actualiza las columnas de la tabla con propiedades base y personalizadas"""
        todas_las_propiedades = self.propiedades_base + self.propiedades_personalizadas
        self.tabla.setColumnCount(len(todas_las_propiedades))
        self.tabla.setHorizontalHeaderLabels(todas_las_propiedades)
    
    def cargar_parametros_defecto(self):
        """Carga los valores por defecto si no hay datos"""
        if not self.parametros_carga_descarga:
            # Los 3 conjuntos por defecto con los valores proporcionados
            self.parametros_carga_descarga = [
                {
                    "ID": 0,
                    "p_a": 100, "p_b": -1, "p_c": -1, "p_d": -1, "p_e": -1,
                    "p_f": -1, "p_g": -1, "p_h": -1, "p_i": -1, "p_j": -1,
                    "p_k": -1, "p_l": -1, "p_m": -1, "p_n": -1, "p_o": -1,
                    "p_p": -1, "p_q": -1, "p_r": -1, "p_s": -1, "p_t": -1
                },
                {
                    "ID": 1,
                    "p_a": 0, "p_b": 32, "p_c": 16, "p_d": 2, "p_e": 13,
                    "p_f": 20, "p_g": 12, "p_h": 31, "p_i": 22, "p_j": 100,
                    "p_k": -1, "p_l": -1, "p_m": -1, "p_n": -1, "p_o": -1,
                    "p_p": -1, "p_q": -1, "p_r": -1, "p_s": -1, "p_t": -1
                },
                {
                    "ID": 2,
                    "p_a": 0, "p_b": 30, "p_c": 33, "p_d": 25, "p_e": 19,
                    "p_f": 18, "p_g": 4, "p_h": 23, "p_i": 12, "p_j": 22,
                    "p_k": 100, "p_l": -1, "p_m": -1, "p_n": -1, "p_o": -1,
                    "p_p": -1, "p_q": -1, "p_r": -1, "p_s": -1, "p_t": -1
                }
            ]
        
        # Actualizar tabla
        self.actualizar_tabla()
    
    def actualizar_tabla(self):
        """Actualiza el contenido de la tabla con los datos actuales"""
        todas_las_propiedades = self.propiedades_base + self.propiedades_personalizadas
        self.tabla.setRowCount(len(self.parametros_carga_descarga))
        
        for i, elemento in enumerate(self.parametros_carga_descarga):
            for j, propiedad in enumerate(todas_las_propiedades):
                valor = elemento.get(propiedad, "")
                item = QTableWidgetItem(str(valor))
                
                # TODAS las celdas son editables
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                
                self.tabla.setItem(i, j, item)
        
        # Ajustar ancho de columnas automáticamente
        self.tabla.resizeColumnsToContents()
        
        # Después de ajustar, asegurar que las columnas tengan un ancho mínimo
        for i in range(self.tabla.columnCount()):
            if self.tabla.columnWidth(i) < 50:
                self.tabla.setColumnWidth(i, 50)
    
    def agregar_propiedad_personalizada(self):
        """Agrega una nueva propiedad personalizada como columna"""
        nombre, ok = QInputDialog.getText(
            self, 
            "Nueva Propiedad Personalizada",
            "Ingrese el nombre de la nueva propiedad:",
            QLineEdit.Normal
        )
        
        if ok and nombre:
            nombre = nombre.strip()
            if nombre and nombre not in self.propiedades_base and nombre not in self.propiedades_personalizadas:
                self.propiedades_personalizadas.append(nombre)
                self.actualizar_columnas_tabla()
                self.actualizar_tabla()
            elif nombre in self.propiedades_base or nombre in self.propiedades_personalizadas:
                QMessageBox.warning(self, "Error", f"La propiedad '{nombre}' ya existe.")
    
    def eliminar_propiedad_personalizada(self):
        """Elimina la propiedad personalizada seleccionada"""
        columna = self.tabla.currentColumn()
        if columna >= 0:
            todas_las_propiedades = self.propiedades_base + self.propiedades_personalizadas
            if columna < len(todas_las_propiedades):
                propiedad = todas_las_propiedades[columna]
                
                if propiedad in self.propiedades_personalizadas:
                    respuesta = QMessageBox.question(
                        self,
                        "Confirmar eliminación",
                        f"¿Está seguro de eliminar la propiedad '{propiedad}'?\nEsta acción eliminará todos los datos de esta columna.",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if respuesta == QMessageBox.Yes:
                        self.propiedades_personalizadas.remove(propiedad)
                        self.actualizar_columnas_tabla()
                        self.actualizar_tabla()
                else:
                    QMessageBox.warning(self, "Error", "No se pueden eliminar propiedades base.")
        else:
            QMessageBox.warning(self, "Advertencia", "Seleccione una columna personalizada para eliminar.")
    
    def agregar_fila(self):
        """Agrega una nueva fila a la tabla"""
        # Calcular el próximo ID
        max_id = -1
        for i in range(self.tabla.rowCount()):
            item = self.tabla.item(i, 0)  # Columna ID
            if item and item.text().strip():
                try:
                    pid = int(item.text().strip())
                    if pid > max_id:
                        max_id = pid
                except ValueError:
                    pass
        
        # Agregar nueva fila
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)
        
        # Configurar valores por defecto para las propiedades base
        # Para las propiedades p_a a p_t, usar -1 como valor por defecto
        valores_por_defecto = {"ID": str(max_id + 1)}
        for prop in self.propiedades_base[1:]:  # Todas excepto ID
            valores_por_defecto[prop] = "-1"
        
        todas_las_propiedades = self.propiedades_base + self.propiedades_personalizadas
        
        for j, propiedad in enumerate(todas_las_propiedades):
            valor = valores_por_defecto.get(propiedad, "")
            item = QTableWidgetItem(str(valor))
            
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            
            self.tabla.setItem(fila, j, item)
        
        # Seleccionar la nueva fila
        self.tabla.setCurrentCell(fila, 0)
    
    def eliminar_fila(self):
        """Elimina la fila seleccionada"""
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.tabla.removeRow(fila)
        else:
            QMessageBox.warning(self, "Advertencia", "Seleccione una fila para eliminar.")
    
    def guardar_parametros(self):
        """Guarda todos los parámetros de la tabla"""
        todas_las_propiedades = self.propiedades_base + self.propiedades_personalizadas
        nuevos_parametros = []
        ids_vistos = set()
        
        for fila in range(self.tabla.rowCount()):
            elemento = {}
            
            for j, propiedad in enumerate(todas_las_propiedades):
                item = self.tabla.item(fila, j)
                valor = item.text().strip() if item else ""
                
                if propiedad == "ID":
                    if not valor:
                        QMessageBox.warning(self, "Error", f"Fila {fila+1}: El ID es obligatorio.")
                        return
                    
                    try:
                        id_valor = int(valor)
                        if id_valor in ids_vistos:
                            QMessageBox.warning(self, "Error", f"El ID {id_valor} está duplicado.")
                            return
                        ids_vistos.add(id_valor)
                        elemento[propiedad] = id_valor
                    except ValueError:
                        QMessageBox.warning(self, "Error", f"Fila {fila+1}: El ID debe ser un número entero.")
                        return
                else:
                    # Para las demás propiedades, intentamos convertirlas a número si es posible
                    if valor:
                        try:
                            # Intentar convertir a entero
                            elemento[propiedad] = int(valor)
                        except ValueError:
                            # Si no es entero, intentar float
                            try:
                                elemento[propiedad] = float(valor)
                            except ValueError:
                                # Si no, dejar como string
                                elemento[propiedad] = valor
                    else:
                        # Si está vacío, asignar -1 por defecto para las propiedades base (excepto ID)
                        if propiedad in self.propiedades_base and propiedad != "ID":
                            elemento[propiedad] = -1
                        else:
                            elemento[propiedad] = ""
            
            nuevos_parametros.append(elemento)
        
        self.parametros_carga_descarga = nuevos_parametros
        self.accept()
    
    def obtener_parametros(self):
        """Retorna la lista de parámetros de carga/descarga"""
        return self.parametros_carga_descarga