import pandas as pd
import numpy as np

def alinear_temporal_espacial(caminho_iot, caminho_satelite_tratado, caminho_saida_unificado):
    print("🔄 Iniciando la alineación temporal y espacial entre IoT y Satélite...")
    
    # 1. Cargar los datos limpios de ambas fuentes
    # Datos de los sensores físicos (ESP32 en la calle)
    df_iot = pd.read_csv(caminho_iot)
    # Datos macroclimáticos ya filtrados del satélite
    df_satelite = pd.read_csv(caminho_satelite_tratado)
    
    # 2. Asegurarnos de que las marcas de tiempo (timestamps) sean tratadas como fechas de Pandas
    df_iot['timestamp'] = pd.to_datetime(df_iot['timestamp'])
    df_satelite['timestamp'] = pd.to_datetime(df_satelite['timestamp'])
    
    # 3. Resampleo y Redondeo Temporal (Agrupación por hora)
    # Como el ESP32 envía datos cada pocos minutos y el satélite tiene registros horarios, 
    # redondeamos el timestamp del IoT a la hora exacta para poder compararlos.
    df_iot['timestamp_hora'] = df_iot['timestamp'].dt.floor('h')
    
    df_iot_hourly = df_iot.groupby('timestamp_hora').agg({
        'temperature': 'mean',
        'humidity': 'mean',
        'pressure': 'mean'
    }).reset_index().rename(columns={'timestamp_hora': 'timestamp'})
    
    # 4. Fusión (Merge) de ambos conjuntos de datos basados en el timestamp común
    df_unificado = pd.merge(
        df_iot_hourly, 
        df_satelite, 
        on='timestamp', 
        suffixes=('_iot', '_satelite')
    )
    
    # 5. Cálculo de la Brecha Térmica (Indicador clave para la Isla de Calor Urbana)
    # Brecha = Temperatura hiperlocal de la calle (IoT) - Temperatura macro del satélite
    df_unificado['brecha_termica'] = df_unificado['temperature_iot'] - df_unificado['temperature_satelite']
    
    # 6. Guardar la tabla unificada resultante en un nuevo archivo CSV
    df_unificado.to_csv(caminho_saida_unificado, index=False)
    print(f"✅ ¡Alineación completada con éxito! Archivo unificado guardado en: {caminho_saida_unificado}")
    print(f"📊 Total de registros cruzados: {len(df_unificado)}")
    
    return df_unificado

# Ejemplo de ejecución local si se ejecuta este archivo directamente
if __name__ == "__main__":
    # Rutas de ejemplo (ajustar según la ubicación real de sus archivos)
    # path_iot = "../iot/datos_sensores_crudos.csv"
    # path_satelite = "satelite_queretaro_tratado.csv"
    # path_salida = "datos_unificados_iot_satelite.csv"
    
    # alinear_temporal_espacial(path_iot, path_satelite, path_salida)
    pass