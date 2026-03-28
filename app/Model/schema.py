# -*- coding: utf-8 -*-
"""
Esquema centralizado de todos los campos del modelo.
Cada entrada define:
    - default: valor por defecto
    - type: tipo de dato esperado (int, float, str, etc.)
    - csv_name: nombre de la columna en el archivo CSV (si es diferente a la clave)
    - db_type: tipo de columna SQLite (para crear la tabla)
"""

# --- Nodos (todos los campos que aparecen en la tabla 'puntos' y en la estructura interna) ---
NODO_FIELDS = {
    'id': {'default': None, 'type': int, 'csv_name': 'id', 'db_type': 'INTEGER PRIMARY KEY'},
    'X': {'default': 0, 'type': float, 'csv_name': 'X', 'db_type': 'REAL'},
    'Y': {'default': 0, 'type': float, 'csv_name': 'Y', 'db_type': 'REAL'},
    'objetivo': {'default': 0, 'type': int, 'csv_name': 'objetivo', 'db_type': 'INTEGER'},
    'A': {'default': 0, 'type': float, 'csv_name': 'A', 'db_type': 'REAL'},
    'Vmax': {'default': 0, 'type': float, 'csv_name': 'Vmax', 'db_type': 'REAL'},
    'Seguridad': {'default': 0, 'type': float, 'csv_name': 'Seguridad', 'db_type': 'REAL'},
    'Seg_alto': {'default': 0, 'type': float, 'csv_name': 'Seg_alto', 'db_type': 'REAL'},
    'Seg_tresD': {'default': 0, 'type': float, 'csv_name': 'Seg_tresD', 'db_type': 'REAL'},
    'Tipo_curva': {'default': 0, 'type': int, 'csv_name': 'Tipo_curva', 'db_type': 'INTEGER'},
    'Reloc': {'default': 0, 'type': int, 'csv_name': 'Reloc', 'db_type': 'INTEGER'},
    'decision': {'default': 0, 'type': int, 'csv_name': 'decision', 'db_type': 'INTEGER'},
    'timeout': {'default': 0, 'type': int, 'csv_name': 'timeout', 'db_type': 'INTEGER'},
    'ultimo_metro': {'default': 0, 'type': int, 'csv_name': 'ultimo_metro', 'db_type': 'INTEGER'},
    'es_cargador': {'default': 0, 'type': int, 'csv_name': 'es_cargador', 'db_type': 'INTEGER'},
    'Puerta_Abrir': {'default': 0, 'type': int, 'csv_name': 'Puerta_Abrir', 'db_type': 'INTEGER'},
    'Puerta_Cerrar': {'default': 0, 'type': int, 'csv_name': 'Puerta_Cerrar', 'db_type': 'INTEGER'},
    'Punto_espera': {'default': 0, 'type': int, 'csv_name': 'Punto_espera', 'db_type': 'INTEGER'},
    'es_curva': {'default': 0, 'type': int, 'csv_name': 'es_curva', 'db_type': 'INTEGER'},
}

# --- Campos adicionales para nodos con objetivo != 0 (tabla 'objetivos') ---
OBJETIVO_FIELDS = {
    'Pasillo': {'default': 0, 'type': int, 'csv_name': 'Pasillo', 'db_type': 'INTEGER'},
    'Estanteria': {'default': 0, 'type': int, 'csv_name': 'Estanteria', 'db_type': 'INTEGER'},
    'Altura': {'default': 0, 'type': int, 'csv_name': 'Altura', 'db_type': 'INTEGER'},
    'Altura_en_mm': {'default': 0, 'type': int, 'csv_name': 'Altura_en_mm', 'db_type': 'INTEGER'},
    'Punto_Pasillo': {'default': 0, 'type': int, 'csv_name': 'Punto_Pasillo', 'db_type': 'INTEGER'},
    'Punto_Escara': {'default': 0, 'type': int, 'csv_name': 'Punto_encarar', 'db_type': 'INTEGER'},    # en CSV se llama Punto_encarar
    'Punto_desapr': {'default': 0, 'type': int, 'csv_name': 'Punto_desaproximar', 'db_type': 'INTEGER'}, # en CSV se llama Punto_desaproximar
    'FIFO': {'default': 0, 'type': int, 'csv_name': 'FIFO', 'db_type': 'INTEGER'},
    'Nombre': {'default': '', 'type': str, 'csv_name': 'Nombre', 'db_type': 'TEXT'},
    'Presicion': {'default': 0, 'type': int, 'csv_name': 'Presicion', 'db_type': 'INTEGER'},
    'Ir_a_desicion': {'default': 0, 'type': int, 'csv_name': 'Ir_a_desicion', 'db_type': 'INTEGER'},
    'numero_playa': {'default': 0, 'type': int, 'csv_name': 'numero_playa', 'db_type': 'INTEGER'},
    'tipo_carga_descarga': {'default': 0, 'type': int, 'csv_name': 'tipo_carga_descarga', 'db_type': 'INTEGER'},
    
}

# --- Parámetros generales del sistema (clave-valor) ---
PARAMETROS_FIELDS = {
    'G_AGV_ID': {'default': 2, 'type': int, 'csv_name': 'clave', 'db_type': 'TEXT PRIMARY KEY'},
    'G_thres_error_angle': {'default': 5, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_dist_larguero': {'default': 0, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_pulsos_por_grado_encoder': {'default': 15, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_LAT_OFF': {'default': 905, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_lateral_centro': {'default': 47, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_LAT_MAX': {'default': 1006, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_TACO_OFF': {'default': 76, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_ALT_OFF': {'default': 184, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_PUNTO_CARGADOR': {'default': 75, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_PUNTO_CARGADOR_': {'default': 75, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_offset_Lidar': {'default': 2, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_t_stop_aprox_big': {'default': 0, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_stop_r': {'default': 0, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_PAL_L_P_off': {'default': 0, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
    'G_PAL_A_P_off_peso': {'default': 0, 'type': int, 'csv_name': 'valor', 'db_type': 'TEXT'},
}

# --- Columnas por defecto para la tabla de parámetros de playa ---
PLAYA_DEFAULT_FIELDS = [
    'ID', 'Vertical', 'Columnas', 'Filas', 'Pose_num',
    'Detectar_con_lidar_seguirdad', 'Id_col', 'Id_row', 'ref_final'
]

# --- Columnas por defecto para la tabla de parámetros de carga/descarga ---
CARGA_DESC_DEFAULT_FIELDS = ['ID'] + [f'p_{chr(97+i)}' for i in range(20)]  # p_a .. p_t