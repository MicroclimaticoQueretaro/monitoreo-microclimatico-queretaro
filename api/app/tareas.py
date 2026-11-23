"""Tarea en segundo plano: sincroniza el modelo meteorológico desde la propia API.

Se activa con SINCRONIZAR_EN_API=true. Se usa en la nube porque el plan gratuito
de Render permite un solo servicio web; en local lo hace el servicio "sincronizador".
"""

import logging
import threading

import httpx

from app.config import obtener_configuracion
from app.db import obtener_motor
from app.modelo import sincronizar_estaciones

registro = logging.getLogger("uvicorn.error")


def _ciclo_sincronizacion(evento_parada: threading.Event) -> None:
    intervalo_s = obtener_configuracion().intervalo_sincronizacion_minutos * 60
    while not evento_parada.is_set():
        try:
            with httpx.Client() as cliente, obtener_motor().begin() as conexion:
                resumen = sincronizar_estaciones(conexion, cliente)
            registro.info("Modelo sincronizado: %s", resumen)
        except Exception:  # noqa: BLE001 - un error no debe detener la API
            registro.exception("Falló la sincronización del modelo; se reintentará.")
        # wait() en lugar de sleep(): permite detener el hilo al apagar la API
        evento_parada.wait(intervalo_s)


def iniciar_sincronizacion() -> threading.Event:
    """Lanza el hilo de sincronización y devuelve el evento para detenerlo."""
    evento_parada = threading.Event()
    hilo = threading.Thread(
        target=_ciclo_sincronizacion, args=(evento_parada,), name="sincronizador", daemon=True
    )
    hilo.start()
    return evento_parada
