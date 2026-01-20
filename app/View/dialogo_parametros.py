from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt

class DialogoParametros(QDialog):
    def __init__(self, parent=None, parametros=None):
        super().__init__(parent)
        self.setWindowTitle("Parámetros del Sistema")
        self.setMinimumSize(600, 500)
        
        self.parametros = parametros.copy() if parametros else {}
        
        self.setup_ui()
        self.cargar_parametros_defecto()
    
    def setup_ui(self):
        layout_principal = QVBoxLayout()
        
        # Tabla para parámetros
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(2)
        self.tabla.setHorizontalHeaderLabels(["Parámetro", "Valor"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout_principal.addWidget(self.tabla)
        
        # Botones para agregar/eliminar
        botones_layout = QHBoxLayout()
        
        self.btn_agregar = QPushButton("Agregar Parámetro")
        self.btn_eliminar = QPushButton("Eliminar Seleccionado")
        
        self.btn_agregar.clicked.connect(self.agregar_parametro)
        self.btn_eliminar.clicked.connect(self.eliminar_parametro)
        
        botones_layout.addWidget(self.btn_agregar)
        botones_layout.addWidget(self.btn_eliminar)
        botones_layout.addStretch()
        
        layout_principal.addLayout(botones_layout)
        
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
    
    def cargar_parametros_defecto(self):
        """Carga los parámetros por defecto si no hay datos"""
        if not self.parametros:
            self.parametros = {
                "G_AGV_ID": 2,
                "G_thres_error_angle": 5,
                "G_dist_larguero": 0,
                "G_pulsos_por_grado_encoder": 15,
                "G_LAT_OFF": 905,
                "G_lateral_centro": 47,
                "G_LAT_MAX": 1006,
                "G_TACO_OFF": 76,
                "G_ALT_OFF": 184,
                "G_PUNTO_CARGADOR": 75,
                "G_PUNTO_CARGADOR_": 75,
                "G_offset_Lidar": 2,
                "G_t_stop_aprox_big": 0,
                "G_stop_r": 0,
                "G_PAL_L_P_off": 0,
                "G_PAL_A_P_off_peso": 0
            }
        
        # Actualizar tabla
        self.actualizar_tabla()
    
    def actualizar_tabla(self):
        self.tabla.setRowCount(len(self.parametros))
        
        for i, (nombre, valor) in enumerate(self.parametros.items()):
            item_nombre = QTableWidgetItem(nombre)
            item_nombre.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            
            item_valor = QTableWidgetItem(str(valor))
            item_valor.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            
            self.tabla.setItem(i, 0, item_nombre)
            self.tabla.setItem(i, 1, item_valor)
    
    def agregar_parametro(self):
        # Agregar nueva fila
        filas = self.tabla.rowCount()
        self.tabla.insertRow(filas)
        
        # Crear items para la nueva fila
        item_nombre = QTableWidgetItem("nuevo_parametro")
        item_nombre.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
        
        item_valor = QTableWidgetItem("0")
        item_valor.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
        
        self.tabla.setItem(filas, 0, item_nombre)
        self.tabla.setItem(filas, 1, item_valor)
        
        # Seleccionar la nueva fila
        self.tabla.setCurrentCell(filas, 0)
    
    def eliminar_parametro(self):
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.tabla.removeRow(fila)
        else:
            QMessageBox.warning(self, "Advertencia", 
                              "Selecciona un parámetro para eliminar")
    
    def guardar_parametros(self):
        # Recoger todos los parámetros de la tabla
        nuevos_parametros = {}
        
        for fila in range(self.tabla.rowCount()):
            nombre_item = self.tabla.item(fila, 0)
            valor_item = self.tabla.item(fila, 1)
            
            if nombre_item and valor_item:
                nombre = nombre_item.text().strip()
                valor = valor_item.text().strip()
                
                if nombre:  # Ignorar filas vacías
                    # Intentar convertir valores numéricos
                    try:
                        if '.' in valor:
                            valor = float(valor)
                        else:
                            valor = int(valor)
                    except ValueError:
                        # Mantener como string si no es número
                        pass
                    
                    nuevos_parametros[nombre] = valor
        
        self.parametros = nuevos_parametros
        self.accept()
    
    def obtener_parametros(self):
        return self.parametros