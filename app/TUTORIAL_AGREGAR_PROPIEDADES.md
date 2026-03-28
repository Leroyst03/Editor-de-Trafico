# Guía de `schema.py` — Estructura y extensión del esquema

## 1. Estructura de `schema.py`

En `Model/schema.py` se definen cuatro secciones principales:

- **`NODO_FIELDS`**: campos que pertenecen a todos los nodos (aparecen en la tabla `puntos`).
- **`OBJETIVO_FIELDS`**: campos adicionales para nodos con `objetivo != 0` (tabla `objetivos`).
- **`PARAMETROS_FIELDS`**: parámetros generales del sistema (clave-valor).
- **`PLAYA_DEFAULT_FIELDS`** y **`CARGA_DESC_DEFAULT_FIELDS`**: listas de columnas para las tablas de playa y carga/descarga (estas tablas son de estructura variable).

Cada entrada en `NODO_FIELDS` y `OBJETIVO_FIELDS` es un diccionario con las siguientes claves:

| Clave | Descripción |
|-------|-------------|
| `default` | Valor por defecto |
| `type` | Tipo de dato (`int`, `float`, `str`). Determina el widget generado en el diálogo de propiedades |
| `csv_name` | Nombre de la columna en el CSV (opcional; si se omite, se usa la clave) |
| `db_type` | Tipo de columna SQLite (`INTEGER`, `REAL`, `TEXT`). Para `id` se añade `PRIMARY KEY` |

> En `PARAMETROS_FIELDS`, `csv_name` puede ser `'clave'` o `'valor'` según la columna correspondiente en el CSV de parámetros.

---

## 2. Cómo añadir un nuevo campo a los nodos

### 2.1. Agregar la entrada en `NODO_FIELDS`

Localiza el diccionario `NODO_FIELDS` y añade una nueva entrada al final. Por ejemplo, para un campo `temperatura` (entero, valor por defecto 20, columna CSV `Temperatura`):

```python
'temperatura': {'default': 20, 'type': int, 'csv_name': 'Temperatura', 'db_type': 'INTEGER'},
```

- Tipo flotante: `'type': float, 'db_type': 'REAL'`
- Tipo texto: `'type': str, 'db_type': 'TEXT'`

### 2.2. Asegurar que aparezca en la tabla de propiedades

La tabla de propiedades se genera automáticamente en `EditorController.mostrar_propiedades_nodo` iterando sobre `NODO_FIELDS` (excluyendo `id` y las claves presentes en `OBJETIVO_FIELDS`). Si el nuevo campo no es una propiedad avanzada de objetivo, **aparecerá automáticamente** sin necesidad de modificar nada más.

### 2.3. Si el campo es parte de las propiedades avanzadas de objetivo

Añádelo a `OBJETIVO_FIELDS` en lugar de `NODO_FIELDS`. Luego, en `View/dialogo_propiedades_objetivo.py`, decide en qué grupo debe aparecer y agrégalo a la lista correspondiente dentro del diccionario `grupos`. Si no pertenece a ningún grupo, se mostrará automáticamente en "Otros".

```python
grupos = {
    "Ubicación": ["Pasillo", "Estanteria"],
    "Altura": ["Altura", "Altura_en_mm"],
    "Puntos de Referencia": ["Punto_Pasillo", "Punto_Escara", "Punto_desapr"],
    "Operación": ["FIFO", "Nombre", "Presicion", "Ir_a_desicion", "tipo_carga_descarga", "tu_nuevo_campo"],
    "Configuración Playa": ["numero_playa"]
}
```

El código del diálogo ya está preparado para leer `OBJETIVO_FIELDS` y generar los widgets correspondientes.

---

## 3. Cómo añadir un nuevo parámetro general del sistema

Los parámetros generales son clave-valor. Para añadir uno:

1. Agrega una entrada en `PARAMETROS_FIELDS`:

```python
'MI_NUEVO_PARAM': {'default': 42, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
```

2. En el CSV de parámetros, la columna `clave` tendrá el nombre `MI_NUEVO_PARAM` y la columna `valor` tendrá su valor. El exportador lo manejará automáticamente.

---

## 4. Cómo añadir una nueva columna a las tablas de playa o carga/descarga

Estas tablas tienen estructura variable, definida mediante listas:

- **`PLAYA_DEFAULT_FIELDS`**: columnas para `playas.csv` y `playas.db`.
- **`CARGA_DESC_DEFAULT_FIELDS`**: columnas para `tipo_carga_descarga.csv` y `tipo_carga_descarga.db`.

Para añadir una columna, simplemente agrégala a la lista correspondiente. Ejemplo para añadir `Tiempo_Espera` a las playas:

```python
PLAYA_DEFAULT_FIELDS = [
    'ID', 'Vertical', 'Columnas', 'Filas', 'Pose_num',
    'Detectar_con_lidar_seguirdad', 'Id_col', 'Id_row', 'ref_final', 'Tiempo_Espera'
]
```

> **Importante:** Los diálogos `dialogo_parametros_playa.py` y `dialogo_parametros_carga_descarga.py` **no están automatizados**, por lo que hay que modificarlos manualmente para incluir el nuevo campo en la interfaz. Se puede seguir un enfoque similar al del diálogo de objetivo para automatizarlos.

---

## 5. Qué hacer si el campo no aparece

**En la tabla de propiedades:**
- Verifica que el campo no esté en `OBJETIVO_FIELDS` (si lo está, no se mostrará en la tabla principal).
- Asegúrate de que `EditorController.mostrar_propiedades_nodo` está iterando sobre `NODO_FIELDS` correctamente.

**En el diálogo avanzado:**
- Asegúrate de que el campo esté en `OBJETIVO_FIELDS`.
- Si quieres ubicarlo en un grupo específico, añádelo a la lista correspondiente en `dialogo_propiedades_objetivo.py`. Si no está en ningún grupo, debe aparecer en "Otros".

**En los exportadores:**
- Si el campo no aparece en CSV/DB, verifica que los exportadores usen el esquema. Los exportadores ya están adaptados.

---

## 6. Ejemplo completo: añadir un campo `temperatura` a los nodos

**Paso 1.** En `schema.py`, añadir a `NODO_FIELDS`:

```python
'temperatura': {'default': 20, 'type': int, 'csv_name': 'Temperatura', 'db_type': 'INTEGER'},
```

**Paso 2.** Reiniciar la aplicación. El campo aparecerá automáticamente en la tabla de propiedades de los nodos (al no ser de objetivo).

**Paso 3.** Al exportar, `puntos.csv` incluirá la columna `Temperatura` con sus valores, y lo mismo en `puntos.db`.

> Si se quisiera que el campo fuera exclusivo de nodos con objetivo, se añadiría a `OBJETIVO_FIELDS` y luego al grupo correspondiente en el diálogo.