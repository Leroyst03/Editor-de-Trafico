from PyQt5.QtWidgets import QGraphicsObject, QMessageBox, QGraphicsItem
from PyQt5.QtCore import QRectF, Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QBrush, QPainter,QPainterPath, QPen, QColor, QFont, QCursor, QPixmap, QImage
from Model.Nodo import Nodo
import os

class NodoItem(QGraphicsObject):
    moved = pyqtSignal(object)  # emite (id, x, y) o el objeto nodo según preferencia
    movimiento_iniciado = pyqtSignal(object, int, int)  # Señal para inicio de movimiento: (nodo, x_inicial, y_inicial)
    # NUEVA SEÑAL: cuando el nodo es seleccionado
    nodo_seleccionado = pyqtSignal(object)
    # NUEVAS SEÑALES: para eventos hover
    hover_entered = pyqtSignal(object)  # Emite self cuando el ratón entra
    hover_leaved = pyqtSignal(object)   # Emite self cuando el ratón sale

    def __init__(self, nodo: Nodo, size=35, editor=None):  # Tamaño moderado para mejor visibilidad
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

        # NUEVO: Activar eventos hover
        self.setAcceptHoverEvents(True)

        # Estado interno para detectar arrastre
        self._dragging = False
        self._posicion_inicial = None  # Para guardar posición al inicio del arrastre

        # Cargar imágenes de iconos
        self._cargar_pixmap = None
        self._descargar_pixmap = None
        self._cargador_pixmap = None
        self._cargar_icono_optimizado()
        
        # Obtener parámetros del nodo
        self.objetivo = self.nodo.get("objetivo", 0) if hasattr(self.nodo, "get") else getattr(self.nodo, "objetivo", 0)
        self.es_cargador = self.nodo.get("es_cargador", 0) if hasattr(self.nodo, "get") else getattr(self.nodo, "es_cargador", 0)
        
        # Definir qué mostrar según las reglas
        self._determinar_visualizacion()
        
        # Colores para estados especiales (ahora solo para nodos sin iconos)
        self.color_selected = QColor(255, 255, 255)   # Blanco para selección (borde)
        self.color_route_selected = QColor(255, 165, 0)  # Naranja para nodos en ruta seleccionada
        
        # Color de borde normal
        self.border_color = Qt.black

    def _cargar_png_con_calidad(self, path, target_size):
        """Carga PNG con máxima calidad usando técnica de escalado optimizado"""
        if not os.path.exists(path):
            return None
            
        # Cargar como QImage para mejor control
        image = QImage(path)
        
        # Convertir a formato ARGB32 si no lo está (para transparencia)
        if image.format() != QImage.Format_ARGB32:
            image = image.convertToFormat(QImage.Format_ARGB32)
        
        # Si la imagen es muy pequeña o muy grande, escalar en dos pasos
        original_width = image.width()
        original_height = image.height()
        
        # Determinar el mejor enfoque de escalado
        if original_width < target_size * 0.5 or original_width > target_size * 2:
            # Escalar a un tamaño intermedio (múltiplo de 2)
            intermediate_size = target_size * 2
            scaled_image = image.scaled(
                intermediate_size, intermediate_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            # Luego escalar al tamaño final
            scaled_image = scaled_image.scaled(
                target_size, target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        else:
            # Escalar directamente al tamaño deseado
            scaled_image = image.scaled(
                target_size, target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        
        return QPixmap.fromImage(scaled_image)

    def _cargar_icono_optimizado(self):
        """Carga y optimiza iconos PNG para máxima nitidez"""
        try:
            # Obtener el directorio base del proyecto
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_dir = os.path.join(base_dir, "Static", "Icons")
            
            # Lista de tamaños preferidos (de mayor a menor calidad)
            preferred_sizes = [
                self.size * 4,  # 140x140 para 35px final (alta densidad)
                self.size * 2,  # 70x70
                self.size,      # 35x35
                128,            # Tamaño estándar
                64,
                32
            ]
            
            # Función para encontrar el mejor icono disponible
            def encontrar_mejor_icono(nombre):
                # 1. Buscar en carpetas de tamaño específico
                for size in preferred_sizes:
                    # Buscar en carpeta específica (ej: "70x70/cargar.png")
                    specific_dir = os.path.join(icon_dir, f"{size}x{size}")
                    specific_path = os.path.join(specific_dir, f"{nombre}.png")
                    if os.path.exists(specific_path):
                        print(f"✓ Encontrado {nombre} en tamaño específico {size}x{size}")
                        return self._cargar_png_con_calidad(specific_path, self.size)
                
                # 2. Buscar en la raíz con tamaño específico en nombre (ej: "cargar_70x70.png")
                for size in preferred_sizes:
                    sized_path = os.path.join(icon_dir, f"{nombre}_{size}x{size}.png")
                    if os.path.exists(sized_path):
                        print(f"✓ Encontrado {nombre}_{size}x{size}.png")
                        return self._cargar_png_con_calidad(sized_path, self.size)
                
                # 3. Buscar en la raíz sin tamaño
                root_path = os.path.join(icon_dir, f"{nombre}.png")
                if os.path.exists(root_path):
                    print(f"✓ Encontrado {nombre}.png en raíz")
                    return self._cargar_png_con_calidad(root_path, self.size)
                
                return None
            
            # Cargar cada icono con la mejor calidad disponible
            self._cargar_pixmap = encontrar_mejor_icono("cargar")
            self._descargar_pixmap = encontrar_mejor_icono("descargar")
            self._cargador_pixmap = encontrar_mejor_icono("bateria")
            
            # Si algún icono no se encontró, crear alternativo
            if self._cargar_pixmap is None or self._cargar_pixmap.isNull():
                self._cargar_pixmap = self._crear_icono_vectorial("cargar")
                print("⚠ Creado icono alternativo para 'cargar'")
            
            if self._descargar_pixmap is None or self._descargar_pixmap.isNull():
                self._descargar_pixmap = self._crear_icono_vectorial("descargar")
                print("⚠ Creado icono alternativo para 'descargar'")
            
            if self._cargador_pixmap is None or self._cargador_pixmap.isNull():
                self._cargador_pixmap = self._crear_icono_vectorial("cargador")
                print("⚠ Creado icono alternativo para 'bateria'")
                
        except Exception as e:
            print(f"Error cargando iconos optimizados: {e}")
            # Crear iconos alternativos
            self._cargar_pixmap = self._crear_icono_vectorial("cargar")
            self._descargar_pixmap = self._crear_icono_vectorial("descargar")
            self._cargador_pixmap = self._crear_icono_vectorial("cargador")

    def _crear_icono_vectorial(self, tipo):
        """Crea iconos vectoriales personalizados con alta calidad"""
        # Crear a mayor resolución para luego escalar
        canvas_size = self.size * 4  # Crear a 4x la resolución
        pixmap = QPixmap(canvas_size, canvas_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHints(
            QPainter.Antialiasing | 
            QPainter.TextAntialiasing | 
            QPainter.SmoothPixmapTransform |
            QPainter.HighQualityAntialiasing
        )
        
        rect = QRectF(0, 0, canvas_size, canvas_size)
        
        # Configuración común
        border_width = 4  # Ancho del borde a alta resolución
        
        if tipo == "cargar":
            # Icono de cargar (flecha arriba)
            color = QColor(0, 150, 0)  # Verde oscuro
            
            # Dibujar círculo de fondo
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, border_width))
            painter.drawEllipse(rect.adjusted(border_width, border_width, -border_width, -border_width))
            
            # Dibujar flecha hacia arriba
            center = rect.center()
            arrow_size = canvas_size * 0.25
            
            # Crear forma de flecha
            arrow = QPainterPath()
            arrow.moveTo(center.x(), center.y() - arrow_size)
            arrow.lineTo(center.x() - arrow_size * 0.6, center.y())
            arrow.lineTo(center.x() - arrow_size * 0.3, center.y())
            arrow.lineTo(center.x() - arrow_size * 0.3, center.y() + arrow_size * 0.5)
            arrow.lineTo(center.x() + arrow_size * 0.3, center.y() + arrow_size * 0.5)
            arrow.lineTo(center.x() + arrow_size * 0.3, center.y())
            arrow.lineTo(center.x() + arrow_size * 0.6, center.y())
            arrow.closeSubpath()
            
            painter.setBrush(Qt.white)
            painter.setPen(QPen(Qt.white, border_width))
            painter.drawPath(arrow)
            
        elif tipo == "descargar":
            # Icono de descargar (flecha abajo)
            color = QColor(150, 0, 0)  # Rojo oscuro
            
            # Dibujar círculo de fondo
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, border_width))
            painter.drawEllipse(rect.adjusted(border_width, border_width, -border_width, -border_width))
            
            # Dibujar flecha hacia abajo
            center = rect.center()
            arrow_size = canvas_size * 0.25
            
            # Crear forma de flecha
            arrow = QPainterPath()
            arrow.moveTo(center.x(), center.y() + arrow_size)
            arrow.lineTo(center.x() - arrow_size * 0.6, center.y())
            arrow.lineTo(center.x() - arrow_size * 0.3, center.y())
            arrow.lineTo(center.x() - arrow_size * 0.3, center.y() - arrow_size * 0.5)
            arrow.lineTo(center.x() + arrow_size * 0.3, center.y() - arrow_size * 0.5)
            arrow.lineTo(center.x() + arrow_size * 0.3, center.y())
            arrow.lineTo(center.x() + arrow_size * 0.6, center.y())
            arrow.closeSubpath()
            
            painter.setBrush(Qt.white)
            painter.setPen(QPen(Qt.white, border_width))
            painter.drawPath(arrow)
            
        else:  # cargador
            # Icono de cargador (batería)
            color = QColor(255, 165, 0)  # Naranja
            
            # Dibujar círculo de fondo
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, border_width))
            painter.drawEllipse(rect.adjusted(border_width, border_width, -border_width, -border_width))
            
            # Dibujar símbolo de batería/rayo
            center = rect.center()
            bolt_size = canvas_size * 0.3
            
            # Crear forma de rayo
            bolt = QPainterPath()
            bolt.moveTo(center.x() + bolt_size * 0.3, center.y() - bolt_size * 0.4)
            bolt.lineTo(center.x() - bolt_size * 0.3, center.y() - bolt_size * 0.1)
            bolt.lineTo(center.x() + bolt_size * 0.1, center.y() - bolt_size * 0.1)
            bolt.lineTo(center.x() - bolt_size * 0.3, center.y() + bolt_size * 0.4)
            bolt.lineTo(center.x() + bolt_size * 0.3, center.y() + bolt_size * 0.1)
            bolt.lineTo(center.x() - bolt_size * 0.1, center.y() + bolt_size * 0.1)
            bolt.closeSubpath()
            
            painter.setBrush(Qt.white)
            painter.setPen(QPen(Qt.white, border_width))
            painter.drawPath(bolt)
        
        painter.end()
        
        # Escalar al tamaño final con alta calidad
        return pixmap.scaled(
            self.size, self.size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

    def _determinar_visualizacion(self):
        """Determina qué visualización usar según las reglas"""
        # Prioridad 1: es_cargador != 0
        if self.es_cargador != 0:
            self.mostrar_icono = True
            self.icono_actual = self._cargador_pixmap
            self.texto = "CARGADOR"
            self.con_horquilla = False
            return
        
        # Prioridad 2: objetivo = 1 (cargar)
        if self.objetivo == 1:
            self.mostrar_icono = True
            self.icono_actual = self._cargar_pixmap
            self.texto = "CARGAR"
            self.con_horquilla = False
            return
            
        # Prioridad 3: objetivo = 2 (descargar)
        if self.objetivo == 2:
            self.mostrar_icono = True
            self.icono_actual = self._descargar_pixmap
            self.texto = "DESCARGAR"
            self.con_horquilla = False
            return
            
        # Caso 4: objetivo = 3 (mantener comportamiento actual)
        if self.objetivo == 3:
            self.mostrar_icono = False
            self.color_io = QColor("darkViolet")
            self.texto = "I/O"
            self.con_horquilla = False
            return
            
        # Caso por defecto: sin objetivo especial
        self.mostrar_icono = False
        self.color_default = QColor(0, 120, 215)
        self.texto = str(self.nodo.get('id', ''))
        self.con_horquilla = True

    def boundingRect(self):
        return QRectF(0, 0, self.size, self.size)

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        
        # Configuración de renderizado de ALTA CALIDAD
        painter.setRenderHints(
            QPainter.Antialiasing | 
            QPainter.TextAntialiasing | 
            QPainter.SmoothPixmapTransform |
            QPainter.HighQualityAntialiasing
        )
        
        painter.translate(self.size / 2, self.size / 2)
        angle = int(self.nodo.get("A", 0))  # Leemos el angulo
        painter.rotate(360 - angle)
        painter.translate(-self.size / 2, -self.size / 2)

        if self.mostrar_icono and self.icono_actual and not self.icono_actual.isNull():
            # Calcular posición para centrar el icono con coordenadas enteras
            icon_width = self.icono_actual.width()
            icon_height = self.icono_actual.height()
            
            # Asegurar que las coordenadas sean enteras para evitar subpixelado
            x = round((self.size - icon_width) / 2)
            y = round((self.size - icon_height) / 2)
            
            # Asegurar que esté dentro de los límites
            x = max(0, x)
            y = max(0, y)
            
            # Crear rectángulo con coordenadas enteras
            icon_rect = QRectF(x, y, icon_width, icon_height)
            
            # Dibujar el icono con alta calidad
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.drawPixmap(icon_rect, self.icono_actual, 
                             QRectF(0, 0, self.icono_actual.width(), self.icono_actual.height()))
            
            # Borde fino y oscuro para mejor contraste
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(50, 50, 50), 1))  # Gris oscuro, 1px
            painter.drawEllipse(0, 0, self.size, self.size)
        else:
            # Comportamiento original para nodos sin iconos
            if self.objetivo == 3:
                # Nodo I/O (objetivo = 3)
                painter.setBrush(QBrush(self.color_io))
                painter.setPen(QPen(self.border_color, 2))
                painter.drawEllipse(self.boundingRect())
                
                # Configurar fuente para el texto
                font = QFont()
                font.setPointSize(9)
                font.setBold(True)
                painter.setFont(font)
                
                # Dibujar el texto en el centro
                painter.setPen(QPen(Qt.black, 1))
                text_rect = self.boundingRect()
                painter.drawText(text_rect, Qt.AlignCenter, self.texto)
                
            else:
                # Nodo por defecto (objetivo = 0)
                painter.setBrush(QBrush(self.color_default))
                painter.setPen(QPen(self.border_color, 2))
                painter.drawEllipse(self.boundingRect())

                # Si el nodo tiene horquilla (objetivo=0 o sin objetivo)
                if self.con_horquilla:
                    center_y = self.size / 2

                    # Parámetros de las horquillas ORIGINALES (no aumentadas)
                    fork_length = 15   # longitud de cada horquilla
                    fork_gap = 6       # separación entre las dos horquillas
                    offset_from_node = 1  # separación desde el borde izquierdo del nodo

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
                font.setPointSize(9)
                font.setBold(True)
                painter.setFont(font)

                # Dibujar el texto en el centro
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
            # Notificar al editor que terminó el arrastre
            if self.editor:
                print("Llamando a nodo_arrastre_terminado")
                self.editor.nodo_arrastre_terminado()
            super().mouseReleaseEvent(event)
    
    def hoverEnterEvent(self, event):
        """Cuando el ratón entra en el nodo"""
        print(f"HoverEnter en nodo {self.nodo.get('id')}")
        if self.editor:
            self.editor.nodo_hover_entered(self)
        self.hover_entered.emit(self)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Cuando el ratón sale del nodo"""
        print(f"HoverLeave en nodo {self.nodo.get('id')}")
        if self.editor:
            self.editor.nodo_hover_leaved(self)
        self.hover_leaved.emit(self)
        super().hoverLeaveEvent(event)