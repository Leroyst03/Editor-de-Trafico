import sqlite3
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import os

class ExportadorDB:
    @staticmethod
    def exportar(proyecto, view, escala=0.05):
        """
        Exporta el proyecto a dos bases de datos SQLite: nodos.db y rutas.db.
        Las coordenadas se exportan en metros usando la escala proporcionada.
        """
        if not proyecto:
            QMessageBox.warning(view, "Error", "No hay proyecto cargado.")
            return

        # Preguntar al usuario dónde guardar los archivos
        carpeta = QFileDialog.getExistingDirectory(
            view, 
            "Seleccionar carpeta para exportar bases de datos"
        )
        if not carpeta:
            return  # El usuario canceló

        # Ruta para la base de datos de nodos
        ruta_nodos = os.path.join(carpeta, "nodos.db")
        # Ruta para la base de datos de rutas
        ruta_rutas = os.path.join(carpeta, "rutas.db")

        try:
            # --- Exportar nodos ---
            conn_nodos = sqlite3.connect(ruta_nodos)
            cursor_nodos = conn_nodos.cursor()
            
            # Crear tabla de nodos con TODOS los campos del modelo
            cursor_nodos.execute("""
                CREATE TABLE IF NOT EXISTS nodos (
                    id INTEGER PRIMARY KEY,
                    X REAL,   -- en metros
                    Y REAL,   -- en metros
                    objetivo INTEGER,
                    A REAL,
                    Vmax REAL,
                    Seguridad REAL,
                    Seg_alto REAL,
                    Seg_tresD REAL,
                    Tipo_curva INTEGER,
                    Reloc INTEGER,
                    decision INTEGER,
                    timeout INTEGER,
                    ultimo_metro INTEGER,
                    es_cargador INTEGER,
                    Puerta_Abrir INTEGER,
                    Puerta_Cerrar INTEGER,
                    Punto_espera INTEGER,
                    es_curva INTEGER
                )
            """)
            
            # Insertar nodos (convertir coordenadas a metros)
            for nodo in proyecto.nodos:
                # Obtener datos del nodo
                if hasattr(nodo, 'to_dict'):
                    datos = nodo.to_dict()
                else:
                    datos = nodo
                
                # Convertir X e Y a metros
                x_px = datos.get('X', 0)
                y_px = datos.get('Y', 0)
                x_m = x_px * escala
                y_m = y_px * escala
                
                cursor_nodos.execute("""
                    INSERT INTO nodos (id, X, Y, objetivo, A, Vmax, Seguridad, 
                                     Seg_alto, Seg_tresD, Tipo_curva, Reloc, 
                                     decision, timeout, ultimo_metro, 
                                     es_cargador, Puerta_Abrir, Puerta_Cerrar, 
                                     Punto_espera, es_curva)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datos.get('id'),
                    x_m,  # X en metros
                    y_m,  # Y en metros
                    datos.get('objetivo', 0),
                    datos.get('A', 0),
                    datos.get('Vmax', 0),
                    datos.get('Seguridad', 0),
                    datos.get('Seg_alto', 0),
                    datos.get('Seg_tresD', 0),
                    datos.get('Tipo_curva', 0),
                    datos.get('Reloc', 0),
                    datos.get('decision', 0),
                    datos.get('timeout', 0),
                    datos.get('ultimo_metro', 0),
                    datos.get('es_cargador', 0),
                    datos.get('Puerta_Abrir', 0),
                    datos.get('Puerta_Cerrar', 0),
                    datos.get('Punto_espera', 0),
                    datos.get('es_curva', 0)  # <-- AQUÍ ESTÁ LA CORRECCIÓN: se añade este valor
                ))
            
            conn_nodos.commit()
            conn_nodos.close()
            
            # --- Exportar rutas ---
            conn_rutas = sqlite3.connect(ruta_rutas)
            cursor_rutas = conn_rutas.cursor()
            
            # Crear tabla de rutas
            cursor_rutas.execute("""
                CREATE TABLE IF NOT EXISTS rutas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origen_id INTEGER,
                    destino_id INTEGER,
                    visitados TEXT  -- lista de IDs separados por comas
                )
            """)
            
            # Insertar rutas
            for ruta in proyecto.rutas:
                if hasattr(ruta, 'to_dict'):
                    ruta_dict = ruta.to_dict()
                else:
                    ruta_dict = ruta
                
                # Obtener IDs de los nodos de la ruta
                origen = ruta_dict.get('origen', {})
                destino = ruta_dict.get('destino', {})
                visita = ruta_dict.get('visita', [])
                
                origen_id = origen.get('id') if isinstance(origen, dict) else None
                destino_id = destino.get('id') if isinstance(destino, dict) else None
                
                # Convertir lista de visitas a string separado por comas
                visitados_ids = []
                if origen_id is not None:
                    visitados_ids.append(str(origen_id))
                
                for v in visita:
                    if isinstance(v, dict):
                        visitados_ids.append(str(v.get('id', '')))
                    else:
                        visitados_ids.append(str(v))
                
                if destino_id is not None:
                    visitados_ids.append(str(destino_id))
                
                visitados_str = ','.join(visitados_ids)
                
                cursor_rutas.execute("""
                    INSERT INTO rutas (origen_id, destino_id, visitados)
                    VALUES (?, ?, ?)
                """, (origen_id, destino_id, visitados_str))
            
            conn_rutas.commit()
            conn_rutas.close()
            
            QMessageBox.information(
                view, 
                "Exportación completada", 
                f"Se han exportado {len(proyecto.nodos)} nodos y {len(proyecto.rutas)} rutas.\n"
                f"Archivos creados:\n• {ruta_nodos}\n• {ruta_rutas}\n\n"
                f"Coordenadas exportadas en METROS (escala: {escala})"
            )
            
        except Exception as e:
            QMessageBox.critical(
                view, 
                "Error en la exportación", 
                f"Ocurrió un error al exportar: {str(e)}"
            )