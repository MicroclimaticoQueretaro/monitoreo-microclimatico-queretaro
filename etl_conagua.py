from pyspark.sql import SparkSession
from pyspark.sql.functions import col, isnan, when, count

spark = SparkSession.builder \
    .appName("ETL_CONAGUA_Microclima") \
    .getOrCreate()

df_conagua = spark.read.csv("conagua_10k_recientes.csv", header=True, inferSchema=True)
df_pueblito = spark.read.csv("El_Pueblito_10K.csv", header=True, inferSchema=True)

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