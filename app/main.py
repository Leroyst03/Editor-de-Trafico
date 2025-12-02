from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QFile, QTextStream
from View.view import EditorView
from Controller.editor_controller import EditorController
import sys, traceback
import os
from pathlib import Path

def excepthook(type, value, tb):
    print("Excepción no capturada:", type.__name__, value)
    traceback.print_tb(tb)

def cargar_estilos(app, ruta_estilos):
    """Carga la hoja de estilos QSS desde un archivo"""

    try:
        # Verificar si el archivo existe
        if not Path(ruta_estilos).exists():
            print(f"Advertencia: No se encontro {ruta_estilos}")
            return False

        # Usar QFile para leer el archivo
        archivo = QFile(ruta_estilos)
        if archivo.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(archivo)
            app.setStyleSheet(stream.readAll())
            archivo.close()
            print(f"Estilos cargados desde: {ruta_estilos}")
            return True
        
        else:
            print(f"Error: No se pudo abrir {ruta_estilos}")
            return False
        
    except Exception as err:
        print(f"Exception al cargar estilos: {err}")
        return False

def main():
    # Instalar excepthook global
    sys.excepthook = excepthook

    app = QApplication(sys.argv)

    # Ruta el archivo de estilos 
    ruta_base = Path(__file__).parent
    ruta_estilos = ruta_base / "Static" / "Scripts" / "estilos.qss"

    # Cargar estilos antes de crear cualquier widget
    cargar_estilos(app, str(ruta_estilos))

    view = EditorView()
    controller = EditorController(view)

    view.show()

    try:
        sys.exit(app.exec_())
    except Exception:
        # Captura cualquier excepción que escape del bucle Qt
        excepthook(*sys.exc_info())

if __name__ == "__main__":
    main()
