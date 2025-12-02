from PyQt5.QtWidgets import (
    QFileDialog, QGraphicsScene, QGraphicsPixmapItem,
    QButtonGroup, QListWidgetItem, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu
)
from PyQt5.QtGui import QPixmap, QPen
from PyQt5.QtCore import Qt, QEvent, QObject
from Model.Proyecto import Proyecto
from Controller.seleccionar_controller import SeleccionarController
from Controller.mover_controller import MoverController
from Controller.colocar_controller import ColocarController
from Controller.ruta_controller import RutaController
from View.node_item import NodoItem
import ast

class EditorController(QObject):
    def __init__(self, view, proyecto=None):
        super().__init__()
        self.view = view
        self.proyecto = proyecto

        # --- Inicializar escena con padre ---
        self.scene = QGraphicsScene(self.view.marco_trabajo)
        self.view.marco_trabajo.setScene(self.scene)

        # Conexión: selección en el mapa
        self.scene.selectionChanged.connect(self.seleccionar_nodo_desde_mapa)

        # Conexión: selección en la lista lateral
        self.view.nodosList.itemSelectionChanged.connect(self.seleccionar_nodo_desde_lista)

        header = self.view.propertiesTable.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # --- Menú Proyecto ---
        nuevo_action = self.view.menuProyecto.addAction("Nuevo")
        abrir_action = self.view.menuProyecto.addAction("Abrir")
        guardar_action = self.view.menuProyecto.addAction("Guardar")

        nuevo_action.triggered.connect(self.nuevo_proyecto)
        abrir_action.triggered.connect(self.abrir_proyecto)
        guardar_action.triggered.connect(self.guardar_proyecto)

        # --- Subcontroladores ---
        self.seleccionar_ctrl = SeleccionarController(self.proyecto, self.view, self)
        self.mover_ctrl = MoverController(self.proyecto, self.view, self)
        self.colocar_ctrl = ColocarController(self.proyecto, self.view, self)
        self.ruta_ctrl = RutaController(self.proyecto, self.view, self)

        # --- Grupo de botones de modo ---
        self.modo_group = QButtonGroup()
        self.modo_group.setExclusive(False)

        self.modo_group.addButton(self.view.seleccionar_button)
        self.modo_group.addButton(self.view.mover_button)
        self.modo_group.addButton(self.view.colocar_vertice_button)
        self.modo_group.addButton(self.view.crear_ruta_button)

        self.modo_group.buttonClicked.connect(self.cambiar_modo)
        self.modo_actual = None

        # Estado inicial: zoom libre
        self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.ScrollHandDrag)

        self._changing_selection = False
        self._updating_ui = False

        # mantener referencias a las líneas de rutas dibujadas: lista de listas de QGraphicsLineItem
        self._route_lines = []            # líneas rojas por ruta
        self._highlight_lines = []        # líneas amarillas de selección

        # instalar filtro de eventos en el viewport para detectar clicks fuera de paneles
        try:
            self.view.marco_trabajo.viewport().installEventFilter(self)
        except Exception:
            pass

        if hasattr(self.view, "rutasList"):
            try:
                self.view.rutasList.itemSelectionChanged.disconnect(self.seleccionar_ruta_desde_lista)
            except Exception:
                pass
            self.view.rutasList.itemSelectionChanged.connect(self.seleccionar_ruta_desde_lista)

        # Índice de la ruta actualmente seleccionada
        self.ruta_actual_idx = None

    # --- Gestión de modos ---
    def cambiar_modo(self, boton):
        if not boton.isChecked():
            self.modo_actual = None
            self.seleccionar_ctrl.desactivar()
            self.mover_ctrl.desactivar()
            self.colocar_ctrl.desactivar()
            # Asegurarse de desactivar el controlador de rutas al salir del modo
            try:
                self.ruta_ctrl.desactivar()
            except Exception:
                pass
            self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.ScrollHandDrag)
            # desactivar movimiento en nodos
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    try:
                        item.setFlag(item.ItemIsMovable, False)
                    except Exception:
                        pass
            return

        for b in (self.view.seleccionar_button, self.view.mover_button,
                self.view.colocar_vertice_button, self.view.crear_ruta_button):
            if b is not boton:
                b.setChecked(False)

        if boton == self.view.seleccionar_button:
            # --- MODO SELECCIONAR ---
            self.modo_actual = "seleccionar"
            self.seleccionar_ctrl.activar()
            self.mover_ctrl.desactivar()
            self.colocar_ctrl.desactivar()
            try:
                self.ruta_ctrl.desactivar()
            except Exception:
                pass

            # No se puede arrastrar ni mover nada
            self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.NoDrag)

            # Desactivar movimiento en todos los nodos pero mantenerlos focusable
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    try:
                        item.setFlag(item.ItemIsMovable, False)
                        item.setFlag(item.ItemIsFocusable, True)
                    except Exception:
                        pass

            print("Modo Seleccionar activado: solo ver propiedades de nodos")

        elif boton == self.view.mover_button:
            # --- MODO MOVER ---
            self.modo_actual = "mover"
            self.mover_ctrl.activar()
            self.seleccionar_ctrl.desactivar()
            self.colocar_ctrl.desactivar()
            try:
                self.ruta_ctrl.desactivar()
            except Exception:
                pass
            self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.ScrollHandDrag)

            # Activar movimiento en todos los nodos
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    try:
                        item.setFlag(item.ItemIsMovable, True)
                        item.setFlag(item.ItemIsFocusable, True)
                    except Exception:
                        pass

            print("Modo Mover activado: nodos arrastrables")

        elif boton == self.view.colocar_vertice_button:
            # --- MODO COLOCAR ---
            self.modo_actual = "colocar"
            self.colocar_ctrl.activar()
            self.seleccionar_ctrl.desactivar()
            self.mover_ctrl.desactivar()
            try:
                self.ruta_ctrl.desactivar()
            except Exception:
                pass
            self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.NoDrag)

            print("Modo Colocar activado: añadir nuevos nodos")

        elif boton == self.view.crear_ruta_button:
            # --- MODO RUTA ---
            self.modo_actual = "ruta"
            self.ruta_ctrl.activar()
            self.seleccionar_ctrl.desactivar()
            self.mover_ctrl.desactivar()
            self.colocar_ctrl.desactivar()
            self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.NoDrag)

            print("Modo Ruta activado: crear rutas entre nodos")

        # Actualizar líneas después de cambiar modo
        self.actualizar_lineas_rutas()

    def actualizar_lineas_rutas(self):
        """Fuerza la actualización de todas las líneas de ruta"""
        self._dibujar_rutas()
        if hasattr(self.view, "rutasList") and self.view.rutasList.selectedItems():
            self.seleccionar_ruta_desde_lista()

    # --- Funciones de proyecto ---
    def nuevo_proyecto(self):
        ruta_mapa, _ = QFileDialog.getOpenFileName(
            self.view, "Seleccionar mapa", "", "Imagenes (*.png *.jpg *.jpeg)"
        )
        if not ruta_mapa:
            return
        self.proyecto = Proyecto(ruta_mapa)
        self._mostrar_mapa(ruta_mapa)
        print("Nuevo proyecto creado con mapa:", ruta_mapa)
        self.diagnosticar_estado_proyecto()

    def abrir_proyecto(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self.view, "Abrir proyecto", "", "JSON Files (*.json)"
        )
        if not ruta_archivo:
            return
        try:
            self.proyecto = Proyecto.cargar(ruta_archivo)

            # Actualizar referencias en subcontroladores
            self.seleccionar_ctrl.proyecto = self.proyecto
            self.mover_ctrl.proyecto = self.proyecto
            self.colocar_ctrl.proyecto = self.proyecto
            self.ruta_ctrl.proyecto = self.proyecto

            if self.proyecto.mapa:
                self._mostrar_mapa(self.proyecto.mapa)

            # Crear NodoItem correctamente con editor=self
            for nodo in self.proyecto.nodos:
                try:
                    nodo_item = self._create_nodo_item(nodo)
                except Exception:
                    # Crear manualmente pero manteniendo el patrón
                    nodo_item = NodoItem(nodo, editor=self)
                    try:
                        nodo_item.setFlag(nodo_item.ItemIsSelectable, True)
                        nodo_item.setFlag(nodo_item.ItemIsFocusable, True)
                        nodo_item.setFlag(nodo_item.ItemIsMovable, (self.modo_actual == "mover"))
                        nodo_item.setAcceptedMouseButtons(Qt.LeftButton)
                        nodo_item.setZValue(1)
                        self.scene.addItem(nodo_item)
                        nodo_item.moved.connect(self.on_nodo_moved)
                    except Exception:
                        pass

                item = QListWidgetItem(f"ID {nodo.get('id')} - ({nodo.get('X')}, {nodo.get('Y')})")
                item.setData(Qt.UserRole, nodo)
                self.view.nodosList.addItem(item)

            self._dibujar_rutas()
            self._mostrar_rutas_lateral()

            print("Proyecto cargado desde:", ruta_archivo)
            self.diagnosticar_estado_proyecto()
        except Exception as err:
            print("Error al abrir proyecto:", err)

    def guardar_proyecto(self):
        if not self.proyecto:
            print("No hay proyecto cargado para guardar")
            return
        ruta_archivo, _ = QFileDialog.getSaveFileName(
            self.view, "Guardar proyecto", "", "JSON Files (*.json)"
        )
        if not ruta_archivo:
            return
        if not ruta_archivo.lower().endswith(".json"):
            ruta_archivo += ".json"
        try:
            self.proyecto.guardar(ruta_archivo)
            print("Proyecto guardado en:", ruta_archivo)
        except Exception as err:
            print("Error al guardar proyecto:", err)

    def _mostrar_mapa(self, ruta_mapa):
        # Limpia la escena y coloca el mapa al fondo sin interceptar clics
        self.scene.clear()
        pixmap = QPixmap(ruta_mapa)
        pm_item = QGraphicsPixmapItem(pixmap)
        pm_item.setAcceptedMouseButtons(Qt.NoButton)
        pm_item.setFlag(QGraphicsPixmapItem.ItemIsSelectable, False)
        pm_item.setFlag(QGraphicsPixmapItem.ItemIsFocusable, False)
        pm_item.setZValue(0)
        self.scene.addItem(pm_item)

    # --- Helper centralizado para crear NodoItem ---
    def _create_nodo_item(self, nodo, size=20):
        """
        Crea (o recupera) un NodoItem visual para el nodo del modelo,
        lo configura (flags, z-order), conecta la señal moved y lo añade a la escena.
        Devuelve el NodoItem creado.
        """
        # Si ya existe un NodoItem en la escena para este nodo, devolverlo
        for it in self.scene.items():
            if isinstance(it, NodoItem) and getattr(it, "nodo", None) == nodo:
                return it

        # Crear nuevo NodoItem
        nodo_item = NodoItem(nodo, size=size, editor=self)

        # Flags básicos: seleccionable y focusable siempre; movible según modo actual
        try:
            nodo_item.setFlag(nodo_item.ItemIsSelectable, True)
            nodo_item.setFlag(nodo_item.ItemIsFocusable, True)
            nodo_item.setFlag(nodo_item.ItemIsMovable, (self.modo_actual == "mover"))
            nodo_item.setAcceptedMouseButtons(Qt.LeftButton)
            nodo_item.setZValue(1)
        except Exception:
            pass

        # Conectar la señal moved para que el editor actualice modelo/UI cuando se suelte
        try:
            nodo_item.moved.connect(self.on_nodo_moved)
        except Exception:
            pass

        # Añadir a la escena y devolver
        try:
            self.scene.addItem(nodo_item)
        except Exception:
            pass

        return nodo_item

    def crear_nodo(self, x=100, y=100):
        if not self.proyecto:
            print("No hay proyecto cargado")
            return

        # Primero agregar al modelo
        nodo = self.proyecto.agregar_nodo(x, y)

        # Crear NodoItem con referencia al editor usando helper centralizado
        try:
            nodo_item = self._create_nodo_item(nodo)
        except Exception:
            nodo_item = NodoItem(nodo, editor=self)
            try:
                nodo_item.setFlag(nodo_item.ItemIsSelectable, True)
                nodo_item.setFlag(nodo_item.ItemIsFocusable, True)
                nodo_item.setFlag(nodo_item.ItemIsMovable, (self.modo_actual == "mover"))
                nodo_item.setAcceptedMouseButtons(Qt.LeftButton)
                nodo_item.setZValue(1)
                self.scene.addItem(nodo_item)
                nodo_item.moved.connect(self.on_nodo_moved)
            except Exception:
                pass

        # Añadir a la lista lateral
        item = QListWidgetItem(f"ID {nodo.get('id')} - ({nodo.get('X')}, {nodo.get('Y')})")
        item.setData(Qt.UserRole, nodo)
        self.view.nodosList.addItem(item)

        print("Nodo creado:", getattr(nodo, "to_dict", lambda: nodo)())

    # --- NUEVOS MÉTODOS PARA RESALTADO Y DETECCIÓN DE NODOS SUPERPUESTOS ---
    def resaltar_nodo_seleccionado(self, nodo_item):
        """Resalta el nodo seleccionado con color especial"""
        # Restaurar color normal a todos los nodos primero
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.set_normal_color()
        
        # Aplicar color de selección al nodo específico
        nodo_item.set_selected_color()
        
        # También resaltar nodos de ruta si hay una ruta seleccionada
        if hasattr(self, 'ruta_actual_idx') and self.ruta_actual_idx is not None:
            self.resaltar_nodos_ruta()

    def resaltar_nodos_ruta(self, ruta=None):
        """Resalta todos los nodos que pertenecen a una ruta seleccionada"""
        if not ruta:
            if not hasattr(self, 'ruta_actual_idx') or self.ruta_actual_idx is None:
                return
            if not self.proyecto or not hasattr(self.proyecto, 'rutas'):
                return
            if self.ruta_actual_idx >= len(self.proyecto.rutas):
                return
            ruta = self.proyecto.rutas[self.ruta_actual_idx]
        
        try:
            ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
        except Exception:
            ruta_dict = ruta
        
        self._normalize_route_nodes(ruta_dict)
        
        # Coleccionar todos los nodos de la ruta
        nodos_ruta = []
        if ruta_dict.get("origen"):
            nodos_ruta.append(ruta_dict["origen"])
        if ruta_dict.get("visita"):
            nodos_ruta.extend(ruta_dict["visita"])
        if ruta_dict.get("destino"):
            nodos_ruta.append(ruta_dict["destino"])
        
        # Resaltar cada nodo de la ruta - FORZAR color de ruta incluso si está seleccionado
        for nodo in nodos_ruta:
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    if item.nodo == nodo or (
                        isinstance(item.nodo, dict) and isinstance(nodo, dict) and
                        item.nodo.get('id') == nodo.get('id')
                    ):
                        item.set_route_selected_color()
                        break

    def _resaltar_nodos_de_ruta(self, ruta):
        """Método mejorado para resaltar nodos de una ruta específica"""
        try:
            # Convertir ruta a diccionario si es necesario
            ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
        except Exception:
            ruta_dict = ruta
        
        # Normalizar la ruta
        self._normalize_route_nodes(ruta_dict)
        
        # Obtener todos los nodos de la ruta
        nodos_ruta = []
        
        # Origen
        origen = ruta_dict.get("origen")
        if origen:
            if isinstance(origen, dict):
                nodos_ruta.append(origen)
            else:
                # Intentar obtener como objeto Nodo
                try:
                    nodo_id = origen.get('id') if hasattr(origen, 'get') else getattr(origen, 'id', None)
                    if nodo_id:
                        nodos_ruta.append(origen)
                except:
                    pass
        
        # Visita
        visita = ruta_dict.get("visita", [])
        for nodo_visita in visita:
            if isinstance(nodo_visita, dict):
                nodos_ruta.append(nodo_visita)
            else:
                try:
                    nodo_id = nodo_visita.get('id') if hasattr(nodo_visita, 'get') else getattr(nodo_visita, 'id', None)
                    if nodo_id:
                        nodos_ruta.append(nodo_visita)
                except:
                    pass
        
        # Destino
        destino = ruta_dict.get("destino")
        if destino:
            if isinstance(destino, dict):
                nodos_ruta.append(destino)
            else:
                try:
                    nodo_id = destino.get('id') if hasattr(destino, 'get') else getattr(destino, 'id', None)
                    if nodo_id:
                        nodos_ruta.append(destino)
                except:
                    pass
        
        # DEBUG: Mostrar qué nodos se van a resaltar
        print(f"DEBUG: Resaltando {len(nodos_ruta)} nodos de la ruta")
        for i, nodo in enumerate(nodos_ruta):
            print(f"  Nodo {i}: {nodo}")
        
        # Resaltar cada nodo en la escena
        nodos_resaltados = 0
        for nodo_ruta in nodos_ruta:
            # Obtener el ID del nodo de la ruta
            if isinstance(nodo_ruta, dict):
                nodo_ruta_id = nodo_ruta.get('id')
            else:
                try:
                    nodo_ruta_id = nodo_ruta.get('id') if hasattr(nodo_ruta, 'get') else getattr(nodo_ruta, 'id', None)
                except:
                    nodo_ruta_id = None
            
            if nodo_ruta_id is None:
                continue
                
            # Buscar el NodoItem correspondiente en la escena
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    # Obtener el ID del nodo del item
                    item_nodo = item.nodo
                    if isinstance(item_nodo, dict):
                        item_id = item_nodo.get('id')
                    else:
                        try:
                            item_id = item_nodo.get('id') if hasattr(item_nodo, 'get') else getattr(item_nodo, 'id', None)
                        except:
                            item_id = None
                    
                    # Si los IDs coinciden, resaltar el nodo
                    if item_id is not None and str(item_id) == str(nodo_ruta_id):
                        item.set_route_selected_color()
                        nodos_resaltados += 1
                        break
        
        print(f"DEBUG: Se resaltaron {nodos_resaltados} nodos de la ruta")

    def restaurar_colores_nodos(self):
        """Restaura todos los nodos a su color normal"""
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.set_normal_color()

    # --- Sincronización lista ↔ mapa (MODIFICADOS) ---
    def seleccionar_nodo_desde_lista(self):
        if self._changing_selection:
            return
        items = self.view.nodosList.selectedItems()
        if not items:
            return
        nodo = items[0].data(Qt.UserRole)

        self._changing_selection = True
        try:
            # Deseleccionar rutas primero
            if hasattr(self.view, "rutasList"):
                self.view.rutasList.clearSelection()
            
            # Primero restaurar todos los nodos a color normal
            self.restaurar_colores_nodos()
            
            # Deseleccionar todo en la escena primero
            for scene_item in self.scene.selectedItems():
                scene_item.setSelected(False)
            
            # Buscar y seleccionar el nodo correspondiente
            for scene_item in self.scene.items():
                if isinstance(scene_item, NodoItem) and scene_item.nodo == nodo:
                    scene_item.setSelected(True)
                    # Solo aplicar color de selección (no de ruta)
                    scene_item.set_selected_color()
                    self.view.marco_trabajo.centerOn(scene_item)
                    self.mostrar_propiedades_nodo(nodo)
                    break
        finally:
            self._changing_selection = False

    def seleccionar_nodo_desde_mapa(self):
        if self._changing_selection:
            return
        seleccionados = self.scene.selectedItems()
        if not seleccionados:
            return
        nodo_item = seleccionados[0]
        nodo = nodo_item.nodo

        # --- DETECCIÓN DE NODOS SUPERPUESTOS ---
        # Verificar si hay más nodos en la misma posición (o muy cerca)
        pos = nodo_item.scenePos()
        # Usar un rectángulo pequeño alrededor del punto para detectar nodos cercanos
        search_rect = nodo_item.boundingRect().translated(pos)
        search_rect.adjust(-5, -5, 5, 5)  # Expandir un poco el área de búsqueda
        
        items_en_pos = self.scene.items(search_rect)
        nodos_en_pos = []
        
        for item in items_en_pos:
            if isinstance(item, NodoItem):
                # Verificar si está realmente superpuesto (misma posición aproximada)
                item_pos = item.scenePos()
                if (abs(item_pos.x() - pos.x()) < 10 and 
                    abs(item_pos.y() - pos.y()) < 10):
                    nodos_en_pos.append(item)
        
        if len(nodos_en_pos) > 1:
            # Hay nodos superpuestos, mostrar menú
            self.mostrar_menu_nodos_superpuestos(nodos_en_pos, pos)
            return  # El menú manejará la selección

        # --- CONTINUAR CON SELECCIÓN NORMAL ---
        self._changing_selection = True
        try:
            # Deseleccionar rutas primero
            if hasattr(self.view, "rutasList"):
                self.view.rutasList.clearSelection()
            
            # Primero restaurar todos los nodos a color normal
            self.restaurar_colores_nodos()
            
            # Deseleccionar todos los nodos primero
            for item in self.scene.selectedItems():
                if item != nodo_item:
                    item.setSelected(False)
            
            # Resaltar el nodo seleccionado
            nodo_item.set_selected_color()
            
            # Sincronizar con la lista lateral
            for i in range(self.view.nodosList.count()):
                item = self.view.nodosList.item(i)
                if item.data(Qt.UserRole) == nodo:
                    self.view.nodosList.setCurrentItem(item)
                    self.mostrar_propiedades_nodo(nodo)
                    break
        finally:
            self._changing_selection = False

    def mostrar_menu_nodos_superpuestos(self, nodos, pos):
        """Muestra un menú para seleccionar entre nodos superpuestos"""
        menu = QMenu(self.view)
        menu.setTitle("Nodos superpuestos - Selecciona uno:")
        
        for nodo_item in nodos:
            nodo = nodo_item.nodo
            action = menu.addAction(f"ID: {nodo.get('id')} - ({nodo.get('X')}, {nodo.get('Y')})")
            action.triggered.connect(lambda checked, n=nodo: self.seleccionar_nodo_especifico(n))
        
        # Mostrar el menú en la posición del cursor
        menu.exec_(self.view.marco_trabajo.mapToGlobal(
            self.view.marco_trabajo.mapFromScene(pos)
        ))

    def seleccionar_nodo_especifico(self, nodo):
        """Selecciona un nodo específico desde el menú de superposición"""
        self._changing_selection = True
        try:
            # Limpiar selecciones previas
            for item in self.scene.selectedItems():
                item.setSelected(False)
            
            # Primero restaurar todos los nodos a color normal
            self.restaurar_colores_nodos()
            
            # Seleccionar el nodo específico en la escena
            for item in self.scene.items():
                if isinstance(item, NodoItem) and item.nodo == nodo:
                    item.setSelected(True)
                    item.set_selected_color()
                    self.view.marco_trabajo.centerOn(item)
                    break
            
            # Sincronizar con la lista lateral
            for i in range(self.view.nodosList.count()):
                item = self.view.nodosList.item(i)
                if item.data(Qt.UserRole) == nodo:
                    self.view.nodosList.setCurrentItem(item)
                    self.mostrar_propiedades_nodo(nodo)
                    break
        finally:
            self._changing_selection = False

    def actualizar_lista_nodo(self, nodo):
        """Actualizar la lista lateral del panel de propiedades con las coordenadas nuevas"""
        for i in range(self.view.nodosList.count()):
            item = self.view.nodosList.item(i)
            if item.data(Qt.UserRole) == nodo:
                item.setText(f"ID {nodo.get('id')} - ({nodo.get('X')}, {nodo.get('Y')})")
                break

        # Refrescar el panel de propiedades si el nodo esta seleccionado
        seleccionados = self.view.nodosList.selectedItems()
        if seleccionados and seleccionados[0].data(Qt.UserRole) == nodo:
            self.mostrar_propiedades_nodo(nodo)

    def _mostrar_rutas_lateral(self):
        """
        Rellena la lista lateral de rutas. Cada item contiene la ruta (dict) en Qt.UserRole.
        La etiqueta es compacta (OrigenID -> DestinoID) pero la edición y detalles se hacen en propertiesTable.
        """
        if not hasattr(self.view, "rutasList") or not self.proyecto:
            return

        self.view.rutasList.clear()

        for idx, ruta in enumerate(self.proyecto.rutas, start=1):
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
            except Exception:
                ruta_dict = ruta

            # Normalizar para obtener ids legibles
            self._normalize_route_nodes(ruta_dict)
            origen = ruta_dict.get("origen")
            destino = ruta_dict.get("destino")

            origen_id = origen.get("id", "?") if isinstance(origen, dict) else str(origen)
            destino_id = destino.get("id", "?") if isinstance(destino, dict) else str(destino)

            item_text = f"Ruta {idx}: Origen {origen_id} → Destino {destino_id}"
            item = QListWidgetItem(item_text)
            # Guardamos la referencia al dict real (no a una copia) si es posible
            item.setData(Qt.UserRole, ruta_dict)
            item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.view.rutasList.addItem(item)

    def seleccionar_ruta_desde_lista(self):
        """
        Maneja selección/deselección en rutasList:
        - limpia highlights previos,
        - si no hay selección limpia propertiesTable,
        - si hay selección muestra propiedades y resalta sin duplicar líneas.
        """
        if not hasattr(self.view, "rutasList"):
            return

        items = self.view.rutasList.selectedItems()

        # limpiar highlights previos
        self._clear_highlight_lines()

        if not items:
            # limpiar propertiesTable
            try:
                self.view.propertiesTable.itemChanged.disconnect(self._actualizar_propiedad_ruta)
            except Exception:
                pass
            self.view.propertiesTable.clear()
            self.view.propertiesTable.setRowCount(0)
            self.view.propertiesTable.setColumnCount(2)
            self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])
            try:
                self.view.propertiesTable.itemChanged.connect(self._actualizar_propiedad_ruta)
            except Exception:
                pass
            self.ruta_actual_idx = None
            
            # Restaurar colores normales de TODOS los nodos
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    item.set_normal_color()
            return

        # Guardar el índice de la ruta seleccionada
        self.ruta_actual_idx = self.view.rutasList.currentRow()
        ruta = items[0].data(Qt.UserRole)

        # IMPORTANTE: Restaurar todos los nodos a color normal primero
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.set_normal_color()

        # Deseleccionar todos los nodos primero
        self._changing_selection = True
        try:
            # Deseleccionar nodos en la lista lateral
            self.view.nodosList.clearSelection()
            
            # Deseleccionar nodos en la escena
            for item in self.scene.selectedItems():
                item.setSelected(False)
        finally:
            self._changing_selection = False
        
        self.mostrar_propiedades_ruta(ruta)

        # Resaltar nodos de la ruta - VERSIÓN MEJORADA
        self._resaltar_nodos_de_ruta(ruta)

        # resaltar la ruta seleccionada con líneas amarillas
        try:
            highlight_pen = QPen(Qt.yellow, 3)
            ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
            self._normalize_route_nodes(ruta_dict)
            puntos = []
            if ruta_dict.get("origen"):
                puntos.append(ruta_dict.get("origen"))
            puntos.extend(ruta_dict.get("visita", []) or [])
            if ruta_dict.get("destino"):
                puntos.append(ruta_dict.get("destino"))

            for i in range(len(puntos) - 1):
                n1, n2 = puntos[i], puntos[i + 1]
                try:
                    l = self.scene.addLine(n1["X"], n1["Y"], n2["X"], n2["Y"], highlight_pen)
                    l.setZValue(0.7)
                    l.setData(0, ("route_highlight", i))
                    self._highlight_lines.append(l)
                except Exception:
                    pass
        except Exception:
            pass

    def mostrar_propiedades_ruta(self, ruta):
        """
        Muestra la ruta en propertiesTable con el formato:
        Origen: id_origen
        Destino: id_destino  
        visita: [id1, id2, id3]
        """
        if not ruta:
            return

        try:
            ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
        except Exception:
            ruta_dict = ruta

        self._normalize_route_nodes(ruta_dict)

        try:
            self.view.propertiesTable.itemChanged.disconnect(self._actualizar_propiedad_ruta)
        except Exception:
            pass
        
        self.view.propertiesTable.blockSignals(True)
        self.view.propertiesTable.clear()
        self.view.propertiesTable.setColumnCount(2)
        self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])

        # Mostrar solo origen, destino y visita
        propiedades = [
            ("Origen", self._obtener_id_nodo(ruta_dict.get("origen"))),
            ("Destino", self._obtener_id_nodo(ruta_dict.get("destino"))),
            ("visita", self._obtener_ids_visita(ruta_dict.get("visita", [])))
        ]

        self.view.propertiesTable.setRowCount(len(propiedades))

        for row, (clave, valor) in enumerate(propiedades):
            key_item = QTableWidgetItem(clave)
            key_item.setFlags(Qt.ItemIsEnabled)
            self.view.propertiesTable.setItem(row, 0, key_item)

            val_item = QTableWidgetItem(str(valor))
            val_item.setFlags(val_item.flags() | Qt.ItemIsEditable)
            val_item.setData(Qt.UserRole, (ruta_dict, clave.lower()))
            self.view.propertiesTable.setItem(row, 1, val_item)

        self.view.propertiesTable.blockSignals(False)
        self.view.propertiesTable.itemChanged.connect(self._actualizar_propiedad_ruta)

    def _obtener_id_nodo(self, nodo):
        """Obtiene el ID de un nodo, manejando diferentes formatos"""
        if not nodo:
            return ""
        
        if isinstance(nodo, dict):
            return nodo.get("id", "")
        elif hasattr(nodo, "id"):
            return getattr(nodo, "id", "")
        else:
            return str(nodo)

    def _obtener_ids_visita(self, visita):
        """Convierte una lista de nodos de visita en una lista de IDs"""
        if not visita:
            return "[]"
        
        ids = []
        for nodo in visita:
            ids.append(self._obtener_id_nodo(nodo))
        return f"[{', '.join(str(id) for id in ids)}]"

    def _actualizar_propiedad_ruta(self, item):
        """Actualiza la ruta cuando el usuario edita propertiesTable"""
        if item.column() != 1:
            return
            
        try:
            # Verificar que tenemos una ruta seleccionada
            if self.ruta_actual_idx is None:
                print("No hay ruta seleccionada")
                return

            # Obtener la ruta actual del proyecto
            if self.ruta_actual_idx >= len(self.proyecto.rutas):
                print("Índice de ruta inválido")
                return

            ruta_original = self.proyecto.rutas[self.ruta_actual_idx]
            # Convertir a diccionario
            try:
                ruta_dict = ruta_original.to_dict() if hasattr(ruta_original, "to_dict") else ruta_original
            except Exception:
                ruta_dict = ruta_original

            # Obtener el campo y el valor del item de la tabla
            data = item.data(Qt.UserRole)
            if not data or not isinstance(data, tuple):
                return
            campo = data[1]
            texto = item.text().strip()
            
            print(f"Actualizando ruta - Campo: {campo}, Valor: {texto}")
            
            # Procesar según el campo
            if campo == "origen":
                try:
                    nuevo_id = int(texto)
                    # Buscar nodo existente o crear uno temporal
                    nodo_existente = next((n for n in getattr(self.proyecto, "nodos", []) 
                                         if self._obtener_id_nodo(n) == nuevo_id), None)
                    if nodo_existente:
                        ruta_dict["origen"] = nodo_existente
                    else:
                        # Crear nodo temporal (será normalizado después)
                        ruta_dict["origen"] = {"id": nuevo_id, "X": 0, "Y": 0}
                except ValueError:
                    print(f"Error: ID de origen debe ser un número entero")
                    
            elif campo == "destino":
                try:
                    nuevo_id = int(texto)
                    # Buscar nodo existente o crear uno temporal
                    nodo_existente = next((n for n in getattr(self.proyecto, "nodos", []) 
                                         if self._obtener_id_nodo(n) == nuevo_id), None)
                    if nodo_existente:
                        ruta_dict["destino"] = nodo_existente
                    else:
                        # Crear nodo temporal (será normalizado después)
                        ruta_dict["destino"] = {"id": nuevo_id, "X": 0, "Y": 0}
                except ValueError:
                    print(f"Error: ID de destino debe ser un número entero")
                    
            elif campo == "visita":
                try:
                    # Parsear lista de IDs: [1, 2, 3] o 1, 2, 3
                    if texto.startswith('[') and texto.endswith(']'):
                        texto = texto[1:-1]
                    
                    ids_texto = [id_str.strip() for id_str in texto.split(',')] if texto else []
                    nueva_visita = []
                    
                    for id_str in ids_texto:
                        if id_str:  # Ignorar strings vacíos
                            try:
                                nodo_id = int(id_str)
                                # Buscar nodo existente
                                nodo_existente = next((n for n in getattr(self.proyecto, "nodos", []) 
                                                     if self._obtener_id_nodo(n) == nodo_id), None)
                                if nodo_existente:
                                    nueva_visita.append(nodo_existente)
                                else:
                                    # Crear nodo temporal
                                    nueva_visita.append({"id": nodo_id, "X": 0, "Y": 0})
                            except ValueError:
                                print(f"Error: ID de visita debe ser número entero: {id_str}")
                    
                    ruta_dict["visita"] = nueva_visita
                    
                except Exception as e:
                    print(f"Error procesando lista de visita: {e}")

            # Normalizar y actualizar referencia en proyecto.rutas
            self._normalize_route_nodes(ruta_dict)
            
            # Actualizar la ruta en el proyecto
            self.proyecto.rutas[self.ruta_actual_idx] = ruta_dict

            # Actualizar UI
            self._dibujar_rutas()
            self._mostrar_rutas_lateral()
            
            # Reseleccionar la ruta para actualizar la vista
            if hasattr(self.view, "rutasList"):
                self.view.rutasList.setCurrentRow(self.ruta_actual_idx)

            print(f"Ruta actualizada exitosamente")
            
        except Exception as err:
            print("Error en _actualizar_propiedad_ruta:", err)

    # --- Dibujar rutas guardadas en rojo --
    def _dibujar_rutas(self):
        """Dibuja todas las rutas con REPARACIÓN PREVIA de referencias"""
        try:
            self._clear_route_lines()
        except Exception as e:
            print(f"Error en clear: {e}")

        if not getattr(self, "proyecto", None) or not hasattr(self.proyecto, "rutas"):
            print("DEBUG: No hay proyecto o rutas para dibujar")
            return

        # REPARAR REFERENCIAS ANTES DE DIBUJAR
        self._reparar_referencias_rutas()

        pen = QPen(Qt.red, 2)
        pen.setCosmetic(True)
        self._route_lines = []

        for ruta_idx, ruta in enumerate(self.proyecto.rutas):
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
            except Exception as e:
                print(f"Error convirtiendo ruta {ruta_idx}: {e}")
                ruta_dict = ruta

            # NORMALIZACIÓN (ahora debería funcionar porque las referencias están reparadas)
            self._normalize_route_nodes(ruta_dict)
            
            # ACTUALIZAR LA RUTA EN EL PROYECTO
            self.proyecto.rutas[ruta_idx] = ruta_dict

            # Obtener puntos ACTUALIZADOS
            puntos = []
            if ruta_dict.get("origen"):
                puntos.append(ruta_dict["origen"])
            puntos.extend(ruta_dict.get("visita", []) or [])
            if ruta_dict.get("destino"):
                puntos.append(ruta_dict["destino"])

            if len(puntos) < 2:
                print(f"DEBUG: Ruta {ruta_idx} tiene menos de 2 puntos")
                self._route_lines.append([])
                continue

            route_line_items = []
            for i in range(len(puntos) - 1):
                n1, n2 = puntos[i], puntos[i + 1]
                
                try:
                    # Obtener coordenadas - FORZAR actualización
                    x1 = n1.get("X", 0) if isinstance(n1, dict) else getattr(n1, "X", 0)
                    y1 = n1.get("Y", 0) if isinstance(n1, dict) else getattr(n1, "Y", 0)
                    x2 = n2.get("X", 0) if isinstance(n2, dict) else getattr(n2, "X", 0)
                    y2 = n2.get("Y", 0) if isinstance(n2, dict) else getattr(n2, "Y", 0)
                    
                    line_item = self.scene.addLine(x1, y1, x2, y2, pen)
                    line_item.setZValue(0.5)
                    line_item.setData(0, ("route_line", ruta_idx, i))
                    line_item.setVisible(True)
                    
                    route_line_items.append(line_item)
                    
                except Exception as e:
                    print(f"Error dibujando segmento: {e}")
                    continue
            
            self._route_lines.append(route_line_items)

        self.view.marco_trabajo.viewport().update()

    # --- Propiedades de nodo en QListWidget editable ---
    def mostrar_propiedades_nodo(self, nodo):
        if self._updating_ui:
            return
        self._updating_ui = True
        try:
            try:
                self.view.propertiesTable.itemChanged.disconnect(self._actualizar_propiedad_nodo)
            except Exception:
                pass
            self.view.propertiesTable.blockSignals(True)

            self.view.propertiesTable.clear()
            self.view.propertiesTable.setColumnCount(2)
            self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])

            propiedades = nodo.to_dict() if hasattr(nodo, "to_dict") else nodo
            claves_filtradas = [k for k in propiedades.keys() if k != "id"]

            self.view.propertiesTable.setRowCount(len(claves_filtradas))

            for row, clave in enumerate(claves_filtradas):
                valor = propiedades.get(clave)

                key_item = QTableWidgetItem(clave)
                key_item.setFlags(Qt.ItemIsEnabled)
                self.view.propertiesTable.setItem(row, 0, key_item)

                val_item = QTableWidgetItem(str(valor))
                val_item.setFlags(val_item.flags() | Qt.ItemIsEditable)
                val_item.setData(Qt.UserRole, (nodo, clave))
                self.view.propertiesTable.setItem(row, 1, val_item)
        finally:
            self.view.propertiesTable.blockSignals(False)
            self.view.propertiesTable.itemChanged.connect(self._actualizar_propiedad_nodo)
        self._updating_ui = False

    def actualizar_propiedades_valores(self, nodo, claves=("X", "Y")):
        """
        Actualiza en propertiesTable los valores de las claves indicadas para `nodo`
        sin repoblar toda la tabla. Busca las celdas que tengan Qt.UserRole == (nodo, clave).
        """
        try:
            for row in range(self.view.propertiesTable.rowCount()):
                try:
                    cell = self.view.propertiesTable.item(row, 1)
                    if not cell:
                        continue
                    data = cell.data(Qt.UserRole)
                    if not data or not isinstance(data, tuple):
                        continue
                    cell_nodo, cell_clave = data
                    if cell_nodo == nodo and cell_clave in claves:
                        try:
                            val = nodo.get(cell_clave) if hasattr(nodo, "get") else getattr(nodo, cell_clave, "")
                        except Exception:
                            val = getattr(nodo, cell_clave, "")
                        cell.setText(str(val))
                except Exception:
                    pass
        except Exception as err:
            print("Error en actualizar_propiedades_valores:", err)

    # --- Eliminar nodo con reconfiguración de rutas ---
    def eliminar_nodo(self, nodo, nodo_item):
        """
        Elimina un nodo del proyecto y de la escena. Además:
        - Reconfigura las rutas que contengan este nodo según su posición:
        * Si es el origen: toma el primer elemento de visita como nuevo origen
        * Si es el destino: toma el último elemento de visita como nuevo destino  
        * Si es intermedio: elimina el nodo de la visita y reconecta
        - Actualiza la lista lateral de nodos y rutas y limpia el panel de propiedades si procede.
        """
        try:
            # 1) Quitar de la escena el NodoItem visual si sigue vivo
            try:
                if getattr(nodo_item, "scene", None) and nodo_item.scene() is not None:
                    self.scene.removeItem(nodo_item)
            except Exception:
                pass

            nodo_id = nodo.get("id")

            # 2) Quitar del modelo por identidad o por id
            try:
                if nodo in self.proyecto.nodos:
                    self.proyecto.nodos.remove(nodo)
                else:
                    self.proyecto.nodos = [n for n in self.proyecto.nodos if n.get("id") != nodo_id]
            except Exception:
                # fallback por id
                self.proyecto.nodos = [n for n in getattr(self.proyecto, "nodos", []) if n.get("id") != nodo_id]

            # 3) Quitar de la lista lateral por id
            try:
                for i in range(self.view.nodosList.count()):
                    item = self.view.nodosList.item(i)
                    data = item.data(Qt.UserRole)
                    if hasattr(data, "get") and data.get("id") == nodo_id:
                        self.view.nodosList.takeItem(i)
                        break
            except Exception:
                pass

            # 4) RECONFIGURAR RUTAS en lugar de eliminarlas
            try:
                self._reconfigurar_rutas_por_eliminacion(nodo_id)
            except Exception as err:
                print("Error reconfigurando rutas:", err)
                # fallback: redibujar todo
                try:
                    self._dibujar_rutas()
                    self._mostrar_rutas_lateral()
                except Exception:
                    pass

            # 5) Si el nodo estaba seleccionado, limpiar propiedades y deseleccionar visualmente
            try:
                seleccionados = self.view.nodosList.selectedItems()
                if seleccionados:
                    sel = seleccionados[0].data(Qt.UserRole)
                    if hasattr(sel, "get") and sel.get("id") == nodo_id:
                        self.view.propertiesTable.clear()
                        self.view.propertiesTable.setRowCount(0)
                        self.view.propertiesTable.setColumnCount(2)
                        self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])
            except Exception:
                pass

            print(f"Nodo eliminado: {nodo_id}")
        except Exception as err:
            print("Error eliminando nodo:", err)

    def _reconfigurar_rutas_por_eliminacion(self, nodo_id_eliminado):
        """
        Reconfigura las rutas que contienen el nodo eliminado según su posición:
        - Si es origen: primer elemento de visita como nuevo origen
        - Si es destino: último elemento de visita como nuevo destino
        - Si es intermedio: elimina el nodo de la visita y reconecta
        - Si la ruta queda con solo un nodo, se elimina automáticamente
        """
        if not getattr(self, "proyecto", None):
            return

        nuevas_rutas = []
        
        for ruta in getattr(self.proyecto, "rutas", []) or []:
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
            except Exception:
                ruta_dict = ruta

            # Normalizar la ruta primero
            self._normalize_route_nodes(ruta_dict)
            
            origen = ruta_dict.get("origen")
            visita = ruta_dict.get("visita", []) or []
            destino = ruta_dict.get("destino")
            
            # Verificar si la ruta contiene el nodo eliminado
            contiene_nodo = False
            posicion_en_ruta = None
            
            # Verificar origen
            if origen and isinstance(origen, dict) and origen.get("id") == nodo_id_eliminado:
                contiene_nodo = True
                posicion_en_ruta = "origen"
            
            # Verificar destino
            if not contiene_nodo and destino and isinstance(destino, dict) and destino.get("id") == nodo_id_eliminado:
                contiene_nodo = True
                posicion_en_ruta = "destino"
            
            # Verificar visita
            if not contiene_nodo:
                for i, nodo_visita in enumerate(visita):
                    if isinstance(nodo_visita, dict) and nodo_visita.get("id") == nodo_id_eliminado:
                        contiene_nodo = True
                        posicion_en_ruta = f"visita_{i}"
                        break
            
            if not contiene_nodo:
                # La ruta no contiene el nodo eliminado, se mantiene igual
                nuevas_rutas.append(ruta)
                continue
            
            print(f"Reconfigurando ruta - Nodo eliminado en posición: {posicion_en_ruta}")
            
            # RECONFIGURACIÓN SEGÚN POSICIÓN
            if posicion_en_ruta == "origen":
                # Si es el origen: tomar primer elemento de visita como nuevo origen
                if visita:
                    nuevo_origen = visita[0]
                    nueva_visita = visita[1:]  # resto de la visita
                    nuevo_destino = destino
                    
                    ruta_dict["origen"] = nuevo_origen
                    ruta_dict["visita"] = nueva_visita
                    ruta_dict["destino"] = nuevo_destino
                    
                    # Verificar si la ruta queda con al menos 2 nodos
                    if self._ruta_tiene_al_menos_dos_nodos(ruta_dict):
                        nuevas_rutas.append(ruta_dict)
                        print(f"  -> Nuevo origen: {nuevo_origen.get('id')}")
                    else:
                        print("  -> Ruta eliminada (queda con menos de 2 nodos)")
                else:
                    # No hay visita, el destino pasa a ser el nuevo origen
                    if destino:
                        ruta_dict["origen"] = destino
                        ruta_dict["visita"] = []
                        ruta_dict["destino"] = None
                        
                        # Verificar si la ruta queda con al menos 2 nodos
                        if self._ruta_tiene_al_menos_dos_nodos(ruta_dict):
                            nuevas_rutas.append(ruta_dict)
                            print(f"  -> Destino {destino.get('id')} pasa a ser origen")
                        else:
                            print("  -> Ruta eliminada (queda con solo un nodo)")
                    else:
                        # No hay destino, la ruta queda inválida - se elimina
                        print("  -> Ruta eliminada (sin origen ni destino válido)")
            
            elif posicion_en_ruta == "destino":
                # Si es el destino: tomar último elemento de visita como nuevo destino
                if visita:
                    nuevo_origen = origen
                    nueva_visita = visita[:-1]  # todos menos el último
                    nuevo_destino = visita[-1]  # último elemento
                    
                    ruta_dict["origen"] = nuevo_origen
                    ruta_dict["visita"] = nueva_visita
                    ruta_dict["destino"] = nuevo_destino
                    
                    # Verificar si la ruta queda con al menos 2 nodos
                    if self._ruta_tiene_al_menos_dos_nodos(ruta_dict):
                        nuevas_rutas.append(ruta_dict)
                        print(f"  -> Nuevo destino: {nuevo_destino.get('id')}")
                    else:
                        print("  -> Ruta eliminada (queda con menos de 2 nodos)")
                else:
                    # No hay visita, el origen pasa a ser el nuevo destino
                    if origen:
                        ruta_dict["origen"] = None
                        ruta_dict["visita"] = []
                        ruta_dict["destino"] = origen
                        
                        # Verificar si la ruta queda con al menos 2 nodos
                        if self._ruta_tiene_al_menos_dos_nodos(ruta_dict):
                            nuevas_rutas.append(ruta_dict)
                            print(f"  -> Origen {origen.get('id')} pasa a ser destino")
                        else:
                            print("  -> Ruta eliminada (queda con solo un nodo)")
                    else:
                        # No hay origen, la ruta queda inválida - se elimina
                        print("  -> Ruta eliminada (sin origen ni destino válido)")
            
            elif posicion_en_ruta.startswith("visita_"):
                # Si es intermedio: eliminar de la visita y mantener conexión
                posicion = int(posicion_en_ruta.split("_")[1])
                
                nuevo_origen = origen
                nueva_visita = [n for i, n in enumerate(visita) if i != posicion]
                nuevo_destino = destino
                
                ruta_dict["origen"] = nuevo_origen
                ruta_dict["visita"] = nueva_visita
                ruta_dict["destino"] = nuevo_destino
                
                # Verificar si la ruta queda con al menos 2 nodos
                if self._ruta_tiene_al_menos_dos_nodos(ruta_dict):
                    nuevas_rutas.append(ruta_dict)
                    print(f"  -> Nodo intermedio eliminado de visita, nueva longitud: {len(nueva_visita)}")
                else:
                    print("  -> Ruta eliminada (queda con menos de 2 nodos después de eliminar visita)")
            
            else:
                # Caso por defecto - mantener la ruta si tiene al menos 2 nodos
                if self._ruta_tiene_al_menos_dos_nodos(ruta_dict):
                    nuevas_rutas.append(ruta)
                else:
                    print("  -> Ruta eliminada (queda con menos de 2 nodos)")
        
        # Actualizar las rutas del proyecto
        try:
            self.proyecto.rutas = nuevas_rutas
        except Exception:
            setattr(self.proyecto, "rutas", nuevas_rutas)
        
        # Redibujar rutas y actualizar UI
        try:
            self._dibujar_rutas()
            self._mostrar_rutas_lateral()
        except Exception as err:
            print("Error actualizando UI después de reconfigurar rutas:", err)

    def _ruta_tiene_al_menos_dos_nodos(self, ruta_dict):
        """
        Verifica si una ruta tiene al menos 2 nodos (origen, destino o nodos en visita).
        Una ruta necesita al menos 2 nodos para poder trazar líneas entre ellos.
        """
        try:
            # Contar nodos en origen, destino y visita
            count = 0
            
            if ruta_dict.get("origen") is not None:
                count += 1
            
            if ruta_dict.get("destino") is not None:
                count += 1
            
            count += len(ruta_dict.get("visita", []) or [])
            
            return count >= 2
        except Exception:
            return False

    # --- Normalizador mejorado para rutas ---
    def _normalize_route_nodes(self, ruta_dict):
        """
        RECONSTRUYE COMPLETAMENTE las referencias de nodos en las rutas
        usando los nodos actuales del proyecto. VERSIÓN CORREGIDA.
        """
        try:
            # 1. NORMALIZAR ORIGEN - Buscar el nodo actual en self.proyecto.nodos
            origen = ruta_dict.get("origen")
            if origen:
                if isinstance(origen, dict) and 'id' in origen:
                    origen_id = origen['id']
                    
                    # Buscar el nodo ACTUAL en el proyecto
                    nodo_actual = None
                    for nodo in getattr(self.proyecto, "nodos", []):
                        try:
                            # Usar nodo.get() para objetos Nodo
                            if hasattr(nodo, 'get'):
                                if nodo.get('id') == origen_id:
                                    nodo_actual = nodo
                                    break
                            elif isinstance(nodo, dict) and nodo.get('id') == origen_id:
                                nodo_actual = nodo
                                break
                        except Exception as e:
                            continue
                    
                    if nodo_actual:
                        # Actualizar las coordenadas del origen con las del nodo actual
                        if hasattr(nodo_actual, 'get'):
                            origen['X'] = nodo_actual.get('X')
                            origen['Y'] = nodo_actual.get('Y')
                        else:
                            origen['X'] = nodo_actual.get('X', origen.get('X', 0))
                            origen['Y'] = nodo_actual.get('Y', origen.get('Y', 0))
                        ruta_dict["origen"] = origen
            
            # 2. NORMALIZAR DESTINO 
            destino = ruta_dict.get("destino")
            if destino:
                if isinstance(destino, dict) and 'id' in destino:
                    destino_id = destino['id']
                    
                    # Buscar el nodo ACTUAL en el proyecto - VERSIÓN CORREGIDA
                    nodo_actual = None
                    for nodo in getattr(self.proyecto, "nodos", []):
                        try:
                            # Usar nodo.get() para objetos Nodo
                            if hasattr(nodo, 'get'):
                                if nodo.get('id') == destino_id:
                                    nodo_actual = nodo
                                    break
                            elif isinstance(nodo, dict) and nodo.get('id') == destino_id:
                                nodo_actual = nodo
                                break
                        except Exception as e:
                            continue
                    
                    if nodo_actual:
                        # Actualizar las coordenadas del destino con las del nodo actual
                        if hasattr(nodo_actual, 'get'):
                            destino['X'] = nodo_actual.get('X')
                            destino['Y'] = nodo_actual.get('Y')
                        else:
                            destino['X'] = nodo_actual.get('X', destino.get('X', 0))
                            destino['Y'] = nodo_actual.get('Y', destino.get('Y', 0))
                        ruta_dict["destino"] = destino
            
            # 3. NORMALIZAR VISITA
            visita = ruta_dict.get("visita", []) or []
            nueva_visita = []
            
            for v in visita:
                if isinstance(v, dict) and 'id' in v:
                    visita_id = v['id']
                    
                    # Buscar el nodo ACTUAL en el proyecto
                    nodo_actual = None
                    for nodo in getattr(self.proyecto, "nodos", []):
                        try:
                            # Usar nodo.get() para objetos Nodo
                            if hasattr(nodo, 'get'):
                                if nodo.get('id') == visita_id:
                                    nodo_actual = nodo
                                    break
                            elif isinstance(nodo, dict) and nodo.get('id') == visita_id:
                                nodo_actual = nodo
                                break
                        except Exception as e:
                            continue
                    
                    if nodo_actual:
                        # Actualizar las coordenadas de la visita con las del nodo actual
                        if hasattr(nodo_actual, 'get'):
                            v['X'] = nodo_actual.get('X')
                            v['Y'] = nodo_actual.get('Y')
                        else:
                            v['X'] = nodo_actual.get('X', v.get('X', 0))
                            v['Y'] = nodo_actual.get('Y', v.get('Y', 0))
                        nueva_visita.append(v)
                    else:
                        nueva_visita.append(v)
                else:
                    nueva_visita.append(v)
            
            ruta_dict["visita"] = nueva_visita
            
        except Exception as e:
            print(f"ERROR CRÍTICO en _normalize_route_nodes: {e}")

    # --- MÉTODOS NUEVOS PARA REPARACIÓN DE REFERENCIAS ---
    
    def _reparar_referencias_rutas(self):
        """
        REPARA LAS RUTAS: Asegura que todos los nodos en las rutas existan en el proyecto
        y actualiza las referencias con los nodos actuales. VERSIÓN CORREGIDA.
        """
        if not hasattr(self.proyecto, "nodos") or not hasattr(self.proyecto, "rutas"):
            return

        # Crear mapa de nodos por ID para búsqueda rápida - VERSIÓN CORREGIDA
        mapa_nodos = {}
        for nodo in self.proyecto.nodos:
            try:
                # CORRECCIÓN: Usar nodo.get() para objetos Nodo
                if hasattr(nodo, 'get'):
                    nodo_id = nodo.get('id')
                else:
                    nodo_id = nodo.get('id') if isinstance(nodo, dict) else None
                    
                if nodo_id is not None:
                    mapa_nodos[nodo_id] = nodo
            except Exception as e:
                pass

        for ruta_idx, ruta in enumerate(self.proyecto.rutas):
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
                
                # Reparar ORIGEN - VERSIÓN CORREGIDA
                origen = ruta_dict.get("origen")
                if origen and isinstance(origen, dict) and 'id' in origen:
                    origen_id = origen['id']
                    if origen_id in mapa_nodos:
                        # Actualizar coordenadas en lugar de reemplazar el objeto
                        nodo_actual = mapa_nodos[origen_id]
                        if hasattr(nodo_actual, 'get'):
                            origen['X'] = nodo_actual.get('X')
                            origen['Y'] = nodo_actual.get('Y')
                        else:
                            origen['X'] = nodo_actual.get('X', origen.get('X', 0))
                            origen['Y'] = nodo_actual.get('Y', origen.get('Y', 0))
                
                # Reparar DESTINO - VERSIÓN CORREGIDA  
                destino = ruta_dict.get("destino")
                if destino and isinstance(destino, dict) and 'id' in destino:
                    destino_id = destino['id']
                    if destino_id in mapa_nodos:
                        # Actualizar coordenadas en lugar de reemplazar el objeto
                        nodo_actual = mapa_nodos[destino_id]
                        if hasattr(nodo_actual, 'get'):
                            destino['X'] = nodo_actual.get('X')
                            destino['Y'] = nodo_actual.get('Y')
                        else:
                            destino['X'] = nodo_actual.get('X', destino.get('X', 0))
                            destino['Y'] = nodo_actual.get('Y', destino.get('Y', 0))
                
                # Reparar VISITA - VERSIÓN CORREGIDA
                visita = ruta_dict.get("visita", [])
                nueva_visita = []
                for v in visita:
                    if isinstance(v, dict) and 'id' in v:
                        visita_id = v['id']
                        if visita_id in mapa_nodos:
                            # CORRECCIÓN: Actualizar coordenadas en lugar de reemplazar el objeto
                            nodo_actual = mapa_nodos[visita_id]
                            if hasattr(nodo_actual, 'get'):
                                v['X'] = nodo_actual.get('X')
                                v['Y'] = nodo_actual.get('Y')
                            else:
                                v['X'] = nodo_actual.get('X', v.get('X', 0))
                                v['Y'] = nodo_actual.get('Y', v.get('Y', 0))
                            nueva_visita.append(v)
                        else:
                            nueva_visita.append(v)
                    else:
                        nueva_visita.append(v)
                
                ruta_dict["visita"] = nueva_visita
                
                # Actualizar la ruta en el proyecto
                self.proyecto.rutas[ruta_idx] = ruta_dict
                    
            except Exception as e:
                print(f"Error reparando ruta {ruta_idx}: {e}")

    # --- Actualizar líneas cuando un nodo se mueve ---
    def on_nodo_moved(self, nodo_item):
        """VERSIÓN MEJORADA con reparación de referencias"""
        try:
            nodo = getattr(nodo_item, "nodo", None)
            if not nodo:
                return

            # 1. Obtener posición ACTUAL del nodo
            scene_pos = nodo_item.scenePos()
            x = int(scene_pos.x() + nodo_item.size / 2)
            y = int(scene_pos.y() + nodo_item.size / 2)

            # 2. Obtener ID del nodo movido
            nodo_id = nodo.get("id") if isinstance(nodo, dict) else getattr(nodo, "id", None)

            # 3. Actualizar modelo
            if isinstance(nodo, dict):
                nodo["X"] = x
                nodo["Y"] = y
            else:
                setattr(nodo, "X", x)
                setattr(nodo, "Y", y)

            # 4. REPARAR REFERENCIAS ANTES DE ACTUALIZAR RUTAS
            self._reparar_referencias_rutas()

            # 5. ACTUALIZAR UI
            self.actualizar_lista_nodo(nodo)
            self.actualizar_propiedades_valores(nodo, claves=("X", "Y"))

            # 6. ACTUALIZAR RUTAS
            self._dibujar_rutas()

            # 7. ACTUALIZAR HIGHLIGHTS
            if hasattr(self.view, "rutasList") and self.view.rutasList.selectedItems():
                self.seleccionar_ruta_desde_lista()

            # 8. FORZAR ACTUALIZACIÓN VISUAL
            self.scene.update()
            self.view.marco_trabajo.viewport().update()

        except Exception as err:
            print(f"ERROR CRÍTICO en on_nodo_moved: {err}")

    # --- Utilidades para líneas y rutas ---
    def _clear_route_lines(self):
        """
        Elimina todas las líneas de rutas guardadas en self._route_lines de la escena.
        Versión mejorada.
        """
        try:
            # eliminar líneas rojas
            for route_lines in getattr(self, "_route_lines", []) or []:
                for li in (route_lines or []):
                    try:
                        if li and li.scene() is not None:
                            self.scene.removeItem(li)
                    except Exception:
                        pass
        except Exception:
            pass
        
        # reset
        self._route_lines = []

    def _clear_highlight_lines(self):
        """Elimina todas las líneas de highlight (amarillas) de la escena."""
        try:
            for hl in getattr(self, "_highlight_lines", []) or []:
                try:
                    if hl and hl.scene() is not None:
                        self.scene.removeItem(hl)
                except Exception:
                    pass
        except Exception:
            pass
        self._highlight_lines = []

    def _actualizar_propiedad_nodo(self, item):
        """
        Maneja cambios en propertiesTable para un nodo.
        - Evita reentradas con self._updating_ui.
        - Parsea el valor (ast.literal_eval cuando sea posible).
        - Actualiza el modelo (nodo.update) y la UI.
        """
        if self._updating_ui or item.column() != 1:
            return

        try:
            nodo, clave = item.data(Qt.UserRole)
        except Exception:
            return

        texto = item.text()
        try:
            valor = ast.literal_eval(texto)
        except Exception:
            valor = texto

        try:
            # Actualizar el modelo
            if hasattr(nodo, "update"):
                nodo.update({clave: valor})
            else:
                try:
                    setattr(nodo, clave, valor)
                except Exception:
                    pass
            print(f"Nodo actualizado: {clave} = {valor}")
        except Exception as err:
            print("Error actualizando nodo en el modelo:", err)
            return

        # Si cambiaron coordenadas, actualizar la posición visual del NodoItem
        if clave in ("X", "Y"):
            try:
                for scene_item in self.scene.items():
                    if isinstance(scene_item, NodoItem) and getattr(scene_item, "nodo", None) == nodo:
                        try:
                            scene_item.actualizar_posicion()
                        except Exception:
                            try:
                                x = int(nodo.get("X", 0)) if hasattr(nodo, "get") else int(getattr(nodo, "X", 0))
                                y = int(nodo.get("Y", 0)) if hasattr(nodo, "get") else int(getattr(nodo, "Y", 0))
                                scene_item.setPos(x - scene_item.size / 2, y - scene_item.size / 2)
                            except Exception:
                                pass
                        break
            except Exception:
                pass

            # Forzar actualización de líneas de rutas asociadas
            try:
                # Buscar el NodoItem correspondiente
                for scene_item in self.scene.items():
                    if isinstance(scene_item, NodoItem) and getattr(scene_item, "nodo", None) == nodo:
                        self.on_nodo_moved(scene_item)
                        break
            except Exception:
                try:
                    self._dibujar_rutas()
                except Exception:
                    pass

        # Actualizar texto en la lista lateral (si existe)
        try:
            for i in range(self.view.nodosList.count()):
                li = self.view.nodosList.item(i)
                if li.data(Qt.UserRole) == nodo:
                    li.setText(f"ID {nodo.get('id')} - ({nodo.get('X')}, {nodo.get('Y')})")
                    break
        except Exception:
            pass

        # Si la tabla de propiedades está mostrando este nodo, mantenerla sincronizada
        try:
            seleccionados = self.view.nodosList.selectedItems()
            if seleccionados and seleccionados[0].data(Qt.UserRole) == nodo:
                self.actualizar_propiedades_valores(nodo, claves=("X", "Y"))
        except Exception:
            pass

    # --- Event filter para deselección al clicar en fondo (MODIFICADO) ---
    def eventFilter(self, obj, event):
        # Detectar click izquierdo en el viewport y deseleccionar si se hace en el fondo
        try:
            if event.type() == QEvent.MouseButtonPress:
                # mapear a escena
                pos = self.view.marco_trabajo.mapToScene(event.pos())
                items = self.scene.items(pos)
                # si no hay NodoItem bajo el cursor, limpiar selección
                if not any(isinstance(it, NodoItem) for it in items):
                    # deseleccionar items de la escena
                    try:
                        for it in self.scene.selectedItems():
                            it.setSelected(False)
                    except Exception:
                        pass
                    # deseleccionar lista de nodos
                    try:
                        self.view.nodosList.clearSelection()
                    except Exception:
                        pass
                    # deseleccionar lista de rutas y limpiar highlights
                    try:
                        if hasattr(self.view, "rutasList"):
                            self.view.rutasList.clearSelection()
                    except Exception:
                        pass
                    self._clear_highlight_lines()
                    # limpiar propertiesTable
                    try:
                        self.view.propertiesTable.clear()
                        self.view.propertiesTable.setRowCount(0)
                        self.view.propertiesTable.setColumnCount(2)
                        self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])
                    except Exception:
                        pass
                    # Restaurar colores de nodos
                    for item in self.scene.items():
                        if isinstance(item, NodoItem):
                            item.set_normal_color()
            return False
        except Exception:
            return False

    def diagnosticar_estado_proyecto(self):
        """Diagnóstico completo del estado del proyecto"""
        print("\n" + "="*50)
        print("DIAGNÓSTICO COMPLETO DEL PROYECTO")
        print("="*50)
        
        if not self.proyecto:
            print("No hay proyecto cargado")
            return
            
        print(f"Nodos en proyecto: {len(getattr(self.proyecto, 'nodos', []))}")
        for i, nodo in enumerate(getattr(self.proyecto, "nodos", [])):
            try:
                # CORRECCIÓN: Usar nodo.get() para objetos Nodo
                if hasattr(nodo, 'get'):
                    nodo_id = nodo.get('id', "N/A")
                    x = nodo.get('X', "N/A")
                    y = nodo.get('Y', "N/A")
                else:
                    nodo_id = nodo.get('id', "N/A") if isinstance(nodo, dict) else "N/A"
                    x = nodo.get('X', "N/A") if isinstance(nodo, dict) else "N/A"
                    y = nodo.get('Y', "N/A") if isinstance(nodo, dict) else "N/A"
                print(f"  Nodo {i}: ID {nodo_id} - ({x}, {y})")
            except Exception as e:
                print(f"  Nodo {i}: ERROR - {e}")
        
        print(f"Rutas en proyecto: {len(getattr(self.proyecto, 'rutas', []))}")
        for i, ruta in enumerate(getattr(self.proyecto, "rutas", [])):
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
                origen = ruta_dict.get("origen", {})
                destino = ruta_dict.get("destino", {})
                
                # CORRECCIÓN: Usar .get() para diccionarios
                origen_id = origen.get("id", "N/A") if isinstance(origen, dict) else "N/A"
                destino_id = destino.get("id", "N/A") if isinstance(destino, dict) else "N/A"
                print(f"  Ruta {i}: Origen {origen_id} -> Destino {destino_id}")
            except Exception as e:
                print(f"  Ruta {i}: ERROR - {e}")
        
        print("="*50)