class Nodo:
    def __init__(self, datos: dict):
        self._datos = datos.copy()

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
