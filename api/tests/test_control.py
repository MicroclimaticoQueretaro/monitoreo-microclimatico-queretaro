"""Pruebas del control remoto por MQTT.

Necesitan un broker MQTT local sin TLS en localhost:1883 (por ejemplo Mosquitto).
Si no hay broker disponible, las pruebas que lo requieren se omiten.
"""

import json
import socket
import threading

import paho.mqtt.client as mqtt
import pytest

from app import mqtt as modulo_mqtt
from app.config import obtener_configuracion
from app.rutas import admin as modulo_admin

PUERTO_BROKER = 1883


def hay_broker_local() -> bool:
    try:
        with socket.create_connection(("localhost", PUERTO_BROKER), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture
def broker(monkeypatch):
    if not hay_broker_local():
        pytest.skip("No hay un broker MQTT local en localhost:1883")
    configuracion = obtener_configuracion()
    monkeypatch.setattr(configuracion, "mqtt_host", "localhost")
    monkeypatch.setattr(configuracion, "mqtt_puerto", PUERTO_BROKER)
    monkeypatch.setattr(configuracion, "mqtt_tls", False)
    monkeypatch.setattr(configuracion, "mqtt_prefijo", "prueba-microclima")
    modulo_mqtt._cache_estado.clear()
    yield
    modulo_mqtt._cache_estado.clear()


@pytest.fixture
def cabecera_admin(cliente, admin_prueba):
    modulo_admin._intentos_fallidos.clear()
    respuesta = cliente.post(
        "/api/v1/admin/login",
        json={"usuario": admin_prueba["usuario"], "contrasena": admin_prueba["contrasena"]},
    )
    return {"Authorization": f"Bearer {respuesta.json()['token']}"}


def leer_retenido(tema: str) -> dict | None:
    """Se suscribe como lo haría el ESP32 y devuelve el mensaje retenido del tema."""
    recibido = {}
    llego = threading.Event()
    cliente = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    cliente.on_message = lambda c, u, m: (recibido.update(json.loads(m.payload)), llego.set())
    cliente.connect("localhost", PUERTO_BROKER)
    cliente.subscribe(tema, qos=1)
    cliente.loop_start()
    llego.wait(3)
    cliente.loop_stop()
    cliente.disconnect()
    return recibido or None


def publicar_retenido(tema: str, carga: dict) -> None:
    """Simula a la estación publicando su estado."""
    cliente = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    cliente.connect("localhost", PUERTO_BROKER)
    cliente.loop_start()
    cliente.publish(tema, json.dumps(carga), qos=1, retain=True).wait_for_publish(3)
    cliente.loop_stop()
    cliente.disconnect()


# --- Seguridad ---

def test_comando_sin_sesion_es_rechazado(cliente, tokens):
    respuesta = cliente.post("/api/v1/estaciones/PRUEBA-01/comando", json={"accion": "activar"})
    assert respuesta.status_code == 401


def test_comando_invalido_es_rechazado(cliente, tokens, cabecera_admin):
    respuesta = cliente.post(
        "/api/v1/estaciones/PRUEBA-01/comando", json={"accion": "explotar"}, headers=cabecera_admin
    )
    assert respuesta.status_code == 422


def test_token_de_estacion_no_sirve_como_admin(cliente, tokens):
    respuesta = cliente.post(
        "/api/v1/estaciones/PRUEBA-01/comando",
        json={"accion": "activar"},
        headers={"Authorization": f"Bearer {tokens['PRUEBA-01']}"},
    )
    assert respuesta.status_code == 401


# --- Comandos por MQTT ---

def test_activar_publica_comando_retenido(cliente, tokens, cabecera_admin, broker):
    respuesta = cliente.post(
        "/api/v1/estaciones/PRUEBA-01/comando", json={"accion": "activar"}, headers=cabecera_admin
    )
    assert respuesta.status_code == 202
    mensaje = leer_retenido("prueba-microclima/PRUEBA-01/comando")
    assert mensaje["accion"] == "activar"


def test_comando_queda_en_el_historial(cliente, tokens, cabecera_admin, broker):
    cliente.post("/api/v1/estaciones/PRUEBA-01/comando", json={"accion": "detener"}, headers=cabecera_admin)
    historial = cliente.get("/api/v1/estaciones/PRUEBA-01/comandos", headers=cabecera_admin).json()
    assert historial[0]["accion"] == "detener"
    assert historial[0]["usuario"] == "prueba_admin"


def test_broker_caido_responde_503(cliente, tokens, cabecera_admin, monkeypatch):
    configuracion = obtener_configuracion()
    monkeypatch.setattr(configuracion, "mqtt_host", "localhost")
    monkeypatch.setattr(configuracion, "mqtt_puerto", 1)  # puerto sin broker
    monkeypatch.setattr(configuracion, "mqtt_tls", False)
    respuesta = cliente.post(
        "/api/v1/estaciones/PRUEBA-01/comando", json={"accion": "activar"}, headers=cabecera_admin
    )
    assert respuesta.status_code == 503


# --- Estado informado por la estación ---

def test_estado_publicado_por_la_estacion(cliente, tokens, broker):
    publicar_retenido("prueba-microclima/PRUEBA-02/estado", {"estado": "en_espera", "ts": "2026-11-23T20:00:00Z"})
    respuesta = cliente.get("/api/v1/estaciones/PRUEBA-02/estado").json()
    assert respuesta["estado"] == "en_espera"
    assert respuesta["control_remoto"] is True


def test_estado_sin_mqtt_configurado(cliente, tokens, monkeypatch):
    monkeypatch.setattr(obtener_configuracion(), "mqtt_host", None)
    respuesta = cliente.get("/api/v1/estaciones/PRUEBA-01/estado").json()
    assert respuesta == {"estado": "desconocido", "ts": None, "control_remoto": False}
