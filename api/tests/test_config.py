"""Pruebas de la configuración de conexión (local y nube)."""

import pytest
from pydantic import ValidationError

from app.config import Configuracion


def test_database_url_de_la_nube_usa_el_driver_psycopg(monkeypatch):
    configuracion = Configuracion(
        _env_file=None,
        database_url="postgresql://usuario:clave@ep-ejemplo.neon.tech/microclima?sslmode=require",
    )
    url = configuracion.url_base_datos
    assert url.drivername == "postgresql+psycopg"
    assert url.host == "ep-ejemplo.neon.tech"
    assert url.query["sslmode"] == "require"


def test_sin_datos_de_conexion_da_error(monkeypatch):
    for variable in ["DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]:
        monkeypatch.delenv(variable, raising=False)
    with pytest.raises(ValidationError):
        Configuracion(_env_file=None)
