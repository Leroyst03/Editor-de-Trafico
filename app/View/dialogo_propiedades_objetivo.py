from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QSpinBox, QPushButton,
                             QFormLayout, QGroupBox, QFrame, QWidget)
from PyQt5.QtCore import Qt

class DialogoPropiedadesObjetivo(QDialog):
    def __init__(self, parent=None, propiedades=None):
        super().__init__(parent)
        self.setWindowTitle("Propiedades de Objetivo")
        self.setMinimumWidth(450)
        
        # Configurar estilo para mejor visibilidad
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                min-width: 120px;
            }
            QSpinBox, QLineEdit {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
                min-width: 80px;
            }
            QPushButton {
                background-color: #5a5a5a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #6a6a6a;
            }
        """)
        
        if propiedades is None:
            propiedades = {}
        
        layout_principal = QVBoxLayout()
        
        # Crear un widget con scroll si es necesario
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # --- GRUPO 1: Ubicación ---
        grupo_ubicacion = QGroupBox("Ubicación")
        layout_ubicacion = QFormLayout()
        layout_ubicacion.setLabelAlignment(Qt.AlignRight)
        
        self.spin_pasillo = QSpinBox()
        self.spin_pasillo.setRange(0, 1000)
        self.spin_pasillo.setValue(propiedades.get("Pasillo", 0))
        layout_ubicacion.addRow("Pasillo:", self.spin_pasillo)
        
        self.spin_estanteria = QSpinBox()
        self.spin_estanteria.setRange(0, 1000)
        self.spin_estanteria.setValue(propiedades.get("Estanteria", 0))
        layout_ubicacion.addRow("Estantería:", self.spin_estanteria)
        
        grupo_ubicacion.setLayout(layout_ubicacion)
        scroll_layout.addWidget(grupo_ubicacion)
        
        # --- GRUPO 2: Altura ---
        grupo_altura = QGroupBox("Altura")
        layout_altura = QFormLayout()
        layout_altura.setLabelAlignment(Qt.AlignRight)
        
        self.spin_altura = QSpinBox()
        self.spin_altura.setRange(0, 10)
        self.spin_altura.setValue(propiedades.get("Altura", 0))
        layout_altura.addRow("Niveles:", self.spin_altura)
        
        self.spin_altura_mm = QSpinBox()
        self.spin_altura_mm.setRange(0, 10000)
        self.spin_altura_mm.setValue(propiedades.get("Altura_en_mm", 0))
        layout_altura.addRow("Altura en mm:", self.spin_altura_mm)
        
        grupo_altura.setLayout(layout_altura)
        scroll_layout.addWidget(grupo_altura)
        
        # --- GRUPO 3: Puntos de Referencia ---
        grupo_puntos = QGroupBox("Puntos de Referencia")
        layout_puntos = QFormLayout()
        layout_puntos.setLabelAlignment(Qt.AlignRight)
        
        self.spin_punto_pasillo = QSpinBox()
        self.spin_punto_pasillo.setRange(0, 1000)
        self.spin_punto_pasillo.setValue(propiedades.get("Punto_Pasillo", 0))
        layout_puntos.addRow("Punto Pasillo:", self.spin_punto_pasillo)
        
        self.spin_punto_escara = QSpinBox()
        self.spin_punto_escara.setRange(0, 1000)
        self.spin_punto_escara.setValue(propiedades.get("Punto_Escara", 0))
        layout_puntos.addRow("Punto Encarar", self.spin_punto_escara)
        
        self.spin_punto_desapr = QSpinBox()
        self.spin_punto_desapr.setRange(0, 1000)
        self.spin_punto_desapr.setValue(propiedades.get("Punto_desapr", 0))
        layout_puntos.addRow("Punto Desaproximar:", self.spin_punto_desapr)
        
        grupo_puntos.setLayout(layout_puntos)
        scroll_layout.addWidget(grupo_puntos)
        
        # --- GRUPO 4: Operación ---
        grupo_operacion = QGroupBox("Operación")
        layout_operacion = QFormLayout()
        layout_operacion.setLabelAlignment(Qt.AlignRight)
        
        self.spin_fifo = QSpinBox()
        self.spin_fifo.setRange(0, 1)
        self.spin_fifo.setValue(propiedades.get("FIFO", 0))
        layout_operacion.addRow("FIFO (0/1):", self.spin_fifo)
        
        self.edit_nombre = QLineEdit()
        self.edit_nombre.setText(propiedades.get("Nombre", ""))
        layout_operacion.addRow("Nombre:", self.edit_nombre)
        
        self.spin_presicion = QSpinBox()
        self.spin_presicion.setRange(0, 100)
        self.spin_presicion.setValue(propiedades.get("Presicion", 0))
        layout_operacion.addRow("Precisión:", self.spin_presicion)
        
        self.spin_ir_a_desicion = QSpinBox()
        self.spin_ir_a_desicion.setRange(0, 1)
        self.spin_ir_a_desicion.setValue(propiedades.get("Ir_a_desicion", 0))
        layout_operacion.addRow("Ir a decisión:", self.spin_ir_a_desicion)
        
        grupo_operacion.setLayout(layout_operacion)
        scroll_layout.addWidget(grupo_operacion)
        
        # --- GRUPO 5: Configuración Final ---
        grupo_final = QGroupBox("Configuración Final")
        layout_final = QFormLayout()
        layout_final.setLabelAlignment(Qt.AlignRight)
        
        self.spin_numero_playa = QSpinBox()
        self.spin_numero_playa.setRange(0, 1000)
        self.spin_numero_playa.setValue(propiedades.get("numero_playa", 0))
        layout_final.addRow("Número playa:", self.spin_numero_playa)
        
        # Tipo carga/descarga (NUMÉRICO)
        tipo_layout = QHBoxLayout()
        self.spin_tipo_carga = QSpinBox()
        self.spin_tipo_carga.setRange(0, 3)
        self.spin_tipo_carga.setValue(propiedades.get("tipo_carga_descarga", 0))
        
        # Label para mostrar el significado del valor actual
        self.label_tipo_descripcion = QLabel(self._obtener_descripcion_tipo(propiedades.get("tipo_carga_descarga", 0)))
        self.label_tipo_descripcion.setStyleSheet("color: #cccccc; font-style: italic; padding-left: 10px;")
        
        tipo_layout.addWidget(self.spin_tipo_carga)
        tipo_layout.addWidget(self.label_tipo_descripcion)
        tipo_layout.addStretch()
        
        # Conectar el cambio de valor para actualizar la descripción
        self.spin_tipo_carga.valueChanged.connect(self._actualizar_descripcion_tipo)
        
        layout_final.addRow("Tipo carga/descarga:", tipo_layout)
        
        grupo_final.setLayout(layout_final)
        scroll_layout.addWidget(grupo_final)
        
        # Agregar widget con scroll al layout principal
        layout_principal.addWidget(scroll_widget)
        
        # Separador
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setFrameShadow(QFrame.Sunken)
        separador.setStyleSheet("background-color: #555555;")
        layout_principal.addWidget(separador)
        
        # Botones
        botones_layout = QHBoxLayout()
        botones_layout.addStretch()
        
        self.btn_aceptar = QPushButton("Aceptar")
        self.btn_cancelar = QPushButton("Cancelar")
        
        self.btn_aceptar.setDefault(True)
        self.btn_aceptar.clicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)
        
        botones_layout.addWidget(self.btn_aceptar)
        botones_layout.addWidget(self.btn_cancelar)
        
        layout_principal.addLayout(botones_layout)
        self.setLayout(layout_principal)
    
    def _obtener_descripcion_tipo(self, valor):
        """Obtiene la descripción textual del tipo de carga/descarga"""
        descripciones = {
            0: "Normal",
            1: "Carga",
            2: "Descarga", 
            3: "Mixto"
        }
        return f"({descripciones.get(valor, 'Desconocido')})"
    
    def _actualizar_descripcion_tipo(self, valor):
        """Actualiza la descripción cuando cambia el valor"""
        self.label_tipo_descripcion.setText(self._obtener_descripcion_tipo(valor))
    
    def obtener_propiedades(self):
        """Devuelve un diccionario con los valores actuales"""
        return {
            "Pasillo": self.spin_pasillo.value(),
            "Estanteria": self.spin_estanteria.value(),
            "Altura": self.spin_altura.value(),
            "Altura_en_mm": self.spin_altura_mm.value(),
            "Punto_Pasillo": self.spin_punto_pasillo.value(),
            "Punto_encarar": self.spin_punto_escara.value(),
            "Punto_desaproximar": self.spin_punto_desapr.value(),
            "FIFO": self.spin_fifo.value(),
            "Nombre": self.edit_nombre.text(),
            "Presicion": self.spin_presicion.value(),
            "Ir_a_desicion": self.spin_ir_a_desicion.value(),
            "numero_playa": self.spin_numero_playa.value(),
            "tipo_carga_descarga": self.spin_tipo_carga.value()
        }