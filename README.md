# Editor de Tráfico

## Resumen
 Esta es un aplicación de escritorio pensada para la edición de rutas sobre un mapa para los robots AGVs (Vehículo de Guiado Automático),
  la aplicación continua en desarrollo donde se están implementando nuevas funcionalidades.

## Requisitos
* **Python:** Contar con python instalado en el sistema
* **PyQt5:** Tener instalada la librería para poder lanzar correctamente el programa

## Instalación 
* Clona este repositorio
  ```bash
  https://github.com/Leroyst03/Editor-de-Trafico.git
  ```
* Instala PyQt5 si no lo tienes
```bash
pip install pyqt5
```
## Lanzar la aplicación
Si tienes python3: ``python3 main.py``, de lo contrario ``python main.py``


## Elementos de la UI
 ### Menú principal
 #### Proyecto
 * **Nuevo:** Nos permite crear un proyecto nuevo donde podemos escoger el mapa en el que se trabajará
 * **Abrir:** Podemos seguir trabajando sobre un proyecto ya empezado
 * **Guardar:** Guardar el trabajo actual en un archivo formato json

#### Archivo (Por implmentar)
* **Exportar archivo:** Permite exportar el proyecto a una tabla SQL que será interpretada por los AGVs

### Menú lateral nodos
* Muestra los IDs de los nodos creados hasta el momento

### Menú lateral rutas
* Muestra la cantidad de rutas con su origen y destino

### Panel lateral de propiedades 
* Muestra y permite edición de las propiedades de el nodo o ruta que se haya seleccionado

## Estructura del proyecto dentro del directorio `app`
```
.
├── Controller
│   ├── colocar_controller.py
│   ├── editor_controller.py
│   ├── mover_controller.py
│   ├── ruta_controller.py
│   └── seleccionar_controller.py
├── main.py
├── Model
│   ├── Nodo.py
│   ├── Proyecto.py
│   └── Ruta.py
├── Static
│   └── Scripts
│       └── estilos.qss
└── View
    ├── editor.ui
    ├── node_item.py
    ├── view.py
    └── zoom_view.py
```
