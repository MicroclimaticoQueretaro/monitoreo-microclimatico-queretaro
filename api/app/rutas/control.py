"""Control remoto de la estación: estado (público) y comandos activar/detener (solo admin)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.db import obtener_conexion
from app.esquemas import ComandoEstacion, EstadoEstacion, RegistroComando
from app.mqtt import ErrorMqtt, leer_estado, mqtt_configurado, publicar_comando
from app.rutas.admin import autenticar_admin
from app.rutas.estaciones import obtener_estacion_o_404

router = APIRouter(tags=["Control de la estación"])


@router.get(
    "/estaciones/{codigo}/estado",
    response_model=EstadoEstacion,
    summary="Estado informado por la estación (midiendo, en espera o desconectada)",
)
def consultar_estado(codigo: str, conexion: Connection = Depends(obtener_conexion)) -> EstadoEstacion:
    obtener_estacion_o_404(conexion, codigo)
    if not mqtt_configurado():
        return EstadoEstacion(estado="desconocido", ts=None, control_remoto=False)
    try:
        estado = leer_estado(codigo)
    except ErrorMqtt:
        return EstadoEstacion(estado="desconocido", ts=None, control_remoto=True)
    return EstadoEstacion(estado=estado["estado"], ts=estado["ts"], control_remoto=True)


@router.post(
    "/estaciones/{codigo}/comando",
    response_model=RegistroComando,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Activar o detener la estación (requiere sesión de administrador)",
)
def enviar_comando(
    codigo: str,
    comando: ComandoEstacion,
    administrador: dict = Depends(autenticar_admin),
    conexion: Connection = Depends(obtener_conexion),
) -> RegistroComando:
    estacion = obtener_estacion_o_404(conexion, codigo)
    try:
        publicar_comando(codigo, comando.accion)
    except ErrorMqtt as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error

    # Registro de auditoría: quién envió qué y cuándo
    fila = conexion.execute(
        text(
            "INSERT INTO comandos (estacion_id, administrador_id, accion) VALUES (:e, :a, :accion) "
            "RETURNING accion, enviado_en"
        ),
        {"e": estacion["id"], "a": administrador["id"], "accion": comando.accion},
    ).mappings().one()
    return RegistroComando(accion=fila["accion"], enviado_en=fila["enviado_en"], usuario=administrador["usuario"])


@router.get(
    "/estaciones/{codigo}/comandos",
    response_model=list[RegistroComando],
    summary="Historial de comandos enviados (requiere sesión de administrador)",
)
def historial_comandos(
    codigo: str,
    limite: int = Query(default=10, ge=1, le=100),
    _administrador: dict = Depends(autenticar_admin),
    conexion: Connection = Depends(obtener_conexion),
) -> list[RegistroComando]:
    estacion = obtener_estacion_o_404(conexion, codigo)
    filas = conexion.execute(
        text(
            "SELECT c.accion, c.enviado_en, a.usuario FROM comandos c "
            "LEFT JOIN administradores a ON a.id = c.administrador_id "
            "WHERE c.estacion_id = :e ORDER BY c.enviado_en DESC LIMIT :limite"
        ),
        {"e": estacion["id"], "limite": limite},
    ).mappings()
    return [RegistroComando(**fila) for fila in filas]
