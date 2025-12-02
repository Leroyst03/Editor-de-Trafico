from PyQt5.QtCore import QObject
from View.node_item import NodoItem

class MoverController(QObject):
    def __init__(self, proyecto, view, editor):
        super().__init__()
        self.proyecto = proyecto
        self.view = view
        self.editor = editor
        self.activo = False

    def activar(self):
        """Activa el modo mover: hace todos los NodoItem movibles."""
        if self.activo:
            return
        self.activo = True

        # Hacer movibles todos los NodoItem en la escena
        try:
            for item in self.view.marco_trabajo.scene().items():
                if isinstance(item, NodoItem):
                    item.setFlag(item.ItemIsMovable, True)
                    item.setFlag(item.ItemIsFocusable, True)
        except Exception as err:
            print("Error al activar modo mover:", err)

        # cambiar cursor del view para indicar modo mover
        try:
            self.view.marco_trabajo.setCursor(self.view.marco_trabajo.cursor())
        except Exception:
            pass

        print("Modo Mover activado: nodos arrastrables")

    def desactivar(self):
        """Desactiva el modo mover: desactiva la movilidad en los NodoItem."""
        if not self.activo:
            return
        self.activo = False

        try:
            for item in self.view.marco_trabajo.scene().items():
                if isinstance(item, NodoItem):
                    item.setFlag(item.ItemIsMovable, False)
                    item.setFlag(item.ItemIsFocusable, True)
        except Exception as err:
            print("Error al desactivar modo mover:", err)

        # Restaurar cursor si lo cambiaste
        try:
            self.view.marco_trabajo.unsetCursor()
        except Exception:
            pass

        print("Modo Mover desactivado: nodos no movibles")