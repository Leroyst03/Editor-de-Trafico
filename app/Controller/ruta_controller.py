from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtWidgets import QListWidgetItem, QGraphicsLineItem
from PyQt5.QtGui import QPen
from View.node_item import NodoItem

class RutaController(QObject):
    def __init__(self, proyecto, view, editor):
        super().__init__()
        self.proyecto = proyecto
        self.view = view
        self.editor = editor
        self.activo = False

        # Estado de la ruta en construcción (como en la versión anterior)
        self._nodes_seq = []     # lista de objetos Nodo (orden)
        self._lines = []         # QGraphicsLineItem temporales (verdes)
        self._last_item = None   # último NodoItem visual añadido

    def activar(self):
        """Activa el modo de creación de rutas"""
        if not self.activo:
            self.view.marco_trabajo.viewport().installEventFilter(self)
            self.activo = True
            self._clear_state()
            print("✓ Modo Ruta activado")
            print("Instrucciones:")
            print("- Haz clic en nodos existentes o en el mapa para crear nuevos")
            print("- Los nodos se conectarán con líneas verdes")
            print("- Presiona ENTER para finalizar la ruta")
            print("- Presiona ESC para cancelar")
            print("- Haz clic en el botón de ruta nuevamente para terminar")

    def desactivar(self):
        """Desactiva el modo de creación de rutas - VERSIÓN SIMPLIFICADA COMO LA ANTERIOR"""
        if self.activo:
            # Finalizar la ruta en construcción (si procede) - EXACTAMENTE COMO LA VERSIÓN ANTERIOR
            self._finalize_route()
            self.view.marco_trabajo.viewport().removeEventFilter(self)
            self.activo = False
            self._clear_state()
            print("✗ Modo Ruta desactivado")

    def cancelar_ruta_actual(self):
        """Cancela la ruta actualmente en creación (con Escape)"""
        print("⚠ Cancelando creación de ruta")
        self._clear_state()

    def finalizar_ruta_con_enter(self):
        """Finaliza la ruta actualmente en creación con Enter"""
        if len(self._nodes_seq) < 2:
            print("⚠ No hay ruta en creación o tiene menos de 2 nodos")
            return
        
        print(f"✓ Finalizando ruta con Enter ({len(self._nodes_seq)} nodos)")
        self._finalize_route()

    def eventFilter(self, obj, event):
        """Filtra eventos del ratón para manejar clics en nodos y mapa"""
        # Solo procesar clicks de ratón en el viewport del QGraphicsView
        if obj is self.view.marco_trabajo.viewport() and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton and self.proyecto and self.activo:
                scene_pos = self.view.marco_trabajo.mapToScene(event.pos())
                # Mostrar en metros
                x_m = self.editor.pixeles_a_metros(scene_pos.x())
                y_m = self.editor.pixeles_a_metros(scene_pos.y())
                print(f"✓ Clic en mapa - Posición: ({x_m:.2f}, {y_m:.2f}) metros")
                
                # itemAt recibe coordenadas del viewport
                item = self.view.marco_trabajo.itemAt(event.pos())
                
                if isinstance(item, NodoItem):
                    print(f"✓ Clic en nodo existente ID {item.nodo.get('id')}")
                    self._add_existing_node(item)
                else:
                    # Crear nuevo nodo en la posición del clic
                    print(f"✓ Creando nuevo nodo en posición ({x_m:.2f}, {y_m:.2f}) metros")
                    self._create_and_add_node(int(scene_pos.x()), int(scene_pos.y()))
                return True
        return False

    # --- Métodos de la versión anterior que funcionaban ---
    def _create_and_add_node(self, x, y):
        """Crea un nuevo nodo y lo añade a la ruta (CORREGIDO para incluir botón de visibilidad)"""
        # Crear el nodo en el modelo
        nodo = self.proyecto.agregar_nodo(x, y)
        
        # Asegurar que el nodo tenga campo "objetivo"
        if isinstance(nodo, dict):
            if "objetivo" not in nodo:
                nodo["objetivo"] = 0
        elif not hasattr(nodo, "objetivo"):
            setattr(nodo, "objetivo", 0)
        
        # Crear visual mediante helper del editor
        try:
            nodo_item = self.editor._create_nodo_item(nodo)
        except Exception:
            nodo_item = NodoItem(nodo, editor=self.editor)
            nodo_item.setZValue(1)
            self.view.marco_trabajo.scene().addItem(nodo_item)
            try:
                nodo_item.moved.connect(self.editor.on_nodo_moved)
            except Exception:
                pass

        # --- CORRECCIÓN CRÍTICA: Usar el método del editor para inicializar visibilidad ---
        print(f"DEBUG RutaController: Inicializando visibilidad para nodo nuevo {nodo.get('id')}")
        self.editor._inicializar_nodo_visibilidad(nodo, agregar_a_lista=True)
        
        # Añadir a la secuencia de la ruta y dibujar segmento si hay anterior
        self._append_node_to_route(nodo, nodo_item)

    def _add_existing_node(self, nodo_item):
        """Añade un nodo existente a la ruta (CORREGIDO para asegurar visibilidad)"""
        nodo = nodo_item.nodo
        
        # --- CORRECCIÓN: Asegurar que el nodo esté en la lista lateral con widget ---
        # Verificar si el nodo ya está inicializado en el sistema de visibilidad
        nodo_id = nodo.get('id')
        
        if nodo_id is not None:
            # Verificar si el nodo ya está en el sistema de visibilidad del editor
            if nodo_id not in self.editor.visibilidad_nodos:
                print(f"DEBUG RutaController: Nodo existente {nodo_id} no tiene visibilidad, inicializando...")
                self.editor._inicializar_nodo_visibilidad(nodo, agregar_a_lista=True)
            else:
                # El nodo ya está en el sistema, solo verificar que esté en la lista lateral
                print(f"DEBUG RutaController: Nodo existente {nodo_id} ya tiene visibilidad")
                
                # Verificar si ya está en la lista lateral
                en_lista = False
                for i in range(self.view.nodosList.count()):
                    item = self.view.nodosList.item(i)
                    widget = self.view.nodosList.itemWidget(item)
                    if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
                        en_lista = True
                        break
                
                if not en_lista:
                    print(f"DEBUG RutaController: Nodo {nodo_id} no está en lista lateral, agregando...")
                    self.editor._inicializar_nodo_visibilidad(nodo, agregar_a_lista=True)
        
        # Añadir a la secuencia de la ruta
        self._append_node_to_route(nodo, nodo_item)

    def _append_node_to_route(self, nodo, nodo_item):
        """Añade un nodo a la secuencia de la ruta y dibuja líneas (versión anterior)"""
        # Primer nodo: solo añadir y marcar
        if not self._nodes_seq:
            self._nodes_seq.append(nodo)
            self._last_item = nodo_item
            try:
                nodo_item.setSelected(True)
                nodo_item.set_selected_color()
            except Exception:
                pass
            return

        # Evitar duplicados consecutivos
        if self._nodes_seq and self._nodes_seq[-1].get("id") == nodo.get("id"):
            return

        # Dibujar línea entre last_item y nodo_item
        p1 = self._last_item.scenePos()
        p2 = nodo_item.scenePos()
        line = QGraphicsLineItem(p1.x() + self._last_item.size/2, 
                               p1.y() + self._last_item.size/2,
                               p2.x() + nodo_item.size/2, 
                               p2.y() + nodo_item.size/2)
        pen = QPen(Qt.darkGreen, 2)  # Color diferente para líneas temporales
        line.setPen(pen)
        line.setZValue(0.6)  # Z-value entre las líneas rojas y los nodos
        line.setData(0, "ruta_temporal")  # Marcar como línea temporal
        self.view.marco_trabajo.scene().addItem(line)
        self._lines.append(line)

        # Conectar la señal moved de ambos nodos para actualizar líneas temporales
        try:
            self._last_item.moved.connect(self._update_temp_lines)
            nodo_item.moved.connect(self._update_temp_lines)
        except Exception:
            pass

        # Añadir nodo a la secuencia y actualizar last_item
        self._nodes_seq.append(nodo)
        self._last_item = nodo_item
        nodo_item.set_selected_color()

    def _update_temp_lines(self, nodo_item=None):
        """Actualiza todas las líneas temporales cuando un nodo se mueve"""
        if not self._lines or len(self._nodes_seq) < 2:
            return

        # Reconstruir todas las líneas temporales
        self._clear_temp_lines()
        
        # Redibujar todas las líneas entre los nodos en la secuencia
        for i in range(len(self._nodes_seq) - 1):
            # Buscar los NodoItems en la escena
            nodo1_item = None
            nodo2_item = None
            
            for item in self.view.marco_trabajo.scene().items():
                if isinstance(item, NodoItem):
                    if getattr(item, "nodo", None) == self._nodes_seq[i]:
                        nodo1_item = item
                    if getattr(item, "nodo", None) == self._nodes_seq[i + 1]:
                        nodo2_item = item
                
                if nodo1_item and nodo2_item:
                    break
            
            if nodo1_item and nodo2_item:
                p1 = nodo1_item.scenePos()
                p2 = nodo2_item.scenePos()
                line = QGraphicsLineItem(p1.x() + nodo1_item.size/2, 
                                       p1.y() + nodo1_item.size/2,
                                       p2.x() + nodo2_item.size/2, 
                                       p2.y() + nodo2_item.size/2)
                pen = QPen(Qt.darkGreen, 2)
                line.setPen(pen)
                line.setZValue(0.6)
                line.setData(0, "ruta_temporal")  # Marcar como línea temporal
                self.view.marco_trabajo.scene().addItem(line)
                self._lines.append(line)

    def _finalize_route(self):
        """Finaliza la ruta en construcción: guarda la ruta en el modelo (versión anterior mejorada)"""
        # Si no hay suficientes nodos, limpiar temporales y salir
        if len(self._nodes_seq) < 2:
            print("⚠ No se puede guardar: ruta necesita al menos 2 nodos")
            self._clear_temp_lines()
            self._clear_state()
            return

        print(f"✓ Guardando ruta con {len(self._nodes_seq)} nodos")
        
        # Normalizar nodos a dicts con id,X,Y
        ruta_nodes = []
        for n in self._nodes_seq:
            try:
                if hasattr(n, "to_dict"):
                    ruta_nodes.append(n.to_dict())
                elif isinstance(n, dict):
                    ruta_nodes.append(n)
                else:
                    ruta_nodes.append({"id": getattr(n, "id", None), 
                                     "X": getattr(n, "X", 0), 
                                     "Y": getattr(n, "Y", 0)})
            except Exception:
                ruta_nodes.append({"id": None, "X": 0, "Y": 0})

        origen = ruta_nodes[0]
        destino = ruta_nodes[-1]
        visita = ruta_nodes[1:-1] if len(ruta_nodes) > 2 else []

        # Guardar en proyecto.rutas como dict (compatible con Proyecto.guardar)
        ruta_dict = {"origen": origen, "visita": visita, "destino": destino}
        if not hasattr(self.proyecto, "rutas") or self.proyecto.rutas is None:
            self.proyecto.rutas = []
        self.proyecto.rutas.append(ruta_dict)

        # Mostrar coordenadas en metros
        x_origen_m = self.editor.pixeles_a_metros(origen.get('X', 0))
        y_origen_m = self.editor.pixeles_a_metros(origen.get('Y', 0))
        x_destino_m = self.editor.pixeles_a_metros(destino.get('X', 0))
        y_destino_m = self.editor.pixeles_a_metros(destino.get('Y', 0))
        
        print(f"✓ Ruta guardada: Origen {origen.get('id')} ({x_origen_m:.2f}, {y_origen_m:.2f}) -> Destino {destino.get('id')} ({x_destino_m:.2f}, {y_destino_m:.2f})")

        # Limpiar líneas temporales y estado de construcción
        self._clear_temp_lines()
        self._clear_state()

        # Delegar el dibujo al editor (que debe limpiar y redibujar todo)
        try:
            if hasattr(self.editor, "_dibujar_rutas"):
                self.editor._dibujar_rutas()
            if hasattr(self.editor, "_mostrar_rutas_lateral"):
                self.editor._mostrar_rutas_lateral()
        except Exception as e:
            print(f"Error actualizando UI: {e}")

    def _clear_temp_lines(self):
        """Elimina todas las líneas temporales"""
        # Desconectar todas las señales de los nodos
        try:
            for nodo in self._nodes_seq:
                for item in self.view.marco_trabajo.scene().items():
                    if isinstance(item, NodoItem) and getattr(item, "nodo", None) == nodo:
                        try:
                            item.moved.disconnect(self._update_temp_lines)
                        except Exception:
                            pass
        except Exception:
            pass
        
        # Eliminar líneas temporales
        for l in list(self._lines):
            try:
                if l.scene() is not None:
                    self.view.marco_trabajo.scene().removeItem(l)
            except Exception:
                pass
        self._lines = []

    def _clear_state(self):
        """Limpia todo el estado de la ruta en construcción"""
        try:
            if self._last_item:
                self._last_item.setSelected(False)
                self._last_item.set_normal_color()
        except Exception:
            pass
        
        # Restaurar colores de todos los nodos en la secuencia
        for nodo in self._nodes_seq:
            for item in self.view.marco_trabajo.scene().items():
                if isinstance(item, NodoItem) and getattr(item, "nodo", None) == nodo:
                    try:
                        item.set_normal_color()
                    except Exception:
                        pass
        
        self._nodes_seq = []
        self._last_item = None
        self._clear_temp_lines()