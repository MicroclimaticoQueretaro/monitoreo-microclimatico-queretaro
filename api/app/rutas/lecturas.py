"""Rutas para recibir lecturas del ESP32 y consultarlas."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.config import obtener_configuracion
from app.db import obtener_conexion
from app.esquemas import Lectura, LecturaCreada, LecturaEntrada
from app.rutas.estaciones import obtener_estacion_o_404
from app.seguridad import autenticar_estacion
from app.ventana import CTE_VENTANA, FILTRO_VENTANA

router = APIRouter(tags=["Lecturas"])


@router.post(
    "/lecturas",
    response_model=LecturaCreada,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una lectura del sensor (requiere token)",
)
def registrar_lectura(
    lectura: LecturaEntrada,
    estacion: dict = Depends(autenticar_estacion),
    conexion: Connection = Depends(obtener_conexion),
) -> LecturaCreada:
    # Un token solo puede escribir datos de su propia estación
    if lectura.estacion != estacion["codigo"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El token no corresponde a la estación indicada.",
        )

    # Rechaza lecturas del futuro (reloj del ESP32 desincronizado)
    tolerancia = timedelta(minutes=obtener_configuracion().tolerancia_futuro_minutos)
    if lectura.ts > datetime.now(timezone.utc) + tolerancia:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha de la lectura está en el futuro. Revise el reloj (NTP) del ESP32.",
        )

    # Consulta parametrizada (:nombre): nunca se concatenan valores en el SQL (evita inyección SQL)
    try:
        # Savepoint: si la inserción falla, solo se deshace esta parte de la transacción
        with conexion.begin_nested():
            conexion.execute(
                text(
                    "INSERT INTO lecturas (estacion_id, ts, temperatura_dht, temperatura_bmp, "
                    "humedad, presion_hpa, iluminancia_lux) "
                    "VALUES (:estacion_id, :ts, :temperatura_dht, :temperatura_bmp, "
                    ":humedad, :presion_hpa, :iluminancia_lux)"
                ),
                {"estacion_id": estacion["id"], **lectura.model_dump(exclude={"estacion"})},
            )
    except IntegrityError:
        # La clave primaria (estacion_id, ts) impide registrar dos veces el mismo instante
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una lectura de esta estación en ese instante.",
        )

    return LecturaCreada(mensaje="Lectura registrada.", estacion=lectura.estacion, ts=lectura.ts)


@router.get(
    "/estaciones/{codigo}/lecturas",
    response_model=list[Lectura],
    summary="Consultar las lecturas más recientes de una estación",
    description="Devuelve las lecturas de las N horas que terminan en la última lectura registrada.",
)
def listar_lecturas(
    codigo: str,
    horas: int = Query(default=24, ge=1, le=24 * 31, description="Ventana de tiempo hacia atrás."),
    limite: int = Query(default=1000, ge=1, le=10000, description="Máximo de registros."),
    conexion: Connection = Depends(obtener_conexion),
) -> list[Lectura]:
    estacion = obtener_estacion_o_404(conexion, codigo)
    filas = conexion.execute(
        text(
            f"WITH {CTE_VENTANA} "
            "SELECT ts, temperatura_dht, temperatura_bmp, humedad, presion_hpa, iluminancia_lux "
            "FROM lecturas "
            f"WHERE estacion_id = :estacion_id AND {FILTRO_VENTANA} "
            "ORDER BY ts DESC LIMIT :limite"
        ),
        {"estacion_id": estacion["id"], "horas": horas, "limite": limite},
    ).mappings()
    return [Lectura(**fila) for fila in filas]
