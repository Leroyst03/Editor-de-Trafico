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
                # CORRECCIÓN: Usar el método crear_nodo del editor para registrar en historial
                self.editor.crear_nodo(int(pos.x()), int(pos.y()), registrar_historial=True)
                return True  # Consumimos el evento para que no se procese más

        return False  # Dejar pasar otros eventos normalmente