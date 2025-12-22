from PyQt5.QtWidgets import QGraphicsObject, QMessageBox, QGraphicsItem
from PyQt5.QtCore import QRectF, Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QBrush, QPainter, QPen, QColor, QFont
from Model.Nodo import Nodo

class NodoItem(QGraphicsObject):
    moved = pyqtSignal(object)  # emite (id, x, y) o el objeto nodo según preferencia
    movimiento_iniciado = pyqtSignal(object, int, int)  # Señal para inicio de movimiento: (nodo, x_inicial, y_inicial)
    # NUEVA SEÑAL: cuando el nodo es seleccionado
    nodo_seleccionado = pyqtSignal(object)

    def __init__(self, nodo: Nodo, size=20, editor=None):
        super().__init__()
        self.nodo = nodo
        self.size = size
        self.editor = editor
        
        # Valor z original para restaurar después
        self.z_value_original = 1

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
        self.setZValue(self.z_value_original)

        # Estado interno para detectar arrastre
        self._dragging = False
        self._posicion_inicial = None  # Para guardar posición al inicio del arrastre

        # Colores configurables según objetivo
        self.color_in = QColor("darkGreen")        # Verde para IN
        self.color_out = QColor("darkRed")       # Rojo para OUT
        self.color_io = QColor("darkViolet")      # Amarillo para I/O
        self.color_default = QColor(0, 120, 215) # Azul por defecto si no hay objetivo
        
        # Colores para estados especiales
        self.color_selected = QColor(255, 255, 255)   # Blanco para selección (borde)
        self.color_route_selected = QColor(255, 165, 0)  # Naranja para nodos en ruta seleccionada
        
        # Obtener objetivo del nodo
        self.objetivo = self.nodo.get("objetivo", 0) if hasattr(self.nodo, "get") else getattr(self.nodo, "objetivo", 0)
        
        # Definir color de relleno según objetivo
        if self.objetivo == 1:
            self.fill_color = self.color_in
            self.texto = "IN"
            self.con_horquilla = False  # Sin horquilla para IN
        elif self.objetivo == 2:
            self.fill_color = self.color_out
            self.texto = "OUT"
            self.con_horquilla = False  # Sin horquilla para OUT
        elif self.objetivo == 3:
            self.fill_color = self.color_io
            self.texto = "I/O"
            self.con_horquilla = False  # Sin horquilla para I/O
        else:
            self.fill_color = self.color_default
            self.texto = str(self.nodo.get('id', ''))
            self.con_horquilla = True  # Con horquilla para nodos comunes
        
        # Color de borde normal
        self.border_color = Qt.black

    def boundingRect(self):
        return QRectF(0, 0, self.size, self.size)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        
        painter.translate(self.size / 2, self.size / 2)
        angle = int(self.nodo.get("A", 0))  # Leemos el angulo
        painter.rotate(360 - angle)
        painter.translate(-self.size / 2, -self.size / 2)

        # Dibujar círculo con color según objetivo
        painter.setBrush(QBrush(self.fill_color))
        painter.setPen(QPen(self.border_color, 2))
        painter.drawEllipse(self.boundingRect())

        # Si el nodo tiene horquilla (objetivo=0 o sin objetivo)
        if self.con_horquilla:
            center_y = self.size / 2

            # Parámetros de las horquillas
            fork_length = 15   # longitud de cada horquilla (hacia la izquierda)
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

        # Configurar fuente para el texto
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)

        # Dibujar el texto en el centro
        if self.objetivo in [1, 2, 3]:  # Para IN, OUT, I/O usar color negro
            painter.setPen(QPen(Qt.black, 1))
        else:  # Para nodos comunes usar color blanco
            painter.setPen(QPen(Qt.white, 1))
            
        text_rect = self.boundingRect()
        painter.drawText(text_rect, Qt.AlignCenter, self.texto)

        # Si está seleccionado, dibujar un borde adicional
        if self.isSelected():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(self.color_selected, 3))
            painter.drawEllipse(self.boundingRect().adjusted(2, 2, -2, -2))

        painter.restore()

    def set_selected_color(self):
        """Cambia al color de selección (borde blanco)"""
        self.border_color = self.color_selected
        self.update()

    def set_route_selected_color(self):
        """Cambia al color para nodos en ruta seleccionada (borde naranja)"""
        self.border_color = self.color_route_selected
        self.update()

    def set_normal_color(self):
        """Vuelve al color normal (borde negro)"""
        self.border_color = Qt.black
        self.update()

    def actualizar_posicion(self):
        # Mantener la posición visual sincronizada con el modelo (centrado)
        try:
            x = int(self.nodo.get("X", 0)) if hasattr(self.nodo, "get") else int(getattr(self.nodo, "X", 0))
            y = int(self.nodo.get("Y", 0)) if hasattr(self.nodo, "get") else int(getattr(self.nodo, "Y", 0))
            self.setPos(x - self.size / 2, y - self.size / 2)
        except Exception:
            pass

    def actualizar_objetivo(self):
        """Actualiza el color y texto cuando cambia el campo objetivo"""
        self.objetivo = self.nodo.get("objetivo", 0) if hasattr(self.nodo, "get") else getattr(self.nodo, "objetivo", 0)
        
        # Definir color de relleno y texto según objetivo
        if self.objetivo == 1:
            self.fill_color = self.color_in
            self.texto = "IN"
            self.con_horquilla = False  # Sin horquilla para IN
        elif self.objetivo == 2:
            self.fill_color = self.color_out
            self.texto = "OUT"
            self.con_horquilla = False  # Sin horquilla para OUT
        elif self.objetivo == 3:
            self.fill_color = self.color_io
            self.texto = "I/O"
            self.con_horquilla = False  # Sin horquilla para I/O
        else:
            self.fill_color = self.color_default
            self.texto = str(self.nodo.get('id', ''))
            self.con_horquilla = True  # Con horquilla para nodos comunes
        
        self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.editor:
            # Seleccionar este nodo primero
            self.setSelected(True)
            # Llamar al método del editor que ahora incluye confirmación
            self.editor.eliminar_nodo_seleccionado()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        # Marcar inicio de arrastre si el item es movible
        if event.button() == Qt.LeftButton and (self.flags() & QGraphicsObject.ItemIsMovable):
            self._dragging = True
            # Guardar posición inicial al iniciar el arrastre
            scene_pos = self.scenePos()
            x_centro = int(scene_pos.x() + self.size / 2)
            y_centro = int(scene_pos.y() + self.size / 2)
            self._posicion_inicial = (x_centro, y_centro)
            
            # Emitir señal de movimiento iniciado
            if self.editor and hasattr(self.editor, 'registrar_movimiento_iniciado'):
                self.editor.registrar_movimiento_iniciado(self, x_centro, y_centro)
        
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        try:
            if change == QGraphicsObject.ItemSelectedChange:
                # Cuando el nodo es seleccionado
                if value:  # Si se está seleccionando
                    # Guardar el valor z original
                    self.z_value_original = self.zValue()
                    # Establecer un valor z muy alto para que esté encima de todos
                    self.setZValue(1000)
                    # Emitir señal de nodo seleccionado
                    if self.editor:
                        self.nodo_seleccionado.emit(self)
                else:  # Si se está deseleccionando
                    # Restaurar el valor z original
                    self.setZValue(self.z_value_original)
            
            # CRÍTICO: Emitir moved DURANTE el arrastre (ItemPositionChange)
            if change == QGraphicsObject.ItemPositionChange:
                # Obtener la nueva posición propuesta
                new_pos = value
                cx = int(new_pos.x() + self.size / 2)
                cy = int(new_pos.y() + self.size / 2)
                
                # DEBUG: Verificar estructura del nodo
                if hasattr(self.nodo, "__dict__"):
                    print(f"DEBUG NodoItem: nodo es objeto con id={getattr(self.nodo, 'id', 'NO ID')}")
                elif isinstance(self.nodo, dict):
                    print(f"DEBUG NodoItem: nodo es dict con id={self.nodo.get('id', 'NO ID')}")
                else:
                    print(f"DEBUG NodoItem: nodo tipo={type(self.nodo)}")
                
                # Actualizar modelo temporalmente durante el arrastre
                if hasattr(self.nodo, "set_posicion"):
                    self.nodo.set_posicion(cx, cy)
                elif hasattr(self.nodo, "update"):
                    # Asegurar que el nodo tenga ID antes de actualizar
                    if isinstance(self.nodo, dict):
                        self.nodo["X"] = cx
                        self.nodo["Y"] = cy
                        print(f"DEBUG NodoItem: Actualizado dict nodo {self.nodo.get('id')} a ({cx}, {cy})")
                    else:
                        # Si es un objeto Nodo, usar update
                        self.nodo.update({"X": cx, "Y": cy})
                        print(f"DEBUG NodoItem: Actualizado objeto nodo con update")
                else:
                    # Fallback: intentar establecer directamente
                    try:
                        setattr(self.nodo, "X", cx)
                        setattr(self.nodo, "Y", cy)
                        print(f"DEBUG NodoItem: Actualizado con setattr")
                    except:
                        pass
                
                # EMITIR SEÑAL DURANTE EL ARRASTRE - ESTO ES CLAVE
                print(f"DEBUG NodoItem: Emitiendo moved para nodo_item")
                self.moved.emit(self)
                return value
                
            if change == QGraphicsObject.ItemPositionHasChanged:
                # Al finalizar el movimiento
                p = self.scenePos()
                cx = int(p.x() + self.size / 2)
                cy = int(p.y() + self.size / 2)
                
                print(f"DEBUG NodoItem: ItemPositionHasChanged - posición final ({cx}, {cy})")
                
                # Actualizar modelo
                if hasattr(self.nodo, "set_posicion"):
                    self.nodo.set_posicion(cx, cy)
                elif hasattr(self.nodo, "update"):
                    if isinstance(self.nodo, dict):
                        self.nodo["X"] = cx
                        self.nodo["Y"] = cy
                    else:
                        self.nodo.update({"X": cx, "Y": cy})
                
                # Emitir señal al final también
                self.moved.emit(self)
                
            return super().itemChange(change, value)
        except Exception as err:
            print("Error en itemChange:", err)
            return super().itemChange(change, value)
    
    def mouseReleaseEvent(self, event):
        try:
            if self._dragging and self._posicion_inicial:
                p = self.scenePos()
                cx = int(p.x() + self.size / 2)
                cy = int(p.y() + self.size / 2)
                
                # Verificar si realmente hubo movimiento
                x_inicial, y_inicial = self._posicion_inicial
                if cx != x_inicial or cy != y_inicial:
                    # Registrar movimiento finalizado en el editor
                    if self.editor and hasattr(self.editor, 'registrar_movimiento_finalizado'):
                        self.editor.registrar_movimiento_finalizado(self, x_inicial, y_inicial, cx, cy)
                
                self._posicion_inicial = None
                
        except Exception as err:
            print("Error al procesar mouseReleaseEvent:", err)
        finally:
            self._dragging = False
            super().mouseReleaseEvent(event)