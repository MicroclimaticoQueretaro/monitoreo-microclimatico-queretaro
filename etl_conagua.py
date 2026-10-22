from pyspark.sql import SparkSession
from pyspark.sql.functions import col, isnan, when, count, year, avg


spark = SparkSession.builder \
    .appName("ETL_CONAGUA_Microclima") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

df_conagua = spark.read.csv("conagua_10k_recientes.csv", header=True, inferSchema=True, nullValue="NULO")
df_pueblito = spark.read.csv("El_Pueblito_10K.csv", header=True, inferSchema=True, nullValue="NULO")

print("=== Esquema de CONAGUA ===")
df_conagua.printSchema()

print("=== Esquema de El Pueblito ===")
df_pueblito.printSchema()

print("=== Muestra de datos: El Pueblito ===")
df_pueblito.show(5)

print("=== Conteo de valores nulos (El Pueblito) ===")
df_pueblito.select([count(when(col(c).isNull(), c)).alias(c) for c in df_pueblito.columns]).show()
from pyspark.sql.types import FloatType

columnas_numericas = ["PRECIP", "EVAP", "TEMP_MAX", "TEMP_MIN"]

for col_name in columnas_numericas:
    df_conagua = df_conagua.withColumn(col_name, col(col_name).cast(FloatType()))
    df_pueblito = df_pueblito.withColumn(col_name, col(col_name).cast(FloatType()))

df_conagua_limpio = df_conagua.na.drop()
df_pueblito_limpio = df_pueblito.na.drop()

print("=== Nuevo Esquema Limpio y Listo (El Pueblito) ===")
df_pueblito_limpio.printSchema()

print("=== Calculando Métricas y Guardando en Parquet ===")
# 1. Transformación: Agrupar por año y calcular promedios (Cumple rubro de "Transformación")
df_metricas = df_pueblito_limpio.withColumn("Anio", year(col("FECHA"))) \
    .groupBy("Anio") \
    .agg(
        avg("TEMP_MAX").alias("Promedio_Temp_Max"), 
        avg("PRECIP").alias("Promedio_Lluvia")
    )

# 2. Almacenamiento: Guardar el resultado en formato Parquet (Cumple rubro de "Almacenamiento")
df_metricas.write.mode("overwrite").parquet("metricas_microclima.parquet")
print("¡Métricas generadas y guardadas en Parquet!")

# 7. Carga de datos a PostgreSQL
print("=== Iniciando guardado en Base de Datos ===")

db_url = "jdbc:postgresql://localhost:5433/microclima_db"
db_properties = {
    "user": "admin",
    "password": "admin_clima_2026",
    "driver": "org.postgresql.Driver"
}

# Escribir DataFrames como tablas en la base de datos
df_conagua_limpio.write.jdbc(url=db_url, table="conagua_historico", mode="overwrite", properties=db_properties)
df_pueblito_limpio.write.jdbc(url=db_url, table="pueblito_historico", mode="overwrite", properties=db_properties)

print("¡Datos históricos guardados exitosamente en PostgreSQL!")