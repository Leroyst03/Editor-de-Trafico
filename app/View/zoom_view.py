from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QWheelEvent, QCursor

class ZoomGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)
        
        # Configuración para mejor rendimiento en Windows
        self.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.DontSavePainterState, True)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        
        # Mejorar la respuesta al ratón en Windows
        self.setMouseTracking(True)
        
        # Variables para zoom
        self.zoom_level = 0
        self.zoom_factor = 1.25
        self.min_zoom = 0.1
        self.max_zoom = 10.0

        # --- NUEVO: Variables para pan con botón central ---
        self._pan = False
        self._pan_start_pos = QPoint()

    def wheelEvent(self, event: QWheelEvent):
        # Zoom con la rueda del ratón
        if event.angleDelta().y() > 0:
            factor = self.zoom_factor
            self.zoom_level += 1
        else:
            factor = 1 / self.zoom_factor
            self.zoom_level -= 1
        
        # Limitar zoom
        current_scale = self.transform().m11()
        new_scale = current_scale * factor
        
        if self.min_zoom <= new_scale <= self.max_zoom:
            self.scale(factor, factor)
        
        event.accept()

    # --- NUEVOS MÉTODOS PARA NAVEGACIÓN CON BOTÓN CENTRAL ---

    def mousePressEvent(self, event):
        # Si es el botón central (scroll), activamos pan manual
        if event.button() == Qt.MiddleButton:
            self._pan = True
            self._pan_start_pos = event.pos()
            # Cambiar cursor a mano cerrada
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return # Importante: no llamar a super para no seleccionar nada
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan:
            # Calcular cuánto se ha movido el ratón
            delta = self._pan_start_pos - event.pos()
            self._pan_start_pos = event.pos()
            
            # Mover las barras de desplazamiento
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() + delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() + delta.y()
            )
            event.accept()
            return
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._pan:
            self._pan = False
            # Restaurar cursor. 
            # Nota: El EditorController actualizará el cursor según el modo si es necesario,
            # pero unsetCursor() devuelve el control al sistema.
            self.unsetCursor() 
            event.accept()
            return
        
        super().mouseReleaseEvent(event)