"""Comunicación con la estación por MQTT (broker HiveMQ Cloud).

Temas (topics) por estación:
  <prefijo>/<codigo>/comando  -> la API publica "activar" o "detener" (mensaje RETENIDO)
  <prefijo>/<codigo>/estado   -> el ESP32 publica "midiendo", "en_espera" o
                                 "desconectado" (último deseo / LWT), también RETENIDO

Un mensaje "retenido" queda guardado en el broker: quien se suscribe después lo
recibe de inmediato. Así la API no necesita estar conectada todo el tiempo (en el
plan gratuito de Render se duerme) y el ESP32 recibe el último comando al reconectarse.
"""

import json
import secrets
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from app.config import obtener_configuracion

TIEMPO_ESPERA_S = 5.0
CACHE_ESTADO_S = 10.0  # evita conectarse al broker en cada visita al sitio

_cache_estado: dict[str, tuple[float, dict]] = {}
_candado_cache = threading.Lock()


class ErrorMqtt(Exception):
    """El broker no está configurado o no respondió."""


def mqtt_configurado() -> bool:
    return bool(obtener_configuracion().mqtt_host)


def tema(codigo_estacion: str, tipo: str) -> str:
    return f"{obtener_configuracion().mqtt_prefijo}/{codigo_estacion}/{tipo}"


def _crear_cliente() -> mqtt.Client:
    configuracion = obtener_configuracion()
    if not configuracion.mqtt_host:
        raise ErrorMqtt("El broker MQTT no está configurado (MQTT_HOST).")
    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"api-microclima-{secrets.token_hex(4)}",  # único: evita expulsar otra conexión
        protocol=mqtt.MQTTv311,
    )
    if configuracion.mqtt_usuario:
        cliente.username_pw_set(configuracion.mqtt_usuario, configuracion.mqtt_contrasena)
    if configuracion.mqtt_tls:
        cliente.tls_set()  # TLS verificando el certificado del broker con los CA del sistema
    return cliente


def _conectar(cliente: mqtt.Client) -> None:
    configuracion = obtener_configuracion()
    conectado = threading.Event()
    cliente.on_connect = lambda c, u, f, codigo, p: conectado.set() if not codigo.is_failure else None
    try:
        cliente.connect(configuracion.mqtt_host, configuracion.mqtt_puerto, keepalive=30)
    except OSError as error:
        raise ErrorMqtt(f"No se pudo conectar al broker MQTT: {error}") from error
    cliente.loop_start()
    if not conectado.wait(TIEMPO_ESPERA_S):
        cliente.loop_stop()
        raise ErrorMqtt("El broker MQTT rechazó la conexión o no respondió (revisar usuario y contraseña).")


def publicar_comando(codigo_estacion: str, accion: str) -> None:
    """Publica el comando como mensaje retenido, con QoS 1 (entrega confirmada)."""
    cliente = _crear_cliente()
    _conectar(cliente)
    try:
        carga = json.dumps({"accion": accion, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        info = cliente.publish(tema(codigo_estacion, "comando"), carga, qos=1, retain=True)
        info.wait_for_publish(TIEMPO_ESPERA_S)
        if not info.is_published():
            raise ErrorMqtt("El broker no confirmó la publicación del comando.")
    finally:
        cliente.disconnect()
        cliente.loop_stop()
    with _candado_cache:
        _cache_estado.pop(codigo_estacion, None)


def _interpretar(carga: bytes) -> dict:
    """Acepta JSON {"estado": ..., "ts": ...} o texto plano ("midiendo")."""
    texto = carga.decode("utf-8", errors="replace").strip()
    try:
        datos = json.loads(texto)
        if isinstance(datos, dict):
            return {"estado": str(datos.get("estado", "desconocido")), "ts": datos.get("ts")}
    except json.JSONDecodeError:
        pass
    return {"estado": texto or "desconocido", "ts": None}


def leer_estado(codigo_estacion: str) -> dict:
    """Lee el último estado publicado por la estación (mensaje retenido)."""
    with _candado_cache:
        guardado = _cache_estado.get(codigo_estacion)
        if guardado and time.monotonic() - guardado[0] < CACHE_ESTADO_S:
            return guardado[1]

    recibido: dict = {}
    llego = threading.Event()

    def al_recibir(_cliente, _usuario, mensaje):
        recibido.update(_interpretar(mensaje.payload))
        llego.set()

    cliente = _crear_cliente()
    cliente.on_message = al_recibir
    _conectar(cliente)
    try:
        cliente.subscribe(tema(codigo_estacion, "estado"), qos=1)
        # Si nunca se publicó un estado, no llega nada: se responde "desconocido"
        llego.wait(3.0)
    finally:
        cliente.disconnect()
        cliente.loop_stop()

    resultado = recibido or {"estado": "desconocido", "ts": None}
    with _candado_cache:
        _cache_estado[codigo_estacion] = (time.monotonic(), resultado)
    return resultado
