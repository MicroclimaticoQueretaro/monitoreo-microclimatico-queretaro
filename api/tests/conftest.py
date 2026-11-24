"""Configuración compartida de las pruebas.

Las pruebas usan la base de datos configurada en .env (debe estar levantada) y
crean estaciones temporales 'PRUEBA-01', 'PRUEBA-02' y 'PRUEBA-03' que se borran al terminar.
Nunca modifican la estación real.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import obtener_motor
from app.main import app
from app.seguridad import calcular_hash, generar_token

CODIGOS_PRUEBA = ("PRUEBA-01", "PRUEBA-02", "PRUEBA-03")


def _borrar_datos_de_prueba(conexion) -> None:
    # Primero las tablas que dependen de estaciones (llaves foráneas), luego las estaciones
    conexion.execute(
        text(
            "DELETE FROM comandos WHERE estacion_id IN "
            "(SELECT id FROM estaciones WHERE codigo = ANY(:codigos))"
        ),
        {"codigos": list(CODIGOS_PRUEBA)},
    )
    conexion.execute(
        text(
            "DELETE FROM modelo_horario WHERE estacion_id IN "
            "(SELECT id FROM estaciones WHERE codigo = ANY(:codigos))"
        ),
        {"codigos": list(CODIGOS_PRUEBA)},
    )
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
                    "INSERT INTO estaciones (codigo, nombre, latitud, longitud, altitud_m, token_hash) "
                    "VALUES (:codigo, 'Estación de prueba', 20.59, -100.39, 1820, :hash)"
                ),
                {"codigo": codigo, "hash": calcular_hash(token)},
            )
    yield tokens_generados
    with obtener_motor().begin() as conexion:
        _borrar_datos_de_prueba(conexion)


@pytest.fixture(scope="session")
def cliente() -> TestClient:
    return TestClient(app)


USUARIO_ADMIN_PRUEBA = "prueba_admin"
CONTRASENA_ADMIN_PRUEBA = "contrasena-de-prueba-123"


@pytest.fixture(scope="session")
def admin_prueba() -> dict:
    """Crea un administrador temporal y lo elimina al final (sus sesiones se borran en cascada)."""
    from app.contrasenas import generar_hash

    with obtener_motor().begin() as conexion:
        conexion.execute(text("DELETE FROM administradores WHERE usuario = :u"), {"u": USUARIO_ADMIN_PRUEBA})
        conexion.execute(
            text("INSERT INTO administradores (usuario, hash_contrasena) VALUES (:u, :h)"),
            {"u": USUARIO_ADMIN_PRUEBA, "h": generar_hash(CONTRASENA_ADMIN_PRUEBA)},
        )
    yield {"usuario": USUARIO_ADMIN_PRUEBA, "contrasena": CONTRASENA_ADMIN_PRUEBA}
    with obtener_motor().begin() as conexion:
        conexion.execute(
            text("UPDATE comandos SET administrador_id = NULL WHERE administrador_id IN "
                 "(SELECT id FROM administradores WHERE usuario = :u)"),
            {"u": USUARIO_ADMIN_PRUEBA},
        )
        conexion.execute(text("DELETE FROM administradores WHERE usuario = :u"), {"u": USUARIO_ADMIN_PRUEBA})
