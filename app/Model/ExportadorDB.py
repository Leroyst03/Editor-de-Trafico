import sqlite3
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox

class ExportadorDB:
    """
    Clase para exportar nodos y rutas a bases de datos SQLite separadas.
    Genera dos archivos: nodos.db y rutas.db
    """
    
    @staticmethod
    def exportar(proyecto, parent_window=None):
        """
        Abre diálogo para seleccionar carpeta y exporta los datos
        
        Args:
            proyecto: Instancia de Proyecto con nodos y rutas
            parent_window: Ventana padre para diálogos
        """
        if not proyecto:
            if parent_window:
                QMessageBox.warning(parent_window, "Advertencia", 
                                   "No hay proyecto cargado para exportar")
            return False
        
        # Abrir diálogo para seleccionar carpeta
        carpeta = QFileDialog.getExistingDirectory(
            parent_window, 
            "Seleccionar carpeta para exportar",
            os.path.expanduser("~")
        )
        
        if not carpeta:
            return False  # Usuario canceló
        
        # Definir rutas de los archivos
        ruta_nodos = os.path.join(carpeta, "nodos.db")
        ruta_rutas = os.path.join(carpeta, "rutas.db")
        
        try:
            # Exportar nodos
            ExportadorDB._exportar_nodos(proyecto.nodos, ruta_nodos)
            
            # Exportar rutas (solo IDs)
            ExportadorDB._exportar_rutas(proyecto.rutas, ruta_rutas)
            
            # Mostrar mensaje de éxito
            if parent_window:
                QMessageBox.information(
                    parent_window,
                    "Exportación exitosa",
                    f"Se exportaron {len(proyecto.nodos)} nodos y {len(proyecto.rutas)} rutas.\n\n"
                    f"Archivos creados:\n• {os.path.basename(ruta_nodos)}\n• {os.path.basename(ruta_rutas)}"
                )
            
            print(f"✓ Exportación exitosa a: {carpeta}")
            return True
            
        except Exception as e:
            print(f"✗ Error en exportación: {e}")
            if parent_window:
                QMessageBox.critical(
                    parent_window,
                    "Error en exportación",
                    f"No se pudieron exportar los datos:\n{str(e)}"
                )
            return False
    
    @staticmethod
    def _exportar_nodos(nodos, ruta_db):
        """
        Exporta todos los nodos a una base de datos SQLite
        
        Args:
            nodos: Lista de objetos Nodo o diccionarios
            ruta_db: Ruta del archivo .db
        """
        conn = sqlite3.connect(ruta_db)
        cursor = conn.cursor()
        
        # Crear tabla de nodos con todos los campos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodos (
                id INTEGER PRIMARY KEY,
                X REAL,
                Y REAL,
                A REAL,
                Vmax REAL,
                Seguridad REAL,
                Seg_alto REAL,
                Seg_tresD REAL,
                Tipo_curva INTEGER,
                Reloc INTEGER,
                objetivo INTEGER,
                decision INTEGER,
                timeout INTEGER,
                ultimo_metro INTEGER,
                es_cargador INTEGER,
                Puerta_Abrir INTEGER,
                Puerta_Cerrar INTEGER,
                Punto_espera INTEGER
            )
        ''')
        
        # Limpiar tabla existente
        cursor.execute("DELETE FROM nodos")
        
        # Insertar cada nodo
        for nodo in nodos:
            # Convertir a diccionario si es objeto Nodo
            if hasattr(nodo, 'to_dict'):
                nodo_dict = nodo.to_dict()
            else:
                nodo_dict = nodo
            
            cursor.execute('''
                INSERT INTO nodos VALUES (
                    :id, :X, :Y, :A, :Vmax, :Seguridad,
                    :Seg_alto, :Seg_tresD, :Tipo_curva, :Reloc,
                    :objetivo, :decision, :timeout, :ultimo_metro,
                    :es_cargador, :Puerta_Abrir, :Puerta_Cerrar, :Punto_espera
                )
            ''', nodo_dict)
        
        conn.commit()
        conn.close()
        print(f"✓ Nodos exportados: {len(nodos)} registros")
    
    @staticmethod
    def _exportar_rutas(rutas, ruta_db):
        """
        Exporta todas las rutas a una base de datos SQLite
        Solo guarda IDs: origen, destino, visitados (nodos intermedios)
        
        Args:
            rutas: Lista de rutas (diccionarios u objetos)
            ruta_db: Ruta del archivo .db
        """
        conn = sqlite3.connect(ruta_db)
        cursor = conn.cursor()
        
        # Crear tabla simplificada de rutas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rutas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origen_id INTEGER,
                destino_id INTEGER,
                visitados TEXT
            )
        ''')
        
        # Limpiar tabla existente
        cursor.execute("DELETE FROM rutas")
        
        # Insertar cada ruta
        for i, ruta in enumerate(rutas):
            # Convertir a diccionario si es necesario
            if hasattr(ruta, 'to_dict'):
                ruta_dict = ruta.to_dict()
            else:
                ruta_dict = ruta
            
            # Extraer IDs de origen y destino
            origen = ruta_dict.get('origen', {})
            destino = ruta_dict.get('destino', {})
            visita = ruta_dict.get('visita', [])
            
            # Obtener IDs
            origen_id = origen.get('id') if isinstance(origen, dict) else origen
            destino_id = destino.get('id') if isinstance(destino, dict) else destino
            
            # Extraer solo IDs de los nodos intermedios (visita)
            visitados_ids = []
            for nodo_visita in visita:
                if isinstance(nodo_visita, dict) and 'id' in nodo_visita:
                    visitados_ids.append(str(nodo_visita['id']))
                elif hasattr(nodo_visita, 'id'):
                    visitados_ids.append(str(nodo_visita.id))
                else:
                    # Asumir que ya es un ID
                    visitados_ids.append(str(nodo_visita))
            
            # Convertir a string separado por comas
            visitados_str = ','.join(visitados_ids)
            
            # Insertar en la base de datos
            cursor.execute('''
                INSERT INTO rutas (origen_id, destino_id, visitados)
                VALUES (?, ?, ?)
            ''', (origen_id, destino_id, visitados_str))
        
        conn.commit()
        conn.close()
        print(f"✓ Rutas exportadas: {len(rutas)} registros")