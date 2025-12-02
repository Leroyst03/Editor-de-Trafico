class Ruta:
    def __init__(self, origen: int, destino: int, ruta: list[int] = None):
        self._origen = origen
        self._destino = destino
        self._ruta = ruta if ruta is not None else []

    # Setters
    def actualizar_lista(self, nueva_ruta: list[int]):
        self._ruta = nueva_ruta

    def set_origen(self, origen: int):
        self._origen = origen

    def set_destino(self, destino: int):
        self._destino = destino

    def update(self, nuevos_datos: dict):
        if "origen" in nuevos_datos:
            self._origen = nuevos_datos["origen"]
        if "destino" in nuevos_datos:
            self._destino = nuevos_datos["destino"]
        if "ruta" in nuevos_datos:
            self._ruta = nuevos_datos["ruta"]

    # Getters
    def get_ruta(self) -> list[int]:
        return self._ruta

    def get_origen(self) -> int:
        return self._origen

    def get_destino(self) -> int:
        return self._destino

    # Exportar a dict (para guardar en JSON)
    def to_dict(self) -> dict:
        return {
            "origen": self._origen,
            "destino": self._destino,
            "ruta": self._ruta
        }
