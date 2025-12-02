import json
from Model.Nodo import Nodo

class Proyecto:
    def __init__(self, mapa=None, nodos=None, rutas=None):
        self.mapa = mapa
        # Si no hay nodos/rutas, inicializar listas vacías
        self.nodos = nodos if nodos is not None else []
        self.rutas = rutas if rutas is not None else []

    def nuevo(self, mapa):
        """Inicializa un proyecto nuevo con un mapa vacío."""
        self.mapa = mapa
        self.nodos = []
        self.rutas = []

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
            "Punto_espera": 0
        }
        nodo = Nodo(datos)
        self.nodos.append(nodo)
        return nodo

    def actualizar_nodo(self, nodo_actualizado: dict):
        """Actualiza un nodo existente con los datos proporcionados."""
        for nodo in self.nodos:
            if nodo.get("id") == nodo_actualizado.get("id"):
                nodo.update(nodo_actualizado)
                return nodo
        return None

    def guardar(self, ruta_archivo):
        """Guarda el proyecto en un archivo JSON."""
        datos = {
            "mapa": self.mapa,
            "nodos": [n.to_dict() for n in self.nodos],
            "rutas": self.rutas  
        }
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)

    @classmethod
    def cargar(cls, ruta_archivo):
        """Carga un proyecto desde un archivo JSON."""
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)

        mapa = datos.get("mapa", "")
        nodos_data = datos.get("nodos", [])
        rutas = datos.get("rutas", [])

        # Convertir nodos del JSON en objetos Nodo
        nodos = [Nodo(nd) for nd in nodos_data]

        return cls(mapa, nodos, rutas)
    
   # En la clase Proyecto, modifica el método _update_routes_for_node:
    def _update_routes_for_node(self, nodo_id):
        """
        Recorre proyecto.rutas y, cuando encuentre referencias al nodo por id,
        actualiza los dicts origen/visita/destino con las coordenadas actuales del nodo.
        """
        try:
            # buscar nodo actual en proyecto.nodos
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
                    # si la ruta está almacenada por identidad en proyecto.rutas, actualizar referencia
                    try:
                        for i, r in enumerate(self.rutas):
                            try:
                                rdict2 = r.to_dict() if hasattr(r, "to_dict") else r
                            except Exception:
                                rdict2 = r
                            if rdict2 is rdict or r is rdict:
                                self.rutas[i] = rdict
                                break
                    except Exception:
                        pass
        except Exception as err:
            print("Error en _update_routes_for_node:", err)

