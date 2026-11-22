"""Brecha térmica: comparación hora por hora entre el sensor y el modelo meteorológico."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.calculos import diferencia, presion_a_nivel_del_mar, radiacion_estimada_desde_lux
from app.db import obtener_conexion
from app.esquemas import BrechaHoraria
from app.rutas.estaciones import obtener_estacion_o_404

router = APIRouter(tags=["Comparación"])

# Alineación temporal con el modelo:
#  * Temperatura, humedad y presión del modelo son valores INSTANTÁNEOS en la hora en punto,
#    por eso se promedian las lecturas de ±30 min alrededor (ej. 14:30-15:29 -> 15:00).
#  * La radiación del modelo es el PROMEDIO de la hora ANTERIOR,
#    por eso se promedian las lecturas de esa hora (ej. 14:00-14:59 -> 15:00).
CONSULTA_BRECHA = """
WITH sensor_instantaneo AS (
    SELECT
        date_trunc('hour', ts + INTERVAL '30 minutes')   AS hora,
        COUNT(*)                                          AS lecturas,
        AVG(COALESCE(temperatura_bmp, temperatura_dht))   AS temperatura,
        AVG(humedad)                                      AS humedad,
        AVG(presion_hpa)                                  AS presion
    FROM lecturas
    WHERE estacion_id = :estacion_id
      AND ts >= now() - make_interval(hours => :horas)
    GROUP BY 1
),
sensor_radiacion AS (
    SELECT
        date_trunc('hour', ts) + INTERVAL '1 hour'        AS hora,
        AVG(iluminancia_lux)                              AS iluminancia
    FROM lecturas
    WHERE estacion_id = :estacion_id
      AND ts >= now() - make_interval(hours => :horas)
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
    m.radiacion_wm2::FLOAT      AS radiacion_modelo
FROM sensor_instantaneo s
LEFT JOIN sensor_radiacion r ON r.hora = s.hora
LEFT JOIN modelo_horario m   ON m.estacion_id = :estacion_id AND m.hora = s.hora
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
