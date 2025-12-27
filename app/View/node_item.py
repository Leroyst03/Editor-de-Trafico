from PyQt5.QtWidgets import QGraphicsObject, QMessageBox, QGraphicsItem
from PyQt5.QtCore import QRectF, Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QBrush, QPainter, QPainterPath, QPen, QColor, QFont, QCursor, QPixmap, QImage
from Model.Nodo import Nodo
import os

class NodoItem(QGraphicsObject):
    # Escala única para TODOS los iconos respecto al tamaño del nodo
    ICON_SCALE = 1.8

    moved = pyqtSignal(object)
    movimiento_iniciado = pyqtSignal(object, int, int)
    nodo_seleccionado = pyqtSignal(object)
    hover_entered = pyqtSignal(object)
    hover_leaved = pyqtSignal(object)

    def __init__(self, nodo: Nodo, size=70, editor=None):
        super().__init__()
        self.nodo = nodo
        self.size = size
        self.editor = editor
        
        self.z_value_original = 1
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        try:
            x = int(self.nodo.get("X", 0)) if hasattr(self.nodo, "get") else int(getattr(self.nodo, "X", 0))
            y = int(self.nodo.get("Y", 0)) if hasattr(self.nodo, "get") else int(getattr(self.nodo, "Y", 0))
        except Exception:
            x = y = 0

        self.setPos(x - self.size / 2, y - self.size / 2)

        self.setFlag(QGraphicsObject.ItemIsSelectable, True)
        self.setFlag(QGraphicsObject.ItemIsFocusable, True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setZValue(self.z_value_original)
        self.setAcceptHoverEvents(True)

        self._dragging = False
        self._posicion_inicial = None

        self._cargar_pixmap = None
        self._descargar_pixmap = None
        self._cargador_pixmap = None
        self._cargador_io_pixmap = None

        self._cargar_icono_optimizado()

        self.objetivo = self.nodo.get("objetivo", 0) if hasattr(self.nodo, "get") else getattr(self.nodo, "objetivo", 0)
        self.es_cargador = self.nodo.get("es_cargador", 0) if hasattr(self.nodo, "get") else getattr(self.nodo, "es_cargador", 0)

        self._determinar_visualizacion()

        self.color_selected = QColor(255, 255, 255)
        self.color_route_selected = QColor(255, 165, 0)
        self.border_color = Qt.black

    # ============================================================
    # VARIANTE 1 — RECORTE AUTOMÁTICO DEL CONTENIDO REAL DEL PNG
    # ============================================================

    def _recortar_contenido(self, image: QImage):
        """Recorta automáticamente el área donde hay píxeles no transparentes."""
        w = image.width()
        h = image.height()

        min_x, min_y = w, h
        max_x, max_y = 0, 0

        for y in range(h):
            for x in range(w):
                if image.pixelColor(x, y).alpha() > 0:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if min_x > max_x or min_y > max_y:
            return image  # imagen vacía

        return image.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

    def _cargar_png_con_calidad(self, path, target_size):
        """Carga PNG, recorta contenido real, normaliza y escala."""
        if not os.path.exists(path):
            return None

        image = QImage(path)
        if image.format() != QImage.Format_ARGB32:
            image = image.convertToFormat(QImage.Format_ARGB32)

        # 1. Recortar contenido real
        recortada = self._recortar_contenido(image)

        # 2. Escalar manteniendo proporción
        scaled = recortada.scaled(
            target_size,
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # 3. Canvas cuadrado uniforme
        canvas = QImage(target_size, target_size, QImage.Format_ARGB32)
        canvas.fill(Qt.transparent)

        painter = QPainter(canvas)
        painter.setRenderHints(
            QPainter.Antialiasing |
            QPainter.SmoothPixmapTransform |
            QPainter.HighQualityAntialiasing
        )

        x = (target_size - scaled.width()) // 2
        y = (target_size - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
        painter.end()

        return QPixmap.fromImage(canvas)

    # ============================================================
    # CARGA DE ICONOS
    # ============================================================

    def _cargar_icono_optimizado(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_dir = os.path.join(base_dir, "Static", "Icons")

            icon_target_size = int(self.size * self.ICON_SCALE)

            preferred_sizes = [
                icon_target_size * 4,
                icon_target_size * 2,
                icon_target_size,
                128,
                64,
                32
            ]

            def encontrar_mejor_icono(nombre):
                for size in preferred_sizes:
                    specific_dir = os.path.join(icon_dir, f"{size}x{size}")
                    specific_path = os.path.join(specific_dir, f"{nombre}.png")
                    if os.path.exists(specific_path):
                        return self._cargar_png_con_calidad(specific_path, icon_target_size)

                for size in preferred_sizes:
                    sized_path = os.path.join(icon_dir, f"{nombre}_{size}x{size}.png")
                    if os.path.exists(sized_path):
                        return self._cargar_png_con_calidad(sized_path, icon_target_size)

                root_path = os.path.join(icon_dir, f"{nombre}.png")
                if os.path.exists(root_path):
                    return self._cargar_png_con_calidad(root_path, icon_target_size)

                return None

            self._cargar_pixmap = encontrar_mejor_icono("cargar")
            self._descargar_pixmap = encontrar_mejor_icono("descargar")
            self._cargador_pixmap = encontrar_mejor_icono("bateria")
            self._cargador_io_pixmap = encontrar_mejor_icono("cargadorIO")

        except Exception as e:
            print(f"Error cargando iconos optimizados: {e}")

    # ============================================================
    # LÓGICA DE VISUALIZACIÓN
    # ============================================================

    def _determinar_visualizacion(self):
        if self.es_cargador != 0:
            self.mostrar_icono = True
            self.icono_actual = self._cargador_pixmap
            return

        if self.objetivo == 1:
            self.mostrar_icono = True
            self.icono_actual = self._cargar_pixmap
            return

        if self.objetivo == 2:
            self.mostrar_icono = True
            self.icono_actual = self._descargar_pixmap
            return

        if self.objetivo == 3:
            self.mostrar_icono = True
            self.icono_actual = self._cargador_io_pixmap
            return

        self.mostrar_icono = False
        self.color_default = QColor(0, 120, 215)
        self.texto = str(self.nodo.get('id', ''))
        self.con_horquilla = True

    # ============================================================
    # DIBUJADO
    # ============================================================

    def boundingRect(self):
        extra_margin = 10
        return QRectF(-extra_margin, -extra_margin,
                      self.size + extra_margin * 2,
                      self.size + extra_margin * 2)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        painter.setRenderHints(
            QPainter.Antialiasing |
            QPainter.TextAntialiasing |
            QPainter.SmoothPixmapTransform |
            QPainter.HighQualityAntialiasing
        )

        margin = 10

        painter.translate(self.size / 2, self.size / 2)
        angle = int(self.nodo.get("A", 0))
        painter.rotate(360 - angle)
        painter.translate(-self.size / 2, -self.size / 2)

        if self.mostrar_icono and self.icono_actual:
            icon_size = int(self.size * self.ICON_SCALE)
            x = (self.size - icon_size) / 2
            y = (self.size - icon_size) / 2

            icon_rect = QRectF(x, y, icon_size, icon_size)

            painter.drawPixmap(
                icon_rect,
                self.icono_actual,
                QRectF(0, 0, self.icono_actual.width(), self.icono_actual.height())
            )

        else:
            painter.setBrush(QBrush(self.color_default))
            painter.setPen(QPen(self.border_color, 2))
            painter.drawEllipse(self.boundingRect().adjusted(margin, margin, -margin, -margin))

            if self.con_horquilla:
                center_y = self.size / 2
                fork_length = 15
                fork_gap = 6
                offset_from_node = 13.5

                x_start = margin - offset_from_node
                x_end = x_start - fork_length

                y_top = center_y - fork_gap / 2
                y_bottom = center_y + fork_gap / 2

                pen = QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap)
                painter.setPen(pen)
                painter.drawLine(QPointF(x_start, y_top), QPointF(x_end, y_top))
                painter.drawLine(QPointF(x_start, y_bottom), QPointF(x_end, y_bottom))

            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)

            text_rect = self.boundingRect().adjusted(margin, margin, -margin, -margin)
            painter.setPen(QPen(Qt.white, 1))
            painter.drawText(text_rect, Qt.AlignCenter, self.texto)

        if self.isSelected():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(self.color_selected, 3))
            painter.drawEllipse(self.boundingRect().adjusted(margin + 2, margin + 2,
                                                             -margin - 2, -margin - 2))

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
        """Actualiza la visualización cuando cambian los parámetros del nodo"""
        # Actualizar valores del nodo
        self.objetivo = self.nodo.get("objetivo", 0) if hasattr(self.nodo, "get") else getattr(self.nodo, "objetivo", 0)
        self.es_cargador = self.nodo.get("es_cargador", 0) if hasattr(self.nodo, "get") else getattr(self.nodo, "es_cargador", 0)
        
        # Re-determinar visualización
        self._determinar_visualizacion()
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
        print(f"MousePress en nodo {self.nodo.get('id')}")
        
        # Marcar inicio de arrastre si el item es movible
        if event.button() == Qt.LeftButton and (self.flags() & QGraphicsObject.ItemIsMovable):
            self._dragging = True
            # Guardar posición inicial
            scene_pos = self.scenePos()
            x_centro = int(scene_pos.x() + self.size / 2)
            y_centro = int(scene_pos.y() + self.size / 2)
            self._posicion_inicial = (x_centro, y_centro)
            
            # Notificar al editor que se inició el arrastre
            if self.editor:
                print("Llamando a nodo_arrastre_iniciado")
                self.editor.nodo_arrastre_iniciado()
            
            # También para el historial
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
        print(f"MouseRelease en nodo {self.nodo.get('id')}")
        
        try:
            if self._dragging and self._posicion_inicial:
                p = self.scenePos()
                cx = int(p.x() + self.size / 2)
                cy = int(p.y() + self.size / 2)
                
                # Verificar si hubo movimiento
                x_inicial, y_inicial = self._posicion_inicial
                if cx != x_inicial or cy != y_inicial:
                    if self.editor and hasattr(self.editor, 'registrar_movimiento_finalizado'):
                        self.editor.registrar_movimiento_finalizado(self, x_inicial, y_inicial, cx, cy)
                
                self._posicion_inicial = None
                
        except Exception as err:
            print(f"Error en mouseReleaseEvent: {err}")
        finally:
            self._dragging = False
            # CRÍTICO: Notificar al editor que terminó el arrastre
            if self.editor:
                print("Llamando a nodo_arrastre_terminado desde mouseReleaseEvent")
                # Forzar la actualización del cursor
                self.editor._arrastrando_nodo = False
                # Primero actualizar estado hover
                pos = event.scenePos()
                items = self.scene().items(pos)
                hay_nodo = any(isinstance(it, NodoItem) for it in items)
                self.editor._cursor_sobre_nodo = hay_nodo
                # Luego actualizar cursor
                self.editor._actualizar_cursor()
            super().mouseReleaseEvent(event)
    
    def hoverEnterEvent(self, event):
        """Cuando el ratón entra en el nodo"""
        print(f"HoverEnter en nodo {self.nodo.get('id')}")
        if self.editor:
            self.editor.nodo_hover_entered(self)
        self.hover_entered.emit(self)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Cuando el ratón sale del nodo - MEJORADO"""
        print(f"HoverLeave en nodo {self.nodo.get('id')}")
        
        # Solo procesar si no estamos arrastrando
        if not self._dragging:
            if self.editor:
                # Verificar si el cursor realmente salió de TODOS los nodos
                pos = event.scenePos()
                items = self.scene().items(pos)
                
                # Contar nodos bajo el cursor
                nodos_bajo_cursor = [it for it in items if isinstance(it, NodoItem)]
                
                if len(nodos_bajo_cursor) == 0:
                    # Realmente salió de todos los nodos
                    self.editor._cursor_sobre_nodo = False
                    print(f"Cursor realmente salió de nodo {self.nodo.get('id')}")
                else:
                    # Todavía está sobre otro nodo (superposición)
                    print(f"Cursor sigue sobre {len(nodos_bajo_cursor)} nodos")
                    self.editor._cursor_sobre_nodo = True
            
            self.hover_leaved.emit(self)
        
        super().hoverLeaveEvent(event)