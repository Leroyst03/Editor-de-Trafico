import sqlite3
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import os

class ExportadorDB:
    @staticmethod
    def exportar(proyecto, view, escala=0.05):
        """
        Exporta el proyecto a seis bases de datos SQLite:
        - puntos.db: propiedades básicas de todos los nodos
        - objetivos.db: propiedades avanzadas de nodos con objetivo != 0
        - rutas.db: información de las rutas
        - playas.db: parámetros de playa
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

        # --- VERIFICAR ARCHIVOS EXISTENTES ---
        rutas_a_generar = []
        # Archivos que se generan siempre
        rutas_a_generar.append(os.path.join(carpeta, "puntos.db"))
        rutas_a_generar.append(os.path.join(carpeta, "rutas.db"))

        # Objetivos (solo si hay nodos con objetivo != 0)
        if any(n.get("objetivo", 0) != 0 for n in proyecto.nodos):
            rutas_a_generar.append(os.path.join(carpeta, "objetivos.db"))

        # Parámetros de playa
        if getattr(proyecto, 'parametros_playa', []):
            rutas_a_generar.append(os.path.join(carpeta, "playas.db"))

        # Parámetros generales
        if getattr(proyecto, 'parametros', {}):
            rutas_a_generar.append(os.path.join(carpeta, "parametros.db"))

        # Parámetros de carga/descarga
        if getattr(proyecto, 'parametros_carga_descarga', []):
            rutas_a_generar.append(os.path.join(carpeta, "tipo_carga_descarga.db"))

        # Filtrar los que ya existen
        existentes = [r for r in rutas_a_generar if os.path.exists(r)]
        if existentes:
            msg = "Los siguientes archivos ya existen en la carpeta seleccionada:\n\n"
            msg += "\n".join(f"  • {os.path.basename(r)}" for r in existentes)
            msg += "\n\n¿Deseas sobrescribirlos?"
            respuesta = QMessageBox.question(
                view,
                "Confirmar sobrescritura",
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if respuesta != QMessageBox.Yes:
                return

        # --- CONTINUAR CON LA EXPORTACIÓN NORMAL ---
        try:
            # --- Exportar nodos (puntos básicos) ---
            conn_nodos = sqlite3.connect(os.path.join(carpeta, "puntos.db"))
            cursor_nodos = conn_nodos.cursor()

            # Eliminar tabla si existe para evitar conflictos de clave única
            cursor_nodos.execute("DROP TABLE IF EXISTS nodos")
            # Crear tabla de nodos con TODOS los campos del modelo
            cursor_nodos.execute("""
                CREATE TABLE nodos (
                    id INTEGER PRIMARY KEY,
                    X REAL,
                    Y REAL,
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
                if hasattr(nodo, 'to_dict'):
                    datos = nodo.to_dict()
                else:
                    datos = nodo

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
                    x_m,
                    y_m,
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
            if os.path.join(carpeta, "objetivos.db") in rutas_a_generar:
                conn_objetivos = sqlite3.connect(os.path.join(carpeta, "objetivos.db"))
                cursor_objetivos = conn_objetivos.cursor()

                cursor_objetivos.execute("DROP TABLE IF EXISTS objetivos")
                cursor_objetivos.execute("""
                    CREATE TABLE objetivos (
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

                for nodo in proyecto.nodos:
                    if hasattr(nodo, 'to_dict'):
                        datos = nodo.to_dict()
                    else:
                        datos = nodo

                    if datos.get("objetivo", 0) != 0:
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
            conn_rutas = sqlite3.connect(os.path.join(carpeta, "rutas.db"))
            cursor_rutas = conn_rutas.cursor()

            cursor_rutas.execute("DROP TABLE IF EXISTS rutas")
            cursor_rutas.execute("""
                CREATE TABLE rutas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origen_id INTEGER,
                    destino_id INTEGER,
                    visitados TEXT
                )
            """)

            for ruta in proyecto.rutas:
                if hasattr(ruta, 'to_dict'):
                    ruta_dict = ruta.to_dict()
                else:
                    ruta_dict = ruta

                origen = ruta_dict.get('origen', {})
                destino = ruta_dict.get('destino', {})
                visita = ruta_dict.get('visita', [])

                origen_id = origen.get('id') if isinstance(origen, dict) else None
                destino_id = destino.get('id') if isinstance(destino, dict) else None

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
            if os.path.join(carpeta, "playas.db") in rutas_a_generar:
                parametros_playa = getattr(proyecto, 'parametros_playa', [])
                if parametros_playa:
                    conn_playa = sqlite3.connect(os.path.join(carpeta, "playas.db"))
                    cursor_playa = conn_playa.cursor()

                    cursor_playa.execute("DROP TABLE IF EXISTS parametros_playa")

                    # Obtener todas las propiedades únicas de todos los registros
                    todas_las_propiedades = set()
                    for playa in parametros_playa:
                        todas_las_propiedades.update(playa.keys())

                    propiedades_ordenadas = sorted(todas_las_propiedades)
                    if 'ID' in propiedades_ordenadas:
                        propiedades_ordenadas.remove('ID')
                        propiedades_ordenadas = ['ID'] + propiedades_ordenadas

                    # Construir CREATE TABLE dinámico
                    create_table_sql = f"""
                        CREATE TABLE parametros_playa (
                            {propiedades_ordenadas[0]} INTEGER PRIMARY KEY,
                    """
                    for i, prop in enumerate(propiedades_ordenadas[1:], 1):
                        create_table_sql += f"\n    {prop} TEXT"
                        if i < len(propiedades_ordenadas) - 1:
                            create_table_sql += ","
                    create_table_sql += "\n)"
                    cursor_playa.execute(create_table_sql)

                    for playa in parametros_playa:
                        valores = []
                        placeholders = []
                        for prop in propiedades_ordenadas:
                            placeholders.append("?")
                            valor = playa.get(prop, "")
                            valores.append(str(valor) if valor is not None else "")
                        insert_sql = f"""
                            INSERT INTO parametros_playa ({', '.join(propiedades_ordenadas)})
                            VALUES ({', '.join(placeholders)})
                        """
                        cursor_playa.execute(insert_sql, tuple(valores))

                    conn_playa.commit()
                    conn_playa.close()

            # --- Exportar parámetros generales ---
            if os.path.join(carpeta, "parametros.db") in rutas_a_generar:
                parametros = getattr(proyecto, 'parametros', {})
                if parametros:
                    conn_param = sqlite3.connect(os.path.join(carpeta, "parametros.db"))
                    cursor_param = conn_param.cursor()

                    cursor_param.execute("DROP TABLE IF EXISTS parametros")
                    cursor_param.execute("""
                        CREATE TABLE parametros (
                            clave TEXT PRIMARY KEY,
                            valor TEXT
                        )
                    """)

                    for clave, valor in parametros.items():
                        cursor_param.execute("""
                            INSERT OR REPLACE INTO parametros (clave, valor)
                            VALUES (?, ?)
                        """, (clave, str(valor)))

                    conn_param.commit()
                    conn_param.close()

            # --- Exportar tipo_carga_descarga ---
            if os.path.join(carpeta, "tipo_carga_descarga.db") in rutas_a_generar:
                parametros_carga_descarga = getattr(proyecto, 'parametros_carga_descarga', [])
                if parametros_carga_descarga:
                    conn_carga = sqlite3.connect(os.path.join(carpeta, "tipo_carga_descarga.db"))
                    cursor_carga = conn_carga.cursor()

                    cursor_carga.execute("DROP TABLE IF EXISTS tipo_carga_descarga")

                    # Obtener todas las propiedades únicas de todos los registros
                    todas_las_propiedades = set()
                    for item in parametros_carga_descarga:
                        todas_las_propiedades.update(item.keys())

                    propiedades_ordenadas = sorted(todas_las_propiedades)
                    if 'ID' in propiedades_ordenadas:
                        propiedades_ordenadas.remove('ID')
                        propiedades_ordenadas = ['ID'] + propiedades_ordenadas

                    # Construir CREATE TABLE dinámico
                    create_table_sql = f"""
                        CREATE TABLE tipo_carga_descarga (
                            {propiedades_ordenadas[0]} INTEGER PRIMARY KEY,
                    """
                    for i, prop in enumerate(propiedades_ordenadas[1:], 1):
                        create_table_sql += f"\n    {prop} TEXT"
                        if i < len(propiedades_ordenadas) - 1:
                            create_table_sql += ","
                    create_table_sql += "\n)"
                    cursor_carga.execute(create_table_sql)

                    for item in parametros_carga_descarga:
                        valores = []
                        placeholders = []
                        for prop in propiedades_ordenadas:
                            placeholders.append("?")
                            valor = item.get(prop, "")
                            valores.append(str(valor) if valor is not None else "")
                        insert_sql = f"""
                            INSERT INTO tipo_carga_descarga ({', '.join(propiedades_ordenadas)})
                            VALUES ({', '.join(placeholders)})
                        """
                        cursor_carga.execute(insert_sql, tuple(valores))

                    conn_carga.commit()
                    conn_carga.close()

            # Mostrar mensaje de éxito
            nodos_con_objetivo = sum(1 for n in proyecto.nodos if n.get("objetivo", 0) != 0)
            archivos_creados = [
                f"• {os.path.basename(rutas_a_generar[0])} ({len(proyecto.nodos)} nodos)",
                f"• {os.path.basename(rutas_a_generar[1])} ({len(proyecto.rutas)} rutas)"
            ]
            if os.path.join(carpeta, "objetivos.db") in rutas_a_generar:
                archivos_creados.append(f"• objetivos.db ({nodos_con_objetivo} nodos con objetivo)")
            if os.path.join(carpeta, "playas.db") in rutas_a_generar:
                archivos_creados.append(f"• playas.db ({len(getattr(proyecto, 'parametros_playa', []))} playas)")
            if os.path.join(carpeta, "parametros.db") in rutas_a_generar:
                archivos_creados.append(f"• parametros.db ({len(getattr(proyecto, 'parametros', {}))} parámetros)")
            if os.path.join(carpeta, "tipo_carga_descarga.db") in rutas_a_generar:
                archivos_creados.append(f"• tipo_carga_descarga.db ({len(getattr(proyecto, 'parametros_carga_descarga', []))} tipos)")

            QMessageBox.information(
                view,
                "Exportación completada",
                f"Se han exportado:\n"
                f"• Nodos: {len(proyecto.nodos)}\n"
                f"• Rutas: {len(proyecto.rutas)}\n"
                f"• Nodos con objetivo: {nodos_con_objetivo}\n"
                f"• Playas: {len(getattr(proyecto, 'parametros_playa', []))}\n"
                f"• Parámetros generales: {len(getattr(proyecto, 'parametros', {}))}\n"
                f"• Tipos carga/descarga: {len(getattr(proyecto, 'parametros_carga_descarga', []))}\n\n"
                f"Archivos creados en:\n{carpeta}\n" + "\n".join(archivos_creados) + f"\n\n"
                f"Coordenadas exportadas en METROS (escala: {escala})"
            )

        except Exception as e:
            QMessageBox.critical(
                view,
                "Error en la exportación",
                f"Ocurrió un error al exportar: {str(e)}"
            )