"""Pruebas de la API: seguridad, validación y consultas."""

from datetime import datetime, timedelta, timezone
from itertools import count

# Contador para que cada lectura de prueba tenga un instante distinto
_minutos = count(start=1)


def lectura_valida(**cambios) -> dict:
    """Lectura de ejemplo que cumple el contrato; los parámetros sobrescriben campos."""
    instante = datetime.now(timezone(timedelta(hours=-6))) - timedelta(minutes=next(_minutos))
    lectura = {
        "estacion": "PRUEBA-01",
        "ts": instante.isoformat(),
        "temperatura_dht": 24.0,
        "temperatura_bmp": 23.6,
        "humedad": 41.0,
        "presion_hpa": 812.4,
        "iluminancia_lux": 35200.0,
    }
    lectura.update(cambios)
    return lectura


def cabecera(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- Sistema ---

def test_salud(cliente):
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "base_de_datos": "ok"}


# --- Seguridad ---

def test_rechaza_lectura_sin_token(cliente, tokens):
    assert cliente.post("/api/v1/lecturas", json=lectura_valida()).status_code == 401


def test_rechaza_token_falso(cliente, tokens):
    respuesta = cliente.post(
        "/api/v1/lecturas", json=lectura_valida(), headers=cabecera("token-inventado")
    )
    assert respuesta.status_code == 401


def test_rechaza_token_de_otra_estacion(cliente, tokens):
    # Token de PRUEBA-02 intentando escribir datos de PRUEBA-01
    respuesta = cliente.post(
        "/api/v1/lecturas", json=lectura_valida(), headers=cabecera(tokens["PRUEBA-02"])
    )
    assert respuesta.status_code == 403


def test_listado_de_estaciones_no_expone_token(cliente, tokens):
    respuesta = cliente.get("/api/v1/estaciones")
    assert respuesta.status_code == 200
    assert all("token_hash" not in estacion for estacion in respuesta.json())


# --- Registro y validación ---

def test_registra_lectura_valida(cliente, tokens):
    respuesta = cliente.post(
        "/api/v1/lecturas", json=lectura_valida(), headers=cabecera(tokens["PRUEBA-01"])
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["estacion"] == "PRUEBA-01"


def test_rechaza_lectura_duplicada(cliente, tokens):
    lectura = lectura_valida()
    primera = cliente.post("/api/v1/lecturas", json=lectura, headers=cabecera(tokens["PRUEBA-01"]))
    segunda = cliente.post("/api/v1/lecturas", json=lectura, headers=cabecera(tokens["PRUEBA-01"]))
    assert primera.status_code == 201
    assert segunda.status_code == 409


def test_rechaza_valores_fuera_de_rango(cliente, tokens):
    for campo, valor in [("temperatura_dht", 99), ("humedad", 150), ("presion_hpa", 50)]:
        respuesta = cliente.post(
            "/api/v1/lecturas",
            json=lectura_valida(**{campo: valor}),
            headers=cabecera(tokens["PRUEBA-01"]),
        )
        assert respuesta.status_code == 422, campo


def test_rechaza_fecha_sin_zona_horaria(cliente, tokens):
    respuesta = cliente.post(
        "/api/v1/lecturas",
        json=lectura_valida(ts="2026-11-19T14:30:00"),
        headers=cabecera(tokens["PRUEBA-01"]),
    )
    assert respuesta.status_code == 422


def test_rechaza_fecha_en_el_futuro(cliente, tokens):
    futuro = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    respuesta = cliente.post(
        "/api/v1/lecturas", json=lectura_valida(ts=futuro), headers=cabecera(tokens["PRUEBA-01"])
    )
    assert respuesta.status_code == 422


def test_rechaza_campos_desconocidos(cliente, tokens):
    respuesta = cliente.post(
        "/api/v1/lecturas",
        json=lectura_valida(temperatura=25),
        headers=cabecera(tokens["PRUEBA-01"]),
    )
    assert respuesta.status_code == 422


def test_rechaza_lectura_sin_mediciones(cliente, tokens):
    vacia = {"estacion": "PRUEBA-01", "ts": lectura_valida()["ts"]}
    respuesta = cliente.post("/api/v1/lecturas", json=vacia, headers=cabecera(tokens["PRUEBA-01"]))
    assert respuesta.status_code == 422


# --- Consultas ---

def test_consulta_lecturas(cliente, tokens):
    cliente.post("/api/v1/lecturas", json=lectura_valida(), headers=cabecera(tokens["PRUEBA-01"]))
    respuesta = cliente.get("/api/v1/estaciones/PRUEBA-01/lecturas?horas=24")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) >= 1


def test_estacion_inexistente_devuelve_404(cliente):
    assert cliente.get("/api/v1/estaciones/NO-EXISTE/lecturas").status_code == 404


def test_comparacion_calcula_anomalia(cliente, tokens):
    lectura = lectura_valida(temperatura_bmp=30.0)
    cliente.post("/api/v1/lecturas", json=lectura, headers=cabecera(tokens["PRUEBA-01"]))
    respuesta = cliente.get("/api/v1/estaciones/PRUEBA-01/comparacion?horas=24")
    assert respuesta.status_code == 200
    # Busca la fila de esta lectura comparando instantes (no el texto, que puede cambiar de formato)
    instante = datetime.fromisoformat(lectura["ts"])
    fila = next(f for f in respuesta.json() if datetime.fromisoformat(f["ts"]) == instante)
    assert fila["temperatura_sensor"] == 30.0
    # Si la climatología está cargada, la anomalía debe ser sensor - normal
    if fila["temperatura_normal"] is not None:
        assert round(30.0 - fila["temperatura_normal"], 2) == fila["anomalia_temperatura"]
