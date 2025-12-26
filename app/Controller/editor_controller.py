from PyQt5.QtWidgets import (
    QFileDialog, QGraphicsScene, QGraphicsPixmapItem,
    QButtonGroup, QListWidgetItem,
    QTableWidgetItem, QHeaderView, QMenu, QMessageBox, QLabel
)
from PyQt5.QtGui import QPixmap, QPen, QColor, QCursor
from PyQt5.QtCore import Qt, QEvent, QObject, QSize
from Model.Proyecto import Proyecto
from Model.ExportadorDB import ExportadorDB
from Controller.mover_controller import MoverController
from Controller.colocar_controller import ColocarController
from Controller.ruta_controller import RutaController
from View.view import NodoListItemWidget, RutaListItemWidget
from View.node_item import NodoItem
import ast

class EditorController(QObject):
    def __init__(self, view, proyecto=None):
        super().__init__()
        self.view = view
        self.proyecto = proyecto
        
        # --- ESCALA GLOBAL: 1 píxel = 0.05 metros ---
        self.ESCALA = 0.05

        # --- NUEVO: Estado del cursor ---
        self._cursor_sobre_nodo = False
        self._arrastrando_nodo = False  # Para rastrear si estamos arrastrando un nodo

        if self.proyecto:
            self._conectar_señales_proyecto()

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
        
        # --- NUEVO: Submenú Exportar ---
        self.view.menuProyecto.addSeparator()  # Separador visual
        exportar_action = self.view.menuProyecto.addAction("Exportar a SQLite...")
        exportar_action.triggered.connect(self.exportar_a_sqlite)

        nuevo_action.triggered.connect(self.nuevo_proyecto)
        abrir_action.triggered.connect(self.abrir_proyecto)
        guardar_action.triggered.connect(self.guardar_proyecto)

        # --- Subcontroladores---
        self.mover_ctrl = MoverController(self.proyecto, self.view, self)
        self.colocar_ctrl = ColocarController(self.proyecto, self.view, self)
        self.ruta_ctrl = RutaController(self.proyecto, self.view, self)

        # --- Grupo de botones de modo ---
        self.modo_group = QButtonGroup()
        self.modo_group.setExclusive(False)

        self.modo_group.addButton(self.view.mover_button)
        self.modo_group.addButton(self.view.colocar_vertice_button)
        self.modo_group.addButton(self.view.crear_ruta_button)

        self.modo_group.buttonClicked.connect(self.cambiar_modo)
        self.modo_actual = None

        # Estado inicial: modo por defecto (navegación)
        self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.ScrollHandDrag)

        self.scene.selectionChanged.connect(self.manejar_seleccion_nodo)

        self._changing_selection = False
        self._updating_ui = False

        # mantener referencias a las líneas de rutas dibujadas
        self._route_lines = []            
        self._highlight_lines = []        

        # instalar filtro de eventos en el viewport
        try:
            self.view.marco_trabajo.viewport().installEventFilter(self)
        except Exception:
            pass

        # Instalar filtro de eventos en la ventana principal para manejo de teclado
        self.view.installEventFilter(self)

        if hasattr(self.view, "rutasList"):
            try:
                self.view.rutasList.itemSelectionChanged.disconnect(self.seleccionar_ruta_desde_lista)
            except Exception:
                pass
            self.view.rutasList.itemSelectionChanged.connect(self.seleccionar_ruta_desde_lista)

        # Índice de la ruta actualmente seleccionada
        self.ruta_actual_idx = None
        
        # --- SISTEMA DE DESHACER/REHACER (UNDO/REDO) ---
        self.historial_movimientos = []  # Lista de movimientos
        self.indice_historial = -1  # Puntero a la posición actual en el historial (-1 = vacío)
        self.max_historial = 100  # Límite de cambios en el historial
        
        # Movimiento actual en progreso (para guardar en historial)
        self.movimiento_actual = None  # {'nodo': nodo_item, 'x_inicial': x, 'y_inicial': y}
        
        # --- SISTEMA DE VISIBILIDAD MEJORADO CON RECONSTRUCCIÓN DE RUTAS ---
        self.visibilidad_nodos = {}  # {nodo_id: visible} - Para UI
        self.visibilidad_rutas = {}  # {ruta_index: visible} - Para líneas
        self.nodo_en_rutas = {}  # {nodo_id: [ruta_index1, ...]} - Relaciones originales
        
        # NUEVO: Rutas reconstruidas para dibujo (excluyendo nodos ocultos)
        self.rutas_para_dibujo = []  # Lista de rutas reconstruidas para dibujar
        
        # --- CAMBIO: Conectar botones de visibilidad como interruptores ---
        if hasattr(self.view, "btnOcultarTodo"):
            self.view.btnOcultarTodo.setText("Ocultar Nodos")  # Cambiar texto inicial
            self.view.btnOcultarTodo.clicked.connect(self.toggle_visibilidad_nodos)
        if hasattr(self.view, "btnMostrarTodo"):
            self.view.btnMostrarTodo.setText("Ocultar Rutas")  # Cambiar texto inicial
            self.view.btnMostrarTodo.clicked.connect(self.toggle_visibilidad_rutas)
            self.view.btnMostrarTodo.setEnabled(True)  # Inicialmente habilitado
        
        # Si hay proyecto inicial, configurarlo
        if self.proyecto:
            self._actualizar_referencias_proyecto(self.proyecto)
            self.inicializar_visibilidad()
            # Asegurar que los botones estén inicializados
            self._actualizar_lista_nodos_con_widgets()
        
        # --- NUEVO: Actualizar descripción del modo inicial ---
        self.actualizar_descripcion_modo()

        # Asegurar que el cursor inicial sea correcto
        self._actualizar_cursor()

    # --- MÉTODOS DE CONVERSIÓN PÍXELES-METROS ---
    def pixeles_a_metros(self, valor_px):
        """Convierte píxeles a metros usando la escala global."""
        return valor_px * self.ESCALA
    
    def metros_a_pixeles(self, valor_m):
        """Convierte metros a píxeles usando la escala global."""
        return valor_m / self.ESCALA
    
    def format_coords_m(self, x_px, y_px):
        """Formatea coordenadas en metros con 2 decimales."""
        x_m = self.pixeles_a_metros(x_px)
        y_m = self.pixeles_a_metros(y_px)
        return f"{x_m:.2f}, {y_m:.2f}"

    # --- MÉTODOS PARA GESTIÓN DE PUNTEROS ---
    def _actualizar_cursor(self, cursor_tipo=None):
        """
        Actualiza el cursor del viewport según el modo y situación.
        
        Args:
            cursor_tipo: Puede ser None (auto-determinar) o un valor de Qt.CursorShape
        """
        try:
            # Depuración para entender qué está pasando
            debug_info = f"DEBUG Cursor: modo={self.modo_actual}, sobre_nodo={self._cursor_sobre_nodo}, arrastrando={self._arrastrando_nodo}"
            print(debug_info)
            
            if cursor_tipo is not None:
                # Si se especifica un cursor específico, usarlo
                self.view.marco_trabajo.viewport().setCursor(QCursor(cursor_tipo))
                print(f"Cursor forzado a: {cursor_tipo}")
                return
            
            # Determinar cursor según el modo actual y estado
            if self.modo_actual is None:
                # MODO POR DEFECTO (navegación)
                if self._cursor_sobre_nodo:
                    # ABSOLUTAMENTE SIEMPRE PointingHandCursor cuando está sobre un nodo
                    cursor = Qt.PointingHandCursor
                    print("MODO POR DEFECTO: PointingHandCursor (sobre nodo)")
                else:
                    # Dejar que Qt maneje el cursor de navegación (ScrollHandDrag)
                    self.view.marco_trabajo.viewport().unsetCursor()
                    print("MODO POR DEFECTO: Cursor por defecto de Qt")
                    return
                    
            elif self.modo_actual == "mover":
                # MODO MOVER - CORREGIDO
                if self._arrastrando_nodo:
                    # Mano cerrada cuando se está arrastrando un nodo
                    cursor = Qt.ClosedHandCursor
                    print("MODO MOVER: ClosedHandCursor (arrastrando nodo)")
                elif self._cursor_sobre_nodo:
                    # PointingHandCursor cuando está sobre un nodo pero NO arrastrando
                    cursor = Qt.PointingHandCursor
                    print("MODO MOVER: PointingHandCursor (sobre nodo, no arrastrando)")
                else:
                    # Flecha cuando no está sobre un nodo
                    cursor = Qt.ArrowCursor
                    print("MODO MOVER: ArrowCursor (no sobre nodo)")
                    
            elif self.modo_actual == "colocar":
                # MODO COLOCAR VÉRTICE
                cursor = Qt.ArrowCursor
                print("MODO COLOCAR: ArrowCursor")
                
            elif self.modo_actual == "ruta":
                # MODO RUTA
                cursor = Qt.ArrowCursor
                print("MODO RUTA: ArrowCursor")
                
            else:
                # Cualquier otro modo
                cursor = Qt.ArrowCursor
                print("MODO DESCONOCIDO: ArrowCursor")
            
            # Aplicar el cursor
            self.view.marco_trabajo.viewport().setCursor(QCursor(cursor))
            
        except Exception as e:
            print(f"Error al actualizar cursor: {e}")


    def nodo_hover_entered(self, nodo_item):
        """Cuando el ratón entra en un nodo"""
        self._cursor_sobre_nodo = True
        print(f"HOVER ENTRADO: Nodo ID {nodo_item.nodo.get('id')}")
        self._actualizar_cursor()

    def nodo_hover_leaved(self, nodo_item):
        """Cuando el ratón sale de un nodo"""
        self._cursor_sobre_nodo = False
        print(f"HOVER SALIDO: Nodo ID {nodo_item.nodo.get('id')}")
        self._actualizar_cursor()

    def nodo_arrastre_iniciado(self):
        """Cuando se inicia el arrastre de un nodo en modo mover"""
        if self.modo_actual == "mover":
            self._arrastrando_nodo = True
            print("ARRASRE INICIADO: Mano cerrada")
            self._actualizar_cursor()

    def nodo_arrastre_terminado(self):
        """Cuando se termina el arrastre de un nodo"""
        self._arrastrando_nodo = False
        print("ARRASRE TERMINADO: Mano apuntando")
        self._actualizar_cursor()

    # --- MÉTODOS NUEVOS PARA MANEJO DE PROYECTO ---
    def _actualizar_referencias_proyecto(self, proyecto):
        """Actualiza todas las referencias al proyecto en controladores y subcontroladores"""
        self.proyecto = proyecto
        
        # Actualizar en subcontroladores
        self.mover_ctrl.proyecto = proyecto
        self.colocar_ctrl.proyecto = proyecto
        self.ruta_ctrl.proyecto = proyecto
        
        # IMPORTANTE: Resetear el estado de los subcontroladores
        if self.modo_actual:
            self._resetear_modo_actual()
        
        # Asegurar que todos los nodos tienen el campo es_cargador
        for nodo in self.proyecto.nodos:
            if isinstance(nodo, dict):
                if "es_cargador" not in nodo:
                    nodo["es_cargador"] = 0  # Valor por defecto
            elif not hasattr(nodo, "es_cargador"):
                setattr(nodo, "es_cargador", 0)
        
        print("✓ Referencias del proyecto actualizadas en todos los controladores")

    def _resetear_modo_actual(self):
        """Resetea el modo actual para forzar reconfiguración"""
        modo_temp = self.modo_actual
        self.modo_actual = None
        
        # Desactivar todos los botones primero
        for b in (self.view.mover_button,
                  self.view.colocar_vertice_button, self.view.crear_ruta_button):
            b.setChecked(False)
        
        # Re-activar el modo si es necesario
        if modo_temp:
            boton = None
            if modo_temp == "mover":
                boton = self.view.mover_button
            elif modo_temp == "colocar":
                boton = self.view.colocar_vertice_button
            elif modo_temp == "ruta":
                boton = self.view.crear_ruta_button
            
            if boton:
                boton.setChecked(True)
                self.cambiar_modo(boton)

    def _limpiar_ui_completa(self):
        """Limpia toda la UI para nuevo proyecto"""
        # Limpiar escena
        self.scene.clear()
        
        # Limpiar listas
        self.view.nodosList.clear()
        if hasattr(self.view, "rutasList"):
            self.view.rutasList.clear()
        
        # Limpiar tabla de propiedades
        self.view.propertiesTable.clear()
        self.view.propertiesTable.setRowCount(0)
        self.view.propertiesTable.setColumnCount(2)
        self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])
        
        # Limpiar líneas de ruta
        self._clear_route_lines()
        self._clear_highlight_lines()
        
        # Resetear índices
        self.ruta_actual_idx = None
        self._changing_selection = False
        self._updating_ui = False
        
        # Limpiar historial cuando se crea/abre un nuevo proyecto
        self._limpiar_historial()
        
        # Limpiar visibilidad
        self.visibilidad_nodos.clear()
        self.visibilidad_rutas.clear()
        self.nodo_en_rutas.clear()
        
        # Resetear textos y estados de botones de visibilidad
        if hasattr(self.view, "btnOcultarTodo"):
            self.view.btnOcultarTodo.setText("Ocultar Nodos")
        if hasattr(self.view, "btnMostrarTodo"):
            self.view.btnMostrarTodo.setText("Ocultar Rutas")
            self.view.btnMostrarTodo.setEnabled(True)  # Habilitado inicialmente
        
        print("✓ UI completamente limpiada para nuevo proyecto")

    # --- Gestión de modos ---
    def cambiar_modo(self, boton):
        print(f"\n=== CAMBIANDO MODO: boton={boton.text()} ===")
        
        # Si el botón ya estaba activado y se hace clic, se desactiva
        if not boton.isChecked():
            print("Desactivando todos los modos...")
            # Desactivar todos los modos
            self.modo_actual = None
            self.mover_ctrl.desactivar()
            self.colocar_ctrl.desactivar()
            
            # IMPORTANTE: Desconectar señales de movimiento
            try:
                for item in self.scene.items():
                    if isinstance(item, NodoItem):
                        try:
                            item.moved.disconnect()
                        except:
                            pass
            except Exception:
                pass
            
            # IMPORTANTE: CORRECCIÓN CRÍTICA - SIEMPRE DESACTIVAR EL CONTROLADOR DE RUTA
            try:
                self.ruta_ctrl.desactivar()
            except Exception as e:
                print(f"Error al desactivar ruta: {e}")
            
            # VOLVER AL MODO POR DEFECTO: navegación del mapa
            self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.ScrollHandDrag)
            
            # desactivar movimiento en nodos
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    try:
                        item.setFlag(item.ItemIsMovable, False)
                        item.setFlag(item.ItemIsFocusable, True)
                    except Exception:
                        pass
            
            # Restaurar colores normales de nodos
            self.restaurar_colores_nodos()
            
            print("Modo por defecto activado: navegación del mapa y selección")
            
            # --- NUEVO: Actualizar descripción del modo ---
            self.actualizar_descripcion_modo()
            
            # --- NUEVO: Resetear estado de arrastre y actualizar cursor ---
            self._arrastrando_nodo = False
            self._cursor_sobre_nodo = False
            print("Reset estados cursor: arrastrando=False, sobre_nodo=False")
            self._actualizar_cursor()
            
            return

        # Desactivar los otros botones
        for b in (self.view.mover_button, self.view.colocar_vertice_button, 
                self.view.crear_ruta_button):
            if b is not boton:
                b.setChecked(False)

        if boton == self.view.mover_button:
            print("Activando modo MOVER...")
            # --- MODO MOVER ---
            self.modo_actual = "mover"
            self.mover_ctrl.activar()
            self.colocar_ctrl.desactivar()
            
            # IMPORTANTE: Desactivar modo ruta
            try:
                self.ruta_ctrl.desactivar()
            except Exception:
                pass
            
            # IMPORTANTE: Desactivar arrastre del mapa (NoDrag)
            self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.NoDrag)

            # Activar movimiento en todos los nodos
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    try:
                        item.setFlag(item.ItemIsMovable, True)
                        item.setFlag(item.ItemIsFocusable, True)
                    except Exception:
                        pass

            print("Modo Mover activado: nodos arrastrables, mapa fijo")
            
            # --- NUEVO: Actualizar descripción del modo ---
            self.actualizar_descripcion_modo("mover")
            
            # --- NUEVO: Resetear estado de arrastre y actualizar cursor ---
            self._arrastrando_nodo = False
            self._cursor_sobre_nodo = False
            print("Reset estados cursor: arrastrando=False, sobre_nodo=False")
            self._actualizar_cursor()

        elif boton == self.view.colocar_vertice_button:
            print("Activando modo COLOCAR...")
            # --- MODO COLOCAR ---
            self.modo_actual = "colocar"
            self.colocar_ctrl.activar()
            self.mover_ctrl.desactivar()
            
            # IMPORTANTE: Desactivar modo ruta
            try:
                self.ruta_ctrl.desactivar()
            except Exception:
                pass
            
            self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.NoDrag)
            
            print("Modo Colocar activado: añadir nuevos nodos")
            
            # --- NUEVO: Actualizar descripción del modo ---
            self.actualizar_descripcion_modo("colocar")
            
            # --- NUEVO: Resetear estado de arrastre y actualizar cursor ---
            self._arrastrando_nodo = False
            self._cursor_sobre_nodo = False
            print("Reset estados cursor: arrastrando=False, sobre_nodo=False")
            self._actualizar_cursor()

        elif boton == self.view.crear_ruta_button:
            print("Activando modo RUTA...")
            # --- MODO RUTA ---
            self.modo_actual = "ruta"
            
            # IMPORTANTE: Verificar que tenemos un proyecto
            if not self.proyecto:
                print("✗ ERROR: No hay proyecto cargado. Crea o abre un proyecto primero.")
                boton.setChecked(False)
                QMessageBox.warning(self.view, "Error", 
                                "No hay proyecto cargado. Crea o abre un proyecto primero.")
                return
                    
            print("Activando modo ruta - El usuario puede crear nodos haciendo clic en el mapa")
            
            # Activar modo ruta
            self.ruta_ctrl.activar()
            self.mover_ctrl.desactivar()
            self.colocar_ctrl.desactivar()
            self.view.marco_trabajo.setDragMode(self.view.marco_trabajo.NoDrag)
            
            print("Modo Ruta activado: crear rutas entre nodos")
            
            # --- NUEVO: Actualizar descripción del modo ---
            self.actualizar_descripcion_modo("ruta")
            
            # --- NUEVO: Resetear estado de arrastre y actualizar cursor ---
            self._arrastrando_nodo = False
            self._cursor_sobre_nodo = False
            print("Reset estados cursor: arrastrando=False, sobre_nodo=False")
            self._actualizar_cursor()

        # Actualizar líneas después de cambiar modo
        self.actualizar_lineas_rutas()
    
    # --- NUEVO MÉTODO: Actualizar descripción del modo ---
    def actualizar_descripcion_modo(self, modo=None):
        """
        Actualiza la descripción del modo actual en la barra inferior.
        Si no se especifica modo, usa self.modo_actual.
        """
        if modo is None:
            modo = self.modo_actual
        
        # Si no hay modo activo, usar navegación por defecto
        if modo is None:
            modo = "navegacion"
        
        # Llamar al método de la vista para actualizar
        if hasattr(self.view, 'actualizar_descripcion_modo'):
            try:
                self.view.actualizar_descripcion_modo(modo)
            except Exception as e:
                print(f"Error al actualizar descripción del modo: {e}")

    # --- MÉTODOS PARA MANEJO DE EVENTOS DE TECLADO ---
    
    def finalizar_ruta_actual(self):
        """Finaliza la creación de la ruta actual cuando se presiona Enter"""
        if self.modo_actual == "ruta":
            try:
                # Finalizar la ruta primero
                self.ruta_ctrl.finalizar_ruta_con_enter()
                print("✓ Ruta finalizada con Enter")
                
                # Desactivar el botón de ruta después de finalizar
                self.view.crear_ruta_button.setChecked(False)
                # Y llamar a cambiar_modo para limpiar todo
                self.cambiar_modo(self.view.crear_ruta_button)
                
                # --- NUEVO: Actualizar descripción al volver a modo navegación ---
                self.actualizar_descripcion_modo("navegacion")
                
            except Exception as e:
                print(f"Error al finalizar ruta con Enter: {e}")
        else:
            print("⚠ No estás en modo Ruta")
    
    def cancelar_ruta_actual(self):
        """Cancela la creación de la ruta actual cuando se presiona Escape"""
        if self.modo_actual == "ruta":
            try:
                # Cancelar la ruta primero
                self.ruta_ctrl.cancelar_ruta_actual()
                print("✓ Ruta cancelada con Escape")
                
                # Desactivar el botón de ruta
                self.view.crear_ruta_button.setChecked(False)
                # Y llamar a cambiar_modo para limpiar todo
                self.cambiar_modo(self.view.crear_ruta_button)
                
                # --- NUEVO: Actualizar descripción al volver a modo navegación ---
                self.actualizar_descripcion_modo("navegacion")
                
            except Exception as e:
                print(f"Error al cancelar ruta: {e}")
        else:
            print("⚠ No estás en modo Ruta")
    
    def eliminar_nodo_seleccionado(self):
        """Elimina el nodo seleccionado cuando se presiona Suprimir, mostrando confirmación"""
        try:
            # Verificar si hay nodos seleccionados en la escena
            seleccionados_escena = self.scene.selectedItems()
            
            # Verificar si hay nodos seleccionados en la lista lateral
            seleccionados_lista = self.view.nodosList.selectedItems()
            
            nodo_a_eliminar = None
            nodo_item_a_eliminar = None
            
            # Prioridad: selección en la escena sobre selección en la lista
            if seleccionados_escena:
                for item in seleccionados_escena:
                    if isinstance(item, NodoItem):
                        nodo_a_eliminar = item.nodo
                        nodo_item_a_eliminar = item
                        break
            
            # Si no hay selección en la escena, buscar en la lista lateral
            elif seleccionados_lista:
                for i in range(self.view.nodosList.count()):
                    item = self.view.nodosList.item(i)
                    if item.isSelected():
                        nodo_a_eliminar = item.data(Qt.UserRole)
                        break
            
            # Si encontramos un nodo para eliminar
            if nodo_a_eliminar:
                nodo_id = nodo_a_eliminar.get('id')
                
                # Mostrar cuadro de confirmación
                reply = QMessageBox.question(
                    self.view,
                    "Confirmar eliminación",
                    f"¿Estás seguro de que quieres eliminar el nodo ID {nodo_id}?\n\n"
                    f"Esta acción eliminará el nodo y reconfigurará las rutas que lo contengan.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    print(f"✓ Eliminando nodo ID {nodo_id}")
                    # Buscar el NodoItem en la escena
                    for item in self.scene.items():
                        if isinstance(item, NodoItem) and item.nodo.get('id') == nodo_id:
                            nodo_item_a_eliminar = item
                            break
                    if nodo_item_a_eliminar:
                        self.eliminar_nodo(nodo_a_eliminar, nodo_item_a_eliminar)
                else:
                    print("✗ Eliminación cancelada por el usuario")
            else:
                print("⚠ No hay nodo seleccionado para eliminar")
                
        except Exception as e:
            print(f"Error al eliminar nodo: {e}")
            QMessageBox.warning(self.view, "Error", 
                               f"No se pudo eliminar el nodo:\n{str(e)}")

    def keyPressEvent(self, event):
        """Maneja eventos de teclado globales"""
        try:
            # Tecla Suprimir (Delete)
            if event.key() == Qt.Key_Delete:
                self.eliminar_nodo_seleccionado()
                event.accept()
            # Ctrl+Z para deshacer
            elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
                self.deshacer_movimiento()
                event.accept()
            # Ctrl+Y para rehacer
            elif event.key() == Qt.Key_Y and event.modifiers() == Qt.ControlModifier:
                self.rehacer_movimiento()
                event.accept()
            # Enter para finalizar ruta
            elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self.finalizar_ruta_actual()
                event.accept()
            # Escape para cancelar ruta
            elif event.key() == Qt.Key_Escape:
                self.cancelar_ruta_actual()
                event.accept()
            else:
                event.ignore()
        except Exception as e:
            print(f"Error en keyPressEvent: {e}")
            event.ignore()

    # --- SISTEMA DE DESHACER/REHACER (UNDO/REDO) ---
    
    def _limpiar_historial(self):
        """Limpia el historial de movimientos"""
        self.historial_movimientos = []
        self.indice_historial = -1
        self.movimiento_actual = None
        print("Historial de movimientos limpiado")
    
    def registrar_movimiento_iniciado(self, nodo_item, x_inicial, y_inicial):
        """Registra el inicio de un movimiento (cuando se empieza a arrastrar un nodo)"""
        try:
            nodo_id = nodo_item.nodo.get('id')
            if nodo_id is None:
                return
                
            self.movimiento_actual = {
                'nodo_item': nodo_item,
                'nodo_id': nodo_id,
                'x_inicial': x_inicial,
                'y_inicial': y_inicial
            }
            
            # NUEVO: Iniciar arrastre para cambiar cursor
            self.nodo_arrastre_iniciado()
        except Exception as e:
            print(f"Error registrando movimiento iniciado: {e}")
    
    def registrar_movimiento_finalizado(self, nodo_item, x_inicial, y_inicial, x_final, y_final):
        """Registra el final de un movimiento y lo agrega al historial"""
        try:
            # Verificar que tenemos un movimiento en progreso
            if not self.movimiento_actual:
                return
                
            # Verificar que es el mismo nodo
            nodo_id = nodo_item.nodo.get('id')
            if nodo_id != self.movimiento_actual['nodo_id']:
                return
            
            # Verificar que realmente hubo movimiento
            if x_inicial == x_final and y_inicial == y_final:
                self.movimiento_actual = None
                return
            
            # Si estamos en medio del historial (por deshacer previo), eliminar movimientos futuros
            if self.indice_historial < len(self.historial_movimientos) - 1:
                self.historial_movimientos = self.historial_movimientos[:self.indice_historial + 1]
            
            # Crear entrada del historial
            movimiento = {
                'nodo_id': nodo_id,
                'x_anterior': x_inicial,
                'y_anterior': y_inicial,
                'x_nueva': x_final,
                'y_nueva': y_final
            }
            
            # Agregar al historial
            self.historial_movimientos.append(movimiento)
            
            # Limitar tamaño del historial a max_historial
            if len(self.historial_movimientos) > self.max_historial:
                # Eliminar el movimiento más antiguo
                self.historial_movimientos.pop(0)
            else:
                # Incrementar índice solo si no estamos eliminando elementos
                self.indice_historial += 1
            
            # Mover puntero a la última posición
            self.indice_historial = len(self.historial_movimientos) - 1
            
            # Mostrar en metros
            x_inicial_m = self.pixeles_a_metros(x_inicial)
            y_inicial_m = self.pixeles_a_metros(y_inicial)
            x_final_m = self.pixeles_a_metros(x_final)
            y_final_m = self.pixeles_a_metros(y_final)
            print(f"Movimiento registrado: Nodo {nodo_id} de ({x_inicial_m:.2f},{y_inicial_m:.2f}) a ({x_final_m:.2f},{y_final_m:.2f}) metros")
            
        except Exception as e:
            print(f"Error registrando movimiento finalizado: {e}")
        finally:
            self.movimiento_actual = None
            # NUEVO: Terminar arrastre para cambiar cursor
            self.nodo_arrastre_terminado()
    
    def deshacer_movimiento(self):
        """Deshace el último movimiento (Ctrl+Z)"""
        if self.indice_historial < 0:
            print("No hay movimientos para deshacer")
            return
            
        try:
            # Obtener el movimiento actual
            movimiento = self.historial_movimientos[self.indice_historial]
            nodo_id = movimiento['nodo_id']
            x_anterior = movimiento['x_anterior']
            y_anterior = movimiento['y_anterior']
            
            # Mostrar en metros
            x_anterior_m = self.pixeles_a_metros(x_anterior)
            y_anterior_m = self.pixeles_a_metros(y_anterior)
            print(f"Deshaciendo movimiento: Nodo {nodo_id} a ({x_anterior_m:.2f},{y_anterior_m:.2f}) metros")
            
            # Buscar el nodo en la escena
            nodo_encontrado = False
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    if item.nodo.get('id') == nodo_id:
                        # Mover el nodo a la posición anterior
                        item.setPos(x_anterior - item.size / 2, y_anterior - item.size / 2)
                        
                        # Actualizar el modelo
                        if isinstance(item.nodo, dict):
                            item.nodo["X"] = x_anterior
                            item.nodo["Y"] = y_anterior
                        else:
                            setattr(item.nodo, "X", x_anterior)
                            setattr(item.nodo, "Y", y_anterior)
                        
                        # Actualizar UI
                        self.actualizar_lista_nodo(item.nodo)
                        self.actualizar_propiedades_valores(item.nodo, claves=("X", "Y"))
                        
                        # Actualizar rutas
                        self._dibujar_rutas()
                        
                        nodo_encontrado = True
                        break
            
            if nodo_encontrado:
                # Decrementar índice del historial
                self.indice_historial -= 1
                print(f"Movimiento deshecho. Índice actual: {self.indice_historial}")
            else:
                print(f"Error: No se encontró el nodo {nodo_id}")
                
        except Exception as e:
            print(f"Error deshaciendo movimiento: {e}")
    
    def rehacer_movimiento(self):
        """Rehace el movimiento deshecho (Ctrl+Y)"""
        if self.indice_historial >= len(self.historial_movimientos) - 1:
            print("No hay movimientos para rehacer")
            return
            
        try:
            # Incrementar índice primero
            self.indice_historial += 1
            
            # Obtener el movimiento a rehacer
            movimiento = self.historial_movimientos[self.indice_historial]
            nodo_id = movimiento['nodo_id']
            x_nueva = movimiento['x_nueva']
            y_nueva = movimiento['y_nueva']
            
            # Mostrar en metros
            x_nueva_m = self.pixeles_a_metros(x_nueva)
            y_nueva_m = self.pixeles_a_metros(y_nueva)
            print(f"Rehaciendo movimiento: Nodo {nodo_id} a ({x_nueva_m:.2f},{y_nueva_m:.2f}) metros")
            
            # Buscar el nodo en la escena
            nodo_encontrado = False
            for item in self.scene.items():
                if isinstance(item, NodoItem):
                    if item.nodo.get('id') == nodo_id:
                        # Mover el nodo a la nueva posición
                        item.setPos(x_nueva - item.size / 2, y_nueva - item.size / 2)
                        
                        # Actualizar el modelo
                        if isinstance(item.nodo, dict):
                            item.nodo["X"] = x_nueva
                            item.nodo["Y"] = y_nueva
                        else:
                            setattr(item.nodo, "X", x_nueva)
                            setattr(item.nodo, "Y", y_nueva)
                        
                        # Actualizar UI
                        self.actualizar_lista_nodo(item.nodo)
                        self.actualizar_propiedades_valores(item.nodo, claves=("X", "Y"))
                        
                        # Actualizar rutas
                        self._dibujar_rutas()
                        
                        nodo_encontrado = True
                        break
            
            if not nodo_encontrado:
                print(f"Error: No se encontró el nodo {nodo_id}")
                # Si no encontramos el nodo, revertir el incremento del índice
                self.indice_historial -= 1
            else:
                print(f"Movimiento rehecho. Índice actual: {self.indice_historial}")
                
        except Exception as e:
            print(f"Error rehaciendo movimiento: {e}")
            # En caso de error, revertir el incremento del índice
            if self.indice_historial > 0:
                self.indice_historial -= 1

    # --- FUNCIONES DE PROYECTO ---
    
    def nuevo_proyecto(self):
        ruta_mapa, _ = QFileDialog.getOpenFileName(
            self.view, "Seleccionar mapa", "", "Imagenes (*.png *.jpg *.jpeg)"
        )
        if not ruta_mapa:
            return
        
        # Crear nuevo proyecto
        self.proyecto = Proyecto(ruta_mapa)
        
        # Actualizar referencias en TODOS los subcontroladores
        self._actualizar_referencias_proyecto(self.proyecto)
        
        # Limpiar UI (esto también limpia el historial)
        self._limpiar_ui_completa()
        
        # Mostrar mapa
        self._mostrar_mapa(ruta_mapa)
        
        # Resetear botones y modo
        self._resetear_modo_actual()
        
        # Inicializar sistema de visibilidad
        self.inicializar_visibilidad()
        
        print("✓ Nuevo proyecto creado con mapa:", ruta_mapa)
        self.diagnosticar_estado_proyecto()

    def abrir_proyecto(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self.view, "Abrir proyecto", "", "JSON Files (*.json)"
        )
        if not ruta_archivo:
            return
        try:
            # Cargar proyecto
            self.proyecto = Proyecto.cargar(ruta_archivo)
            
            # Asegurarse de que todos los nodos tengan campo "objetivo"
            for nodo in self.proyecto.nodos:
                if isinstance(nodo, dict):
                    if "objetivo" not in nodo:
                        nodo["objetivo"] = 0
                elif not hasattr(nodo, "objetivo"):
                    setattr(nodo, "objetivo", 0)
            
            # Usar el mismo método para actualizar referencias
            self._actualizar_referencias_proyecto(self.proyecto)
            
            # Limpiar UI primero (esto también limpia el historial)
            self._limpiar_ui_completa()
            
            if self.proyecto.mapa:
                self._mostrar_mapa(self.proyecto.mapa)

            # Crear NodoItem correctamente
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

                # Inicializar sistema de visibilidad para cada nodo
                self._inicializar_nodo_visibilidad(nodo, agregar_a_lista=True)

            # Inicializar sistema de visibilidad
            self.inicializar_visibilidad()
            
            # Actualizar listas con widgets
            self._actualizar_lista_nodos_con_widgets()
            self._dibujar_rutas()
            self._mostrar_rutas_lateral()

            print("✓ Proyecto cargado desde:", ruta_archivo)
            self.diagnosticar_estado_proyecto()
        except Exception as err:
            print("✗ Error al abrir proyecto:", err)

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
            # El método guardar() de Proyecto ahora guarda rutas simplificadas (solo IDs)
            self.proyecto.guardar(ruta_archivo)
            print("✓ Proyecto guardado en:", ruta_archivo)
        except Exception as err:
            print("✗ Error al guardar proyecto:", err)

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
    def _create_nodo_item(self, nodo, size=30):
        """
        Crea (o recupera) un NodoItem visual para el nodo del modelo,
        lo configura (flags, z-order), conecta la señal moved y lo añade a la escena.
        Devuelve el NodoItem creado.
        """
        # Si ya existe un NodoItem en la escena para este nodo, devolverlo
        for it in self.scene.items():
            if isinstance(it, NodoItem) and getattr(it, "nodo", None) == nodo:
                return it

        # Asegurar que el nodo tenga campo objetivo
        if isinstance(nodo, dict):
            if "objetivo" not in nodo:
                nodo["objetivo"] = 0  # Valor por defecto
        elif hasattr(nodo, "objetivo"):
            pass  # Ya tiene el atributo
        else:
            try:
                setattr(nodo, "objetivo", 0)  # Valor por defecto
            except:
                pass

        # Crear nuevo NodoItem
        nodo_item = NodoItem(nodo, size=size, editor=self)

        # CONEXIÓN DE SEÑALES HOVER - NUEVO
        try:
            nodo_item.hover_entered.connect(self.nodo_hover_entered)
            nodo_item.hover_leaved.connect(self.nodo_hover_leaved)
        except Exception as e:
            print(f"Error conectando señales hover: {e}")

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

        try:
            print(f"DEBUG crear_nodo: Creando nodo en ({x}, {y}) píxeles")
            
            # Primero agregar al modelo
            nodo = self.proyecto.agregar_nodo(x, y)
            print(f"DEBUG crear_nodo: Nodo creado con ID {nodo.get('id')}")

            # Asegurar que el nodo tenga todos los campos necesarios
            if isinstance(nodo, dict):
                if "objetivo" not in nodo:
                    nodo["objetivo"] = 0
                if "es_cargador" not in nodo:
                    nodo["es_cargador"] = 0
            elif hasattr(nodo, "objetivo"):
                pass  # Ya tiene el atributo
            else:
                setattr(nodo, "objetivo", 0)
                setattr(nodo, "es_cargador", 0)

            # Crear NodoItem con referencia al editor usando helper centralizado
            try:
                nodo_item = self._create_nodo_item(nodo)
            except Exception as e:
                print(f"DEBUG crear_nodo: Error al crear NodoItem: {e}")
                nodo_item = NodoItem(nodo, editor=self)
                try:
                    nodo_item.setFlag(nodo_item.ItemIsSelectable, True)
                    nodo_item.setFlag(nodo_item.ItemIsFocusable, True)
                    nodo_item.setFlag(nodo_item.ItemIsMovable, (self.modo_actual == "mover"))
                    nodo_item.setAcceptedMouseButtons(Qt.LeftButton)
                    nodo_item.setZValue(1)
                    self.scene.addItem(nodo_item)
                    nodo_item.moved.connect(self.on_nodo_moved)
                except Exception as e2:
                    print(f"DEBUG crear_nodo: Error al configurar NodoItem: {e2}")

            # --- NUEVA FUNCIÓN PARA INICIALIZAR VISIBILIDAD ---
            print(f"DEBUG crear_nodo: Llamando a _inicializar_nodo_visibilidad para nodo {nodo.get('id')}")
            self._inicializar_nodo_visibilidad(nodo, agregar_a_lista=True)
            
            # Si hay rutas, actualizar todas las relaciones (para consistencia)
            if hasattr(self.proyecto, 'rutas') and self.proyecto.rutas:
                self._actualizar_todas_relaciones_nodo_ruta()

            # Mostrar en metros
            x_m = self.pixeles_a_metros(x)
            y_m = self.pixeles_a_metros(y)
            
            # Mostrar tipo de nodo
            objetivo = nodo.get('objetivo', 0)
            es_cargador = nodo.get('es_cargador', 0)
            if es_cargador != 0:
                tipo = "CARGADOR"
            elif objetivo == 1:
                tipo = "CARGAR"
            elif objetivo == 2:
                tipo = "DESCARGAR"
            elif objetivo == 3:
                tipo = "I/O"
            else:
                tipo = "Normal"
                
            print(f"✓ Nodo ID {nodo.get('id')} ({tipo}) creado con botón de visibilidad en ({x_m:.2f}, {y_m:.2f}) metros")
            print("Nodo creado:", getattr(nodo, "to_dict", lambda: nodo)())
        except Exception as e:
            print(f"ERROR en crear_nodo: {e}")

    # --- NUEVA FUNCIÓN CENTRALIZADA PARA INICIALIZAR VISIBILIDAD ---
    def _inicializar_nodo_visibilidad(self, nodo, agregar_a_lista=True):
        """
        Inicializa completamente el sistema de visibilidad para un nodo.
        Se usa tanto al crear nodos nuevos como al cargarlos desde archivo.
        
        Args:
            nodo: El objeto nodo a inicializar
            agregar_a_lista: Si True, agrega el nodo a la lista lateral con widget
        """
        try:
            print(f"DEBUG _inicializar_nodo_visibilidad: nodo_id={nodo.get('id')}, agregar_a_lista={agregar_a_lista}")
            nodo_id = nodo.get('id')
            if nodo_id is None:
                print("✗ Advertencia: Nodo sin ID en _inicializar_nodo_visibilidad")
                return
            
            # 1. Inicializar visibilidad del nodo si no existe
            if nodo_id not in self.visibilidad_nodos:
                self.visibilidad_nodos[nodo_id] = True
                print(f"  - Visibilidad inicializada para nodo {nodo_id}: True")
            
            # 2. Inicializar relaciones nodo-ruta si no existen
            if nodo_id not in self.nodo_en_rutas:
                self.nodo_en_rutas[nodo_id] = []
            
            # 3. Buscar en rutas existentes si este nodo está en alguna
            for idx, ruta in enumerate(self.proyecto.rutas):
                try:
                    ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
                except Exception:
                    ruta_dict = ruta
                
                self._normalize_route_nodes(ruta_dict)
                
                # Verificar si la ruta contiene este nodo
                contiene_nodo = False
                
                # Origen
                origen = ruta_dict.get("origen")
                if origen and isinstance(origen, dict) and origen.get('id') == nodo_id:
                    contiene_nodo = True
                
                # Destino
                destino = ruta_dict.get("destino")
                if not contiene_nodo and destino and isinstance(destino, dict) and destino.get('id') == nodo_id:
                    contiene_nodo = True
                
                # Visita
                if not contiene_nodo:
                    for nodo_visita in ruta_dict.get("visita", []):
                        if isinstance(nodo_visita, dict) and nodo_visita.get('id') == nodo_id:
                            contiene_nodo = True
                            break
                
                if contiene_nodo:
                    if idx not in self.nodo_en_rutas[nodo_id]:
                        self.nodo_en_rutas[nodo_id].append(idx)
            
            # 4. Agregar a la lista lateral con widget de visibilidad
            if agregar_a_lista:
                x_px = nodo.get('X', 0)
                y_px = nodo.get('Y', 0)
                # Convertir a metros
                x_m = self.pixeles_a_metros(x_px)
                y_m = self.pixeles_a_metros(y_px)
                objetivo = nodo.get('objetivo', 0)
                
                # Determinar texto según objetivo
                if objetivo == 1:
                    texto_objetivo = "IN"
                elif objetivo == 2:
                    texto_objetivo = "OUT"
                elif objetivo == 3:
                    texto_objetivo = "I/O"
                else:
                    texto_objetivo = "Sin objetivo"
                
                # Mostrar coordenadas en metros con 2 decimales
                texto = f"ID {nodo_id} - {texto_objetivo} ({x_m:.2f}, {y_m:.2f})"
                
                # Verificar si el nodo ya está en la lista (búsqueda exhaustiva)
                nodo_en_lista = False
                for i in range(self.view.nodosList.count()):
                    item = self.view.nodosList.item(i)
                    widget = self.view.nodosList.itemWidget(item)
                    if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
                        nodo_en_lista = True
                        # Actualizar el widget existente
                        widget.lbl_texto.setText(texto)
                        widget.set_visible(self.visibilidad_nodos.get(nodo_id, True))
                        print(f"  - Nodo {nodo_id} ya existe en lista, widget actualizado")
                        break
                
                # Si no está en la lista, agregarlo
                if not nodo_en_lista:
                    item = QListWidgetItem()
                    item.setData(Qt.UserRole, nodo)
                    item.setSizeHint(QSize(0, 24))
                    
                    widget = NodoListItemWidget(
                        nodo_id, 
                        texto, 
                        self.visibilidad_nodos.get(nodo_id, True)
                    )
                    widget.toggle_visibilidad.connect(self.toggle_visibilidad_nodo)
                    
                    self.view.nodosList.addItem(item)
                    self.view.nodosList.setItemWidget(item, widget)
                    
                    print(f"  ✓ Nodo {nodo_id} agregado a lista lateral con widget de visibilidad")
            else:
                print(f"  - Nodo {nodo_id} inicializado (sin agregar a lista)")
        except Exception as e:
            print(f"ERROR en _inicializar_nodo_visibilidad: {e}")

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
        
        # Resaltar cada nodo en la escena
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
                        break

    def restaurar_colores_nodos(self):
        """Restaura todos los nodos a su color normal"""
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.set_normal_color()

    # --- Sincronización lista ↔ mapa---
    def seleccionar_nodo_desde_lista(self):
        if self._changing_selection:
            return
        items = self.view.nodosList.selectedItems()
        if not items:
            return
        
        # Obtener el nodo del widget
        for i in range(self.view.nodosList.count()):
            item = self.view.nodosList.item(i)
            if item.isSelected():
                widget = self.view.nodosList.itemWidget(item)
                if widget and hasattr(widget, 'nodo_id'):
                    nodo_id = widget.nodo_id
                    nodo = self.obtener_nodo_por_id(nodo_id)
                    if nodo:
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
                                if isinstance(scene_item, NodoItem) and scene_item.nodo.get('id') == nodo_id:
                                    scene_item.setSelected(True)
                                    # Solo aplicar color de selección (no de ruta)
                                    scene_item.set_selected_color()
                                    self.view.marco_trabajo.centerOn(scene_item)
                                    self.mostrar_propiedades_nodo(nodo)
                                    break
                        finally:
                            self._changing_selection = False
                    break

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
            nodo_id = nodo.get('id')
            for i in range(self.view.nodosList.count()):
                item = self.view.nodosList.item(i)
                widget = self.view.nodosList.itemWidget(item)
                if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
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
            objetivo = nodo.get('objetivo', 0)
            texto_objetivo = "IN" if objetivo == 1 else "OUT" if objetivo == 2 else "I/O" if objetivo == 3 else "Sin objetivo"
            
            # Obtener coordenadas en metros
            x_px = nodo.get('X', 0)
            y_px = nodo.get('Y', 0)
            x_m = self.pixeles_a_metros(x_px)
            y_m = self.pixeles_a_metros(y_px)
            
            action = menu.addAction(f"ID: {nodo.get('id')} - {texto_objetivo} ({x_m:.2f}, {y_m:.2f})")
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
            nodo_id = nodo.get('id')
            for i in range(self.view.nodosList.count()):
                item = self.view.nodosList.item(i)
                widget = self.view.nodosList.itemWidget(item)
                if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
                    self.view.nodosList.setCurrentItem(item)
                    self.mostrar_propiedades_nodo(nodo)
                    break
        finally:
            self._changing_selection = False
            self._actualizar_cursor()

    def actualizar_lista_nodo(self, nodo):
        """Actualizar la lista lateral del panel de propiedades con las coordenadas nuevas (en metros)"""
        nodo_id = nodo.get('id')
        for i in range(self.view.nodosList.count()):
            item = self.view.nodosList.item(i)
            widget = self.view.nodosList.itemWidget(item)
            if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
                x_px = nodo.get('X', 0)
                y_px = nodo.get('Y', 0)
                # Convertir a metros
                x_m = self.pixeles_a_metros(x_px)
                y_m = self.pixeles_a_metros(y_px)
                objetivo = nodo.get('objetivo', 0)
                
                # Determinar texto según objetivo
                if objetivo == 1:
                    texto_objetivo = "IN"
                elif objetivo == 2:
                    texto_objetivo = "OUT"
                elif objetivo == 3:
                    texto_objetivo = "I/O"
                else:
                    texto_objetivo = "Sin objetivo"
                
                # Mostrar en metros con 2 decimales
                widget.lbl_texto.setText(f"ID {nodo_id} - {texto_objetivo} ({x_m:.2f}, {y_m:.2f})")
                break

        # Refrescar el panel de propiedades si el nodo esta seleccionado
        seleccionados = self.view.nodosList.selectedItems()
        if seleccionados:
            for i in range(self.view.nodosList.count()):
                item = self.view.nodosList.item(i)
                if item.isSelected():
                    widget = self.view.nodosList.itemWidget(item)
                    if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
                        self.mostrar_propiedades_nodo(nodo)
                        break

    def _mostrar_rutas_lateral(self):
        """
        Rellena la lista lateral de rutas con widgets personalizados.
        """
        self._actualizar_lista_rutas_con_widgets()

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
                    # Restaurar z-values normales
                    item.setZValue(1)
            return

        # Guardar el índice de la ruta seleccionada
        for i in range(self.view.rutasList.count()):
            item = self.view.rutasList.item(i)
            if item.isSelected():
                widget = self.view.rutasList.itemWidget(item)
                if widget and hasattr(widget, 'ruta_index'):
                    self.ruta_actual_idx = widget.ruta_index
                    ruta = self.obtener_ruta_por_indice(self.ruta_actual_idx)
                    break
        
        if self.ruta_actual_idx is None:
            return

        # IMPORTANTE: Restaurar todos los nodos a color normal y z-value normal primero
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.set_normal_color()
                item.setZValue(1)

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
        Nombre: nombre_ruta
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

        # Mostrar nombre, origen, destino y visita
        propiedades = [
            ("Nombre", ruta_dict.get("nombre", "Ruta")),
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
        """Actualiza la ruta a través del proyecto para notificar cambios"""
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
            if campo == "nombre":
                ruta_dict["nombre"] = texto
            elif campo == "origen":
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

            # Normalizar y actualizar referencia en proyecto.rutas usando el método del proyecto
            self._normalize_route_nodes(ruta_dict)
            self.proyecto.actualizar_ruta(self.ruta_actual_idx, ruta_dict)
            
            # Actualizar el texto en la lista lateral de rutas
            self._actualizar_widget_ruta_en_lista(self.ruta_actual_idx)
            
            print(f"Ruta actualizada exitosamente")
            
        except Exception as err:
            print("Error en _actualizar_propiedad_ruta:", err)

    # --- Dibujar rutas guardadas en rojo --
    def _dibujar_rutas(self):
        """Dibuja todas las rutas usando la reconstrucción de rutas"""
        try:
            self._clear_route_lines()
        except Exception as e:
            print(f"Error en clear: {e}")

        if not getattr(self, "proyecto", None) or not hasattr(self.proyecto, "rutas"):
            print("DEBUG: No hay proyecto o rutas para dibujar")
            return

        # REPARAR REFERENCIAS ANTES DE DIBUJAR
        self._reparar_referencias_rutas()

        # Reconstruir rutas para dibujo (excluyendo nodos ocultos)
        self.rutas_para_dibujo = self._reconstruir_rutas_para_dibujo()
        
        pen = QPen(Qt.red, 2)
        pen.setCosmetic(True)
        self._route_lines = []

        for ruta_idx, ruta_reconstruida in enumerate(self.rutas_para_dibujo):
            if not ruta_reconstruida or len(ruta_reconstruida) < 2:
                # Ruta vacía o con insuficientes nodos
                self._route_lines.append([])
                continue

            route_line_items = []
            
            # Dibujar segmentos entre nodos consecutivos en la ruta reconstruida
            for i in range(len(ruta_reconstruida) - 1):
                n1, n2 = ruta_reconstruida[i], ruta_reconstruida[i + 1]
                
                try:
                    # Obtener coordenadas
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
        print(f"✓ {len([r for r in self.rutas_para_dibujo if r])} rutas dibujadas (reconstruidas)")

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
                
                # Convertir X e Y a metros para mostrar
                if clave in ["X", "Y"] and isinstance(valor, (int, float)):
                    valor = self.pixeles_a_metros(valor)

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
                        # Convertir a metros para mostrar
                        if cell_clave in ["X", "Y"]:
                            val = self.pixeles_a_metros(val)
                        cell.setText(str(val))
                except Exception:
                    pass
        except Exception as err:
            print("Error en actualizar_propiedades_valores:", err)

    def _actualizar_propiedad_nodo(self, item):
        """Actualiza la propiedad de un nodo a través del proyecto para notificar cambios"""
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
            # Si la clave es X o Y, convertir de metros a píxeles
            if clave in ["X", "Y"]:
                try:
                    valor_metros = float(valor)
                    valor = self.metros_a_pixeles(valor_metros)
                except ValueError:
                    print(f"Error: Valor de {clave} debe ser un número")
                    return

            # Usar el método del proyecto para actualizar (esto emitirá la señal)
            self.proyecto.actualizar_nodo({clave: valor, "id": nodo.get('id')})
            
            # Si la clave es 'objetivo' o 'es_cargador', actualizar visualización del nodo
            if clave in ["objetivo", "es_cargador"]:
                for item in self.scene.items():
                    if isinstance(item, NodoItem):
                        if item.nodo.get('id') == nodo.get('id'):
                            item.actualizar_objetivo()
                            break
                
        except Exception as err:
            print("Error actualizando nodo en el modelo:", err)
            return
        

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

            # 3) Eliminar de visibilidad y relaciones
            if nodo_id in self.visibilidad_nodos:
                del self.visibilidad_nodos[nodo_id]
            if nodo_id in self.nodo_en_rutas:
                del self.nodo_en_rutas[nodo_id]

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
                    for i in range(self.view.nodosList.count()):
                        item = self.view.nodosList.item(i)
                        widget = self.view.nodosList.itemWidget(item)
                        if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
                            self.view.propertiesTable.clear()
                            self.view.propertiesTable.setRowCount(0)
                            self.view.propertiesTable.setColumnCount(2)
                            self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])
                            break
            except Exception:
                pass

            # 6) Actualizar lista de nodos
            self._actualizar_lista_nodos_con_widgets()

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
        
        # Actualizar visibilidad de rutas y relaciones
        self.visibilidad_rutas.clear()
        self.nodo_en_rutas.clear()
        for idx in range(len(nuevas_rutas)):
            self.visibilidad_rutas[idx] = True
            # Reconstruir relaciones
            self._actualizar_relaciones_nodo_ruta(idx, nuevas_rutas[idx])
        
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
                    
                    # Buscar el nodo ACTUAL en el proyecto
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

        # Crear mapa de nodos por ID para búsqueda rápida 
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
                
                # Reparar ORIGEN 
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
                
                # Reparar DESTINO 
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
                
                # Reparar VISITA
                visita = ruta_dict.get("visita", [])
                nueva_visita = []
                for v in visita:
                    if isinstance(v, dict) and 'id' in v:
                        visita_id = v['id']
                        if visita_id in mapa_nodos:
                            # Actualizar coordenadas en lugar de reemplazar el objeto
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
        """Versión CORREGIDA para actualización en tiempo real durante arrastre"""
        try:
            # Verificar que estamos en modo mover
            if self.modo_actual != "mover":
                return
                
            print(f"DEBUG on_nodo_moved: Llamado para nodo_item tipo {type(nodo_item)}")
            
            nodo = getattr(nodo_item, "nodo", None)
            if not nodo:
                print("ERROR: nodo_item no tiene atributo 'nodo'")
                return

            # Obtener posición ACTUAL del nodo DURANTE el arrastre
            scene_pos = nodo_item.scenePos()
            x = int(scene_pos.x() + nodo_item.size / 2)
            y = int(scene_pos.y() + nodo_item.size / 2)

            # Obtener ID del nodo movido - FORMA MEJORADA
            nodo_id = None
            
            # Método 1: Intentar obtener directamente del nodo
            if isinstance(nodo, dict):
                nodo_id = nodo.get("id")
                print(f"DEBUG on_nodo_moved: nodo es dict, id={nodo_id}")
            elif hasattr(nodo, "get"):
                nodo_id = nodo.get("id")
                print(f"DEBUG on_nodo_moved: nodo tiene get(), id={nodo_id}")
            elif hasattr(nodo, "id"):
                nodo_id = getattr(nodo, "id")
                print(f"DEBUG on_nodo_moved: nodo tiene atributo id, id={nodo_id}")
            
            # Método 2: Si aún no tenemos ID, intentar del nodo_item
            if nodo_id is None and hasattr(nodo_item, "nodo_id"):
                nodo_id = getattr(nodo_item, "nodo_id", None)
                print(f"DEBUG on_nodo_moved: Obteniendo de nodo_item.nodo_id={nodo_id}")
            
            # Método 3: Último recurso - buscar en el proyecto
            if nodo_id is None and self.proyecto:
                for n in self.proyecto.nodos:
                    # Comparar por referencia o por posición
                    if n is nodo or (isinstance(n, dict) and n.get('X') == x and n.get('Y') == y):
                        nodo_id = n.get('id') if isinstance(n, dict) else getattr(n, 'id', None)
                        print(f"DEBUG on_nodo_moved: Encontrado por referencia, id={nodo_id}")
                        break

            if nodo_id is None:
                print(f"ERROR: No se pudo obtener ID del nodo. Tipo nodo: {type(nodo)}")
                # Intentar una última opción: si el nodo tiene __dict__
                if hasattr(nodo, "__dict__"):
                    print(f"DEBUG: __dict__ del nodo: {nodo.__dict__}")
                    if 'id' in nodo.__dict__:
                        nodo_id = nodo.__dict__['id']
                        print(f"DEBUG: Encontrado id en __dict__: {nodo_id}")
                
                if nodo_id is None:
                    return

            print(f"DEBUG: Nodo {nodo_id} moviéndose a ({x}, {y})")
            
            # ACTUALIZACIÓN EN TIEMPO REAL de todas las rutas que contienen este nodo
            self._actualizar_rutas_con_nodo_en_tiempo_real(nodo_id, x, y)
            
        except Exception as err:
            print(f"ERROR en on_nodo_moved: {err}")
            import traceback
            traceback.print_exc()

    def _actualizar_rutas_con_nodo_en_tiempo_real(self, nodo_id, x, y):
        """Actualiza TODAS las rutas que contienen el nodo movido, usando las coordenadas en tiempo real"""
        if not getattr(self, "proyecto", None) or not hasattr(self.proyecto, "rutas"):
            print("DEBUG: No hay proyecto o rutas")
            return
        
        print(f"DEBUG: Actualizando rutas para nodo {nodo_id} en ({x}, {y})")
        
        # Buscar todas las rutas que contienen este nodo
        rutas_a_actualizar = []
        for idx, ruta in enumerate(self.proyecto.rutas):
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
                
                # Verificar si la ruta contiene el nodo movido
                contiene_nodo = False
                
                # Función auxiliar para comparar IDs
                def comparar_ids(nodo_ruta, target_id):
                    if nodo_ruta is None:
                        return False
                    if isinstance(nodo_ruta, dict):
                        return nodo_ruta.get("id") == target_id
                    elif hasattr(nodo_ruta, "get"):
                        return nodo_ruta.get("id") == target_id
                    elif hasattr(nodo_ruta, "id"):
                        return getattr(nodo_ruta, "id") == target_id
                    return False
                
                # Verificar origen
                if ruta_dict.get("origen") and comparar_ids(ruta_dict["origen"], nodo_id):
                    contiene_nodo = True
                    print(f"DEBUG: Ruta {idx} contiene nodo {nodo_id} como ORIGEN")
                
                # Verificar destino
                if not contiene_nodo and ruta_dict.get("destino") and comparar_ids(ruta_dict["destino"], nodo_id):
                    contiene_nodo = True
                    print(f"DEBUG: Ruta {idx} contiene nodo {nodo_id} como DESTINO")
                
                # Verificar visita
                if not contiene_nodo:
                    for nodo_visita in ruta_dict.get("visita", []):
                        if comparar_ids(nodo_visita, nodo_id):
                            contiene_nodo = True
                            print(f"DEBUG: Ruta {idx} contiene nodo {nodo_id} en VISITA")
                            break
                
                if contiene_nodo:
                    rutas_a_actualizar.append((idx, ruta_dict))
            except Exception as e:
                print(f"Error verificando ruta {idx}: {e}")
                continue
        
        # Si no hay rutas que actualizar, salir
        if not rutas_a_actualizar:
            print(f"DEBUG: No se encontraron rutas que contengan el nodo {nodo_id}")
            # Mostrar todas las rutas para debug
            print("DEBUG: Rutas disponibles:")
            for idx, ruta in enumerate(self.proyecto.rutas):
                try:
                    ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
                    print(f"  Ruta {idx}: {ruta_dict}")
                except:
                    print(f"  Ruta {idx}: ERROR al convertir")
            return
        
        print(f"DEBUG: Encontradas {len(rutas_a_actualizar)} rutas para actualizar")
        
        # Actualizar las líneas de TODAS las rutas afectadas
        self._actualizar_lineas_rutas_en_tiempo_real(rutas_a_actualizar, nodo_id, x, y)


    def _obtener_id_de_nodo(self, nodo):
        """Obtiene el ID de un nodo de manera segura"""
        if not nodo:
            return None
        if isinstance(nodo, dict):
            return nodo.get("id")
        elif hasattr(nodo, "get"):
            return nodo.get("id")
        elif hasattr(nodo, "id"):
            return getattr(nodo, "id")
        return None

    def _actualizar_lineas_rutas_en_tiempo_real(self, rutas_info, nodo_id, x, y):
        """Actualiza las líneas de las rutas en tiempo real durante el arrastre"""
        # IMPORTANTE: No limpiamos todas las líneas, solo las de las rutas afectadas
        
        pen = QPen(Qt.red, 2)
        pen.setCosmetic(True)
        
        # Primero, eliminar las líneas de las rutas que vamos a actualizar
        for idx, ruta_dict in rutas_info:
            if idx < len(self._route_lines):
                for line_item in self._route_lines[idx]:
                    try:
                        if line_item and line_item.scene() is not None:
                            self.scene.removeItem(line_item)
                    except Exception:
                        pass
                self._route_lines[idx] = []
        
        # Ahora, volver a dibujar CADA ruta con las coordenadas actualizadas
        for idx, ruta_dict in rutas_info:
            # Crear una copia del diccionario de la ruta para modificarla
            ruta_actualizada = dict(ruta_dict)
            
            # Actualizar las coordenadas del nodo movido en la ruta
            self._actualizar_coordenadas_en_ruta(ruta_actualizada, nodo_id, x, y)
            
            # Obtener todos los puntos de la ruta
            puntos = self._obtener_puntos_de_ruta(ruta_actualizada)
            
            if len(puntos) < 2:
                continue
            
            # Verificar visibilidad
            if not self._ruta_es_visible(ruta_actualizada):
                continue
            
            # Dibujar los segmentos de la ruta
            route_line_items = []
            for i in range(len(puntos) - 1):
                n1, n2 = puntos[i], puntos[i + 1]
                
                try:
                    x1 = self._obtener_coordenada_x(n1)
                    y1 = self._obtener_coordenada_y(n1)
                    x2 = self._obtener_coordenada_x(n2)
                    y2 = self._obtener_coordenada_y(n2)
                    
                    # Solo dibujar si las coordenadas son válidas
                    if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
                        line_item = self.scene.addLine(x1, y1, x2, y2, pen)
                        line_item.setZValue(0.5)
                        line_item.setData(0, ("route_line", idx, i))
                        line_item.setVisible(True)
                        
                        route_line_items.append(line_item)
                        
                except Exception as e:
                    print(f"Error dibujando segmento {i}: {e}")
                    continue
            
            # Asegurarse de que tenemos espacio en el array
            while len(self._route_lines) <= idx:
                self._route_lines.append([])
            
            self._route_lines[idx] = route_line_items
        
        # Forzar actualización de la vista INMEDIATAMENTE
        self.view.marco_trabajo.viewport().update()
        print(f"DEBUG: {len(rutas_info)} rutas actualizadas en tiempo real")

    def _actualizar_coordenadas_en_ruta(self, ruta_dict, nodo_id, x, y):
        """Actualiza las coordenadas de un nodo específico en una ruta"""
        # Actualizar origen
        if ruta_dict.get("origen") and self._obtener_id_de_nodo(ruta_dict["origen"]) == nodo_id:
            if isinstance(ruta_dict["origen"], dict):
                ruta_dict["origen"]["X"] = x
                ruta_dict["origen"]["Y"] = y
            elif hasattr(ruta_dict["origen"], "update"):
                ruta_dict["origen"].update({"X": x, "Y": y})
        
        # Actualizar destino
        elif ruta_dict.get("destino") and self._obtener_id_de_nodo(ruta_dict["destino"]) == nodo_id:
            if isinstance(ruta_dict["destino"], dict):
                ruta_dict["destino"]["X"] = x
                ruta_dict["destino"]["Y"] = y
            elif hasattr(ruta_dict["destino"], "update"):
                ruta_dict["destino"].update({"X": x, "Y": y})
        
        # Actualizar visita
        else:
            for nodo_visita in ruta_dict.get("visita", []):
                if self._obtener_id_de_nodo(nodo_visita) == nodo_id:
                    if isinstance(nodo_visita, dict):
                        nodo_visita["X"] = x
                        nodo_visita["Y"] = y
                    elif hasattr(nodo_visita, "update"):
                        nodo_visita.update({"X": x, "Y": y})
                    break

    def _obtener_puntos_de_ruta(self, ruta_dict):
        """Obtiene todos los puntos de una ruta en orden"""
        puntos = []
        
        if ruta_dict.get("origen"):
            puntos.append(ruta_dict["origen"])
        
        if ruta_dict.get("visita"):
            puntos.extend(ruta_dict["visita"])
        
        if ruta_dict.get("destino"):
            puntos.append(ruta_dict["destino"])
        
        return puntos

    def _ruta_es_visible(self, ruta_dict):
        """Verifica si todos los nodos de una ruta están visibles"""
        puntos = self._obtener_puntos_de_ruta(ruta_dict)
        
        for punto in puntos:
            nodo_id = self._obtener_id_de_nodo(punto)
            if nodo_id is not None and not self.visibilidad_nodos.get(nodo_id, True):
                return False
        
        return True

    def _obtener_coordenada_x(self, nodo):
        """Obtiene la coordenada X de un nodo de manera segura"""
        if isinstance(nodo, dict):
            return nodo.get("X", 0)
        elif hasattr(nodo, "get"):
            return nodo.get("X", 0)
        elif hasattr(nodo, "X"):
            return getattr(nodo, "X", 0)
        return 0

    def _obtener_coordenada_y(self, nodo):
        """Obtiene la coordenada Y de un nodo de manera segura"""
        if isinstance(nodo, dict):
            return nodo.get("Y", 0)
        elif hasattr(nodo, "get"):
            return nodo.get("Y", 0)
        elif hasattr(nodo, "Y"):
            return getattr(nodo, "Y", 0)
        return 0

    def _actualizar_rutas_con_nodo(self, nodo_id, nueva_x, nueva_y):
        """Actualiza solo las rutas que contienen el nodo movido (más eficiente)"""
        if not getattr(self, "proyecto", None) or not hasattr(self.proyecto, "rutas"):
            return
        
        # Buscar rutas que contienen este nodo
        rutas_a_actualizar = []
        for idx, ruta in enumerate(self.proyecto.rutas):
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
                self._normalize_route_nodes(ruta_dict)
                
                # Verificar si la ruta contiene el nodo movido
                contiene_nodo = False
                if ruta_dict.get("origen") and ruta_dict["origen"].get("id") == nodo_id:
                    contiene_nodo = True
                elif ruta_dict.get("destino") and ruta_dict["destino"].get("id") == nodo_id:
                    contiene_nodo = True
                else:
                    for nodo_visita in ruta_dict.get("visita", []):
                        if nodo_visita.get("id") == nodo_id:
                            contiene_nodo = True
                            break
                
                if contiene_nodo:
                    rutas_a_actualizar.append(idx)
            except Exception:
                continue
        
        # Actualizar solo las líneas de las rutas afectadas
        self._actualizar_lineas_rutas_especificas(rutas_a_actualizar, nodo_id, nueva_x, nueva_y)

    def _actualizar_lineas_rutas_especificas(self, indices_rutas, nodo_id=None, nueva_x=None, nueva_y=None):
        """Actualiza solo las líneas de las rutas especificadas por sus índices"""
        if not indices_rutas:
            return
        
        # Eliminar líneas de estas rutas específicas
        for idx in indices_rutas:
            if idx < len(self._route_lines):
                for line_item in self._route_lines[idx]:
                    try:
                        if line_item and line_item.scene() is not None:
                            self.scene.removeItem(line_item)
                    except Exception:
                        pass
                self._route_lines[idx] = []
        
        # Volver a dibujar estas rutas
        pen = QPen(Qt.red, 2)
        pen.setCosmetic(True)
        
        for idx in indices_rutas:
            if idx >= len(self.proyecto.rutas):
                continue
                
            ruta = self.proyecto.rutas[idx]
            
            # Verificar si la ruta está visible
            if not self.visibilidad_rutas.get(idx, True):
                continue
                
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
            except Exception:
                ruta_dict = ruta

            self._normalize_route_nodes(ruta_dict)
            
            # Si estamos actualizando un nodo específico, actualizar sus coordenadas en la ruta
            if nodo_id and nueva_x is not None and nueva_y is not None:
                if ruta_dict.get("origen") and ruta_dict["origen"].get("id") == nodo_id:
                    ruta_dict["origen"]["X"] = nueva_x
                    ruta_dict["origen"]["Y"] = nueva_y
                elif ruta_dict.get("destino") and ruta_dict["destino"].get("id") == nodo_id:
                    ruta_dict["destino"]["X"] = nueva_x
                    ruta_dict["destino"]["Y"] = nueva_y
                else:
                    for nodo_visita in ruta_dict.get("visita", []):
                        if nodo_visita.get("id") == nodo_id:
                            nodo_visita["X"] = nueva_x
                            nodo_visita["Y"] = nueva_y
                            break
            
            # Obtener puntos
            puntos = []
            if ruta_dict.get("origen"):
                puntos.append(ruta_dict["origen"])
            puntos.extend(ruta_dict.get("visita", []) or [])
            if ruta_dict.get("destino"):
                puntos.append(ruta_dict["destino"])

            if len(puntos) < 2:
                continue

            # Verificar que todos los nodos de la ruta estén visibles
            todos_visibles = True
            for punto in puntos:
                if isinstance(punto, dict):
                    nodo_id_punto = punto.get('id')
                    if nodo_id_punto is not None and not self.visibilidad_nodos.get(nodo_id_punto, True):
                        todos_visibles = False
                        break
            
            if not todos_visibles:
                continue

            route_line_items = []
            for i in range(len(puntos) - 1):
                n1, n2 = puntos[i], puntos[i + 1]
                
                try:
                    x1 = n1.get("X", 0) if isinstance(n1, dict) else getattr(n1, "X", 0)
                    y1 = n1.get("Y", 0) if isinstance(n1, dict) else getattr(n1, "Y", 0)
                    x2 = n2.get("X", 0) if isinstance(n2, dict) else getattr(n2, "X", 0)
                    y2 = n2.get("Y", 0) if isinstance(n2, dict) else getattr(n2, "Y", 0)
                    
                    line_item = self.scene.addLine(x1, y1, x2, y2, pen)
                    line_item.setZValue(0.5)
                    line_item.setData(0, ("route_line", idx, i))
                    line_item.setVisible(True)
                    
                    route_line_items.append(line_item)
                    
                except Exception:
                    continue
            
            if idx >= len(self._route_lines):
                self._route_lines.extend([[]] * (idx - len(self._route_lines) + 1))
            
            self._route_lines[idx] = route_line_items

        # Forzar actualización de la vista
        self.view.marco_trabajo.viewport().update()

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

    def actualizar_lineas_rutas(self):
        """Fuerza la actualización de todas las líneas de ruta"""
        self._dibujar_rutas()
        if hasattr(self.view, "rutasList") and self.view.rutasList.selectedItems():
            self.seleccionar_ruta_desde_lista()

    # --- Event filter para deselección al clicar en fondo ---
    def eventFilter(self, obj, event):
        # Detectar teclas presionadas
        if event.type() == QEvent.KeyPress:
            self.keyPressEvent(event)
            return True
        
        # Detectar movimiento del ratón para actualizar cursor dinámicamente
        if event.type() == QEvent.MouseMove:
            # Obtener posición actual del ratón
            pos = self.view.marco_trabajo.mapToScene(event.pos())
            items = self.scene.items(pos)
            
            # Verificar si hay nodos en la posición actual
            hay_nodo = any(isinstance(it, NodoItem) for it in items)
            
            # Actualizar estado de hover
            if hay_nodo and not self._cursor_sobre_nodo:
                # El ratón acaba de entrar en un nodo
                self._cursor_sobre_nodo = True
                print(f"MouseMove: Entrando en nodo, sobre_nodo=True")
                self._actualizar_cursor()
            elif not hay_nodo and self._cursor_sobre_nodo:
                # El ratón acaba de salir de un nodo
                self._cursor_sobre_nodo = False
                print(f"MouseMove: Saliendo de nodo, sobre_nodo=False")
                self._actualizar_cursor()
        
        # Detectar click izquierdo en el viewport
        if event.type() == QEvent.MouseButtonPress:
            # Mapear a escena
            pos = self.view.marco_trabajo.mapToScene(event.pos())
            
            # PRIMERO: Si estamos en modo ruta o modo colocar, NO manejar el clic aquí
            if self.modo_actual in ["ruta", "colocar"]:
                return False
            
            # Verificar si hay nodos en la posición del clic
            items = self.scene.items(pos)
            hay_nodo = any(isinstance(it, NodoItem) for it in items)
            
            if not hay_nodo:
                # Click fuera de nodo
                print("CLICK FUERA DE NODO - Forzar estado normal")
                
                # Resetear estados de cursor
                if self._arrastrando_nodo:
                    print("Forzando fin de arrastre")
                    self._arrastrando_nodo = False
                
                self._cursor_sobre_nodo = False
                self._actualizar_cursor()
                
                # Resto del código existente...
                try:
                    for it in self.scene.selectedItems():
                        it.setSelected(False)
                except Exception:
                    pass
                
                for item in self.scene.items():
                    if isinstance(item, NodoItem):
                        item.setZValue(1)
                    
                try:
                    self.view.nodosList.clearSelection()
                except Exception:
                    pass
                
                try:
                    if hasattr(self.view, "rutasList"):
                        self.view.rutasList.clearSelection()
                except Exception:
                    pass
                
                self._clear_highlight_lines()
                
                try:
                    self.view.propertiesTable.clear()
                    self.view.propertiesTable.setRowCount(0)
                    self.view.propertiesTable.setColumnCount(2)
                    self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])
                except Exception:
                    pass
                
                for item in self.scene.items():
                    if isinstance(item, NodoItem):
                        item.set_normal_color()
        
        # NUEVO: Detectar liberación del botón del ratón
        if event.type() == QEvent.MouseButtonRelease:
            print("MouseButtonRelease detectado - Forzar actualización de cursor")
            # Resetear estado de arrastre si aún está activo
            if self._arrastrando_nodo:
                self._arrastrando_nodo = False
                print("Resetear arrastre desde eventFilter")
            
            # Forzar actualización del cursor
            self._actualizar_cursor()
        
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
                # Usar nodo.get() para objetos Nodo
                if hasattr(nodo, 'get'):
                    nodo_id = nodo.get('id', "N/A")
                    x_px = nodo.get('X', "N/A")
                    y_px = nodo.get('Y', "N/A")
                    objetivo = nodo.get('objetivo', "N/A")
                else:
                    nodo_id = nodo.get('id', "N/A") if isinstance(nodo, dict) else "N/A"
                    x_px = nodo.get('X', "N/A") if isinstance(nodo, dict) else "N/A"
                    y_px = nodo.get('Y', "N/A") if isinstance(nodo, dict) else "N/A"
                    objetivo = nodo.get('objetivo', "N/A") if isinstance(nodo, dict) else "N/A"
                
                # Convertir a metros para mostrar
                if isinstance(x_px, (int, float)) and isinstance(y_px, (int, float)):
                    x_m = self.pixeles_a_metros(x_px)
                    y_m = self.pixeles_a_metros(y_px)
                    coords_text = f"({x_m:.2f}, {y_m:.2f}) metros"
                else:
                    coords_text = f"({x_px}, {y_px}) píxeles"
                
                texto_objetivo = "IN" if objetivo == 1 else "OUT" if objetivo == 2 else "I/O" if objetivo == 3 else "Sin objetivo"
                print(f"  Nodo {i}: ID {nodo_id} - {texto_objetivo} {coords_text}")
            except Exception as e:
                print(f"  Nodo {i}: ERROR - {e}")
        
        print(f"Rutas en proyecto: {len(getattr(self.proyecto, 'rutas', []))}")
        for i, ruta in enumerate(getattr(self.proyecto, "rutas", [])):
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
                origen = ruta_dict.get("origen", {})
                destino = ruta_dict.get("destino", {})
                
                # Usar .get() para diccionarios
                origen_id = origen.get("id", "N/A") if isinstance(origen, dict) else "N/A"
                destino_id = destino.get("id", "N/A") if isinstance(destino, dict) else "N/A"
                print(f"  Ruta {i}: Origen {origen_id} -> Destino {destino_id}")
            except Exception as e:
                print(f"  Ruta {i}: ERROR - {e}")
        
        print("="*50)

    # --- SISTEMA DE VISIBILIDAD CON LÓGICA DE RUTAS INCLUYENDO NODOS ---
    def inicializar_visibilidad(self):
        """Inicializa el sistema de visibilidad para todos los elementos"""
        if not self.proyecto:
            return
        
        print("Inicializando sistema de visibilidad...")
        
        # Inicializar visibilidad de nodos como VISIBLES (True)
        for nodo in self.proyecto.nodos:
            nodo_id = nodo.get('id')
            if nodo_id is not None:
                self.visibilidad_nodos[nodo_id] = True  # Inicialmente visibles
                print(f"  - Nodo {nodo_id}: visibilidad = True")
        
        # Inicializar visibilidad de rutas como VISIBLES (True)
        for idx in range(len(self.proyecto.rutas)):
            self.visibilidad_rutas[idx] = True  # Inicialmente visibles
            print(f"  - Ruta {idx}: visibilidad = True")
            
        # Inicializar relaciones nodo-ruta
        self._actualizar_todas_relaciones_nodo_ruta()
        
        # Actualizar listas con widgets
        self._actualizar_lista_nodos_con_widgets()
        self._actualizar_lista_rutas_con_widgets()
        
        # Asegurar que los botones muestren el estado inicial correcto
        if hasattr(self.view, "btnOcultarTodo"):
            self.view.btnOcultarTodo.setText("Ocultar Nodos")
        if hasattr(self.view, "btnMostrarTodo"):
            self.view.btnMostrarTodo.setText("Ocultar Rutas")
            self.view.btnMostrarTodo.setEnabled(True)  # Habilitado porque nodos visibles
        
        print("✓ Sistema de visibilidad inicializado")

    # --- NUEVOS MÉTODOS PARA INTERRUPTORES DE VISIBILIDAD ---
    def toggle_visibilidad_nodos(self):
        """Alterna la visibilidad de TODOS los nodos (y por tanto de TODAS las rutas)"""
        if not self.proyecto:
            return
        
        # Verificar si actualmente los nodos están visibles
        nodos_visibles = any(self.visibilidad_nodos.values()) if self.visibilidad_nodos else False
        
        if nodos_visibles:
            # Si están visibles, ocultar TODOS los nodos y TODAS las rutas
            self.ocultar_todos_los_nodos()
            self.view.btnOcultarTodo.setText("Mostrar Nodos")
            # Deshabilitar botón de rutas porque no hay nodos visibles
            if hasattr(self.view, "btnMostrarTodo"):
                self.view.btnMostrarTodo.setEnabled(False)
                self.view.btnMostrarTodo.setText("Ocultar Rutas")  # Resetear texto
        else:
            # Si están ocultos, mostrar TODOS los nodos y TODAS las rutas
            self.mostrar_todos_los_nodos_y_rutas()
            self.view.btnOcultarTodo.setText("Ocultar Nodos")
            # Habilitar botón de rutas porque ahora hay nodos visibles
            if hasattr(self.view, "btnMostrarTodo"):
                self.view.btnMostrarTodo.setEnabled(True)
                self.view.btnMostrarTodo.setText("Ocultar Rutas")  # Resetear a estado inicial

    def toggle_visibilidad_rutas(self):
        """Alterna la visibilidad de TODAS las rutas (solo funciona si los nodos están visibles)"""
        if not self.proyecto:
            return
        
        # Verificar que los nodos estén visibles
        nodos_visibles = any(self.visibilidad_nodos.values()) if self.visibilidad_nodos else False
        if not nodos_visibles:
            print("⚠ No se pueden mostrar/ocultar rutas porque los nodos están ocultos")
            return
        
        # Verificar si actualmente las rutas están visibles
        rutas_visibles = any(self.visibilidad_rutas.values()) if self.visibilidad_rutas else False
        
        if rutas_visibles:
            # Si están visibles, ocultar solo las líneas de ruta
            self.ocultar_todas_las_rutas()
            self.view.btnMostrarTodo.setText("Mostrar Rutas")
        else:
            # Si están ocultas, mostrar las líneas de ruta
            self.mostrar_todas_las_rutas()
            self.view.btnMostrarTodo.setText("Ocultar Rutas")

    def ocultar_todos_los_nodos(self):
        """Oculta TODOS los nodos y TODAS las rutas"""
        print("Ocultando todos los nodos y rutas...")
        
        # Ocultar todos los nodos en la escena
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.setVisible(False)
                nodo_id = item.nodo.get('id')
                if nodo_id is not None:
                    self.visibilidad_nodos[nodo_id] = False
        
        # Ocultar todas las rutas (porque dependen de nodos)
        for idx in range(len(self.proyecto.rutas)):
            self.visibilidad_rutas[idx] = False
        
        # Limpiar líneas de rutas
        self._clear_route_lines()
        self._clear_highlight_lines()
        
        # Actualizar widgets en las listas
        self._actualizar_lista_nodos_con_widgets()
        self._actualizar_lista_rutas_con_widgets()
        
        # Deseleccionar cualquier ruta seleccionada
        if hasattr(self.view, "rutasList"):
            self.view.rutasList.clearSelection()
        
        # Resetear el índice de ruta seleccionada
        self.ruta_actual_idx = None
        
        # Limpiar tabla de propiedades
        self.view.propertiesTable.clear()
        self.view.propertiesTable.setRowCount(0)
        self.view.propertiesTable.setColumnCount(2)
        self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])
        
        # Restaurar colores normales de TODOS los nodos
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.set_normal_color()
        
        print("✓ Todos los nodos y rutas ocultados")

    def mostrar_todos_los_nodos_y_rutas(self):
        """Muestra TODOS los nodos y TODAS las rutas (fuerza mostrar rutas)"""
        print("Mostrando todos los nodos y rutas...")
        
        # Mostrar todos los nodos en la escena
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.setVisible(True)
                nodo_id = item.nodo.get('id')
                if nodo_id is not None:
                    self.visibilidad_nodos[nodo_id] = True
        
        # Mostrar TODAS las rutas (forzar estado visible)
        for idx in range(len(self.proyecto.rutas)):
            self.visibilidad_rutas[idx] = True
        
        # Actualizar widgets en las listas
        self._actualizar_lista_nodos_con_widgets()
        self._actualizar_lista_rutas_con_widgets()
        
        # Redibujar rutas
        self._dibujar_rutas()
        
        print("✓ Todos los nodos y rutas mostrados")

    def ocultar_todas_las_rutas(self):
        """Oculta solo las líneas de las rutas, manteniendo los nodos visibles"""
        print("Ocultando todas las rutas (líneas)...")
        
        # Ocultar todas las rutas
        for idx in range(len(self.proyecto.rutas)):
            self.visibilidad_rutas[idx] = False
        
        # Limpiar líneas de rutas
        self._clear_route_lines()
        self._clear_highlight_lines()
        
        # Actualizar widgets en la lista de rutas
        self._actualizar_lista_rutas_con_widgets()
        
        # Deseleccionar cualquier ruta seleccionada
        if hasattr(self.view, "rutasList"):
            self.view.rutasList.clearSelection()
        
        # Resetear el índice de ruta seleccionada
        self.ruta_actual_idx = None
        
        # Restaurar colores normales de TODOS los nodos
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.set_normal_color()
        
        print("✓ Todas las rutas (líneas) ocultadas")

    def mostrar_todas_las_rutas(self):
        """Muestra todas las líneas de las rutas (solo si los nodos están visibles)"""
        print("Mostrando todas las rutas (líneas)...")
        
        # Mostrar todas las rutas
        for idx in range(len(self.proyecto.rutas)):
            self.visibilidad_rutas[idx] = True
        
        # Redibujar rutas (solo se dibujarán si los nodos están visibles)
        self._dibujar_rutas()
        
        # Actualizar widgets en la lista de rutas
        self._actualizar_lista_rutas_con_widgets()
        
        print("✓ Todas las rutas (líneas) mostradas")

    # --- MÉTODOS COMPATIBLES (actualizados) ---
    def ocultar_todo(self):
        """Método compatible - oculta nodos y rutas"""
        self.ocultar_todos_los_nodos()
        self.view.btnOcultarTodo.setText("Mostrar Nodos")
        if hasattr(self.view, "btnMostrarTodo"):
            self.view.btnMostrarTodo.setEnabled(False)

    def mostrar_todo(self):
        """Método compatible - muestra nodos y rutas"""
        self.mostrar_todos_los_nodos_y_rutas()
        self.view.btnOcultarTodo.setText("Ocultar Nodos")
        if hasattr(self.view, "btnMostrarTodo"):
            self.view.btnMostrarTodo.setEnabled(True)
            self.view.btnMostrarTodo.setText("Ocultar Rutas")
    
    def _actualizar_todas_relaciones_nodo_ruta(self):
        """Actualiza todas las relaciones entre nodos y rutas"""
        self.nodo_en_rutas.clear()
        
        for idx, ruta in enumerate(self.proyecto.rutas):
            self._actualizar_relaciones_nodo_ruta(idx, ruta)
    
    def _actualizar_relaciones_nodo_ruta(self, ruta_idx, ruta):
        """Actualiza las relaciones para una ruta específica"""
        try:
            ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
        except Exception:
            ruta_dict = ruta
        
        self._normalize_route_nodes(ruta_dict)
        
        # Obtener todos los nodos de la ruta
        nodos = []
        if ruta_dict.get("origen"):
            nodos.append(ruta_dict["origen"])
        nodos.extend(ruta_dict.get("visita", []) or [])
        if ruta_dict.get("destino"):
            nodos.append(ruta_dict["destino"])
        
        # Actualizar relaciones
        for nodo in nodos:
            if isinstance(nodo, dict):
                nodo_id = nodo.get('id')
                if nodo_id is not None:
                    if nodo_id not in self.nodo_en_rutas:
                        self.nodo_en_rutas[nodo_id] = []
                    if ruta_idx not in self.nodo_en_rutas[nodo_id]:
                        self.nodo_en_rutas[nodo_id].append(ruta_idx)
    
    def _obtener_nodos_de_ruta(self, ruta_idx, solo_visibles=False):
        """Obtiene todos los nodos de una ruta específica, opcionalmente solo los visibles"""
        if ruta_idx >= len(self.proyecto.rutas):
            return []
        
        ruta = self.proyecto.rutas[ruta_idx]
        try:
            ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
        except Exception:
            ruta_dict = ruta
        
        self._normalize_route_nodes(ruta_dict)
        
        nodos = []
        
        # Origen
        origen = ruta_dict.get("origen")
        if origen:
            if not solo_visibles or (isinstance(origen, dict) and self.visibilidad_nodos.get(origen.get('id'), True)):
                nodos.append(origen)
        
        # Visita
        visita = ruta_dict.get("visita", []) or []
        for nodo_visita in visita:
            if not solo_visibles or (isinstance(nodo_visita, dict) and self.visibilidad_nodos.get(nodo_visita.get('id'), True)):
                nodos.append(nodo_visita)
        
        # Destino
        destino = ruta_dict.get("destino")
        if destino:
            if not solo_visibles or (isinstance(destino, dict) and self.visibilidad_nodos.get(destino.get('id'), True)):
                nodos.append(destino)
        
        return nodos
    
    def _actualizar_lista_nodos_con_widgets(self):
        """Actualiza la lista de nodos con widgets personalizados"""
        self.view.nodosList.clear()
        
        for nodo in self.proyecto.nodos:
            self._inicializar_nodo_visibilidad(nodo, agregar_a_lista=True)
        
        print(f"✓ Lista de nodos actualizada con widgets ({self.view.nodosList.count()} nodos)")
    
    def _actualizar_lista_rutas_con_widgets(self):
        """Actualiza la lista de rutas con widgets personalizados"""
        if not hasattr(self.view, "rutasList"):
            return
            
        self.view.rutasList.clear()
        
        for idx, ruta in enumerate(self.proyecto.rutas):
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
            
            # Obtener el nombre de la ruta, por defecto "Ruta"
            nombre_ruta = ruta_dict.get("nombre", "Ruta")
            
            # Texto en formato: "nombre: id_origen -> id_destino"
            item_text = f"{nombre_ruta}: {origen_id}→{destino_id}"
            
            item = QListWidgetItem()
            item.setData(Qt.UserRole, ruta_dict)
            item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setSizeHint(QSize(0, 24))
            
            widget = RutaListItemWidget(
                idx, 
                item_text, 
                self.visibilidad_rutas.get(idx, True)
            )
            widget.toggle_visibilidad.connect(self.toggle_visibilidad_ruta)
            
            self.view.rutasList.addItem(item)
            self.view.rutasList.setItemWidget(item, widget)
        
        print(f"✓ Lista de rutas actualizada con widgets ({self.view.rutasList.count()} rutas)")
    
    def ocultar_todo(self):
        """Oculta todos los nodos y rutas de la interfaz"""
        if not self.proyecto:
            QMessageBox.warning(self.view, "Advertencia", "No hay proyecto cargado")
            return
        
        print("Ocultando todos los elementos...")
        
        # Ocultar todos los nodos en la escena
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.setVisible(False)
                nodo_id = item.nodo.get('id')
                if nodo_id is not None:
                    self.visibilidad_nodos[nodo_id] = False
        
        # Ocultar todas las rutas
        for idx in range(len(self.proyecto.rutas)):
            self.visibilidad_rutas[idx] = False
        
        # Limpiar líneas de rutas
        self._clear_route_lines()
        self._clear_highlight_lines()
        
        # Actualizar listas laterales
        self._actualizar_lista_nodos_con_widgets()
        self._actualizar_lista_rutas_con_widgets()
        
        # Deseleccionar cualquier ruta seleccionada
        if hasattr(self.view, "rutasList"):
            self.view.rutasList.clearSelection()
        
        # Resetear el índice de ruta seleccionada
        self.ruta_actual_idx = None
        
        # Limpiar tabla de propiedades
        self.view.propertiesTable.clear()
        self.view.propertiesTable.setRowCount(0)
        self.view.propertiesTable.setColumnCount(2)
        self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])
        
        # Restaurar colores normales de todos los nodos
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.set_normal_color()
        
        print("✓ Todos los elementos ocultados")
    
    def mostrar_todo(self):
        """Muestra todos los nodos y rutas de la interfaz"""
        if not self.proyecto:
            QMessageBox.warning(self.view, "Advertencia", "No hay proyecto cargado")
            return
        
        print("Mostrando todos los elementos...")
        
        # Mostrar todos los nodos en la escena
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                item.setVisible(True)
                nodo_id = item.nodo.get('id')
                if nodo_id is not None:
                    self.visibilidad_nodos[nodo_id] = True
        
        # Mostrar todas las rutas
        for idx in range(len(self.proyecto.rutas)):
            self.visibilidad_rutas[idx] = True
        
        # Redibujar rutas
        self._dibujar_rutas()
        
        # Actualizar listas laterales
        self._actualizar_lista_nodos_con_widgets()
        self._actualizar_lista_rutas_con_widgets()
        
        print("✓ Todos los elementos mostrados")
    
    def toggle_visibilidad_nodo(self, nodo_id):
        """Alterna la visibilidad de un nodo específico y reconstruye rutas"""
        if not self.proyecto:
            return
        
        # Inicializar si no está inicializado
        if nodo_id not in self.visibilidad_nodos:
            self.visibilidad_nodos[nodo_id] = True
        
        # Alternar estado
        nuevo_estado = not self.visibilidad_nodos[nodo_id]
        self.visibilidad_nodos[nodo_id] = nuevo_estado
        
        # Buscar y actualizar el NodoItem correspondiente en la escena
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                if item.nodo.get('id') == nodo_id:
                    item.setVisible(nuevo_estado)
                    break
        
        # Obtener lista de rutas que contienen este nodo
        rutas_con_nodo = self.nodo_en_rutas.get(nodo_id, [])
        
        if not nuevo_estado:
            # Si estamos OCULTANDO el nodo
            print(f"Ocultando nodo {nodo_id} - Rutas afectadas: {rutas_con_nodo}")
            print(f"  Se reconstruirán {len(rutas_con_nodo)} rutas saltando nodo {nodo_id}")
            
            # Si el nodo está siendo ocultado y está seleccionado, deseleccionarlo
            for item in self.scene.selectedItems():
                if isinstance(item, NodoItem) and item.nodo.get('id') == nodo_id:
                    item.setSelected(False)
                    break
            
            # Deseleccionar en la lista lateral
            for i in range(self.view.nodosList.count()):
                item = self.view.nodosList.item(i)
                widget = self.view.nodosList.itemWidget(item)
                if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
                    self.view.nodosList.setCurrentItem(None)
                    break
            
            # Limpiar tabla de propiedades si este nodo estaba seleccionado
            seleccionados = self.view.nodosList.selectedItems()
            if not seleccionados:
                self.view.propertiesTable.clear()
                self.view.propertiesTable.setRowCount(0)
                self.view.propertiesTable.setColumnCount(2)
                self.view.propertiesTable.setHorizontalHeaderLabels(["Propiedad", "Valor"])
        
        else:
            # Si estamos MOSTRANDO el nodo
            print(f"Mostrando nodo {nodo_id} - Reconstruyendo rutas: {rutas_con_nodo}")
            print(f"  Se reconstruirán {len(rutas_con_nodo)} rutas incluyendo nodo {nodo_id}")
            
            # El nodo se incluirá automáticamente en la reconstrucción
        
        # Actualizar widget en la lista
        self._actualizar_widget_nodo_en_lista(nodo_id)
        
        # Reconstruir y dibujar rutas
        self._dibujar_rutas()
        
        # Si hay una ruta seleccionada y contiene este nodo, actualizar sus highlights
        if self.ruta_actual_idx is not None and self.ruta_actual_idx in rutas_con_nodo:
            self.seleccionar_ruta_desde_lista()
        
        print(f"✓ Visibilidad nodo {nodo_id}: {nuevo_estado}")
        print(f"  Rutas reconstruidas: {[i for i in rutas_con_nodo if i < len(self.rutas_para_dibujo) and self.rutas_para_dibujo[i]]}")
        
    def _actualizar_relaciones_nodo_visible(self, nodo_id):
        """Reconstruye relaciones cuando un nodo se vuelve visible"""
        if not self.proyecto:
            return
        
        # Limpiar relaciones antiguas
        if nodo_id in self.nodo_en_rutas:
            self.nodo_en_rutas[nodo_id] = []
        
        # Buscar en todas las rutas si contienen este nodo
        for idx, ruta in enumerate(self.proyecto.rutas):
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
            except Exception:
                ruta_dict = ruta
            
            self._normalize_route_nodes(ruta_dict)
            
            # Verificar si la ruta contiene el nodo
            nodo_encontrado = False
            
            # Verificar origen
            origen = ruta_dict.get("origen")
            if origen and isinstance(origen, dict) and origen.get('id') == nodo_id:
                nodo_encontrado = True
            
            # Verificar destino
            destino = ruta_dict.get("destino")
            if not nodo_encontrado and destino and isinstance(destino, dict) and destino.get('id') == nodo_id:
                nodo_encontrado = True
            
            # Verificar visita
            if not nodo_encontrado:
                for nodo_visita in ruta_dict.get("visita", []):
                    if isinstance(nodo_visita, dict) and nodo_visita.get('id') == nodo_id:
                        nodo_encontrado = True
                        break
            
            # Si la ruta contiene el nodo, agregar a relaciones
            if nodo_encontrado:
                if nodo_id not in self.nodo_en_rutas:
                    self.nodo_en_rutas[nodo_id] = []
                if idx not in self.nodo_en_rutas[nodo_id]:
                    self.nodo_en_rutas[nodo_id].append(idx)
        
        print(f"✓ Relaciones actualizadas para nodo {nodo_id}: {self.nodo_en_rutas.get(nodo_id, [])}")

    def toggle_visibilidad_ruta(self, ruta_index):
        """Alterna la visibilidad de una ruta específica (SOLO líneas, como el botón global)"""
        if not self.proyecto or ruta_index >= len(self.proyecto.rutas):
            return
        
        # Inicializar si no está inicializado
        if ruta_index not in self.visibilidad_rutas:
            self.visibilidad_rutas[ruta_index] = True
        
        # Alternar estado (solo visibilidad de líneas)
        nuevo_estado = not self.visibilidad_rutas[ruta_index]
        self.visibilidad_rutas[ruta_index] = nuevo_estado
        
        # IMPORTANTE: NO MODIFICAR LA VISIBILIDAD DE LOS NODOS
        # Solo afectamos a las líneas de la ruta
        
        # Actualizar visualización de rutas
        self._dibujar_rutas()
        
        # Si la ruta que se está ocultando es la que está seleccionada, limpiar los highlights
        if not nuevo_estado and self.ruta_actual_idx == ruta_index:
            # Limpiar las líneas amarillas de resaltado
            self._clear_highlight_lines()
            
            # Restaurar colores normales de los nodos de esta ruta (pero los nodos siguen visibles)
            nodos_ruta = self._obtener_nodos_de_ruta(ruta_index)
            for nodo in nodos_ruta:
                if isinstance(nodo, dict):
                    nodo_id = nodo.get('id')
                    if nodo_id is not None:
                        for item in self.scene.items():
                            if isinstance(item, NodoItem) and item.nodo.get('id') == nodo_id:
                                # Solo restaurar color si no está seleccionado por otra razón
                                if not item.isSelected():
                                    item.set_normal_color()
                                break
        
        # Actualizar widget en la lista
        self._actualizar_widget_ruta_en_lista(ruta_index)
        
        print(f"Visibilidad ruta {ruta_index}: {nuevo_estado} (solo líneas)")
    
    def _actualizar_widget_nodo_en_lista(self, nodo_id):
        """Actualiza el widget de un nodo en la lista lateral"""
        for i in range(self.view.nodosList.count()):
            item = self.view.nodosList.item(i)
            widget = self.view.nodosList.itemWidget(item)
            if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
                widget.set_visible(self.visibilidad_nodos.get(nodo_id, True))
                break
    
    def _actualizar_widget_ruta_en_lista(self, ruta_index):
        """Actualiza el widget de una ruta en la lista lateral"""
        if not hasattr(self.view, "rutasList"):
            return
            
        for i in range(self.view.rutasList.count()):
            item = self.view.rutasList.item(i)
            widget = self.view.rutasList.itemWidget(item)
            if widget and hasattr(widget, 'ruta_index') and widget.ruta_index == ruta_index:
                # Actualizar el texto del widget
                ruta = self.proyecto.rutas[ruta_index]
                try:
                    ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
                except Exception:
                    ruta_dict = ruta
                self._normalize_route_nodes(ruta_dict)
                origen = ruta_dict.get("origen")
                destino = ruta_dict.get("destino")
                origen_id = origen.get("id", "?") if isinstance(origen, dict) else str(origen)
                destino_id = destino.get("id", "?") if isinstance(destino, dict) else str(destino)
                nombre_ruta = ruta_dict.get("nombre", "Ruta")
                item_text = f"{nombre_ruta}: {origen_id}→{destino_id}"
                widget.lbl_texto.setText(item_text)
                widget.set_visible(self.visibilidad_rutas.get(ruta_index, True))
                break
    
    def obtener_nodo_por_id(self, nodo_id):
        """Busca un nodo por su ID"""
        for nodo in self.proyecto.nodos:
            if nodo.get('id') == nodo_id:
                return nodo
        return None
    
    def obtener_ruta_por_indice(self, ruta_index):
        """Busca una ruta por su índice"""
        if 0 <= ruta_index < len(self.proyecto.rutas):
            return self.proyecto.rutas[ruta_index]
        return None

    # --- NUEVO MÉTODO PARA EXPORTACIÓN SQLITE ---
    
    def exportar_a_sqlite(self):
        """Exporta el proyecto actual a bases de datos SQLite separadas."""
        if not self.proyecto:
            QMessageBox.warning(
                self.view,
                "No hay proyecto",
                "Debes crear o abrir un proyecto primero."
            )
            return
        
        # Verificar que hay datos para exportar
        if not self.proyecto.nodos and not self.proyecto.rutas:
            QMessageBox.warning(
                self.view,
                "Proyecto vacío",
                "El proyecto no contiene nodos ni rutas para exportar."
            )
            return
        
        # Mostrar diálogo de confirmación
        confirmacion = QMessageBox.question(
            self.view,
            "Confirmar exportación",
            f"¿Exportar proyecto actual?\n\n"
            f"• Nodos: {len(self.proyecto.nodos)}\n"
            f"• Rutas: {len(self.proyecto.rutas)}\n\n"
            f"Se crearán dos archivos:\n"
            f"  - nodos.db (todos los atributos de nodos)\n"
            f"  - rutas.db (IDs: origen, destino, visitados)\n\n"
            f"Coordenadas exportadas en METROS (escala: {self.ESCALA})",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if confirmacion == QMessageBox.Yes:
            # Llamar al exportador pasando la escala
            ExportadorDB.exportar(self.proyecto, self.view, self.ESCALA)

    def manejar_seleccion_nodo(self):
        """Maneja la selección de nodos, ajustando z-values para nodos solapados"""
        seleccionados = self.scene.selectedItems()
        
        # Primero, restaurar todos los nodos a su z-value normal
        for item in self.scene.items():
            if isinstance(item, NodoItem):
                if not item.isSelected():
                    item.setZValue(1)  # Valor z normal para nodos no seleccionados
        
        # Si hay nodos seleccionados, asegurarse de que estén encima
        for item in seleccionados:
            if isinstance(item, NodoItem):
                # Establecer un valor z muy alto
                item.setZValue(1000)
                
                # Verificar si hay nodos en la misma posición (solapados)
                pos = item.scenePos()
                rect = item.boundingRect().translated(pos)
                
                # Buscar nodos en la misma posición
                nodos_solapados = []
                for otro_item in self.scene.items():
                    if isinstance(otro_item, NodoItem) and otro_item != item:
                        otro_pos = otro_item.scenePos()
                        # Verificar si están muy cerca (dentro de 5 píxeles)
                        if (abs(otro_pos.x() - pos.x()) < 5 and 
                            abs(otro_pos.y() - pos.y()) < 5):
                            nodos_solapados.append(otro_item)
                
                # Si hay nodos solapados, asegurarse de que el seleccionado esté encima
                if nodos_solapados:
                    # El nodo seleccionado ya está en z=1000
                    # Los otros nodos solapados los ponemos en z=999 para que queden justo debajo
                    for nodo_solapado in nodos_solapados:
                        nodo_solapado.setZValue(999)


    def seleccionar_nodo_desde_lista(self):
        """Versión modificada para manejar nodos solapados"""
        if self._changing_selection:
            return
        items = self.view.nodosList.selectedItems()
        if not items:
            return
        
        # Obtener el nodo del widget
        for i in range(self.view.nodosList.count()):
            item = self.view.nodosList.item(i)
            if item.isSelected():
                widget = self.view.nodosList.itemWidget(item)
                if widget and hasattr(widget, 'nodo_id'):
                    nodo_id = widget.nodo_id
                    nodo = self.obtener_nodo_por_id(nodo_id)
                    if nodo:
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
                                if isinstance(scene_item, NodoItem) and scene_item.nodo.get('id') == nodo_id:
                                    scene_item.setSelected(True)
                                    
                                    # Asegurar que el nodo esté encima de todos
                                    scene_item.setZValue(1000)
                                    
                                    # Verificar si hay nodos solapados
                                    pos = scene_item.scenePos()
                                    rect = scene_item.boundingRect().translated(pos)
                                    
                                    # Buscar nodos solapados
                                    for otro_item in self.scene.items():
                                        if isinstance(otro_item, NodoItem) and otro_item != scene_item:
                                            otro_pos = otro_item.scenePos()
                                            if (abs(otro_pos.x() - pos.x()) < 10 and 
                                                abs(otro_pos.y() - pos.y()) < 10):
                                                # Nodo solapado, ponerlo justo debajo
                                                otro_item.setZValue(999)
                                    
                                    # Aplicar color de selección
                                    scene_item.set_selected_color()
                                    self.view.marco_trabajo.centerOn(scene_item)
                                    self.mostrar_propiedades_nodo(nodo)
                                    break
                        finally:
                            self._changing_selection = False
                    break

    def seleccionar_nodo_especifico(self, nodo):
        """Selecciona un nodo específico desde el menú de superposición - Versión modificada"""
        self._changing_selection = True
        try:
            # Limpiar selecciones previas
            for item in self.scene.selectedItems():
                item.setSelected(False)
            
            # Primero restaurar todos los nodos a color normal
            self.restaurar_colores_nodos()
            
            # Buscar y seleccionar el nodo específico en la escena
            for item in self.scene.items():
                if isinstance(item, NodoItem) and item.nodo == nodo:
                    item.setSelected(True)
                    
                    # Asegurar que el nodo seleccionado esté encima
                    item.setZValue(1000)
                    
                    # Verificar si hay nodos solapados
                    pos = item.scenePos()
                    
                    # Poner otros nodos solapados justo debajo
                    for otro_item in self.scene.items():
                        if isinstance(otro_item, NodoItem) and otro_item != item:
                            otro_pos = otro_item.scenePos()
                            if (abs(otro_pos.x() - pos.x()) < 10 and 
                                abs(otro_pos.y() - pos.y()) < 10):
                                otro_item.setZValue(999)
                    
                    item.set_selected_color()
                    self.view.marco_trabajo.centerOn(item)
                    break
            
            # Sincronizar con la lista lateral
            nodo_id = nodo.get('id')
            for i in range(self.view.nodosList.count()):
                item = self.view.nodosList.item(i)
                widget = self.view.nodosList.itemWidget(item)
                if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo_id:
                    self.view.nodosList.setCurrentItem(item)
                    self.mostrar_propiedades_nodo(nodo)
                    break
        finally:
            self._changing_selection = False

    def eventFilter(self, obj, event):
        # Detectar teclas presionadas
        if event.type() == QEvent.KeyPress:
            self.keyPressEvent(event)
            return True
        
        # Detectar click izquierdo en el viewport
        if event.type() == QEvent.MouseButtonPress:
            # Mapear a escena
            pos = self.view.marco_trabajo.mapToScene(event.pos())
            
            # PRIMERO: Si estamos en modo ruta o modo colocar, NO manejar el clic aquí
            # Los controladores respectivos manejarán los clics a través de su eventFilter
            if self.modo_actual in ["ruta", "colocar"]:
                return False  # Dejar que el controlador respectivo maneje el clic
            
            # SEGUNDO: Comportamiento normal (solo si NO estamos en modo ruta o colocar)
            items = self.scene.items(pos)
            if not any(isinstance(it, NodoItem) for it in items):
                # deseleccionar items de la escena
                try:
                    for it in self.scene.selectedItems():
                        it.setSelected(False)
                except Exception:
                    pass
                
                # Restaurar z-values normales a todos los nodos
                for item in self.scene.items():
                    if isinstance(item, NodoItem):
                        item.setZValue(1)
                    
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
    
    # --- OBSERVER PATTERN: MÉTODOS PARA ACTUALIZACIÓN AUTOMÁTICA ---
    def _conectar_señales_proyecto(self):
        """Conecta las señales del proyecto para actualizar la UI automáticamente"""
        if not self.proyecto:
            return
        
        # Conectar señales de cambios
        self.proyecto.nodo_agregado.connect(self._on_nodo_agregado)
        self.proyecto.nodo_modificado.connect(self._on_nodo_modificado)
        self.proyecto.ruta_agregada.connect(self._on_ruta_agregada)
        self.proyecto.ruta_modificada.connect(self._on_ruta_modificada)
        self.proyecto.proyecto_cambiado.connect(self._on_proyecto_cambiado)
    
    def _on_nodo_agregado(self, nodo):
        """Se llama automáticamente cuando se agrega un nuevo nodo"""
        print(f"Observer: Nodo {nodo.get('id')} agregado, actualizando UI...")
        
        # Inicializar visibilidad del nodo
        self._inicializar_nodo_visibilidad(nodo, agregar_a_lista=True)
        
        # Actualizar rutas si existen
        self._dibujar_rutas()
    
    def _on_nodo_modificado(self, nodo):
        """Se llama automáticamente cuando se modifica un nodo"""
        print(f"Observer: Nodo {nodo.get('id')} modificado, actualizando UI...")
        
        # Actualizar lista lateral del nodo
        self.actualizar_lista_nodo(nodo)
        
        # Actualizar propiedades si el nodo está seleccionado
        seleccionados = self.view.nodosList.selectedItems()
        for i in range(self.view.nodosList.count()):
            item = self.view.nodosList.item(i)
            widget = self.view.nodosList.itemWidget(item)
            if widget and hasattr(widget, 'nodo_id') and widget.nodo_id == nodo.get('id'):
                if item.isSelected():
                    self.mostrar_propiedades_nodo(nodo)
                break
        
        # Actualizar rutas que contengan este nodo
        self._dibujar_rutas()
        
        # Actualizar NodoItem visual si existe
        for item in self.scene.items():
            if isinstance(item, NodoItem) and item.nodo.get('id') == nodo.get('id'):
                item.actualizar_objetivo()
                item.actualizar_posicion()
                break
    
    def _on_ruta_agregada(self, ruta):
        """Se llama automáticamente cuando se agrega una nueva ruta"""
        print("Observer: Ruta agregada, actualizando UI...")
        
        # Actualizar lista lateral de rutas
        self._actualizar_lista_rutas_con_widgets()
        
        # Redibujar rutas
        self._dibujar_rutas()
        
        # Actualizar relaciones nodo-ruta
        self._actualizar_todas_relaciones_nodo_ruta()
    
    def _on_ruta_modificada(self, ruta):
        """Se llama automáticamente cuando se modifica una ruta"""
        print("Observer: Ruta modificada, actualizando UI...")
        
        # Actualizar lista lateral de rutas
        self._actualizar_lista_rutas_con_widgets()
        
        # Redibujar rutas
        self._dibujar_rutas()
        
        # Si hay una ruta seleccionada, actualizar sus propiedades
        if hasattr(self.view, "rutasList") and self.view.rutasList.selectedItems():
            for i in range(self.view.rutasList.count()):
                item = self.view.rutasList.item(i)
                if item.isSelected():
                    widget = self.view.rutasList.itemWidget(item)
                    if widget and hasattr(widget, 'ruta_index'):
                        self.mostrar_propiedades_ruta(self.proyecto.rutas[widget.ruta_index])
                        break
    
    def _on_proyecto_cambiado(self):
        """Se llama automáticamente cuando hay cambios generales en el proyecto"""
        print("Observer: Proyecto cambiado, actualizando relaciones...")
        
        # Actualizar relaciones nodo-ruta
        self._actualizar_todas_relaciones_nodo_ruta()
        
        # Forzar actualización visual
        self.view.marco_trabajo.viewport().update()
    
    def _actualizar_referencias_proyecto(self, proyecto):
        """Actualiza todas las referencias al proyecto en controladores y subcontroladores"""
        self.proyecto = proyecto
        
        # Actualizar en subcontroladores
        self.mover_ctrl.proyecto = proyecto
        self.colocar_ctrl.proyecto = proyecto
        self.ruta_ctrl.proyecto = proyecto
        
        # Reconectar señales del nuevo proyecto
        self._conectar_señales_proyecto()
        
        print("✓ Referencias del proyecto actualizadas en todos los controladores")

    def forzar_actualizacion_cursor(self):
        """Fuerza la actualización del cursor, útil para debug"""
        print("=== FORZANDO ACTUALIZACIÓN DE CURSOR ===")
        self._actualizar_cursor()


    def _reconstruir_rutas_para_dibujo(self):
        """
        Reconstruye todas las rutas excluyendo nodos ocultos.
        Similar a _reconfigurar_rutas_por_eliminacion pero temporal.
        """
        if not self.proyecto:
            return []
        
        rutas_reconstruidas = []
        
        for ruta_idx, ruta in enumerate(self.proyecto.rutas):
            # Verificar si la ruta está visible globalmente
            if not self.visibilidad_rutas.get(ruta_idx, True):
                rutas_reconstruidas.append([])  # Ruta completamente oculta
                continue
                
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
            except Exception:
                ruta_dict = ruta
            
            # Normalizar la ruta
            self._normalize_route_nodes(ruta_dict)
            
            # Obtener todos los nodos de la ruta en orden
            puntos_completos = []
            if ruta_dict.get("origen"):
                puntos_completos.append(ruta_dict["origen"])
            puntos_completos.extend(ruta_dict.get("visita", []) or [])
            if ruta_dict.get("destino"):
                puntos_completos.append(ruta_dict["destino"])
            
            # Filtrar solo nodos visibles
            puntos_visibles = []
            for punto in puntos_completos:
                if isinstance(punto, dict):
                    nodo_id = punto.get('id')
                    if nodo_id is not None and self.visibilidad_nodos.get(nodo_id, True):
                        puntos_visibles.append(punto)
            
            # Reconstruir ruta excluyendo nodos ocultos
            ruta_reconstruida = self._reconstruir_ruta_saltando_nodos_ocultos(puntos_completos, puntos_visibles)
            rutas_reconstruidas.append(ruta_reconstruida)
        
        return rutas_reconstruidas
    
    def _reconstruir_ruta_saltando_nodos_ocultos(self, puntos_completos, puntos_visibles):
        """
        Reconstruye una ruta saltando nodos ocultos, similar a cuando se elimina un nodo.
        
        Args:
            puntos_completos: Todos los nodos de la ruta en orden
            puntos_visibles: Solo los nodos visibles de la ruta
        
        Returns:
            Lista de nodos para dibujar la ruta (puede tener menos nodos que la original)
        """
        if len(puntos_visibles) == len(puntos_completos):
            # Todos los nodos visibles, ruta intacta
            return puntos_completos
        
        if len(puntos_visibles) < 2:
            # No hay suficientes nodos visibles para dibujar una ruta
            return []
        
        # Crear mapa de visibilidad por índice
        visibilidad_por_indice = []
        for punto in puntos_completos:
            if isinstance(punto, dict):
                nodo_id = punto.get('id')
                visible = nodo_id is not None and self.visibilidad_nodos.get(nodo_id, True)
            else:
                visible = False
            visibilidad_por_indice.append(visible)
        
        # Reconstruir ruta saltando nodos ocultos
        ruta_reconstruida = []
        
        for i, punto in enumerate(puntos_completos):
            if not visibilidad_por_indice[i]:
                # Nodo oculto, omitirlo
                continue
                
            if i == 0 or i == len(puntos_completos) - 1:
                # Origen o destino: siempre incluirlo si está visible
                ruta_reconstruida.append(punto)
            else:
                # Nodo intermedio: incluirlo si está visible
                ruta_reconstruida.append(punto)
        
        # Si después de reconstruir tenemos menos de 2 nodos, retornar vacío
        return ruta_reconstruida if len(ruta_reconstruida) >= 2 else []
    
    def forzar_actualizacion_cursor(self):
        """Fuerza la actualización del cursor, útil para debug"""
        print("=== FORZANDO ACTUALIZACIÓN DE CURSOR ===")
        self._actualizar_cursor()