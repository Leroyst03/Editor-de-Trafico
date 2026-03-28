from .schema import NODO_FIELDS, OBJETIVO_FIELDS

class Nodo:
    def __init__(self, datos: dict = None):
        """
        Inicializa un nodo con los valores del esquema.
        Si se pasa un diccionario, se sobreescriben los valores por defecto.
        """
        self._datos = {}
        # Cargar valores por defecto de NODO_FIELDS
        for key, info in NODO_FIELDS.items():
            self._datos[key] = info['default']
        # También los campos de objetivo (aunque sean 0 por defecto)
        for key, info in OBJETIVO_FIELDS.items():
            self._datos[key] = info['default']

        if datos:
            self._datos.update(datos)

    def get(self, clave, default=None):
        return self._datos.get(clave, default)

    def update(self, nuevos_datos: dict):
        self._datos.update(nuevos_datos)

    def to_dict(self):
        return self._datos.copy()

    def set_posicion(self, x, y):
        self._datos["X"] = x
        self._datos["Y"] = y

    def get_posicion(self):
        return self._datos.get("X"), self._datos.get("Y")

    def __repr__(self):
        return f"Nodo({self._datos})"