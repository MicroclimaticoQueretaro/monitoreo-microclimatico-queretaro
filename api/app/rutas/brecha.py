"""Brecha térmica: comparación entre el sensor y el modelo meteorológico (por hora y por minuto)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.calculos import diferencia, presion_a_nivel_del_mar, radiacion_estimada_desde_lux
from app.db import obtener_conexion
from app.esquemas import BrechaHoraria, BrechaMinuto
from app.rutas.estaciones import obtener_estacion_o_404
from app.ventana import CTE_VENTANA, FILTRO_VENTANA

router = APIRouter(tags=["Comparación"])

# Alineación temporal con el modelo:
#  * Temperatura, humedad y presión del modelo son valores INSTANTÁNEOS en la hora en punto,
#    por eso se promedian las lecturas de ±30 min alrededor (ej. 14:30-15:29 -> 15:00).
#  * La radiación del modelo es el PROMEDIO de la hora ANTERIOR,
#    por eso se promedian las lecturas de esa hora (ej. 14:00-14:59 -> 15:00).
CONSULTA_BRECHA = f"""
WITH {CTE_VENTANA},
sensor_instantaneo AS (
    SELECT
        date_trunc('hour', ts + INTERVAL '30 minutes')   AS hora,
        COUNT(*)                                          AS lecturas,
        AVG(COALESCE(temperatura_bmp, temperatura_dht))   AS temperatura,
        AVG(humedad)                                      AS humedad,
        AVG(presion_hpa)                                  AS presion
    FROM lecturas
    WHERE estacion_id = :estacion_id
      AND {FILTRO_VENTANA}
    GROUP BY 1
),
sensor_radiacion AS (
    SELECT
        date_trunc('hour', ts) + INTERVAL '1 hour'        AS hora,
        AVG(iluminancia_lux)                              AS iluminancia
    FROM lecturas
    WHERE estacion_id = :estacion_id
      AND {FILTRO_VENTANA}
    GROUP BY 1
)
SELECT
    s.hora,
    s.lecturas,
    s.temperatura::FLOAT        AS temperatura,
    s.humedad::FLOAT            AS humedad,
    s.presion::FLOAT            AS presion,
    r.iluminancia::FLOAT        AS iluminancia,
    m.temperatura::FLOAT        AS temperatura_modelo,
    m.humedad::FLOAT            AS humedad_modelo,
    m.presion_nivel_mar::FLOAT  AS presion_nivel_mar_modelo,
    m.radiacion_wm2::FLOAT      AS radiacion_modelo,
    c.temperatura_media::FLOAT  AS temperatura_normal,
    c.humedad_media::FLOAT      AS humedad_normal
FROM sensor_instantaneo s
LEFT JOIN sensor_radiacion r ON r.hora = s.hora
LEFT JOIN modelo_horario m   ON m.estacion_id = :estacion_id AND m.hora = s.hora
-- Climatología (lo "normal" de 2023-2025) para el mismo mes y hora en hora local de Querétaro
LEFT JOIN climatologia c
       ON c.mes  = EXTRACT(MONTH FROM s.hora AT TIME ZONE 'America/Mexico_City')
      AND c.hora = EXTRACT(HOUR  FROM s.hora AT TIME ZONE 'America/Mexico_City')
ORDER BY s.hora DESC
"""


def _redondear(valor: float | None, decimales: int = 1) -> float | None:
    return None if valor is None else round(valor, decimales)


@router.get(
    "/estaciones/{codigo}/brecha",
    response_model=list[BrechaHoraria],
    summary="Brecha térmica: sensor vs. modelo meteorológico, hora por hora",
)
def calcular_brecha(
    codigo: str,
    horas: int = Query(default=24, ge=1, le=24 * 31),
    conexion: Connection = Depends(obtener_conexion),
) -> list[BrechaHoraria]:
    estacion = obtener_estacion_o_404(conexion, codigo)
    altitud = float(estacion["altitud_m"]) if estacion["altitud_m"] is not None else None

    filas = conexion.execute(
        text(CONSULTA_BRECHA), {"estacion_id": estacion["id"], "horas": horas}
    ).mappings()

    resultado = []
    for fila in filas:
        temperatura = _redondear(fila["temperatura"])
        humedad = _redondear(fila["humedad"])
        presion_mar_sensor = presion_a_nivel_del_mar(fila["presion"], altitud, fila["temperatura"])
        resultado.append(
            BrechaHoraria(
                hora=fila["hora"],
                lecturas_promediadas=fila["lecturas"],
                temperatura_sensor=temperatura,
                temperatura_modelo=fila["temperatura_modelo"],
                brecha_termica=diferencia(temperatura, fila["temperatura_modelo"]),
                temperatura_normal=fila["temperatura_normal"],
                anomalia_climatologica=diferencia(temperatura, fila["temperatura_normal"]),
                humedad_normal=fila["humedad_normal"],
                humedad_sensor=humedad,
                humedad_modelo=fila["humedad_modelo"],
                diferencia_humedad=diferencia(humedad, fila["humedad_modelo"]),
                presion_estacion_sensor=_redondear(fila["presion"]),
                presion_nivel_mar_sensor=presion_mar_sensor,
                presion_nivel_mar_modelo=fila["presion_nivel_mar_modelo"],
                diferencia_presion=diferencia(presion_mar_sensor, fila["presion_nivel_mar_modelo"]),
                radiacion_estimada_sensor=radiacion_estimada_desde_lux(fila["iluminancia"]),
                radiacion_modelo=fila["radiacion_modelo"],
            )
        )
    return resultado


# Comparación MINUTO A MINUTO: el modelo y la climatología son datos por hora, así que su valor
# en cada minuto se estima por INTERPOLACIÓN LINEAL entre la hora anterior y la siguiente.
#   ej. 14:15 -> 75 % del valor de las 14:00 + 25 % del de las 15:00
# Si todavía no existe la hora siguiente (el modelo solo guarda horas ya transcurridas),
# se usa el valor de la hora anterior.
CONSULTA_BRECHA_MINUTOS = f"""
WITH {CTE_VENTANA},
sensor AS (
    SELECT
        ts,
        COALESCE(temperatura_bmp, temperatura_dht)                 AS temperatura,
        humedad,
        date_trunc('hour', ts)                                     AS hora_anterior,
        EXTRACT(EPOCH FROM ts - date_trunc('hour', ts)) / 3600.0   AS fraccion
    FROM lecturas
    WHERE estacion_id = :estacion_id
      AND {FILTRO_VENTANA}
)
SELECT
    s.ts,
    s.temperatura::FLOAT AS temperatura,
    s.humedad::FLOAT     AS humedad,
    (m0.temperatura + (COALESCE(m1.temperatura, m0.temperatura) - m0.temperatura) * s.fraccion)::FLOAT
                         AS temperatura_modelo,
    (m0.humedad + (COALESCE(m1.humedad, m0.humedad) - m0.humedad) * s.fraccion)::FLOAT
                         AS humedad_modelo,
    (c0.temperatura_media
        + (COALESCE(c1.temperatura_media, c0.temperatura_media) - c0.temperatura_media) * s.fraccion)::FLOAT
                         AS temperatura_normal
FROM sensor s
LEFT JOIN modelo_horario m0
       ON m0.estacion_id = :estacion_id AND m0.hora = s.hora_anterior
LEFT JOIN modelo_horario m1
       ON m1.estacion_id = :estacion_id AND m1.hora = s.hora_anterior + INTERVAL '1 hour'
-- Climatología en hora local de Querétaro, para la hora anterior y la siguiente
LEFT JOIN climatologia c0
       ON c0.mes  = EXTRACT(MONTH FROM s.hora_anterior AT TIME ZONE 'America/Mexico_City')
      AND c0.hora = EXTRACT(HOUR  FROM s.hora_anterior AT TIME ZONE 'America/Mexico_City')
LEFT JOIN climatologia c1
       ON c1.mes  = EXTRACT(MONTH FROM (s.hora_anterior + INTERVAL '1 hour') AT TIME ZONE 'America/Mexico_City')
      AND c1.hora = EXTRACT(HOUR  FROM (s.hora_anterior + INTERVAL '1 hour') AT TIME ZONE 'America/Mexico_City')
ORDER BY s.ts DESC
"""


@router.get(
    "/estaciones/{codigo}/brecha/minutos",
    response_model=list[BrechaMinuto],
    summary="Brecha térmica minuto a minuto (modelo interpolado entre horas)",
)
def calcular_brecha_por_minuto(
    codigo: str,
    horas: int = Query(default=3, ge=1, le=48),
    conexion: Connection = Depends(obtener_conexion),
) -> list[BrechaMinuto]:
    estacion = obtener_estacion_o_404(conexion, codigo)
    filas = conexion.execute(
        text(CONSULTA_BRECHA_MINUTOS), {"estacion_id": estacion["id"], "horas": horas}
    ).mappings()

    resultado = []
    for fila in filas:
        temperatura = _redondear(fila["temperatura"])
        temperatura_modelo = _redondear(fila["temperatura_modelo"], 2)
        temperatura_normal = _redondear(fila["temperatura_normal"], 2)
        humedad = _redondear(fila["humedad"])
        humedad_modelo = _redondear(fila["humedad_modelo"])
        resultado.append(
            BrechaMinuto(
                ts=fila["ts"],
                temperatura_sensor=temperatura,
                temperatura_modelo=temperatura_modelo,
                brecha_termica=diferencia(temperatura, temperatura_modelo),
                temperatura_normal=temperatura_normal,
                anomalia_climatologica=diferencia(temperatura, temperatura_normal),
                humedad_sensor=humedad,
                humedad_modelo=humedad_modelo,
                diferencia_humedad=diferencia(humedad, humedad_modelo),
            )
        )
    return resultado
