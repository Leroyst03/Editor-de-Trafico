from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtWidgets import QListWidgetItem, QGraphicsLineItem
from PyQt5.QtGui import QPen
from View.node_item import NodoItem
from Model.Ruta import Ruta  # si tienes la clase Ruta en Model/Ruta.py

class RutaController(QObject):
    def __init__(self, proyecto, view, editor):
        super().__init__()
        self.proyecto = proyecto
        self.view = view
        self.editor = editor
        self.activo = False

        # Estado de la ruta en construcción
        self._nodes_seq = []     # lista de objetos Nodo (orden)
        self._lines = []         # QGraphicsLineItem temporales
        self._last_item = None   # último NodoItem visual añadido

    def activar(self):
        if not self.activo:
            self.view.marco_trabajo.viewport().installEventFilter(self)
            self.activo = True
            self._clear_state()
            print("Modo Ruta activado")

    def desactivar(self):
        if self.activo:
            # Finalizar la ruta en construcción (si procede)
            self._finalize_route()
            self.view.marco_trabajo.viewport().removeEventFilter(self)
            self.activo = False
            self._clear_state()
            print("Modo Ruta desactivado")

    def eventFilter(self, obj, event):
        # Solo procesar clicks de ratón en el viewport del QGraphicsView
        if obj is self.view.marco_trabajo.viewport() and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton and self.proyecto:
                scene_pos = self.view.marco_trabajo.mapToScene(event.pos())
                # itemAt recibe coordenadas del viewport
                item = self.view.marco_trabajo.itemAt(event.pos())
                if isinstance(item, NodoItem):
                    self._add_existing_node(item)
                else:
                    self._create_and_add_node(int(scene_pos.x()), int(scene_pos.y()))
                return True
        return False

    # --- helpers internos ---
    def _create_and_add_node(self, x, y):
        nodo = self.proyecto.agregar_nodo(x, y)

        # Crear visual mediante helper del editor si existe
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

        # Añadir a la lista lateral
        item = QListWidgetItem(f"ID {nodo.get('id')} - ({nodo.get('X')}, {nodo.get('Y')})")
        item.setData(Qt.UserRole, nodo)
        self.view.nodosList.addItem(item)

        # Añadir a la secuencia de la ruta y dibujar segmento si hay anterior
        self._append_node_to_route(nodo, nodo_item)

    def _add_existing_node(self, nodo_item):
        nodo = nodo_item.nodo
        if nodo not in self.proyecto.nodos:
            self.proyecto.nodos.append(nodo)
            item = QListWidgetItem(f"ID {nodo.get('id')} - ({nodo.get('X')}, {nodo.get('Y')})")
            item.setData(Qt.UserRole, nodo)
            self.view.nodosList.addItem(item)
        self._append_node_to_route(nodo, nodo_item)

    def _append_node_to_route(self, nodo, nodo_item):
        # Primer nodo: solo añadir y marcar
        if not self._nodes_seq:
            self._nodes_seq.append(nodo)
            self._last_item = nodo_item
            try:
                nodo_item.setSelected(True)
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
                self.view.marco_trabajo.scene().addItem(line)
                self._lines.append(line)

    def _finalize_route(self):
        """Finaliza la ruta en construcción: guarda la ruta en el modelo y delega el dibujo al editor."""
        # Si no hay suficientes nodos, limpiar temporales y salir
        if len(self._nodes_seq) < 2:
            self._clear_temp_lines()
            self._clear_state()
            return

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

        # Limpiar líneas temporales y estado de construcción
        self._clear_temp_lines()
        self._clear_state()

        # Delegar el dibujo al editor (que debe limpiar y redibujar todo)
        try:
            if hasattr(self.editor, "_dibujar_rutas"):
                self.editor._dibujar_rutas()
            if hasattr(self.editor, "_mostrar_rutas_lateral"):
                self.editor._mostrar_rutas_lateral()
        except Exception:
            pass

        print(f"Ruta creada: {len(self._nodes_seq)} nodos")

    def _clear_temp_lines(self):
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
        try:
            if self._last_item:
                self._last_item.setSelected(False)
        except Exception:
            pass
        self._nodes_seq = []
        self._last_item = None
        self._clear_temp_lines()