"""Descarga del modelo meteorológico (Open-Meteo) y guardado en la base de datos.

El modelo da el valor "regional" esperado para la ubicación de la estación. La
diferencia entre el sensor (en la calle) y el modelo es la BRECHA TÉRMICA, el
indicador de la isla de calor urbana.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import obtener_configuracion

registro = logging.getLogger(__name__)

# Variables horarias pedidas a Open-Meteo y su columna en la tabla modelo_horario
VARIABLES = {
    "temperature_2m": "temperatura",
    "relative_humidity_2m": "humedad",
    "pressure_msl": "presion_nivel_mar",
    "surface_pressure": "presion_superficie",
    # La radiación de Open-Meteo es el PROMEDIO de la hora anterior a la marca de tiempo
    "shortwave_radiation": "radiacion_wm2",
}

# Rangos válidos (iguales a los CHECK de la tabla). Un valor fuera de rango se guarda como NULL.
RANGOS = {
    "temperatura": (-30, 60),
    "humedad": (0, 100),
    "presion_nivel_mar": (900, 1100),
    "presion_superficie": (600, 1100),
    "radiacion_wm2": (0, 1500),
}


def _validar(columna: str, valor: float | None) -> float | None:
    if valor is None:
        return None
    minimo, maximo = RANGOS[columna]
    return valor if minimo <= valor <= maximo else None


def descargar_modelo(
    cliente: httpx.Client, latitud: float, longitud: float, altitud_m: float | None
) -> list[dict]:
    """Pide a Open-Meteo los valores horarios de los últimos 2 días para un punto.

    Se envía la altitud de la estación para que Open-Meteo ajuste el modelo a esa
    altura; así la brecha térmica no incluye el efecto de la diferencia de altitud.
    """
    configuracion = obtener_configuracion()
    parametros = {
        "latitude": latitud,
        "longitude": longitud,
        "hourly": ",".join(VARIABLES),
        "past_days": 2,
        "forecast_days": 1,
        "timezone": "GMT",  # se trabaja en UTC; la conversión a hora local la hace quien muestra
    }
    if altitud_m is not None:
        parametros["elevation"] = altitud_m

    respuesta = cliente.get(
        configuracion.url_modelo, params=parametros, timeout=configuracion.tiempo_espera_modelo_s
    )
    respuesta.raise_for_status()
    horario = respuesta.json()["hourly"]

    ahora = datetime.now(timezone.utc)
    filas = []
    for indice, texto_hora in enumerate(horario["time"]):
        hora = datetime.fromisoformat(texto_hora).replace(tzinfo=timezone.utc)
        # Solo horas ya ocurridas: el pronóstico futuro no sirve para comparar con el sensor
        if hora > ahora:
            continue
        fila = {"hora": hora}
        for variable, columna in VARIABLES.items():
            fila[columna] = _validar(columna, horario[variable][indice])
        filas.append(fila)
    return filas


def guardar_modelo(conexion: Connection, estacion_id: int, filas: list[dict]) -> int:
    """Inserta o actualiza (upsert) las horas del modelo. Devuelve cuántas filas procesó."""
    if not filas:
        return 0
    conexion.execute(
        text(
            "INSERT INTO modelo_horario (estacion_id, hora, temperatura, humedad, "
            "presion_nivel_mar, presion_superficie, radiacion_wm2) "
            "VALUES (:estacion_id, :hora, :temperatura, :humedad, "
            ":presion_nivel_mar, :presion_superficie, :radiacion_wm2) "
            # Si la hora ya existe, se actualiza: el modelo puede corregir horas recientes
            "ON CONFLICT (estacion_id, hora) DO UPDATE SET "
            "temperatura = EXCLUDED.temperatura, humedad = EXCLUDED.humedad, "
            "presion_nivel_mar = EXCLUDED.presion_nivel_mar, "
            "presion_superficie = EXCLUDED.presion_superficie, "
            "radiacion_wm2 = EXCLUDED.radiacion_wm2, actualizado_en = now()"
        ),
        [{"estacion_id": estacion_id, **fila} for fila in filas],
    )
    return len(filas)


def sincronizar_estaciones(conexion: Connection, cliente: httpx.Client) -> dict[str, int]:
    """Descarga y guarda el modelo para cada estación activa.

    Si una estación falla, se registra el error y se continúa con las demás.
    Devuelve {codigo_estacion: horas_guardadas} (-1 si falló).
    """
    estaciones = conexion.execute(
        text("SELECT id, codigo, latitud, longitud, altitud_m FROM estaciones WHERE activa")
    ).mappings().all()

    resumen = {}
    for estacion in estaciones:
        altitud = float(estacion["altitud_m"]) if estacion["altitud_m"] is not None else None
        try:
            # Savepoint por estación: un error no deshace lo guardado de las otras
            with conexion.begin_nested():
                filas = descargar_modelo(
                    cliente, float(estacion["latitud"]), float(estacion["longitud"]), altitud
                )
                resumen[estacion["codigo"]] = guardar_modelo(conexion, estacion["id"], filas)
        except (httpx.HTTPError, KeyError, ValueError) as error:
            registro.error("No se pudo sincronizar %s: %s", estacion["codigo"], error)
            resumen[estacion["codigo"]] = -1
    return resumen
