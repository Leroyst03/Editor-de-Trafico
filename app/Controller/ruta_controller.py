from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtWidgets import QListWidgetItem, QGraphicsLineItem, QMenu  # Añadimos QMenu
from PyQt5.QtGui import QPen
from View.node_item import NodoItem

class RutaController(QObject):
    def __init__(self, proyecto, view, editor):
        super().__init__()
        self.proyecto = proyecto
        self.view = view
        self.editor = editor
        self.activo = False

        # Estado de la ruta en construcción
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
        """Desactiva el modo de creación de rutas"""
        if self.activo:
            # Finalizar la ruta en construcción (si procede)
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
                
                # --- INICIO MEJORA: DETECCIÓN DE NODOS SUPERPUESTOS ---
                # Obtener TODOS los items en la posición del clic
                items_en_pos = self.view.marco_trabajo.scene().items(scene_pos)
                
                # Filtrar solo los que son NodoItem
                nodos_en_pos = [item for item in items_en_pos if isinstance(item, NodoItem)]
                
                if len(nodos_en_pos) > 1:
                    # CASO: Hay nodos superpuestos -> Mostrar menú de selección
                    print(f"⚠ Detectados {len(nodos_en_pos)} nodos superpuestos. Mostrando menú...")
                    self._mostrar_menu_seleccion_nodo(nodos_en_pos, event.pos())
                    return True
                    
                elif len(nodos_en_pos) == 1:
                    # CASO: Un solo nodo -> Agregar directamente
                    print(f"✓ Clic en nodo existente ID {nodos_en_pos[0].nodo.get('id')}")
                    self._add_existing_node(nodos_en_pos[0])
                    return True
                    
                else:
                    # CASO: No hay nodos -> Crear nuevo nodo
                    x_m = self.editor.pixeles_a_metros(scene_pos.x())
                    y_m = self.editor.pixeles_a_metros(scene_pos.y())
                    print(f"✓ Creando nuevo nodo en posición ({x_m:.2f}, {y_m:.2f}) metros")
                    self._create_and_add_node(int(scene_pos.x()), int(scene_pos.y()))
                    return True
                # --- FIN MEJORA ---

        return False

    def _mostrar_menu_seleccion_nodo(self, nodos, pos_evento):
        """
        Muestra un menú contextual para seleccionar un nodo entre varios superpuestos.
        
        Args:
            nodos: Lista de NodoItem detectados en la posición.
            pos_evento: Posición del ratón (viewport coordinates) para ubicar el menú.
        """
        menu = QMenu(self.view)
        menu.setStyleSheet("""
            QMenu {
                background-color: #3c3c3c; 
                color: white; 
                border: 1px solid #5a5a5a;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 25px 5px 10px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #5a5a5a; 
            }
            QMenu::title {
                color: #aaaaaa;
                padding: 5px;
            }
        """)
        menu.setTitle("Seleccionar nodo:")

        for nodo_item in nodos:
            nodo = nodo_item.nodo
            objetivo = nodo.get('objetivo', 0)
            
            # Determinar tipo de objetivo
            if objetivo == 1: texto_obj = "IN"
            elif objetivo == 2: texto_obj = "OUT"
            elif objetivo == 3: texto_obj = "I/O"
            else: texto_obj = "Normal"
            
            # Formatear coordenadas en metros
            x_m = self.editor.pixeles_a_metros(nodo.get('X', 0))
            y_m = self.editor.pixeles_a_metros(nodo.get('Y', 0))
            
            action_text = f"ID: {nodo.get('id')} - {texto_obj} ({x_m:.2f}, {y_m:.2f})"
            
            action = menu.addAction(action_text)
            # Usar lambda para capturar el nodo_item específico del bucle
            action.triggered.connect(lambda checked, n_item=nodo_item: self._add_existing_node(n_item))

        # Mostrar el menú en la posición global del cursor
        menu.exec_(self.view.marco_trabajo.viewport().mapToGlobal(pos_evento))

    def _create_and_add_node(self, x, y):
        """Crea un nuevo nodo y lo añade a la ruta"""
        # Usar el método crear_nodo del editor para registrar en historial
        nodo_item = self.editor.crear_nodo(x, y, registrar_historial=True)
        
        if nodo_item and hasattr(nodo_item, 'nodo'):
            self._append_node_to_route(nodo_item.nodo, nodo_item)
            return True
        else:
            print("✗ Error: No se pudo crear el nodo")
            return False

    def _add_existing_node(self, nodo_item):
        """Añade un nodo existente a la ruta"""
        nodo = nodo_item.nodo
        self._append_node_to_route(nodo, nodo_item)

    def _append_node_to_route(self, nodo, nodo_item):
        """Añade un nodo a la secuencia de la ruta y dibuja líneas"""
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
        pen = QPen(Qt.darkGreen, 2)
        line.setPen(pen)
        line.setZValue(0.6)
        line.setData(0, "ruta_temporal")
        self.view.marco_trabajo.scene().addItem(line)
        self._lines.append(line)

        # Conectar señales de movimiento
        try:
            self._last_item.moved.connect(self._update_temp_lines)
            nodo_item.moved.connect(self._update_temp_lines)
        except Exception:
            pass

        self._nodes_seq.append(nodo)
        self._last_item = nodo_item
        nodo_item.set_selected_color()

    def _update_temp_lines(self, nodo_item=None):
        """Actualiza todas las líneas temporales cuando un nodo se mueve"""
        if not self._lines or len(self._nodes_seq) < 2:
            return

        self._clear_temp_lines()
        
        for i in range(len(self._nodes_seq) - 1):
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
                line.setData(0, "ruta_temporal")
                self.view.marco_trabajo.scene().addItem(line)
                self._lines.append(line)

    def _finalize_route(self):
        """Finaliza la ruta en construcción: guarda la ruta en el modelo"""
        if len(self._nodes_seq) < 2:
            print("⚠ No se puede guardar: ruta necesita al menos 2 nodos")
            self._clear_temp_lines()
            self._clear_state()
            return

        print(f"✓ Guardando ruta con {len(self._nodes_seq)} nodos")
        
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

        ruta_dict = {"origen": origen, "visita": visita, "destino": destino}
        self.proyecto.agregar_ruta(ruta_dict)

        if self.editor:
            self.editor._actualizar_todas_relaciones_nodo_ruta()
            self.editor._actualizar_lista_rutas_con_widgets()
            self.editor._dibujar_rutas()
        
        # Limpiar estado
        self._clear_temp_lines()
        self._clear_state()

    def _clear_temp_lines(self):
        """Elimina todas las líneas temporales"""
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

    def remover_nodo_de_secuencia(self, nodo_id):
        """Remueve un nodo de la secuencia de la ruta en construcción."""
        if not self.activo or not self._nodes_seq:
            return
            
        nodo_idx = None
        for i, nodo in enumerate(self._nodes_seq):
            if nodo.get('id') == nodo_id:
                nodo_idx = i
                break
        
        if nodo_idx is None:
            return
        
        self._nodes_seq.pop(nodo_idx)
        self._clear_temp_lines()
        
        if self._last_item and self._last_item.nodo.get('id') == nodo_id:
            if self._nodes_seq:
                last_nodo = self._nodes_seq[-1]
                for item in self.view.marco_trabajo.scene().items():
                    if isinstance(item, NodoItem) and item.nodo.get('id') == last_nodo.get('id'):
                        self._last_item = item
                        item.set_normal_color()
                        break
            else:
                self._last_item = None
        
        if len(self._nodes_seq) >= 2:
            self._update_temp_lines()
        
        for nodo in self._nodes_seq:
            for item in self.view.marco_trabajo.scene().items():
                if isinstance(item, NodoItem) and item.nodo.get('id') == nodo.get('id'):
                    item.set_normal_color()
                    break
        
    def contiene_nodo_en_secuencia(self, nodo_id):
        """Verifica si un nodo está en la secuencia de construcción actual"""
        for nodo in self._nodes_seq:
            if nodo.get('id') == nodo_id:
                return True
        return False
