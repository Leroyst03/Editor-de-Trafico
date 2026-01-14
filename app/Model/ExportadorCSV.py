import csv
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox

class ExportadorCSV:
    @staticmethod
    def exportar(proyecto, view, escala=0.05):
        """
        Exporta el proyecto a dos archivos CSV: nodos.csv y rutas.csv.
        Las coordenadas se exportan en metros usando la escala proporcionada.
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

        # Ruta para el archivo de nodos
        ruta_nodos = os.path.join(carpeta, "nodos.csv")
        # Ruta para el archivo de rutas
        ruta_rutas = os.path.join(carpeta, "rutas.csv")

        try:
            # --- Exportar nodos ---
            with open(ruta_nodos, 'w', newline='', encoding='utf-8') as archivo_nodos:
                campos_nodos = [
                    'id', 'X', 'Y', 'objetivo', 'A', 'Vmax', 'Seguridad', 
                    'Seg_alto', 'Seg_tresD', 'Tipo_curva', 'Reloc', 
                    'decision', 'timeout', 'ultimo_metro', 'es_cargador', 
                    'Puerta_Abrir', 'Puerta_Cerrar', 'Punto_espera', 'es_curva'
                ]
                escritor_csv = csv.DictWriter(archivo_nodos, fieldnames=campos_nodos)
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

                    # Preparar fila con todos los campos
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

            # --- Exportar rutas ---
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

            QMessageBox.information(
                view, 
                "Exportación a CSV completada", 
                f"Se han exportado {len(proyecto.nodos)} nodos y {len(proyecto.rutas)} rutas.\n"
                f"Archivos creados:\n• {ruta_nodos}\n• {ruta_rutas}\n\n"
                f"Coordenadas exportadas en METROS (escala: {escala})"
            )

        except Exception as e:
            QMessageBox.critical(
                view, 
                "Error en la exportación a CSV", 
                f"Ocurrió un error al exportar: {str(e)}"
            )