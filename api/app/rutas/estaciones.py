"""Rutas de consulta de estaciones."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.db import obtener_conexion
from app.esquemas import Estacion

router = APIRouter(tags=["Estaciones"])

# Columnas públicas: el token_hash NUNCA se devuelve
COLUMNAS_PUBLICAS = "id, codigo, nombre, latitud, longitud, altitud_m, activa"


def obtener_estacion_o_404(conexion: Connection, codigo: str) -> dict:
    """Busca una estación por código; responde 404 si no existe."""
    estacion = (
        conexion.execute(
            text(f"SELECT {COLUMNAS_PUBLICAS} FROM estaciones WHERE codigo = :codigo"),
            {"codigo": codigo},
        )
        .mappings()
        .one_or_none()
    )
    if estacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estación no encontrada.")
    return dict(estacion)


@router.get("/estaciones", response_model=list[Estacion], summary="Listar estaciones")
def listar_estaciones(conexion: Connection = Depends(obtener_conexion)) -> list[Estacion]:
    filas = conexion.execute(
        text(f"SELECT {COLUMNAS_PUBLICAS} FROM estaciones ORDER BY codigo")
    ).mappings()
    return [Estacion(**fila) for fila in filas]
