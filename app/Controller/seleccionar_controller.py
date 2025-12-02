from PyQt5.QtCore import Qt

class SeleccionarController:
    def __init__(self, proyecto, view, editor):
        self.proyecto = proyecto
        self.view = view
        self.editor = editor

    def activar(self):
        try:
            self.view.marco_trabajo.scene().selectionChanged.connect(self.mostrar_propiedades)
        except Exception:
            pass
        print("Modo Seleccionar activado")

    def desactivar(self):
        try:
            self.view.marco_trabajo.scene().selectionChanged.disconnect(self.mostrar_propiedades)
        except Exception:
            pass
        print("Modo Seleccionar desactivado")

    def mostrar_propiedades(self):
        seleccionados = self.view.marco_trabajo.scene().selectedItems()
        if not seleccionados:
            return
        
        nodo_item = seleccionados[0]
        nodo = nodo_item.nodo
        
        # Resaltar el nodo seleccionado
        if hasattr(self.editor, 'resaltar_nodo_seleccionado'):
            self.editor.resaltar_nodo_seleccionado(nodo_item)
        
        self.editor.mostrar_propiedades_nodo(nodo)