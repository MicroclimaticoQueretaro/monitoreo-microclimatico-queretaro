"""Ventana de tiempo de las consultas, anclada a la última lectura de la estación.

Si la estación está midiendo, la última lectura es de hace ~1 minuto y la ventana equivale a
"las últimas N horas". Si la estación estuvo detenida (por ejemplo, durante la noche), la
ventana termina en su última lectura: el sitio sigue mostrando los datos más recientes que
existen en lugar de quedar vacío.
"""

# CTE de SQL reutilizable: "fin" es el instante de la última lectura (o ahora, si no hay ninguna).
# Usa la llave primaria (estacion_id, ts), así que es una búsqueda inmediata.
CTE_VENTANA = """
ventana AS (
    SELECT COALESCE(MAX(ts), now()) AS fin
    FROM lecturas
    WHERE estacion_id = :estacion_id
)"""

# Seguridad: estas cadenas se insertan en el SQL con f-strings, pero son CONSTANTES del código.
# Los valores que llegan del usuario (horas, estación) siempre van como parámetros (:horas).

# Condición para filtrar las lecturas dentro de la ventana (requiere la CTE anterior)
FILTRO_VENTANA = (
    "ts > (SELECT fin FROM ventana) - make_interval(hours => :horas) "
    "AND ts <= (SELECT fin FROM ventana)"
)
