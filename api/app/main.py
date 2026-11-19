"""Punto de entrada de la API.

Ejecutar en desarrollo (desde la carpeta api/):
    uvicorn app.main:app --reload
Documentación interactiva: http://localhost:8000/docs
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import obtener_configuracion
from app.db import obtener_conexion
from app.rutas import comparacion, estaciones, lecturas

PREFIJO_API = "/api/v1"  # versionar la API permite cambiarla en el futuro sin romper el ESP32

app = FastAPI(
    title="API Monitoreo Microclimático de Querétaro",
    description=(
        "Recibe lecturas de la estación IoT (ESP32) y las compara con la climatología "
        "histórica del reanálisis ERA5-Land (2023-2025)."
    ),
    version="0.1.0",
)

# CORS: solo los orígenes configurados (el dashboard) pueden consultar la API desde un navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=obtener_configuracion().origenes_cors,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(estaciones.router, prefix=PREFIJO_API)
app.include_router(lecturas.router, prefix=PREFIJO_API)
app.include_router(comparacion.router, prefix=PREFIJO_API)


@app.get("/salud", tags=["Sistema"], summary="Verificar que la API y la base de datos respondan")
def salud(conexion: Connection = Depends(obtener_conexion)) -> dict:
    conexion.execute(text("SELECT 1"))
    return {"estado": "ok", "base_de_datos": "ok"}
