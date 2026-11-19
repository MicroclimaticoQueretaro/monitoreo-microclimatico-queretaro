"""
Corrige la columna de humedad del histórico de Querétaro.

Problema: la columna 'Humedad (%)' del CSV original fue calculada a mano y sus
valores (7 % a 43 %) no corresponden a humedad relativa real en Querétaro.

Solución: descargar la humedad relativa a 2 m (relative_humidity_2m) del
reanálisis ERA5 a través de la API de Open-Meteo (gratuita, sin llave, uso no
comercial) y reemplazar la columna en el archivo tratado.

Para asegurar que los datos descargados corresponden a la misma fuente y hora,
el script compara la temperatura descargada con la temperatura del histórico y
elige el modelo (ERA5-Land o ERA5) que mejor coincide.

Orden de ejecución (desde la raíz del repositorio):
    1. python data_science/etl_satelite.py
    2. python data_science/corregir_humedad_era5.py
"""

import sys
from pathlib import Path

import pandas as pd
import requests

# --- Configuración ---
URL_API_HISTORICA = "https://archive-api.open-meteo.com/v1/archive"
LATITUD = 20.6
LONGITUD = -100.4
ZONA_HORARIA = "America/Mexico_City"
# Modelos candidatos: ERA5-Land (celda de 0.1°) y ERA5 (celda de 0.25°)
MODELOS_CANDIDATOS = ["era5_land", "era5"]
TIEMPO_ESPERA_SEGUNDOS = 90

RUTA_TRATADO = Path("data_science/notebooks/satelite_queretaro_tratado.csv")
RUTA_CACHE = Path("data/era5_humedad_relativa_queretaro.csv")

# Umbrales de control de calidad para aceptar la descarga
MAX_ERROR_MEDIO_TEMPERATURA = 1.0  # °C
MIN_CORRELACION_TEMPERATURA = 0.95


def descargar_era5(modelo: str, fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Descarga temperatura y humedad relativa horarias de Open-Meteo en hora local."""
    parametros = {
        "latitude": LATITUD,
        "longitude": LONGITUD,
        "start_date": fecha_inicio,
        "end_date": fecha_fin,
        "hourly": "temperature_2m,relative_humidity_2m",
        "models": modelo,
        # Se pide en UTC y se convierte aquí, para controlar la zona horaria nosotros
        "timezone": "GMT",
    }
    respuesta = requests.get(URL_API_HISTORICA, params=parametros, timeout=TIEMPO_ESPERA_SEGUNDOS)
    # Lanza un error claro si la API responde con un código 4xx o 5xx
    respuesta.raise_for_status()
    horario = respuesta.json()["hourly"]

    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(horario["time"], utc=True),
            "temperature_era5": horario["temperature_2m"],
            "humidity": horario["relative_humidity_2m"],
        }
    )
    # Misma convención que el ETL: hora local de Querétaro, sin zona horaria explícita
    df["timestamp"] = df["timestamp"].dt.tz_convert(ZONA_HORARIA).dt.tz_localize(None)
    df["modelo"] = modelo
    return df


def evaluar_coincidencia(df_tratado: pd.DataFrame, df_era5: pd.DataFrame) -> dict:
    """Compara la temperatura descargada con la del histórico para validar la alineación."""
    cruce = df_tratado[["timestamp", "temperature"]].merge(df_era5, on="timestamp", how="inner")
    diferencia = (cruce["temperature"] - cruce["temperature_era5"]).abs()
    return {
        "registros_cruzados": len(cruce),
        "error_medio": diferencia.mean(),
        "correlacion": cruce["temperature"].corr(cruce["temperature_era5"]),
    }


def obtener_mejor_descarga(df_tratado: pd.DataFrame) -> pd.DataFrame:
    """Usa la caché si existe; si no, descarga cada modelo y se queda con el que mejor coincide."""
    if RUTA_CACHE.exists():
        print(f"Usando datos en caché: {RUTA_CACHE}")
        return pd.read_csv(RUTA_CACHE, parse_dates=["timestamp"])

    # Rango de fechas en UTC que cubre todo el histórico en hora local
    inicio_utc = df_tratado["timestamp"].min().tz_localize(ZONA_HORARIA).tz_convert("UTC")
    fin_utc = df_tratado["timestamp"].max().tz_localize(ZONA_HORARIA).tz_convert("UTC")
    fecha_inicio, fecha_fin = inicio_utc.strftime("%Y-%m-%d"), fin_utc.strftime("%Y-%m-%d")

    mejor_df, mejor_metricas = None, None
    for modelo in MODELOS_CANDIDATOS:
        print(f"Descargando modelo '{modelo}' ({fecha_inicio} a {fecha_fin})...")
        try:
            df_modelo = descargar_era5(modelo, fecha_inicio, fecha_fin)
        except requests.RequestException as error:
            print(f"  No se pudo descargar '{modelo}': {error}")
            continue
        metricas = evaluar_coincidencia(df_tratado, df_modelo)
        print(
            f"  Cruce: {metricas['registros_cruzados']} registros | "
            f"error medio de temperatura: {metricas['error_medio']:.2f} °C | "
            f"correlación: {metricas['correlacion']:.3f}"
        )
        if mejor_metricas is None or metricas["error_medio"] < mejor_metricas["error_medio"]:
            mejor_df, mejor_metricas = df_modelo, metricas

    if mejor_df is None:
        sys.exit("Error: no se pudo descargar ningún modelo. Revise su conexión a internet.")

    # Control de calidad: si la temperatura no coincide, la hora o la celda están desalineadas
    if (
        mejor_metricas["error_medio"] > MAX_ERROR_MEDIO_TEMPERATURA
        or mejor_metricas["correlacion"] < MIN_CORRELACION_TEMPERATURA
    ):
        sys.exit(
            "Error: la temperatura descargada no coincide con el histórico "
            f"(error medio {mejor_metricas['error_medio']:.2f} °C). "
            "No se modificó ningún archivo; revise la zona horaria y las coordenadas."
        )

    RUTA_CACHE.parent.mkdir(parents=True, exist_ok=True)
    mejor_df.to_csv(RUTA_CACHE, index=False)
    print(f"Modelo elegido: '{mejor_df['modelo'].iloc[0]}'. Caché guardada en: {RUTA_CACHE}")
    return mejor_df


def corregir_humedad() -> pd.DataFrame:
    """Reemplaza la humedad incorrecta del archivo tratado por la humedad relativa de ERA5."""
    if not RUTA_TRATADO.exists():
        sys.exit(f"Error: no existe {RUTA_TRATADO}. Ejecute primero data_science/etl_satelite.py")

    df_tratado = pd.read_csv(RUTA_TRATADO, parse_dates=["timestamp"])
    df_era5 = obtener_mejor_descarga(df_tratado)

    humedad_anterior = df_tratado["humidity"].describe()
    df_corregido = df_tratado.drop(columns=["humidity"]).merge(
        df_era5[["timestamp", "humidity"]], on="timestamp", how="left"
    )

    faltantes = df_corregido["humidity"].isna().sum()
    if faltantes:
        print(f"Aviso: {faltantes} horas quedaron sin humedad (se conservan como vacías).")

    # Rango físico válido de humedad relativa
    df_corregido["humidity"] = df_corregido["humidity"].clip(lower=0.0, upper=100.0)
    df_corregido.to_csv(RUTA_TRATADO, index=False)

    print("\nHumedad ANTES  -> min {:.1f} | media {:.1f} | max {:.1f}".format(
        humedad_anterior["min"], humedad_anterior["mean"], humedad_anterior["max"]))
    print("Humedad AHORA  -> min {:.1f} | media {:.1f} | max {:.1f}".format(
        df_corregido["humidity"].min(), df_corregido["humidity"].mean(), df_corregido["humidity"].max()))
    print(f"Archivo actualizado: {RUTA_TRATADO}")
    return df_corregido


if __name__ == "__main__":
    corregir_humedad()
