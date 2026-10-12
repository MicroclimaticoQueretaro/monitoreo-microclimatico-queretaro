import pandas as pd
import numpy as np

def calcular_metricas_base(caminho_dados_satelite):
    print("Iniciando Analítica Exploratoria Preliminar (EDA) de los datos históricos...")
    
    # 1. Cargar el dataset histórico y limpio de satélite (3 años)
    df = pd.read_csv(caminho_dados_satelite)
    
    # Asegurar formato de fecha
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 2. Calcular métricas estadísticas base para la temperatura
    temp_media = df['temperature'].mean()
    temp_std = df['temperature'].std()
    temp_min = df['temperature'].min()
    temp_max = df['temperature'].max()
    
    # 3. Definir umbrales para la detección de anomalías (Islas de Calor)
    # Usamos una desviación estándar de 2 sigma para detectar valores atípicos de calor extremo
    umbral_calor_extremo = temp_media + (2 * temp_std)
    umbral_frio_extremo = temp_media - (2 * temp_std)
    
    print(f"Temperatura Media Histórica (3 años): {temp_media:.2f}°C")
    print(f"Desviación Estándar: {temp_std:.2f}°C")
    print(f"Rango Histórico: Min {temp_min:.2f}°C / Max {temp_max:.2f}°C")
    print(f"Umbral de Calor Extremo (Alerta UHI): > {umbral_calor_extremo:.2f}°C")
    
    # 4. Exportar las métricas base calculadas para que el equipo las use en las alertas
    metricas = pd.DataFrame({
        'metrica': ['temperatura_media', 'desviacion_estandar', 'temp_min', 'temp_max', 'umbral_calor_extremo'],
        'valor': [temp_media, temp_std, temp_min, temp_max, umbral_calor_extremo]
    })
    
    metricas.to_csv("data_science/metricas_base_queretaro.csv", index=False)
    print("¡EDA completado! Métricas base guardadas en 'data_science/metricas_base_queretaro.csv'.")
    
    return metricas

if __name__ == "__main__":
    # Ruta de ejemplo para pruebas locales
    # calcular_metricas_base("satelite_queretaro_tratado.csv")
    pass