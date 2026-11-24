"""Comparación de las lecturas del sensor con la climatología histórica (ERA5-Land 2023-2025)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.db import obtener_conexion
from app.esquemas import Comparacion
from app.rutas.estaciones import obtener_estacion_o_404
from app.ventana import CTE_VENTANA, FILTRO_VENTANA

router = APIRouter(tags=["Comparación"])

# Cada lectura se cruza con la climatología del mismo mes y hora (hora local de Querétaro).
# Se usa la temperatura del BMP280 cuando existe porque es más precisa (±1 °C) que la del DHT11 (±2 °C).
CONSULTA_COMPARACION = f"""
WITH {CTE_VENTANA},
sensor AS (
    SELECT
        ts,
        COALESCE(temperatura_bmp, temperatura_dht) AS temperatura_sensor,
        humedad AS humedad_sensor,
        EXTRACT(MONTH FROM ts AT TIME ZONE 'America/Mexico_City')::SMALLINT AS mes,
        EXTRACT(HOUR  FROM ts AT TIME ZONE 'America/Mexico_City')::SMALLINT AS hora
    FROM lecturas
    WHERE estacion_id = :estacion_id
      AND {FILTRO_VENTANA}
)
SELECT
    s.ts,
    s.temperatura_sensor,
    c.temperatura_media                                       AS temperatura_normal,
    ROUND(s.temperatura_sensor - c.temperatura_media, 2)      AS anomalia_temperatura,
    ROUND((s.temperatura_sensor - c.temperatura_media) / NULLIF(c.temperatura_desv, 0), 2)
                                                              AS anomalia_estandarizada,
    s.humedad_sensor,
    c.humedad_media                                           AS humedad_normal
FROM sensor s
LEFT JOIN climatologia c ON c.mes = s.mes AND c.hora = s.hora
ORDER BY s.ts DESC
"""


@router.get(
    "/estaciones/{codigo}/comparacion",
    response_model=list[Comparacion],
    summary="Comparar las lecturas con lo normal para ese mes y hora",
)
def comparar_con_climatologia(
    codigo: str,
    horas: int = Query(default=24, ge=1, le=24 * 31),
    conexion: Connection = Depends(obtener_conexion),
) -> list[Comparacion]:
    estacion = obtener_estacion_o_404(conexion, codigo)
    filas = conexion.execute(
        text(CONSULTA_COMPARACION), {"estacion_id": estacion["id"], "horas": horas}
    ).mappings()
    return [Comparacion(**fila) for fila in filas]
