from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QMessageBox,
    QLabel, QInputDialog, QLineEdit
)
from PyQt5.QtCore import Qt

class DialogoParametrosCargaDescarga(QDialog):
    def __init__(self, parent=None, parametros_carga_descarga=None):
        super().__init__(parent)
        self.setWindowTitle("Parámetros de Carga/Descarga")
        self.setMinimumSize(1200, 600)
        
        # Propiedades base (fijas)
        self.propiedades_base = [
            "ID", "p_a", "p_b", "p_c", "p_d", "p_e", "p_f", "p_g", 
            "p_h", "p_i", "p_j", "p_k", "p_l", "p_m", "p_n", "p_o", 
            "p_p", "p_q", "p_r", "p_s", "p_t"
        ]
        
        # Propiedades personalizadas (dinámicas)
        self.propiedades_personalizadas = []
        
        # Inicializar parámetros de carga/descarga
        if parametros_carga_descarga is None:
            self.parametros_carga_descarga = {
                "propiedades_personalizadas": [],
                "conjuntos": []
            }
        elif isinstance(parametros_carga_descarga, list):
            # Convertir estructura antigua a nueva
            self.parametros_carga_descarga = {
                "propiedades_personalizadas": [],
                "conjuntos": parametros_carga_descarga
            }
        else:
            # Usar estructura nueva
            self.parametros_carga_descarga = parametros_carga_descarga.copy()
        
        # Cargar propiedades personalizadas desde la estructura
        self.propiedades_personalizadas = self.parametros_carga_descarga.get("propiedades_personalizadas", [])
        
        self.setup_ui()
        self.cargar_conjuntos_defecto()
    
    def setup_ui(self):
        layout_principal = QVBoxLayout()
        
        # Información
        info_label = QLabel(
            "Cada fila representa un conjunto de parámetros de carga/descarga.\n"
            "Las columnas gris claro son propiedades fijas. Puede agregar columnas personalizadas.\n"
            "Cada conjunto debe tener un ID único.\n"
            "Los valores -1 indican que el parámetro no se utiliza."
        )
        info_label.setStyleSheet("font-style: italic; color: #666;")
        layout_principal.addWidget(info_label)
        
        # Tabla para parámetros de carga/descarga
        self.tabla = QTableWidget()
        self.actualizar_columnas_tabla()
        
        # Configurar header
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
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
        
        self.btn_agregar_fila = QPushButton("Agregar Conjunto")
        self.btn_eliminar_fila = QPushButton("Eliminar Conjunto Seleccionado")
        
        self.btn_agregar_fila.clicked.connect(self.agregar_conjunto)
        self.btn_eliminar_fila.clicked.connect(self.eliminar_conjunto)
        
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
    
    def cargar_conjuntos_defecto(self):
        """Carga conjuntos por defecto si no hay datos"""
        conjuntos = self.parametros_carga_descarga.get("conjuntos", [])
        
        if not conjuntos:
            # Conjuntos por defecto como en el ejemplo
            conjuntos = [
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
            self.parametros_carga_descarga["conjuntos"] = conjuntos
        
        # Actualizar tabla
        self.actualizar_tabla()
    
    def actualizar_tabla(self):
        """Actualiza el contenido de la tabla con los datos actuales"""
        todas_las_propiedades = self.propiedades_base + self.propiedades_personalizadas
        conjuntos = self.parametros_carga_descarga.get("conjuntos", [])
        
        self.tabla.setRowCount(len(conjuntos))
        
        for i, conjunto in enumerate(conjuntos):
            for j, propiedad in enumerate(todas_las_propiedades):
                valor = conjunto.get(propiedad, "-1")
                item = QTableWidgetItem(str(valor))
                
                # Todas las celdas son editables
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
    
    def agregar_conjunto(self):
        """Agrega una nueva fila (conjunto) a la tabla"""
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
        
        # Configurar valores por defecto (-1 para todos los parámetros excepto ID)
        todas_las_propiedades = self.propiedades_base + self.propiedades_personalizadas
        
        for j, propiedad in enumerate(todas_las_propiedades):
            if propiedad == "ID":
                valor = str(max_id + 1)
            else:
                valor = "-1"
                
            item = QTableWidgetItem(str(valor))
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            self.tabla.setItem(fila, j, item)
        
        # Seleccionar la nueva fila
        self.tabla.setCurrentCell(fila, 0)
    
    def eliminar_conjunto(self):
        """Elimina la fila seleccionada"""
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.tabla.removeRow(fila)
        else:
            QMessageBox.warning(self, "Advertencia", "Seleccione una fila para eliminar.")
    
    def guardar_parametros(self):
        """Guarda todos los parámetros de la tabla"""
        todas_las_propiedades = self.propiedades_base + self.propiedades_personalizadas
        nuevos_conjuntos = []
        ids_vistos = set()
        
        for fila in range(self.tabla.rowCount()):
            conjunto = {}
            
            for j, propiedad in enumerate(todas_las_propiedades):
                item = self.tabla.item(fila, j)
                valor = item.text().strip() if item else "-1"
                
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
                        conjunto[propiedad] = id_valor
                    except ValueError:
                        QMessageBox.warning(self, "Error", f"Fila {fila+1}: El ID debe ser un número entero.")
                        return
                else:
                    # Convertir a número si es posible
                    try:
                        if valor == "" or valor.lower() == "null":
                            conjunto[propiedad] = -1
                        else:
                            conjunto[propiedad] = int(valor)
                    except ValueError:
                        QMessageBox.warning(self, "Error", 
                                          f"Fila {fila+1}, Columna '{propiedad}': Valor inválido. Debe ser un número entero.")
                        return
            
            nuevos_conjuntos.append(conjunto)
        
        # Actualizar la estructura completa
        self.parametros_carga_descarga = {
            "propiedades_personalizadas": self.propiedades_personalizadas,
            "conjuntos": nuevos_conjuntos
        }
        
        self.accept()
    
    def obtener_parametros(self):
        """Retorna la estructura completa de parámetros de carga/descarga"""
        return self.parametros_carga_descarga
    
    def obtener_propiedades(self):
        """Retorna todas las propiedades (base + personalizadas)"""
        return self.propiedades_base + self.propiedades_personalizadas