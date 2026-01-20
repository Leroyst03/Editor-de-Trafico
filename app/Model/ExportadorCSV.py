import csv
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox

class ExportadorCSV:
    @staticmethod
    def exportar(proyecto, view, escala=0.05):
        """
        Exporta el proyecto a archivos CSV.
        """
        if not proyecto:
            QMessageBox.warning(view, "Error", "No hay proyecto cargado.")
            return

        # Preguntar al usuario dónde guardar los archivos
        carpeta = QFileDialog.getExistingDirectory(
            view, 
            "Seleccionar carpeta para exportar archivos CSV"
        )
        if not carpeta:
            return  # El usuario canceló

        try:
            # Contadores para estadísticas
            nodos_con_objetivo = 0
            nodos_total = len(proyecto.nodos)
            
            # --- Exportar puntos (nodos básicos) ---
            ruta_puntos = os.path.join(carpeta, "puntos.csv")
            with open(ruta_puntos, 'w', newline='', encoding='utf-8') as archivo_puntos:
                campos_puntos = [
                    'id', 'X', 'Y', 'objetivo', 'A', 'Vmax', 'Seguridad', 
                    'Seg_alto', 'Seg_tresD', 'Tipo_curva', 'Reloc', 
                    'decision', 'timeout', 'ultimo_metro', 'es_cargador', 
                    'Puerta_Abrir', 'Puerta_Cerrar', 'Punto_espera', 'es_curva'
                ]
                escritor_csv = csv.DictWriter(archivo_puntos, fieldnames=campos_puntos)
                escritor_csv.writeheader()

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

                    # Preparar fila con todos los campos básicos
                    fila = {
                        'id': datos.get('id'),
                        'X': x_m,
                        'Y': y_m,
                        'objetivo': datos.get('objetivo', 0),
                        'A': datos.get('A', 0),
                        'Vmax': datos.get('Vmax', 0),
                        'Seguridad': datos.get('Seguridad', 0),
                        'Seg_alto': datos.get('Seg_alto', 0),
                        'Seg_tresD': datos.get('Seg_tresD', 0),
                        'Tipo_curva': datos.get('Tipo_curva', 0),
                        'Reloc': datos.get('Reloc', 0),
                        'decision': datos.get('decision', 0),
                        'timeout': datos.get('timeout', 0),
                        'ultimo_metro': datos.get('ultimo_metro', 0),
                        'es_cargador': datos.get('es_cargador', 0),
                        'Puerta_Abrir': datos.get('Puerta_Abrir', 0),
                        'Puerta_Cerrar': datos.get('Puerta_Cerrar', 0),
                        'Punto_espera': datos.get('Punto_espera', 0),
                        'es_curva': datos.get('es_curva', 0)
                    }
                    escritor_csv.writerow(fila)
            
            # --- Exportar objetivos (propiedades avanzadas) ---
            ruta_objetivos = os.path.join(carpeta, "objetivos.csv")
            with open(ruta_objetivos, 'w', newline='', encoding='utf-8') as archivo_objetivos:
                campos_objetivos = [
                    'nodo_id', 'objetivo', 'Pasillo', 'Estanteria', 'Altura',
                    'Altura_en_mm', 'Punto_Pasillo', 'Punto_encarar', 'Punto_desaproximar',
                    'FIFO', 'Nombre', 'Presicion', 'Ir_a_desicion', 'numero_playa',
                    'tipo_carga_descarga'
                ]
                escritor_csv = csv.DictWriter(archivo_objetivos, fieldnames=campos_objetivos)
                escritor_csv.writeheader()

                for nodo in proyecto.nodos:
                    # Obtener datos del nodo
                    if hasattr(nodo, 'to_dict'):
                        datos = nodo.to_dict()
                    else:
                        datos = nodo
                    
                    objetivo = datos.get('objetivo', 0)
                    
                    # Solo exportar nodos con objetivo != 0
                    if objetivo != 0:
                        nodos_con_objetivo += 1
                        
                        # Preparar fila con todas las propiedades avanzadas
                        fila = {
                            'nodo_id': datos.get('id'),
                            'objetivo': objetivo,
                            'Pasillo': datos.get('Pasillo', 0),
                            'Estanteria': datos.get('Estanteria', 0),
                            'Altura': datos.get('Altura', 0),
                            'Altura_en_mm': datos.get('Altura_en_mm', 0),
                            'Punto_Pasillo': datos.get('Punto_Pasillo', 0),
                            'Punto_encarar': datos.get('Punto_Escara', 0),
                            'Punto_desaproximar': datos.get('Punto_desapr', 0),
                            'FIFO': datos.get('FIFO', 0),
                            'Nombre': datos.get('Nombre', ''),
                            'Presicion': datos.get('Presicion', 0),
                            'Ir_a_desicion': datos.get('Ir_a_desicion', 0),
                            'numero_playa': datos.get('numero_playa', 0),
                            'tipo_carga_descarga': datos.get('tipo_carga_descarga', 0)
                        }
                        escritor_csv.writerow(fila)

            # --- Exportar rutas ---
            ruta_rutas = os.path.join(carpeta, "rutas.csv")
            with open(ruta_rutas, 'w', newline='', encoding='utf-8') as archivo_rutas:
                campos_rutas = ['origen_id', 'destino_id', 'visitados']
                escritor_csv = csv.DictWriter(archivo_rutas, fieldnames=campos_rutas)
                escritor_csv.writeheader()

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

                    escritor_csv.writerow({
                        'origen_id': origen_id,
                        'destino_id': destino_id,
                        'visitados': visitados_str
                    })
            
            # --- Exportar parámetros de playa ---
            ruta_parametros_playa = os.path.join(carpeta, "parametros_playa.csv")
            parametros_playa = getattr(proyecto, 'parametros_playa', [])
            
            if parametros_playa:
                # Obtener todas las propiedades únicas de todos los registros
                todas_las_propiedades = set()
                for playa in parametros_playa:
                    todas_las_propiedades.update(playa.keys())
                
                # Ordenar propiedades: ID primero, luego las demás alfabéticamente
                propiedades_ordenadas = sorted(todas_las_propiedades)
                if 'ID' in propiedades_ordenadas:
                    propiedades_ordenadas.remove('ID')
                    propiedades_ordenadas = ['ID'] + propiedades_ordenadas
                
                with open(ruta_parametros_playa, 'w', newline='', encoding='utf-8') as archivo_parametros_playa:
                    escritor_csv = csv.DictWriter(archivo_parametros_playa, fieldnames=propiedades_ordenadas)
                    escritor_csv.writeheader()
                    
                    for playa in parametros_playa:
                        # Asegurarse de que todas las propiedades existan en cada registro
                        fila_completa = {}
                        for prop in propiedades_ordenadas:
                            fila_completa[prop] = playa.get(prop, "")
                        escritor_csv.writerow(fila_completa)

            # Mostrar mensaje de éxito con estadísticas
            mensaje = f"Se han exportado:\n"
            mensaje += f"• {nodos_total} nodos a {ruta_puntos}\n"
            mensaje += f"• {nodos_con_objetivo} nodos con objetivo a {ruta_objetivos}\n"
            mensaje += f"• {len(proyecto.rutas)} rutas a {ruta_rutas}\n"
            mensaje += f"• {len(parametros_playa)} playas a {ruta_parametros_playa if parametros_playa else 'No hay parámetros de playa'}\n\n"
            mensaje += f"Coordenadas exportadas en METROS (escala: {escala})"

            QMessageBox.information(
                view, 
                "Exportación a CSV completada", 
                mensaje
            )

        except Exception as e:
            QMessageBox.critical(
                view, 
                "Error en la exportación a CSV", 
                f"Ocurrió un error al exportar: {str(e)}"
            )