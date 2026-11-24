"""Pruebas de las contraseñas y del inicio de sesión de administradores."""

import pytest

from app.contrasenas import generar_hash, verificar
from app.rutas import admin as modulo_admin


@pytest.fixture(autouse=True)
def limpiar_intentos():
    """Cada prueba empieza sin intentos fallidos registrados."""
    modulo_admin._intentos_fallidos.clear()
    yield
    modulo_admin._intentos_fallidos.clear()


def iniciar_sesion(cliente, usuario, contrasena):
    return cliente.post("/api/v1/admin/login", json={"usuario": usuario, "contrasena": contrasena})


# --- Contraseñas ---

def test_hash_de_contrasena_se_verifica():
    hash_guardado = generar_hash("una-contrasena-larga")
    assert verificar("una-contrasena-larga", hash_guardado)
    assert not verificar("otra-contrasena", hash_guardado)


def test_misma_contrasena_genera_hashes_distintos():
    # Gracias a la sal aleatoria
    assert generar_hash("una-contrasena-larga") != generar_hash("una-contrasena-larga")


def test_contrasena_corta_se_rechaza():
    with pytest.raises(ValueError):
        generar_hash("corta")


def test_hash_invalido_no_se_acepta():
    assert not verificar("lo-que-sea", "texto-que-no-es-un-hash")


# --- Inicio de sesión ---

def test_login_correcto_entrega_token(cliente, admin_prueba):
    respuesta = iniciar_sesion(cliente, admin_prueba["usuario"], admin_prueba["contrasena"])
    assert respuesta.status_code == 200
    assert respuesta.json()["token"]


def test_login_con_contrasena_incorrecta(cliente, admin_prueba):
    assert iniciar_sesion(cliente, admin_prueba["usuario"], "incorrecta-123").status_code == 401


def test_login_usuario_inexistente_da_el_mismo_error(cliente, admin_prueba):
    respuesta = iniciar_sesion(cliente, "no_existe", "cualquiera-123")
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario o contraseña incorrectos."


def test_bloqueo_tras_demasiados_intentos(cliente, admin_prueba):
    for _ in range(5):
        iniciar_sesion(cliente, admin_prueba["usuario"], "incorrecta-123")
    # Incluso con la contraseña correcta, la IP queda bloqueada un tiempo
    respuesta = iniciar_sesion(cliente, admin_prueba["usuario"], admin_prueba["contrasena"])
    assert respuesta.status_code == 429


def test_sesion_y_cierre_de_sesion(cliente, admin_prueba):
    token = iniciar_sesion(cliente, admin_prueba["usuario"], admin_prueba["contrasena"]).json()["token"]
    cabecera = {"Authorization": f"Bearer {token}"}
    assert cliente.get("/api/v1/admin/sesion", headers=cabecera).json()["usuario"] == admin_prueba["usuario"]
    assert cliente.post("/api/v1/admin/logout", headers=cabecera).status_code == 204
    # Después de cerrar sesión, el token ya no sirve
    assert cliente.get("/api/v1/admin/sesion", headers=cabecera).status_code == 401


def test_sesion_sin_token(cliente):
    assert cliente.get("/api/v1/admin/sesion").status_code == 401
