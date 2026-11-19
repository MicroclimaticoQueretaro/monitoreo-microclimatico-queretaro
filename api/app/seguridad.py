"""Autenticación de estaciones mediante token (cabecera Authorization: Bearer <token>)."""

import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.db import obtener_conexion

# auto_error=False para devolver nuestro propio mensaje de error en español
esquema_bearer = HTTPBearer(auto_error=False)


def generar_token() -> str:
    """Genera un token aleatorio criptográficamente seguro (256 bits)."""
    return secrets.token_urlsafe(32)


def calcular_hash(token: str) -> str:
    """Hash SHA-256 del token. En la base solo se guarda el hash, nunca el token.

    SHA-256 es suficiente porque el token es aleatorio y largo (no es una contraseña humana).
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def autenticar_estacion(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    conexion: Connection = Depends(obtener_conexion),
) -> dict:
    """Dependencia: devuelve la estación dueña del token o responde 401."""
    error_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token ausente o inválido.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciales is None:
        raise error_401

    hash_recibido = calcular_hash(credenciales.credentials)
    estacion = (
        conexion.execute(
            text(
                "SELECT id, codigo, token_hash FROM estaciones "
                "WHERE token_hash = :hash AND activa"
            ),
            {"hash": hash_recibido},
        )
        .mappings()
        .one_or_none()
    )
    # compare_digest compara en tiempo constante (evita ataques de temporización)
    if estacion is None or not hmac.compare_digest(estacion["token_hash"], hash_recibido):
        raise error_401
    return dict(estacion)
