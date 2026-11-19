"""Conexión a PostgreSQL compartida por toda la API."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

from app.config import obtener_configuracion


@lru_cache
def obtener_motor() -> Engine:
    """Crea un único motor con un grupo (pool) de conexiones reutilizables."""
    # pool_pre_ping verifica que la conexión siga viva antes de usarla
    return create_engine(obtener_configuracion().url_base_datos, pool_pre_ping=True)


def obtener_conexion() -> Iterator[Connection]:
    """Dependencia de FastAPI: abre una transacción por petición y la cierra al terminar.

    Si la petición termina sin errores se confirma (commit); si hay un error, se deshace (rollback).
    """
    with obtener_motor().begin() as conexion:
        yield conexion
