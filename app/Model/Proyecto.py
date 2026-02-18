import json
from Model.Nodo import Nodo
from PyQt5.QtCore import QObject, pyqtSignal

class Proyecto(QObject):  # Ahora hereda de QObject para usar señales
    # Señales para notificar cambios
    nodo_modificado = pyqtSignal(object)  # Emite el nodo modificado
    ruta_modificada = pyqtSignal(object)  # Emite la ruta modificada
    proyecto_cambiado = pyqtSignal()      # Cambio general en el proyecto
    nodo_agregado = pyqtSignal(object)   # Nuevo: nodo agregado
    ruta_agregada = pyqtSignal(object)   # Nuevo: ruta agregada
    parametros_carga_descarga_modificados = pyqtSignal(list)  # Nuevo: parámetros carga/descarga modificados
    parametros_playa_modificados = pyqtSignal(list)          # Nuevo: parámetros playa modificados
    
    def __init__(self, mapa=None, nodos=None, rutas=None):
        super().__init__()
        self.mapa = mapa
        self.nodos = nodos if nodos is not None else []
        self.rutas = rutas if rutas is not None else []
        self.parametros = self._parametros_por_defecto()
        self.parametros_playa = self._parametros_playa_por_defecto()   # ← ahora con datos
        self.parametros_carga_descarga = self._parametros_carga_descarga_por_defecto()   # ← ahora con datos

    def _parametros_por_defecto(self):
        """Devuelve los parámetros por defecto del sistema"""
        return {
            "G_AGV_ID": 2,
            "G_thres_error_angle": 5,
            "G_dist_larguero": 0,
            "G_pulsos_por_grado_encoder": 15,
            "G_LAT_OFF": 905,
            "G_lateral_centro": 47,
            "G_LAT_MAX": 1006,
            "G_TACO_OFF": 76,
            "G_ALT_OFF": 184,
            "G_PUNTO_CARGADOR": 75,
            "G_PUNTO_CARGADOR_": 75,
            "G_offset_Lidar": 2,
            "G_t_stop_aprox_big": 0,
            "G_stop_r": 0,
            "G_PAL_L_P_off": 0,
            "G_PAL_A_P_off_peso": 0
        }
    
    def _parametros_carga_descarga_por_defecto(self):
        """Devuelve los parámetros de carga/descarga por defecto"""
        return [
            {
                "ID": 0,
                "p_a": 100, "p_b": -1, "p_c": -1, "p_d": -1, "p_e": -1,
                "p_f": -1, "p_g": -1, "p_h": -1, "p_i": -1, "p_j": -1,
                "p_k": -1, "p_l": -1, "p_m": -1, "p_n": -1, "p_o": -1,
                "p_p": -1, "p_q": -1, "p_r": -1, "p_s": -1, "p_t": -1
            },
            {
                "ID": 1,
                "p_a": 0, "p_b": 32, "p_c": 16, "p_d": 2, "p_e": 13,
                "p_f": 20, "p_g": 12, "p_h": 31, "p_i": 22, "p_j": 100,
                "p_k": -1, "p_l": -1, "p_m": -1, "p_n": -1, "p_o": -1,
                "p_p": -1, "p_q": -1, "p_r": -1, "p_s": -1, "p_t": -1
            },
            {
                "ID": 2,
                "p_a": 0, "p_b": 30, "p_c": 33, "p_d": 25, "p_e": 19,
                "p_f": 18, "p_g": 4, "p_h": 23, "p_i": 12, "p_j": 22,
                "p_k": 100, "p_l": -1, "p_m": -1, "p_n": -1, "p_o": -1,
                "p_p": -1, "p_q": -1, "p_r": -1, "p_s": -1, "p_t": -1
            }
        ]
    
    def _parametros_playa_por_defecto(self):
        """Devuelve los parámetros de playa por defecto"""
        return [{
            "ID": 1,
            "Vertical": 0,
            "Columnas": 10,
            "Filas": 10,
            "Pose_num": 0,
            "Detectar_con_lidar_seguirdad": 0,
            "Id_col": 1,
            "Id_row": 1,
            "ref_final": 0
        }]

    def agregar_nodo(self, x, y):
        """Crea un nodo con atributos iniciales y lo añade al proyecto."""
        nuevo_id = max((n.get("id") for n in self.nodos), default=0) + 1

        datos = {
            "id": nuevo_id,
            "X": x,
            "Y": y,
            "A": 0,
            "Vmax": 0,
            "Seguridad": 0,
            "Seg_alto": 0,
            "Seg_tresD": 0,
            "Tipo_curva": 0,
            "Reloc": 0,
            "objetivo": 0,
            "decision": 0,
            "timeout": 0,
            "ultimo_metro": 0,
            "es_cargador": 0,
            "Puerta_Abrir": 0,
            "Puerta_Cerrar": 0,
            "Punto_espera": 0,
        }
        nodo = Nodo(datos)
        self.nodos.append(nodo)
        
        # Notificar que se agregó un nodo
        self.nodo_agregado.emit(nodo)
        self.proyecto_cambiado.emit()
        return nodo

    def actualizar_nodo(self, nodo_actualizado: dict):
        """Actualiza un nodo existente con los datos proporcionados."""
        for nodo in self.nodos:
            if nodo.get("id") == nodo_actualizado.get("id"):
                # Actualizar solo las claves proporcionadas
                for key, value in nodo_actualizado.items():
                    if key != "id":  # No actualizar el ID
                        if hasattr(nodo, 'update'):
                            nodo.update({key: value})
                        else:
                            setattr(nodo, key, value)
                
                # Notificar que el nodo fue modificado
                self.nodo_modificado.emit(nodo)
                self.proyecto_cambiado.emit()
                return nodo
        return None

    def agregar_ruta(self, ruta_dict):
        """Agrega una ruta y notifica el cambio."""
        if not hasattr(self, "rutas") or self.rutas is None:
            self.rutas = []
        
        # Asegurar que la ruta tenga un nombre por defecto si no lo tiene
        if "nombre" not in ruta_dict:
            ruta_dict["nombre"] = "Ruta"
        
        self.rutas.append(ruta_dict)
        # Notificar que se agregó una ruta
        self.ruta_agregada.emit(ruta_dict)
        self.proyecto_cambiado.emit()
        return ruta_dict

    def actualizar_ruta(self, ruta_index, ruta_dict):
        """Actualiza una ruta y notifica el cambio."""
        if 0 <= ruta_index < len(self.rutas):
            self.rutas[ruta_index] = ruta_dict
            # Notificar que la ruta fue modificada
            self.ruta_modificada.emit(ruta_dict)
            self.proyecto_cambiado.emit()
            return True
        return False

    def eliminar_ruta(self, ruta_index):
        """Elimina una ruta y notifica el cambio."""
        if 0 <= ruta_index < len(self.rutas):
            ruta_eliminada = self.rutas.pop(ruta_index)
            # Notificar que se eliminó una ruta
            self.proyecto_cambiado.emit()
            return ruta_eliminada
        return None
    
    # NUEVO: Métodos para manejar parámetros de carga/descarga
    def actualizar_parametros_carga_descarga(self, nuevos_parametros):
        """Actualiza los parámetros de carga/descarga"""
        self.parametros_carga_descarga = nuevos_parametros
        # Notificar que se modificaron los parámetros de carga/descarga
        self.parametros_carga_descarga_modificados.emit(self.parametros_carga_descarga)
        self.proyecto_cambiado.emit()
    
    def obtener_parametros_carga_descarga(self):
        """Devuelve los parámetros de carga/descarga"""
        if not self.parametros_carga_descarga:
            return self._parametros_carga_descarga_por_defecto()
        return self.parametros_carga_descarga
    
    # NUEVO: Métodos para manejar parámetros de playa
    def actualizar_parametros_playa(self, nuevos_parametros):
        """Actualiza los parámetros de playa"""
        self.parametros_playa = nuevos_parametros
        # Notificar que se modificaron los parámetros de playa
        self.parametros_playa_modificados.emit(self.parametros_playa)
        self.proyecto_cambiado.emit()
    
    def obtener_parametros_playa(self):
        """Devuelve los parámetros de playa"""
        if not self.parametros_playa:
            return self._parametros_playa_por_defecto()
        return self.parametros_playa

    def guardar(self, ruta_archivo):
        """Guarda el proyecto en un archivo JSON con nodos completos en rutas."""
        # Preparar rutas con nodos completos
        rutas_con_nodos_completos = []
        for ruta in self.rutas:
            try:
                ruta_dict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
            except Exception:
                ruta_dict = ruta
            
            # Crear copia de la ruta con nodos completos
            ruta_completa = {}
            
            # Copiar nombre si existe, sino asignar "Ruta" por defecto
            ruta_completa["nombre"] = ruta_dict.get("nombre", "Ruta")
            
            # Origen completo
            origen = ruta_dict.get("origen")
            if origen:
                # Si origen es solo un ID, buscar el nodo completo
                if isinstance(origen, int):
                    nodo_completo = next((n for n in self.nodos if n.get('id') == origen), None)
                    if nodo_completo:
                        ruta_completa["origen"] = nodo_completo.to_dict() if hasattr(nodo_completo, "to_dict") else nodo_completo
                    else:
                        ruta_completa["origen"] = {"id": origen, "X": 0, "Y": 0}
                elif isinstance(origen, dict):
                    # Si ya es un diccionario, usarlo tal cual
                    ruta_completa["origen"] = origen
                else:
                    # Si es un objeto Nodo
                    ruta_completa["origen"] = origen.to_dict() if hasattr(origen, "to_dict") else origen
            
            # Destino completo
            destino = ruta_dict.get("destino")
            if destino:
                if isinstance(destino, int):
                    nodo_completo = next((n for n in self.nodos if n.get('id') == destino), None)
                    if nodo_completo:
                        ruta_completa["destino"] = nodo_completo.to_dict() if hasattr(nodo_completo, "to_dict") else nodo_completo
                    else:
                        ruta_completa["destino"] = {"id": destino, "X": 0, "Y": 0}
                elif isinstance(destino, dict):
                    ruta_completa["destino"] = destino
                else:
                    ruta_completa["destino"] = destino.to_dict() if hasattr(destino, "to_dict") else destino
            
            # Visita completa
            visita = ruta_dict.get("visita", [])
            if visita:
                visita_completa = []
                for nodo_visita in visita:
                    if isinstance(nodo_visita, int):
                        nodo_completo = next((n for n in self.nodos if n.get('id') == nodo_visita), None)
                        if nodo_completo:
                            visita_completa.append(nodo_completo.to_dict() if hasattr(nodo_completo, "to_dict") else nodo_completo)
                        else:
                            visita_completa.append({"id": nodo_visita, "X": 0, "Y": 0})
                    elif isinstance(nodo_visita, dict):
                        visita_completa.append(nodo_visita)
                    else:
                        visita_completa.append(nodo_visita.to_dict() if hasattr(nodo_visita, "to_dict") else nodo_visita)
                ruta_completa["visita"] = visita_completa
            
            rutas_con_nodos_completos.append(ruta_completa)
        
        datos = {
            "mapa": self.mapa,
            "nodos": [n.to_dict() for n in self.nodos],
            "rutas": rutas_con_nodos_completos,  # Nodos completos
            "parametros": self.parametros,  # incluir parámetros
            "parametros_playa": self.parametros_playa,  # incluir parámetros de playa
            "parametros_carga_descarga": self.parametros_carga_descarga  # NUEVO: incluir parámetros de carga/descarga
        }
        
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        
        print(f"✓ Proyecto guardado con {len(rutas_con_nodos_completos)} rutas, "
              f"{len(self.parametros)} parámetros, {len(self.parametros_playa)} parámetros de playa "
              f"y {len(self.parametros_carga_descarga)} parámetros de carga/descarga")

    @classmethod
    def cargar(cls, ruta_archivo):
        """Carga un proyecto desde un archivo JSON."""
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)

        mapa = datos.get("mapa", "")
        nodos_data = datos.get("nodos", [])
        rutas_simplificadas = datos.get("rutas", [])    
        
        # Cargar parámetros o usar por defecto
        parametros = datos.get("parametros")
        if parametros is None:
            # Crear instancia temporal para obtener parámetros por defecto
            proyecto_temp = cls()
            parametros = proyecto_temp._parametros_por_defecto()

        # Cargar parámetros de playa
        parametros_playa = datos.get("parametros_playa", [])

        # NUEVO: Cargar parámetros de carga/descarga
        parametros_carga_descarga = datos.get("parametros_carga_descarga", [])

        # Convertir nodos del JSON en objetos Nodo
        nodos = [Nodo(nd) for nd in nodos_data]
        
        # Crear diccionario de nodos por ID para búsqueda rápida
        nodos_por_id = {nodo.get('id'): nodo for nodo in nodos}
        
        # Reconstruir rutas completas
        rutas_completas = []
        for ruta_simp in rutas_simplificadas:
            ruta_completa = {}
            
            # Nombre de la ruta (si no existe, asignar "Ruta" por defecto)
            ruta_completa['nombre'] = ruta_simp.get('nombre', 'Ruta')
            
            # Origen
            origen = ruta_simp.get('origen')
            if origen:
                if isinstance(origen, dict) and 'id' in origen:
                    # Si ya es un diccionario con nodo completo
                    ruta_completa['origen'] = origen
                elif isinstance(origen, int):
                    # Si es solo un ID, buscar el nodo
                    nodo_origen = nodos_por_id.get(origen)
                    if nodo_origen:
                        ruta_completa['origen'] = nodo_origen.to_dict() if hasattr(nodo_origen, "to_dict") else nodo_origen
                    else:
                        ruta_completa['origen'] = {"id": origen, "X": 0, "Y": 0}
            
            # Destino
            destino = ruta_simp.get('destino')
            if destino:
                if isinstance(destino, dict) and 'id' in destino:
                    ruta_completa['destino'] = destino
                elif isinstance(destino, int):
                    nodo_destino = nodos_por_id.get(destino)
                    if nodo_destino:
                        ruta_completa['destino'] = nodo_destino.to_dict() if hasattr(nodo_destino, "to_dict") else nodo_destino
                    else:
                        ruta_completa['destino'] = {"id": destino, "X": 0, "Y": 0}
            
            # Visita
            visita = ruta_simp.get('visita', [])
            if visita:
                visita_completa = []
                for item in visita:
                    if isinstance(item, dict) and 'id' in item:
                        visita_completa.append(item)
                    elif isinstance(item, int):
                        nodo_visita = nodos_por_id.get(item)
                        if nodo_visita:
                            visita_completa.append(nodo_visita.to_dict() if hasattr(nodo_visita, "to_dict") else nodo_visita)
                        else:
                            visita_completa.append({"id": item, "X": 0, "Y": 0})
                ruta_completa['visita'] = visita_completa
            
            rutas_completas.append(ruta_completa)
        
        # Crear instancia del proyecto
        proyecto = cls(mapa, nodos, rutas_completas)
        proyecto.parametros = parametros  # asignar parámetros cargados
        proyecto.parametros_playa = parametros_playa  # asignar parámetros de playa cargados
        proyecto.parametros_carga_descarga = parametros_carga_descarga  # NUEVO: asignar parámetros de carga/descarga cargados
        
        print(f"✓ Proyecto cargado: {len(nodos)} nodos, {len(rutas_completas)} rutas, "
              f"{len(parametros)} parámetros, {len(parametros_playa)} parámetros de playa, "
              f"{len(parametros_carga_descarga)} parámetros de carga/descarga")
        return proyecto
    
    def _update_routes_for_node(self, nodo_id):
        """
        Recorre proyecto.rutas y actualiza las referencias al nodo movido.
        """
        try:
            # Buscar nodo actual en proyecto.nodos
            nodo_actual = next((n for n in self.nodos if n.get("id") == nodo_id), None)
            if not nodo_actual:
                return

            for ruta in self.rutas:
                try:
                    rdict = ruta.to_dict() if hasattr(ruta, "to_dict") else ruta
                except Exception:
                    rdict = ruta

                changed = False
                # origen
                origen = rdict.get("origen")
                if isinstance(origen, dict) and origen.get("id") == nodo_id:
                    origen.update({"X": nodo_actual.get("X"), "Y": nodo_actual.get("Y")})
                    changed = True

                # destino
                destino = rdict.get("destino")
                if isinstance(destino, dict) and destino.get("id") == nodo_id:
                    destino.update({"X": nodo_actual.get("X"), "Y": nodo_actual.get("Y")})
                    changed = True

                # visita (lista)
                visita = rdict.get("visita", []) or []
                for idx, v in enumerate(visita):
                    if isinstance(v, dict) and v.get("id") == nodo_id:
                        v.update({"X": nodo_actual.get("X"), "Y": nodo_actual.get("Y")})
                        changed = True

                if changed:
                    # Actualizar referencia en proyecto.rutas
                    try:
                        for i, r in enumerate(self.rutas):
                            try:
                                rdict2 = r.to_dict() if hasattr(r, "to_dict") else r
                            except Exception:
                                rdict2 = r
                            if rdict2 is rdict or r is rdict:
                                # Mantener el nombre si ya existe
                                if "nombre" in rdict:
                                    rdict["nombre"] = rdict.get("nombre", "Ruta")
                                self.rutas[i] = rdict
                                break
                    except Exception:
                        pass
        except Exception as err:
            print("Error en _update_routes_for_node:", err)