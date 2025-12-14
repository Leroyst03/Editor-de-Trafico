from PyQt5.QtCore import Qt, QObject, QEvent
from View.node_item import NodoItem
from PyQt5.QtWidgets import QListWidgetItem

class ColocarController(QObject):
    def __init__(self, proyecto, view, editor):
        super().__init__()
        self.proyecto = proyecto
        self.view = view
        self.editor = editor
        self.activo = False

    def activar(self):
        if not self.activo:
            self.view.marco_trabajo.viewport().installEventFilter(self)
            self.activo = True
            print("Modo Colocar activado")

    def desactivar(self):
        if self.activo:
            self.view.marco_trabajo.viewport().removeEventFilter(self)
            self.activo = False
            print("Modo Colocar desactivado")

    def eventFilter(self, obj, event):
        # Capturar clic izquierdo dentro del QGraphicsView
        if obj is self.view.marco_trabajo.viewport() and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton and self.proyecto:
                pos = self.view.marco_trabajo.mapToScene(event.pos())
                # Crear nodo en el modelo
                nodo = self.proyecto.agregar_nodo(int(pos.x()), int(pos.y()))

                # Crear NodoItem usando helper del editor si existe
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

                # AÑADIR A LA LISTA LATERAL USANDO EL SISTEMA DEL EDITOR
                print(f"DEBUG ColocarController: Agregando nodo ID {nodo.get('id')} a lista lateral")
                
                # Usar el método centralizado del editor para inicializar visibilidad
                if hasattr(self.editor, '_inicializar_nodo_visibilidad'):
                    try:
                        self.editor._inicializar_nodo_visibilidad(nodo, agregar_a_lista=True)
                        print(f"✓ Nodo {nodo.get('id')} agregado con widget de visibilidad")
                    except Exception as e:
                        print(f"✗ Error al inicializar visibilidad: {e}")
                        # Fallback: agregar manualmente
                        # Mostrar en metros
                        x_m = self.editor.pixeles_a_metros(nodo.get('X', 0))
                        y_m = self.editor.pixeles_a_metros(nodo.get('Y', 0))
                        item = QListWidgetItem(f"ID {nodo.get('id')} - ({x_m:.2f}, {y_m:.2f})")
                        item.setData(Qt.UserRole, nodo)
                        self.view.nodosList.addItem(item)
                else:
                    # Fallback si no existe el método
                    # Mostrar en metros
                    x_m = self.editor.pixeles_a_metros(nodo.get('X', 0))
                    y_m = self.editor.pixeles_a_metros(nodo.get('Y', 0))
                    item = QListWidgetItem(f"ID {nodo.get('id')} - ({x_m:.2f}, {y_m:.2f})")
                    item.setData(Qt.UserRole, nodo)
                    self.view.nodosList.addItem(item)

                # También llamar a actualizar rutas si existen
                if hasattr(self.editor, '_dibujar_rutas'):
                    self.editor._dibujar_rutas()

                # Mostrar en metros
                x_m = self.editor.pixeles_a_metros(nodo.get('X'))
                y_m = self.editor.pixeles_a_metros(nodo.get('Y'))
                print(f"Nodo colocado en: ({x_m:.2f}, {y_m:.2f}) metros")
                return True  # Consumimos el evento para que no se procese más

        return False  # Dejar pasar otros eventos normalmente