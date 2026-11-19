"""Genera (o renueva) el token de autenticación de una estación.

Uso (desde la carpeta api/):
    python -m scripts.crear_token QRO-CENTRO-01

El token se muestra UNA sola vez: cópielo al archivo de secretos del firmware.
En la base de datos solo se guarda su hash. Ejecutarlo de nuevo invalida el token anterior.
"""

import sys

from sqlalchemy import text

from app.db import obtener_motor
from app.seguridad import calcular_hash, generar_token


def crear_token(codigo_estacion: str) -> str:
    token = generar_token()
    with obtener_motor().begin() as conexion:
        resultado = conexion.execute(
            text("UPDATE estaciones SET token_hash = :hash WHERE codigo = :codigo"),
            {"hash": calcular_hash(token), "codigo": codigo_estacion},
        )
    if resultado.rowcount == 0:
        sys.exit(f"Error: no existe la estación '{codigo_estacion}'.")
    return token


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m scripts.crear_token <CODIGO_ESTACION>")
    token = crear_token(sys.argv[1])
    print(f"Token de la estación {sys.argv[1]} (guárdelo ahora, no se volverá a mostrar):\n{token}")
