from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QListWidget
import os
from View.zoom_view import ZoomGraphicsView

class EditorView(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(os.path.dirname(__file__), "editor.ui"), self)

        # Sustituir el QGraphicsView por ZoomGraphicsView
        self.zoomView = ZoomGraphicsView(self)
        self.zoomView.setObjectName("marco_trabajo")

        # Reemplazar en el layout
        self.workLayout.replaceWidget(self.marco_trabajo, self.zoomView)
        self.marco_trabajo.deleteLater()
        self.marco_trabajo = self.zoomView
