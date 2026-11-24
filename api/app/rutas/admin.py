"""Inicio y cierre de sesión de administradores."""

import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import obtener_configuracion
from app.contrasenas import HASH_FICTICIO, verificar
from app.db import obtener_conexion
from app.esquemas import CredencialesAdmin, SesionAdmin

router = APIRouter(prefix="/admin", tags=["Administración"])
esquema_bearer = HTTPBearer(auto_error=False)

# Intentos fallidos de inicio de sesión por IP (en memoria; la API corre en una sola instancia)
_intentos_fallidos: dict[str, deque] = defaultdict(deque)
_candado = threading.Lock()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ip_cliente(peticion: Request) -> str:
    return peticion.client.host if peticion.client else "desconocida"


def _demasiados_intentos(ip: str) -> bool:
    configuracion = obtener_configuracion()
    limite = time.monotonic() - configuracion.ventana_intentos_minutos * 60
    with _candado:
        intentos = _intentos_fallidos[ip]
        while intentos and intentos[0] < limite:
            intentos.popleft()
        return len(intentos) >= configuracion.intentos_login_maximos


def _registrar_fallo(ip: str) -> None:
    with _candado:
        _intentos_fallidos[ip].append(time.monotonic())


def autenticar_admin(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    conexion: Connection = Depends(obtener_conexion),
) -> dict:
    """Dependencia: devuelve el administrador de la sesión o responde 401."""
    error_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión inválida o expirada. Inicie sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciales is None:
        raise error_401
    fila = conexion.execute(
        text(
            "SELECT a.id, a.usuario, s.expira_en, s.token_hash FROM sesiones_admin s "
            "JOIN administradores a ON a.id = s.administrador_id "
            "WHERE s.token_hash = :hash AND s.expira_en > now() AND a.activo"
        ),
        {"hash": _hash_token(credenciales.credentials)},
    ).mappings().one_or_none()
    if fila is None:
        raise error_401
    return dict(fila)


@router.post("/login", response_model=SesionAdmin, summary="Iniciar sesión de administrador")
def iniciar_sesion(
    credenciales: CredencialesAdmin,
    peticion: Request,
    conexion: Connection = Depends(obtener_conexion),
) -> SesionAdmin:
    ip = _ip_cliente(peticion)
    if _demasiados_intentos(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Espere unos minutos e intente de nuevo.",
        )

    administrador = conexion.execute(
        text("SELECT id, usuario, hash_contrasena FROM administradores WHERE usuario = :u AND activo"),
        {"u": credenciales.usuario.lower()},
    ).mappings().one_or_none()

    # Se verifica SIEMPRE (con un hash ficticio si el usuario no existe) para no revelar
    # por el tiempo de respuesta qué usuarios existen
    hash_guardado = administrador["hash_contrasena"] if administrador else HASH_FICTICIO
    if not verificar(credenciales.contrasena, hash_guardado) or administrador is None:
        _registrar_fallo(ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos.")

    token = secrets.token_urlsafe(32)
    expira_en = datetime.now(timezone.utc) + timedelta(hours=obtener_configuracion().duracion_sesion_horas)
    # Limpieza: se borran las sesiones vencidas
    conexion.execute(text("DELETE FROM sesiones_admin WHERE expira_en < now()"))
    conexion.execute(
        text("INSERT INTO sesiones_admin (token_hash, administrador_id, expira_en) VALUES (:h, :id, :exp)"),
        {"h": _hash_token(token), "id": administrador["id"], "exp": expira_en},
    )
    return SesionAdmin(token=token, usuario=administrador["usuario"], expira_en=expira_en)


@router.get("/sesion", response_model=SesionAdmin, summary="Verificar la sesión actual")
def ver_sesion(administrador: dict = Depends(autenticar_admin)) -> SesionAdmin:
    return SesionAdmin(token=None, usuario=administrador["usuario"], expira_en=administrador["expira_en"])


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
def cerrar_sesion(
    administrador: dict = Depends(autenticar_admin),
    conexion: Connection = Depends(obtener_conexion),
) -> None:
    conexion.execute(text("DELETE FROM sesiones_admin WHERE token_hash = :h"), {"h": administrador["token_hash"]})
