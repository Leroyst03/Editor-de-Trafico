from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QPushButton, QLabel, QListWidgetItem, QSizePolicy, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont
import os
import sys
from pathlib import Path
from View.zoom_view import ZoomGraphicsView

# ===== WIDGETS PERSONALIZADOS PARA LISTAS =====

class NodoListItemWidget(QWidget):
    """Widget personalizado para ítems de nodo en la lista lateral"""
    toggle_visibilidad = pyqtSignal(int)  # Señal con nodo_id
    
    def __init__(self, nodo_id, texto, visible=True, parent=None):
        super().__init__(parent)
        self.nodo_id = nodo_id
        self.visible = visible
        
        # Layout horizontal
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 1, 2, 1)  # Márgenes más pequeños
        layout.setSpacing(3)  # Espaciado reducido
        
        # Etiqueta con texto (ocupa la mayor parte del espacio)
        self.lbl_texto = QLabel(texto)
        self.lbl_texto.setStyleSheet("color: #e0e0e0; padding: 1px;")
        self.lbl_texto.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Botón de ojo pequeño a la derecha
        self.btn_ojo = QPushButton()
        self.btn_ojo.setFixedSize(20, 20)  # Más pequeño: 20x20px
        self.btn_ojo.setObjectName("btnOjo")
        self.btn_ojo.clicked.connect(self._on_toggle_visibilidad)
        
        # Añadir primero el texto, luego el botón
        layout.addWidget(self.lbl_texto, 1)  # Factor de estiramiento 1
        layout.addWidget(self.btn_ojo, 0, Qt.AlignRight)  # Sin estiramiento, alineado a la derecha
        
        self.setLayout(layout)
        self.actualizar_estado()
    
    def _on_toggle_visibilidad(self):
        """Emite señal cuando se hace clic en el botón de ojo"""
        self.toggle_visibilidad.emit(self.nodo_id)
    
    def actualizar_estado(self):
        """Actualiza la apariencia del botón según el estado de visibilidad"""
        if self.visible:
            self.btn_ojo.setStyleSheet("""
                QPushButton#btnOjo {
                    background-color: #4CAF50;
                    border: 1px solid #388E3C;
                    border-radius: 3px;
                    color: white;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton#btnOjo:hover {
                    background-color: #45a049;
                    border-color: #2E7D32;
                }
            """)
            self.btn_ojo.setText("👁")
            self.lbl_texto.setStyleSheet("color: #e0e0e0; padding: 1px; font-size: 10px;")
        else:
            self.btn_ojo.setStyleSheet("""
                QPushButton#btnOjo {
                    background-color: #f44336;
                    border: 1px solid #D32F2F;
                    border-radius: 3px;
                    color: white;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton#btnOjo:hover {
                    background-color: #da190b;
                    border-color: #B71C1C;
                }
            """)
            self.btn_ojo.setText("👁")
            self.lbl_texto.setStyleSheet("color: #666666; text-decoration: line-through; padding: 1px; font-size: 10px;")

    def set_visible(self, visible):
        """Establece el estado de visibilidad y actualiza"""
        self.visible = visible
        self.actualizar_estado()

class RutaListItemWidget(QWidget):
    """Widget personalizado para ítems de ruta en la lista lateral"""
    toggle_visibilidad = pyqtSignal(int)  # Señal con ruta_index
    
    def __init__(self, ruta_index, texto, visible=True, parent=None):
        super().__init__(parent)
        self.ruta_index = ruta_index
        self.visible = visible
        
        # Layout horizontal
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 1, 2, 1)  # Márgenes más pequeños
        layout.setSpacing(3)  # Espaciado reducido
        
        # Etiqueta con texto (ocupa la mayor parte del espacio)
        self.lbl_texto = QLabel(texto)
        self.lbl_texto.setStyleSheet("color: #e0e0e0; padding: 1px;")
        self.lbl_texto.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Botón de ojo pequeño a la derecha
        self.btn_ojo = QPushButton()
        self.btn_ojo.setFixedSize(20, 20)  # Más pequeño: 20x20px
        self.btn_ojo.setObjectName("btnOjo")
        self.btn_ojo.clicked.connect(self._on_toggle_visibilidad)
        
        # Añadir primero el texto, luego el botón
        layout.addWidget(self.lbl_texto, 1)  # Factor de estiramiento 1
        layout.addWidget(self.btn_ojo, 0, Qt.AlignRight)  # Sin estiramiento, alineado a la derecha
        
        self.setLayout(layout)
        self.actualizar_estado()
    
    def _on_toggle_visibilidad(self):
        """Emite señal cuando se hace clic en el botón de ojo"""
        self.toggle_visibilidad.emit(self.ruta_index)
    
    def actualizar_estado(self):
        """Actualiza la apariencia del botón según el estado de visibilidad"""
        if self.visible:
            self.btn_ojo.setStyleSheet("""
                QPushButton#btnOjo {
                    background-color: #2196F3;
                    border: 1px solid #1976D2;
                    border-radius: 3px;
                    color: white;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton#btnOjo:hover {
                    background-color: #0b7dda;
                    border-color: #1565C0;
                }
            """)
            self.btn_ojo.setText("👁")
            self.lbl_texto.setStyleSheet("color: #e0e0e0; padding: 1px; font-size: 10px;")
        else:
            self.btn_ojo.setStyleSheet("""
                QPushButton#btnOjo {
                    background-color: #ff9800;
                    border: 1px solid #F57C00;
                    border-radius: 3px;
                    color: white;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton#btnOjo:hover {
                    background-color: #e68a00;
                    border-color: #EF6C00;
                }
            """)
            self.btn_ojo.setText("👁")
            self.lbl_texto.setStyleSheet("color: #666666; text-decoration: line-through; padding: 1px; font-size: 10px;")

    def set_visible(self, visible):
        """Establece el estado de visibilidad y actualiza"""
        self.visible = visible
        self.actualizar_estado()

# ===== CLASE PRINCIPAL DE LA VISTA =====

class EditorView(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Buscar el archivo .ui en múltiples ubicaciones
        ui_paths = [
            Path(__file__).parent / "editor.ui",
            Path.cwd() / "View" / "editor.ui",
            Path(sys.executable).parent / "View" / "editor.ui"
        ]
        
        ui_file = None
        for path in ui_paths:
            if path.exists():
                ui_file = str(path)
                print(f"✓ Archivo UI encontrado en: {path}")
                break
        
        if not ui_file:
            raise FileNotFoundError("No se pudo encontrar el archivo editor.ui")
        
        # Cargar UI
        uic.loadUi(ui_file, self)
        
        self.menuParametros = self.menuBar().addMenu("Parámetros")
        #self.actionParametros = self.menuParametros.addAction("Configurar Parámetros...")

        # Sustituir el QGraphicsView por ZoomGraphicsView
        self.zoomView = ZoomGraphicsView(self)
        self.zoomView.setObjectName("marco_trabajo")
        
        # Configuraciones específicas para Windows
        self.zoomView.setViewportUpdateMode(self.zoomView.FullViewportUpdate)
        self.zoomView.setOptimizationFlag(self.zoomView.DontAdjustForAntialiasing, False)
        
        # Reemplazar en el layout
        if hasattr(self, 'workLayout') and self.workLayout is not None:
            self.workLayout.replaceWidget(self.marco_trabajo, self.zoomView)
            self.marco_trabajo.deleteLater()
            self.marco_trabajo = self.zoomView
        else:
            print("✗ ADVERTENCIA: No se encontró workLayout")
            self.marco_trabajo = self.zoomView
        
        # --- NUEVA BARRA DE INFORMACIÓN EN PARTE INFERIOR ---
        # Crear QLabel para mostrar información del modo
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 5px;
                border-top: 1px solid #444444;
                font-size: 11px;
            }
        """)
        self.status_label.setFixedHeight(25)  # Altura fija para la barra
        
        # Agregar al layout principal (mainLayout es QVBoxLayout en centralwidget)
        # Necesitamos acceder al layout del centralwidget
        if hasattr(self.centralwidget, 'layout'):
            main_layout = self.centralwidget.layout()
            if main_layout:
                # Insertar el label al final del layout (parte inferior)
                main_layout.addWidget(self.status_label)
                print("✓ Barra de información agregada en parte inferior")
            else:
                print("✗ No se encontró layout principal")
        else:
            print("✗ No se pudo acceder al layout principal")
        
        # Referencia al controlador (se establecerá después)
        self.controller = None
        
        # Establecer texto inicial
        self.actualizar_descripcion_modo("navegacion")
    
    def actualizar_descripcion_modo(self, modo):
        """Actualiza la descripción del modo en la barra inferior"""
        descripciones = {
            "navegacion": "Modo navegación: Usa el ratón para desplazarte por el mapa. Haz clic en un nodo para seleccionarlo.",
            "mover": "Modo mover: Arrastra los nodos para cambiar su posición. Usa Ctrl+Z para deshacer y Ctrl+Y para rehacer. Mantener pulsado botón scroll del ratón para navegar.",
            "colocar": "Modo colocar: Haz clic en el mapa para colocar un nuevo nodo. Puede pulsar Escape para salir del modo. Mantener pulsado botón scroll del ratón para navegar.",
            "ruta": "Modo ruta: Haz clic en nodos existentes o en el mapa para crear nuevos nodos y formar una ruta. Presiona Enter para finalizar la ruta o Escape para cancelar. Mantener pulsado botón scroll del ratón para navegar."
        }
        
        texto = descripciones.get(modo, "Modo desconocido")
        self.status_label.setText(texto)
        print(f"✓ Descripción del modo actualizada: {modo}")
    
    def set_controller(self, controller):
        """Establece la referencia al controlador"""
        self.controller = controller
    
    def keyPressEvent(self, event):
        """Captura eventos de teclado para atajos globales"""
        try:
            # Pasar el evento al controlador primero
            if self.controller:
                # Check for Enter/Return - Finalizar ruta
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    self.controller.finalizar_ruta_actual()
                    event.accept()
                    return
                    
                # Check for Escape - Cancelar ruta
                elif event.key() == Qt.Key_Escape:
                    self.controller.cancelar_ruta_actual()
                    event.accept()
                    return
                    
                # Check for Delete - Eliminar nodo
                elif event.key() == Qt.Key_Delete:
                    self.controller.eliminar_nodo_seleccionado()
                    event.accept()
                    return
                    
                # Check for Ctrl+Z - Deshacer
                elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
                    self.controller.deshacer_movimiento()
                    event.accept()
                    return
                    
                # Check for Ctrl+Y - Rehacer
                elif event.key() == Qt.Key_Y and event.modifiers() == Qt.ControlModifier:
                    self.controller.rehacer_movimiento()
                    event.accept()
                    return
        
        except Exception as e:
            print(f"Error en keyPressEvent: {e}")
        
        # Pasar el evento a la clase base para manejo normal
        super().keyPressEvent(event)