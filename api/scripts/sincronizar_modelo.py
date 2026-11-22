"""Sincroniza los datos del modelo meteorológico (Open-Meteo) con la base de datos.

Uso (desde la carpeta api/):
    python -m scripts.sincronizar_modelo              # una sola vez
    python -m scripts.sincronizar_modelo --continuo   # cada N minutos, sin parar

En Docker se ejecuta en modo continuo como el servicio "sincronizador".
"""

import argparse
import logging
import time

import httpx

from app.config import obtener_configuracion
from app.db import obtener_motor
from app.modelo import sincronizar_estaciones

registro = logging.getLogger("sincronizador")


def ejecutar_una_vez() -> None:
    with httpx.Client() as cliente, obtener_motor().begin() as conexion:
        resumen = sincronizar_estaciones(conexion, cliente)
    for codigo, horas in resumen.items():
        if horas >= 0:
            registro.info("Estación %s: %d horas del modelo actualizadas.", codigo, horas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza el modelo meteorológico.")
    parser.add_argument("--continuo", action="store_true", help="Repetir cada N minutos.")
    argumentos = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    intervalo_minutos = obtener_configuracion().intervalo_sincronizacion_minutos

    while True:
        try:
            ejecutar_una_vez()
        except Exception:  # noqa: BLE001 - en modo continuo un error no debe detener el servicio
            registro.exception("Falló la sincronización; se reintentará en el próximo ciclo.")
        if not argumentos.continuo:
            break
        registro.info("Próxima sincronización en %d minutos.", intervalo_minutos)
        time.sleep(intervalo_minutos * 60)


if __name__ == "__main__":
    main()
