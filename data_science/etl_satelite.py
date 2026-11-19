from pathlib import Path
import numpy as np
import pandas as pd


def _convertir_columna_numerica(serie: pd.Series) -> pd.Series:
    """Convierte cadenas con coma decimal (ej.: '19,90') a float."""
    if serie.dtype == object or pd.api.types.is_string_dtype(serie):
        limpia = (
            serie.astype(str)
            .str.strip()
            .str.replace("\u00a0", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        limpia = limpia.replace(
            {"": np.nan, "nan": np.nan, "NaN": np.nan, "None": np.nan, "null": np.nan}
        )
        return pd.to_numeric(limpia, errors="coerce")
    return pd.to_numeric(serie, errors="coerce")


def _parsear_timestamp_queretaro(serie: pd.Series) -> pd.Series:
    """
    Convierte fechas/horas a la zona horaria de Querétaro (America/Mexico_City) sin
    aplicar un nuevo desfase manual cuando la hora ya fue ajustada previamente.
    """
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    if getattr(dt.dt, "tz", None) is None:
        return dt.dt.tz_localize(
            "America/Mexico_City", ambiguous="NaT", nonexistent="shift_forward"
        )
    return dt.dt.tz_convert("America/Mexico_City")


def ejecutar_etl_satelite(
    ruta_archivo_crudo,
    ruta_salida_tratado,
    quitar_zona_horaria_salida: bool = False,
):
    """
    Ejecuta el ETL de la base histórica (reanálisis ERA5) para estandarizar nombres,
    tipos y filtros físicos antes del análisis exploratorio y del cruce con datos IoT.
    """
    print("Iniciando el ETL de los datos satelitales / históricos...")

    # utf-8-sig elimina automáticamente el BOM (\ufeff) que genera Excel en CSV UTF-8
    df = pd.read_csv(
        ruta_archivo_crudo,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
    )
    total_inicial = len(df)
    print(f"Registros cargados inicialmente: {total_inicial}")

    # Limpia BOM residual y espacios en los extremos de los nombres de columnas
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]

    # Elimina la columna redundante en Kelvin si todavía existe
    if "t2m" in df.columns:
        df = df.drop(columns=["t2m"])

    # Mapa flexible de columnas (comparación normalizada en minúsculas)
    mapa_normalizado = {
        "timestamp": "timestamp",
        "valid_time": "timestamp",
        "time": "timestamp",
        "datetime": "timestamp",
        "date": "timestamp",
        "fecha": "timestamp",
        "latitude": "lat",
        "lat": "lat",
        "longitude": "lon",
        "lon": "lon",
        "temperatura (c°)": "temperature",
        "temperatura (°c)": "temperature",
        "temperature": "temperature",
        "humedad (%)": "humidity",
        "humidity": "humidity",
        "presión (pa)": "pressure",
        "presion (pa)": "pressure",
        "pressure": "pressure",
        "radiación (w/m2)": "radiation",
        "radiacion (w/m2)": "radiation",
        "radiation": "radiation",
    }

    renombrar = {}
    for col in df.columns:
        clave = col.lower()
        if clave in mapa_normalizado:
            renombrar[col] = mapa_normalizado[clave]

    df = df.rename(columns=renombrar)

    if "timestamp" not in df.columns:
        raise ValueError(
            f"No se encontró la columna de fecha/hora. Columnas detectadas: {df.columns.tolist()}"
        )

    df["timestamp"] = _parsear_timestamp_queretaro(df["timestamp"])
    df = df.dropna(subset=["timestamp"])

    for col_num in ["lat", "lon", "temperature", "humidity", "pressure", "radiation"]:
        if col_num in df.columns:
            df[col_num] = _convertir_columna_numerica(df[col_num])

    # Recorte geográfico amplio para la región de Querétaro (incluye la celda ~20.6, -100.4)
    if "lat" in df.columns and "lon" in df.columns:
        lat_min, lat_max = 20.45, 20.75
        lon_min, lon_max = -100.55, -100.25
        df_filtrado = df[
            (df["lat"] >= lat_min)
            & (df["lat"] <= lat_max)
            & (df["lon"] >= lon_min)
            & (df["lon"] <= lon_max)
        ].copy()
    else:
        df_filtrado = df.copy()

    print(f"Registros después del recorte geográfico: {len(df_filtrado)}")

    # Validación de variables principales y rangos físicos plausibles
    columnas_obligatorias = [c for c in ["temperature", "humidity"] if c in df_filtrado.columns]
    if columnas_obligatorias:
        df_filtrado = df_filtrado.dropna(subset=columnas_obligatorias)

    if "temperature" in df_filtrado.columns:
        df_filtrado = df_filtrado[
            (df_filtrado["temperature"] >= -10.0) & (df_filtrado["temperature"] <= 60.0)
        ]

    if "humidity" in df_filtrado.columns:
        df_filtrado = df_filtrado[
            (df_filtrado["humidity"] >= 0.0) & (df_filtrado["humidity"] <= 100.0)
        ]

    if "pressure" in df_filtrado.columns:
        df_filtrado = df_filtrado[
            df_filtrado["pressure"].isna()
            | ((df_filtrado["pressure"] >= 70000.0) & (df_filtrado["pressure"] <= 110000.0))
        ]

    if "radiation" in df_filtrado.columns:
        df_filtrado["radiation"] = df_filtrado["radiation"].clip(lower=0.0, upper=1500.0)

    df_filtrado = (
        df_filtrado.sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"], keep="last")
    )

    if quitar_zona_horaria_salida and getattr(df_filtrado["timestamp"].dt, "tz", None) is not None:
        df_filtrado["timestamp"] = df_filtrado["timestamp"].dt.tz_localize(None)

    ruta_salida = Path(ruta_salida_tratado)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    df_filtrado.to_csv(ruta_salida, index=False)

    print(
        f"¡ETL completado con éxito! Guardados {len(df_filtrado)} de {total_inicial} "
        f"registros en: {ruta_salida}"
    )
    return df_filtrado


if __name__ == "__main__":
    archivo_entrada = "data/Datos_Climaticos_Completos.csv"
    archivo_salida = "data_science/notebooks/satelite_queretaro_tratado.csv"
    ejecutar_etl_satelite(archivo_entrada, archivo_salida, quitar_zona_horaria_salida=True)