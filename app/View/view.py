from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import Qt
import os
import sys
from pathlib import Path
from View.zoom_view import ZoomGraphicsView

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
        
        # Referencia al controlador (se establecerá después)
        self.controller = None
    
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