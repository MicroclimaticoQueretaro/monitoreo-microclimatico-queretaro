import pandas as pd
import numpy as np

def ejecutar_etl_satelite(caminho_arquivo_bruto, caminho_saida_tratado):
    print("Iniciando el ETL de los datos satelitales")
    
    # 1. Carga de los datos crudos (ej. CSV exportado de fuentes satelitales o históricas)
    df = pd.read_csv(caminho_arquivo_bruto)
    
    # 2. Tratamiento de la marca de tiempo (Timestamp) y conversión a zona horaria local
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Si los datos están en UTC, los convertimos al huso horario de Querétaro (America/Mexico_City)
    if df['timestamp'].dt.tz is None:
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('America/Mexico_City')
    else:
        df['timestamp'] = df['timestamp'].dt.tz_convert('America/Mexico_City')

    # 3. Filtrado Geográfico (Centro Histórico de Querétaro y alrededores)
    # Delimitamos la caja geográfica (Bounding Box) aproximada de la zona
    lat_min, lat_max = 20.585, 20.605
    lon_min, lon_max = -100.405, -100.380
    
    # Filtramos el DataFrame por las coordenadas de latitud y longitud
    df_filtrado = df[
        (df['lat'] >= lat_min) & (df['lat'] <= lat_max) &
        (df['lon'] >= lon_min) & (df['lon'] <= lon_max)
    ].copy()
    
    print(f"Registros después del recorte geográfico: {len(df_filtrado)}")

    # 4. Tratamiento de Valores Nulos e Inconsistentes
    # Eliminamos filas donde la temperatura o humedad sean nulas
    df_filtrado = df_filtrado.dropna(subset=['temperature', 'humidity'])
    
    # Filtramos valores físicamente imposibles (ej. temperaturas fuera del rango lógico)
    df_filtrado = df_filtrado[
        (df_filtrado['temperature'] >= -10) & (df_filtrado['temperature'] <= 60) &
        (df_filtrado['humidity'] >= 0) & (df_filtrado['humidity'] <= 100)
    ]

    # 5. Guardar el resultado limpio
    df_filtrado.to_csv(caminho_saida_tratado, index=False)
    print(f"¡ETL completado con éxito! Archivo guardado en: {caminho_saida_tratado}")
    
    return df_filtrado

# Exemplo de execução local (ajuste os caminhos conforme sua pasta de dados)
if __name__ == "__main__":
    # Caminho de exemplo (você ajustará quando receber o arquivo do colega)
    # arquivo_entrada = "../big_data/data/bruto_satelite.csv"
    # arquivo_saida = "data_science/notebooks/satelite_queretaro_tratado.csv"
    pass