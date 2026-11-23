"""Pruebas de la descarga del modelo y del cálculo de la brecha térmica.

La API de Open-Meteo se SIMULA con httpx.MockTransport: las pruebas no
dependen de internet y siempre dan el mismo resultado.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import text

from app.db import obtener_motor
from app.modelo import descargar_modelo, guardar_modelo, sincronizar_estaciones

# Hora en punto de hace 3 horas (UTC): siempre en el pasado y dentro de las últimas 24 h
HORA_PRUEBA = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=3)


def respuesta_simulada(peticion: httpx.Request) -> httpx.Response:
    """Imita la respuesta de Open-Meteo con dos horas pasadas y una futura."""
    horas = [HORA_PRUEBA - timedelta(hours=1), HORA_PRUEBA, HORA_PRUEBA + timedelta(days=2)]
    return httpx.Response(
        200,
        json={
            "elevation": float(peticion.url.params.get("elevation", 0)),
            "hourly": {
                "time": [h.strftime("%Y-%m-%dT%H:%M") for h in horas],
                "temperature_2m": [19.0, 20.0, 25.0],
                "relative_humidity_2m": [60, 55, 40],
                "pressure_msl": [1012.0, 1011.5, 1010.0],
                "surface_pressure": [822.0, 821.8, 820.0],
                "shortwave_radiation": [0.0, 9999.0, 800.0],  # 9999 es imposible -> None
            },
        },
    )


@pytest.fixture
def cliente_simulado():
    with httpx.Client(transport=httpx.MockTransport(respuesta_simulada)) as cliente:
        yield cliente


def id_estacion(conexion, codigo: str) -> int:
    return conexion.execute(
        text("SELECT id FROM estaciones WHERE codigo = :codigo"), {"codigo": codigo}
    ).scalar_one()


# --- Descarga ---

def test_descarga_descarta_horas_futuras(cliente_simulado):
    filas = descargar_modelo(cliente_simulado, 20.59, -100.39, 1820)
    assert len(filas) == 2
    assert all(fila["hora"] <= datetime.now(timezone.utc) for fila in filas)


def test_descarga_convierte_valores_imposibles_en_none(cliente_simulado):
    filas = descargar_modelo(cliente_simulado, 20.59, -100.39, 1820)
    fila = next(f for f in filas if f["hora"] == HORA_PRUEBA)
    assert fila["temperatura"] == 20.0
    assert fila["radiacion_wm2"] is None


def test_descarga_envia_la_altitud_de_la_estacion():
    peticiones = []

    def registrar(peticion):
        peticiones.append(peticion)
        return respuesta_simulada(peticion)

    with httpx.Client(transport=httpx.MockTransport(registrar)) as cliente:
        descargar_modelo(cliente, 20.59, -100.39, 1820)
    assert peticiones[0].url.params["elevation"] == "1820"


# --- Guardado ---

def test_guardar_dos_veces_no_duplica(tokens, cliente_simulado):
    filas = descargar_modelo(cliente_simulado, 20.59, -100.39, 1820)
    with obtener_motor().begin() as conexion:
        estacion = id_estacion(conexion, "PRUEBA-01")
        guardar_modelo(conexion, estacion, filas)
        guardar_modelo(conexion, estacion, filas)  # upsert: actualiza en lugar de duplicar
        total = conexion.execute(
            text("SELECT COUNT(*) FROM modelo_horario WHERE estacion_id = :id"), {"id": estacion}
        ).scalar_one()
    assert total == 2


def test_sincronizar_estaciones_continua_si_una_falla(tokens):
    def falla_siempre(peticion):
        return httpx.Response(500)

    with httpx.Client(transport=httpx.MockTransport(falla_siempre)) as cliente:
        with obtener_motor().begin() as conexion:
            resumen = sincronizar_estaciones(conexion, cliente)
    assert resumen["PRUEBA-01"] == -1
    assert resumen["PRUEBA-02"] == -1


# --- Brecha térmica ---

def test_brecha_termica_por_hora(cliente, tokens, cliente_simulado):
    with obtener_motor().begin() as conexion:
        estacion = id_estacion(conexion, "PRUEBA-02")
        guardar_modelo(conexion, estacion, descargar_modelo(cliente_simulado, 20.59, -100.39, 1820))
        # Dos lecturas alrededor de la hora en punto (-20 min y +10 min): ambas cuentan para esa hora
        for minutos, temperatura, lux in [(-20, 22.0, 1200.0), (10, 24.0, 1200.0)]:
            conexion.execute(
                text(
                    "INSERT INTO lecturas (estacion_id, ts, temperatura_bmp, humedad, presion_hpa, "
                    "iluminancia_lux) VALUES (:id, :ts, :t, 50, 823.5, :lux)"
                ),
                {"id": estacion, "ts": HORA_PRUEBA + timedelta(minutes=minutos), "t": temperatura, "lux": lux},
            )

    respuesta = cliente.get("/api/v1/estaciones/PRUEBA-02/brecha?horas=24")
    assert respuesta.status_code == 200
    fila = next(
        f for f in respuesta.json() if datetime.fromisoformat(f["hora"]) == HORA_PRUEBA
    )
    assert fila["lecturas_promediadas"] == 2
    assert fila["temperatura_sensor"] == 23.0             # promedio de 22 y 24
    assert fila["temperatura_modelo"] == 20.0
    assert fila["brecha_termica"] == 3.0                  # 23 - 20: la calle está 3 °C más caliente
    assert fila["diferencia_humedad"] == -5.0             # 50 - 55
    assert fila["presion_nivel_mar_sensor"] == pytest.approx(1011, abs=3)
    assert fila["radiacion_estimada_sensor"] == 10.0      # 1200 lux / 120
    # Con la climatología cargada, la anomalía es sensor menos normal
    if fila["temperatura_normal"] is not None:
        assert fila["anomalia_climatologica"] == round(23.0 - fila["temperatura_normal"], 2)


def test_brecha_estacion_inexistente(cliente):
    assert cliente.get("/api/v1/estaciones/NO-EXISTE/brecha").status_code == 404
