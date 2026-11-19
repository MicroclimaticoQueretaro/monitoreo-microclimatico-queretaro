"""
Carga el histórico ERA5-Land tratado en PostgreSQL y actualiza la climatología.

Requisitos previos:
    1. Base de datos levantada:          docker compose up -d
    2. Histórico tratado y corregido:    python data_science/etl_satelite.py
                                         python data_science/corregir_humedad_era5.py
Uso (desde la raíz del repositorio):
    python data_science/cargar_bd.py

El script es idempotente: se puede ejecutar varias veces y el resultado es el
mismo, porque reemplaza el histórico completo dentro de una sola transacción.
"""

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

RUTA_TRATADO = Path("data_science/notebooks/satelite_queretaro_tratado.csv")
ZONA_HORARIA = "America/Mexico_City"

# Correspondencia entre columnas del CSV y columnas de la tabla historico_era5
COLUMNAS_BD = {
    "timestamp": "ts",
    "lat": "latitud",
    "lon": "longitud",
    "temperature": "temperatura",
    "humidity": "humedad",
    "pressure": "presion_hpa",
    "radiation": "radiacion_wm2",
}


def crear_motor() -> Engine:
    """Crea la conexión a PostgreSQL leyendo las credenciales del archivo .env."""
    load_dotenv()
    requeridas = ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
    faltantes = [var for var in requeridas if not os.getenv(var)]
    if faltantes:
        sys.exit(f"Error: faltan variables en el archivo .env: {', '.join(faltantes)}")

    # URL.create escapa caracteres especiales de la contraseña de forma segura
    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB"),
    )
    return create_engine(url)


def preparar_historico() -> pd.DataFrame:
    """Lee el CSV tratado y lo convierte al formato y unidades de la base de datos."""
    if not RUTA_TRATADO.exists():
        sys.exit(f"Error: no existe {RUTA_TRATADO}. Ejecute primero el ETL.")

    df = pd.read_csv(RUTA_TRATADO, parse_dates=["timestamp"])
    df = df[list(COLUMNAS_BD)].rename(columns=COLUMNAS_BD)

    # El CSV guarda la hora local sin zona; se la asignamos para que PostgreSQL la guarde bien
    df["ts"] = df["ts"].dt.tz_localize(ZONA_HORARIA)
    # Pa -> hPa (unidad estándar en meteorología y la misma que usaremos para el BMP280)
    df["presion_hpa"] = df["presion_hpa"] / 100.0

    # Redondeo acorde a la precisión de las columnas NUMERIC de la tabla
    df = df.round({"temperatura": 1, "humedad": 1, "presion_hpa": 1, "radiacion_wm2": 1})
    return df


def cargar_historico(motor: Engine, df: pd.DataFrame) -> None:
    """Reemplaza el histórico y actualiza la climatología en una sola transacción."""
    # engine.begin() abre una transacción: si algo falla, se deshace todo (rollback)
    with motor.begin() as conexion:
        conexion.execute(text("TRUNCATE TABLE historico_era5"))
        df.to_sql(
            "historico_era5",
            conexion,
            if_exists="append",  # la tabla ya existe (la crea db/init/01_esquema.sql)
            index=False,
            method="multi",
            chunksize=2000,
        )
        conexion.execute(text("REFRESH MATERIALIZED VIEW climatologia"))


def mostrar_resumen(motor: Engine) -> None:
    """Imprime conteos de control para verificar que la carga fue correcta."""
    with motor.connect() as conexion:
        total, inicio, fin = conexion.execute(
            text("SELECT COUNT(*), MIN(ts), MAX(ts) FROM historico_era5")
        ).one()
        celdas = conexion.execute(text("SELECT COUNT(*) FROM climatologia")).scalar_one()
        ejemplo = conexion.execute(
            text(
                "SELECT temperatura_media, temperatura_desv, humedad_media "
                "FROM climatologia WHERE mes = 5 AND hora = 15"
            )
        ).one_or_none()

    print(f"Histórico en la base: {total} registros ({inicio} a {fin})")
    print(f"Climatología: {celdas} combinaciones mes-hora (esperado: 12 x 24 = 288)")
    if ejemplo:
        print(
            f"Ejemplo, mayo a las 15:00 -> temperatura normal {ejemplo[0]} °C "
            f"(± {ejemplo[1]}), humedad {ejemplo[2]} %"
        )


def main() -> None:
    motor = crear_motor()
    df = preparar_historico()
    print(f"Cargando {len(df)} registros en historico_era5...")
    try:
        cargar_historico(motor, df)
    except OperationalError:
        sys.exit(
            "Error: no se pudo conectar a PostgreSQL. "
            "¿Está corriendo el contenedor? Pruebe: docker compose up -d"
        )
    mostrar_resumen(motor)
    print("¡Carga completada!")


if __name__ == "__main__":
    main()
