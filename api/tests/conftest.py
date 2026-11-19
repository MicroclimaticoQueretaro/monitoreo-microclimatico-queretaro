"""Configuración compartida de las pruebas.

Las pruebas usan la base de datos configurada en .env (debe estar levantada) y
crean estaciones temporales 'PRUEBA-01' y 'PRUEBA-02' que se borran al terminar.
Nunca modifican la estación real.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import obtener_motor
from app.main import app
from app.seguridad import calcular_hash, generar_token

CODIGOS_PRUEBA = ("PRUEBA-01", "PRUEBA-02")


def _borrar_datos_de_prueba(conexion) -> None:
    conexion.execute(
        text(
            "DELETE FROM lecturas WHERE estacion_id IN "
            "(SELECT id FROM estaciones WHERE codigo = ANY(:codigos))"
        ),
        {"codigos": list(CODIGOS_PRUEBA)},
    )
    conexion.execute(
        text("DELETE FROM estaciones WHERE codigo = ANY(:codigos)"),
        {"codigos": list(CODIGOS_PRUEBA)},
    )


@pytest.fixture(scope="session")
def tokens() -> dict[str, str]:
    """Crea las estaciones de prueba con su token y las elimina al final."""
    tokens_generados = {codigo: generar_token() for codigo in CODIGOS_PRUEBA}
    with obtener_motor().begin() as conexion:
        _borrar_datos_de_prueba(conexion)
        for codigo, token in tokens_generados.items():
            conexion.execute(
                text(
                    "INSERT INTO estaciones (codigo, nombre, latitud, longitud, token_hash) "
                    "VALUES (:codigo, 'Estación de prueba', 20.59, -100.39, :hash)"
                ),
                {"codigo": codigo, "hash": calcular_hash(token)},
            )
    yield tokens_generados
    with obtener_motor().begin() as conexion:
        _borrar_datos_de_prueba(conexion)


@pytest.fixture(scope="session")
def cliente() -> TestClient:
    return TestClient(app)
