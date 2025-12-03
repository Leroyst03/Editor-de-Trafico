from PyQt5.QtWidgets import QGraphicsObject, QMessageBox, QGraphicsItem
from PyQt5.QtCore import QRectF, Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QBrush, QPainter, QPen, QColor
from Model.Nodo import Nodo

class NodoItem(QGraphicsObject):
    moved = pyqtSignal(object)  # emite (id, x, y) o el objeto nodo según preferencia

    def __init__(self, nodo: Nodo, size=20, editor=None):
        super().__init__()
        self.nodo = nodo
        self.size = size
        self.editor = editor

        # Enviar cambios de geometría para que itemChange reciba ItemPositionHasChanged
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        # Posicionar el item según el modelo; centrar el item en la coordenada del modelo
        try:
            x = int(self.nodo.get("X", 0)) if hasattr(self.nodo, "get") else int(getattr(self.nodo, "X", 0))
            y = int(self.nodo.get("Y", 0)) if hasattr(self.nodo, "get") else int(getattr(self.nodo, "Y", 0))
        except Exception:
            x = y = 0
        # colocar de modo que el centro del item coincida con (X,Y)
        self.setPos(x - self.size / 2, y - self.size / 2)

        # Flags y comportamiento de ratón
        self.setFlag(QGraphicsObject.ItemIsSelectable, True)
        self.setFlag(QGraphicsObject.ItemIsFocusable, True)
        # ItemIsMovable se activa/desactiva desde EditorController según el modo
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setZValue(1)

        # Estado interno para detectar arrastre
        self._dragging = False

        # Colores configurables
        self.color_normal = QColor(0, 120, 215)   # Azul por defecto
        self.color_selected = QColor(0, 200, 0)   # Verde para selección
        self.color_route_selected = QColor(255, 165, 0)  # Naranja para nodos en ruta seleccionada
        
        # Usar color normal inicialmente
        self.current_color = self.color_normal

    def boundingRect(self):
        return QRectF(0, 0, self.size, self.size)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        
        painter.translate(self.size / 2, self.size / 2)
        angle = int(self.nodo.get("A", 0))  # Leemos el angulo
        painter.rotate(360 - angle)
        painter.translate(-self.size / 2, -self.size / 2)

        # Determinar el color a usar
        brush_color = self.current_color
        
        # Dibujar círculo
        painter.setBrush(QBrush(brush_color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawEllipse(self.boundingRect())

        center_y = self.size / 2

        # Parámetros de las horquillas
        fork_length = 10   # longitud de cada horquilla (hacia la izquierda)
        fork_gap = 6       # separación entre las dos horquillas
        offset_from_node = 1  # separación desde el borde izquierdo del nodo hasta el inicio de las horquillas

        # Coordenadas: dibujamos a la izquierda del nodo
        x_start = -offset_from_node
        x_end = x_start - fork_length

        # Posiciones verticales de las dos líneas
        y_top = center_y - fork_gap / 2
        y_bottom = center_y + fork_gap / 2

        # Dibujar las dos horquillas
        pen = QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(x_start, y_top), QPointF(x_end, y_top))
        painter.drawLine(QPointF(x_start, y_bottom), QPointF(x_end, y_bottom))

        # Dibujar el ID en el centro
        painter.setPen(QPen(Qt.white, 1))
        node_id = str(self.nodo.get('id', ''))
        painter.drawText(self.boundingRect(), Qt.AlignCenter, node_id)

        painter.restore()

    def set_selected_color(self):
        """Cambia al color de selección"""
        self.current_color = self.color_selected
        self.update()

    def set_route_selected_color(self):
        """Cambia al color para nodos en ruta seleccionada"""
        self.current_color = self.color_route_selected
        self.update()

    def set_normal_color(self):
        """Vuelve al color normal"""
        self.current_color = self.color_normal
        self.update()

    def actualizar_posicion(self):
        # Mantener la posición visual sincronizada con el modelo (centrado)
        try:
            x = int(self.nodo.get("X", 0)) if hasattr(self.nodo, "get") else int(getattr(self.nodo, "X", 0))
            y = int(self.nodo.get("Y", 0)) if hasattr(self.nodo, "get") else int(getattr(self.nodo, "Y", 0))
            self.setPos(x - self.size / 2, y - self.size / 2)
        except Exception:
            pass

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.editor:
            reply = QMessageBox.question(
                None,
                "Eliminar nodo",
                f"¿Seguro que quieres eliminar el nodo ID {self.nodo.get('id')}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    self.editor.eliminar_nodo(self.nodo, self)
                finally:
                    event.accept()
            else:
                event.ignore()
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        # Marcar inicio de arrastre si el item es movible
        if event.button() == Qt.LeftButton and (self.flags() & QGraphicsObject.ItemIsMovable):
            self._dragging = True
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        try:
            if change == QGraphicsObject.ItemPositionHasChanged:
                # Solo actualizar al finalizar el movimiento
                p = self.scenePos()
                cx = int(p.x() + self.size / 2)
                cy = int(p.y() + self.size / 2)
                
                # Actualizar modelo
                if hasattr(self.nodo, "set_posicion"):
                    self.nodo.set_posicion(cx, cy)
                else:
                    self.nodo.update({"X": cx, "Y": cy})
                
                # Emitir señal UNA sola vez
                self.moved.emit(self)
                
            return super().itemChange(change, value)
        except Exception as err:
            print("Error en itemChange:", err)
            return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        try:
            if self._dragging:
                p = self.scenePos()
                cx = int(p.x() + self.size / 2)
                cy = int(p.y() + self.size / 2)
                
                # Actualizar modelo
                if hasattr(self.nodo, "set_posicion"):
                    self.nodo.set_posicion(cx, cy)
                else:
                    self.nodo.update({"X": cx, "Y": cy})
                
                # Emitir señal - IMPORTANTE: solo una vez
                self.moved.emit(self)
                
        except Exception as err:
            print("Error al procesar mouseReleaseEvent:", err)
        finally:
            self._dragging = False
            super().mouseReleaseEvent(event)