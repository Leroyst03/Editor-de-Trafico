from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QWheelEvent

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