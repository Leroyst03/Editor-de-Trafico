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

                # Añadir a la lista lateral
                item = QListWidgetItem(f"ID {nodo.get('id')} - ({nodo.get('X')}, {nodo.get('Y')})")
                item.setData(Qt.UserRole, nodo)
                self.view.nodosList.addItem(item)

                print(f"Nodo colocado en: ({nodo.get('X')}, {nodo.get('Y')})")
                return True  # Consumimos el evento para que no se procese más

        return False  # Dejar pasar otros eventos normalmente