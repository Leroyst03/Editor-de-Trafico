import sqlite3
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import os

class ExportadorDB:
    @staticmethod
    def exportar(proyecto, view, escala=0.05):
        """
        Exporta el proyecto a seis bases de datos SQLite:
        - nodos.db: propiedades básicas de todos los nodos
        - objetivos.db: propiedades avanzadas de nodos con objetivo != 0
        - rutas.db: información de las rutas
        - parametros_playa.db: parámetros de playa
        - parametros.db: parámetros generales del sistema
        - tipo_carga_descarga.db: parámetros de carga/descarga
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

        # Rutas para las bases de datos
        ruta_nodos = os.path.join(carpeta, "puntos.db")
        ruta_objetivos = os.path.join(carpeta, "objetivos.db")
        ruta_rutas = os.path.join(carpeta, "rutas.db")
        ruta_parametros_playa = os.path.join(carpeta, "playas.db")
        ruta_parametros = os.path.join(carpeta, "parametros.db")
        ruta_tipo_carga_descarga = os.path.join(carpeta, "tipo_carga_descarga.db")

        try:
            # --- Exportar nodos (puntos básicos) ---
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
                    datos.get('es_curva', 0)
                ))
            
            conn_nodos.commit()
            conn_nodos.close()
            
            # --- Exportar objetivos (propiedades avanzadas) ---
            # Contar nodos con objetivo
            nodos_con_objetivo = [n for n in proyecto.nodos if n.get("objetivo", 0) != 0]
            
            if nodos_con_objetivo:
                conn_objetivos = sqlite3.connect(ruta_objetivos)
                cursor_objetivos = conn_objetivos.cursor()
                
                # Crear tabla de objetivos
                cursor_objetivos.execute("""
                    CREATE TABLE IF NOT EXISTS objetivos (
                        nodo_id INTEGER PRIMARY KEY,
                        objetivo INTEGER,
                        Pasillo INTEGER,
                        Estanteria INTEGER,
                        Altura INTEGER,
                        Altura_en_mm INTEGER,
                        Punto_Pasillo INTEGER,
                        Punto_encarar INTEGER,
                        Punto_desaproximar INTEGER,
                        FIFO INTEGER,
                        Nombre TEXT,
                        Presicion INTEGER,
                        Ir_a_desicion INTEGER,
                        numero_playa INTEGER,
                        tipo_carga_descarga INTEGER
                    )
                """)
                
                # Insertar objetivos
                for nodo in nodos_con_objetivo:
                    if hasattr(nodo, 'to_dict'):
                        datos = nodo.to_dict()
                    else:
                        datos = nodo
                    
                    cursor_objetivos.execute("""
                        INSERT INTO objetivos (nodo_id, objetivo, Pasillo, Estanteria, Altura,
                                            Altura_en_mm, Punto_Pasillo, Punto_encarar, 
                                            Punto_desaproximar, FIFO, Nombre, Presicion,
                                            Ir_a_desicion, numero_playa, tipo_carga_descarga)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        datos.get('id'),
                        datos.get('objetivo', 0),
                        datos.get('Pasillo', 0),
                        datos.get('Estanteria', 0),
                        datos.get('Altura', 0),
                        datos.get('Altura_en_mm', 0),
                        datos.get('Punto_Pasillo', 0),
                        datos.get('Punto_Escara', 0),  # Mapeado a Punto_encarar
                        datos.get('Punto_desapr', 0),  # Mapeado a Punto_desaproximar
                        datos.get('FIFO', 0),
                        datos.get('Nombre', ''),
                        datos.get('Presicion', 0),
                        datos.get('Ir_a_desicion', 0),
                        datos.get('numero_playa', 0),
                        datos.get('tipo_carga_descarga', 0)
                    ))
                
                conn_objetivos.commit()
                conn_objetivos.close()
            
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
            
            # +++ Exportar parámetros de playa +++
            parametros_playa = getattr(proyecto, 'parametros_playa', [])
            if parametros_playa:
                conn_parametros_playa = sqlite3.connect(ruta_parametros_playa)
                cursor_parametros_playa = conn_parametros_playa.cursor()
                
                # Obtener todas las propiedades únicas de todos los registros
                todas_las_propiedades = set()
                for playa in parametros_playa:
                    todas_las_propiedades.update(playa.keys())
                
                # Ordenar propiedades: ID primero, luego las demás alfabéticamente
                propiedades_ordenadas = sorted(todas_las_propiedades)
                if 'ID' in propiedades_ordenadas:
                    propiedades_ordenadas.remove('ID')
                    propiedades_ordenadas = ['ID'] + propiedades_ordenadas
                
                # Crear tabla con propiedades dinámicas
                create_table_sql = f"""
                    CREATE TABLE IF NOT EXISTS parametros_playa (
                        {propiedades_ordenadas[0]} INTEGER PRIMARY KEY,
                """
                
                # Agregar columnas dinámicas
                for i, prop in enumerate(propiedades_ordenadas[1:], 1):
                    create_table_sql += f"\n    {prop} TEXT"
                    if i < len(propiedades_ordenadas) - 1:
                        create_table_sql += ","
                
                create_table_sql += "\n)"
                
                cursor_parametros_playa.execute(create_table_sql)
                
                # Insertar parámetros de playa
                for playa in parametros_playa:
                    # Preparar valores
                    valores = []
                    placeholders = []
                    
                    for prop in propiedades_ordenadas:
                        placeholders.append("?")
                        valor = playa.get(prop, "")
                        # Convertir a string si no es None
                        valores.append(str(valor) if valor is not None else "")
                    
                    insert_sql = f"""
                        INSERT INTO parametros_playa ({', '.join(propiedades_ordenadas)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    cursor_parametros_playa.execute(insert_sql, tuple(valores))
                
                conn_parametros_playa.commit()
                conn_parametros_playa.close()
            
            # +++ Exportar parámetros generales +++
            parametros = getattr(proyecto, 'parametros', {})
            if parametros:
                conn_parametros = sqlite3.connect(ruta_parametros)
                cursor_parametros = conn_parametros.cursor()
                
                # Crear tabla de parámetros
                cursor_parametros.execute("""
                    CREATE TABLE IF NOT EXISTS parametros (
                        clave TEXT PRIMARY KEY,
                        valor TEXT
                    )
                """)
                
                # Insertar parámetros
                for clave, valor in parametros.items():
                    cursor_parametros.execute("""
                        INSERT OR REPLACE INTO parametros (clave, valor)
                        VALUES (?, ?)
                    """, (clave, str(valor)))
                
                conn_parametros.commit()
                conn_parametros.close()
            
            # +++ Exportar tipo_carga_descarga +++
            parametros_carga_descarga = getattr(proyecto, 'parametros_carga_descarga', [])
            if parametros_carga_descarga:
                conn_tipo_carga_descarga = sqlite3.connect(ruta_tipo_carga_descarga)
                cursor_tipo_carga_descarga = conn_tipo_carga_descarga.cursor()
                
                # Obtener todas las propiedades únicas de todos los registros
                todas_las_propiedades = set()
                for carga_descarga in parametros_carga_descarga:
                    todas_las_propiedades.update(carga_descarga.keys())
                
                # Ordenar propiedades: ID primero, luego las demás alfabéticamente
                propiedades_ordenadas = sorted(todas_las_propiedades)
                if 'ID' in propiedades_ordenadas:
                    propiedades_ordenadas.remove('ID')
                    propiedades_ordenadas = ['ID'] + propiedades_ordenadas
                
                # Crear tabla con propiedades dinámicas
                create_table_sql = f"""
                    CREATE TABLE IF NOT EXISTS tipo_carga_descarga (
                        {propiedades_ordenadas[0]} INTEGER PRIMARY KEY,
                """
                
                # Agregar columnas dinámicas
                for i, prop in enumerate(propiedades_ordenadas[1:], 1):
                    create_table_sql += f"\n    {prop} TEXT"
                    if i < len(propiedades_ordenadas) - 1:
                        create_table_sql += ","
                
                create_table_sql += "\n)"
                
                cursor_tipo_carga_descarga.execute(create_table_sql)
                
                # Insertar parámetros de carga/descarga
                for carga_descarga in parametros_carga_descarga:
                    # Preparar valores
                    valores = []
                    placeholders = []
                    
                    for prop in propiedades_ordenadas:
                        placeholders.append("?")
                        valor = carga_descarga.get(prop, "")
                        # Convertir a string si no es None
                        valores.append(str(valor) if valor is not None else "")
                    
                    insert_sql = f"""
                        INSERT INTO tipo_carga_descarga ({', '.join(propiedades_ordenadas)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    cursor_tipo_carga_descarga.execute(insert_sql, tuple(valores))
                
                conn_tipo_carga_descarga.commit()
                conn_tipo_carga_descarga.close()
            
            # Mostrar mensaje de éxito con estadísticas
            archivos_creados = [
                f"• {ruta_nodos} ({len(proyecto.nodos)} nodos)",
                f"• {ruta_rutas} ({len(proyecto.rutas)} rutas)"
            ]
            
            if nodos_con_objetivo:
                archivos_creados.append(f"• {ruta_objetivos} ({len(nodos_con_objetivo)} nodos con objetivo)")
            
            if parametros_playa:
                archivos_creados.append(f"• {ruta_parametros_playa} ({len(parametros_playa)} playas)")
            
            if parametros:
                archivos_creados.append(f"• {ruta_parametros} ({len(parametros)} parámetros generales)")
            
            if parametros_carga_descarga:
                archivos_creados.append(f"• {ruta_tipo_carga_descarga} ({len(parametros_carga_descarga)} tipos de carga/descarga)")
            
            QMessageBox.information(
                view, 
                "Exportación completada", 
                f"Se han exportado:\n"
                f"• Nodos: {len(proyecto.nodos)}\n"
                f"• Rutas: {len(proyecto.rutas)}\n"
                f"• Nodos con objetivo: {len(nodos_con_objetivo)}\n"
                f"• Playas: {len(parametros_playa)}\n"
                f"• Parámetros generales: {len(parametros)}\n"
                f"• Tipos carga/descarga: {len(parametros_carga_descarga)}\n\n"
                f"Archivos creados:\n" + "\n".join(archivos_creados) + f"\n\n"
                f"Coordenadas exportadas en METROS (escala: {escala})"
            )
            
        except Exception as e:
            QMessageBox.critical(
                view, 
                "Error en la exportación", 
                f"Ocurrió un error al exportar: {str(e)}"
            )