"""Pruebas de la ventana anclada a la última lectura y de la brecha minuto a minuto.

Usan la estación PRUEBA-03, que solo tiene las lecturas creadas aquí (hace ~3 horas):
así se simula una estación que dejó de medir.
"""

from datetime import datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from app.db import obtener_motor
from app.modelo import descargar_modelo, guardar_modelo
from tests.test_modelo import HORA_PRUEBA, id_estacion, respuesta_simulada

# Modelo simulado: 19.0 °C a HORA_PRUEBA - 1 h y 20.0 °C a HORA_PRUEBA
LECTURAS = [
    (-30, 21.0),  # media hora entre las dos horas del modelo -> modelo interpolado 19.5
    (15, 22.0),   # después de la última hora del modelo -> se usa la de HORA_PRUEBA (20.0)
]


@pytest.fixture(scope="module")
def estacion_detenida(tokens):
    with httpx.Client(transport=httpx.MockTransport(respuesta_simulada)) as cliente_http:
        filas_modelo = descargar_modelo(cliente_http, 20.59, -100.39, 1820)
    with obtener_motor().begin() as conexion:
        estacion = id_estacion(conexion, "PRUEBA-03")
        guardar_modelo(conexion, estacion, filas_modelo)
        for minutos, temperatura in LECTURAS:
            conexion.execute(
                text(
                    "INSERT INTO lecturas (estacion_id, ts, temperatura_bmp, humedad) "
                    "VALUES (:id, :ts, :t, 50)"
                ),
                {"id": estacion, "ts": HORA_PRUEBA + timedelta(minutes=minutos), "t": temperatura},
            )
    return "PRUEBA-03"


def test_lecturas_ancladas_a_la_ultima(cliente, estacion_detenida):
    # La última lectura fue hace casi 3 horas: con "ahora - 1 h" no habría nada,
    # pero la ventana termina en la última lectura y devuelve las dos
    respuesta = cliente.get(f"/api/v1/estaciones/{estacion_detenida}/lecturas?horas=1")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 2


def test_brecha_por_hora_anclada(cliente, estacion_detenida):
    respuesta = cliente.get(f"/api/v1/estaciones/{estacion_detenida}/brecha?horas=1")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) >= 1


def test_brecha_por_minuto_interpola_el_modelo(cliente, estacion_detenida):
    respuesta = cliente.get(f"/api/v1/estaciones/{estacion_detenida}/brecha/minutos?horas=3")
    assert respuesta.status_code == 200
    filas = {datetime.fromisoformat(f["ts"]): f for f in respuesta.json()}

    media_hora = filas[HORA_PRUEBA - timedelta(minutes=30)]
    assert media_hora["temperatura_modelo"] == 19.5    # 19.0 + (20.0 - 19.0) * 0.5
    assert media_hora["brecha_termica"] == 1.5         # 21.0 - 19.5

    sin_hora_siguiente = filas[HORA_PRUEBA + timedelta(minutes=15)]
    assert sin_hora_siguiente["temperatura_modelo"] == 20.0
    assert sin_hora_siguiente["brecha_termica"] == 2.0


def test_brecha_por_minuto_ordena_de_mas_reciente_a_mas_antigua(cliente, estacion_detenida):
    instantes = [f["ts"] for f in cliente.get(f"/api/v1/estaciones/{estacion_detenida}/brecha/minutos").json()]
    assert instantes == sorted(instantes, reverse=True)


def test_brecha_por_minuto_limita_las_horas(cliente, estacion_detenida):
    assert cliente.get(f"/api/v1/estaciones/{estacion_detenida}/brecha/minutos?horas=500").status_code == 422
