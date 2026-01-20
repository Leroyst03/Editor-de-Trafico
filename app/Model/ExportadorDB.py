import sqlite3
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import os

class ExportadorDB:
    @staticmethod
    def exportar(proyecto, view, escala=0.05):
        """
        Exporta el proyecto a cinco bases de datos SQLite:
        - nodos.db: propiedades básicas de todos los nodos
        - objetivos.db: propiedades avanzadas de nodos con objetivo != 0
        - rutas.db: información de las rutas
        - parametros_playa.db: parámetros de playa
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
        ruta_nodos = os.path.join(carpeta, "nodos.db")
        ruta_objetivos = os.path.join(carpeta, "objetivos.db")
        ruta_rutas = os.path.join(carpeta, "rutas.db")
        ruta_parametros_playa = os.path.join(carpeta, "parametros_playa.db")
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
            
            # --- Exportar parámetros de playa ---
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
            
            # --- Exportar parámetros de carga/descarga ---
            parametros_carga_descarga = getattr(proyecto, 'parametros_carga_descarga', [])
            
            if parametros_carga_descarga:
                conn_carga_descarga = sqlite3.connect(ruta_tipo_carga_descarga)
                cursor_carga_descarga = conn_carga_descarga.cursor()
                
                # Obtener todas las propiedades únicas de todos los registros
                todas_las_propiedades = set()
                for conjunto in parametros_carga_descarga:
                    todas_las_propiedades.update(conjunto.keys())
                
                # Ordenar propiedades: ID primero, luego p_a a p_t, luego las demás alfabéticamente
                propiedades_ordenadas = sorted(todas_las_propiedades)
                
                # Asegurar que ID esté primero
                if 'ID' in propiedades_ordenadas:
                    propiedades_ordenadas.remove('ID')
                    propiedades_ordenadas = ['ID'] + propiedades_ordenadas
                
                # Ordenar p_a a p_t en orden
                propiedades_p = [f'p_{chr(i)}' for i in range(ord('a'), ord('t')+1)]
                for prop in propiedades_p:
                    if prop in propiedades_ordenadas:
                        propiedades_ordenadas.remove(prop)
                
                propiedades_ordenadas = ['ID'] + propiedades_p + sorted([p for p in propiedades_ordenadas if p not in ['ID'] + propiedades_p])
                
                # Crear tabla con propiedades dinámicas
                create_table_sql = f"""
                    CREATE TABLE IF NOT EXISTS tipo_carga_descarga (
                        {propiedades_ordenadas[0]} INTEGER PRIMARY KEY,
                """
                
                # Agregar columnas dinámicas
                for i, prop in enumerate(propiedades_ordenadas[1:], 1):
                    create_table_sql += f"\n    {prop} INTEGER DEFAULT -1"
                    if i < len(propiedades_ordenadas) - 1:
                        create_table_sql += ","
                
                create_table_sql += "\n)"
                
                cursor_carga_descarga.execute(create_table_sql)
                
                # Insertar parámetros de carga/descarga
                for conjunto in parametros_carga_descarga:
                    # Preparar valores
                    valores = []
                    placeholders = []
                    
                    for prop in propiedades_ordenadas:
                        placeholders.append("?")
                        valor = conjunto.get(prop, -1)
                        valores.append(valor)
                    
                    insert_sql = f"""
                        INSERT INTO tipo_carga_descarga ({', '.join(propiedades_ordenadas)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    cursor_carga_descarga.execute(insert_sql, tuple(valores))
                
                conn_carga_descarga.commit()
                conn_carga_descarga.close()
            
            # Mostrar mensaje de éxito con estadísticas
            archivos_creados = []
            estadisticas = []
            
            # Estadísticas
            estadisticas.append(f"• Nodos: {len(proyecto.nodos)} registros")
            archivos_creados.append(f"  - nodos.db ({len(proyecto.nodos)} nodos)")
            
            if nodos_con_objetivo:
                estadisticas.append(f"• Objetivos: {len(nodos_con_objetivo)} registros")
                archivos_creados.append(f"  - objetivos.db ({len(nodos_con_objetivo)} nodos con objetivo)")
            
            estadisticas.append(f"• Rutas: {len(proyecto.rutas)} registros")
            archivos_creados.append(f"  - rutas.db ({len(proyecto.rutas)} rutas)")
            
            if parametros_playa:
                estadisticas.append(f"• Parámetros de playa: {len(parametros_playa)} registros")
                archivos_creados.append(f"  - parametros_playa.db ({len(parametros_playa)} playas)")
            
            if parametros_carga_descarga:
                estadisticas.append(f"• Tipo de carga/descarga: {len(parametros_carga_descarga)} registros")
                archivos_creados.append(f"  - tipo_carga_descarga.db ({len(parametros_carga_descarga)} conjuntos)")

            mensaje = f"Exportación a SQLite completada exitosamente\n\n"
            mensaje += f"Archivos generados en la carpeta:\n{carpeta}\n\n"
            mensaje += "Estadísticas de exportación:\n" + "\n".join(estadisticas) + "\n\n"
            mensaje += "Bases de datos creadas:\n" + "\n".join(archivos_creados) + "\n\n"
            mensaje += f"Coordenadas exportadas en METROS (escala: 1 píxel = {escala} metros)"

            QMessageBox.information(
                view, 
                "Exportación a SQLite completada", 
                mensaje
            )
            
        except Exception as e:
            QMessageBox.critical(
                view, 
                "Error en la exportación a SQLite", 
                f"Ocurrió un error al exportar:\n\n{str(e)}\n\nPor favor, intente nuevamente."
            )