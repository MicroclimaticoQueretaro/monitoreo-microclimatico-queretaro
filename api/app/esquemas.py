"""Modelos Pydantic: definen y validan el formato de los datos que entran y salen de la API.

Este archivo es el "contrato" entre el firmware del ESP32 y la API.
"""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

# Código de estación: solo mayúsculas, números y guiones (ej. QRO-CENTRO-01)
PATRON_CODIGO_ESTACION = r"^[A-Z0-9-]{3,30}$"


class LecturaEntrada(BaseModel):
    """Lectura enviada por el ESP32. Los rangos coinciden con los CHECK de la base de datos."""

    # extra="forbid" rechaza campos desconocidos (evita errores de escritura silenciosos)
    model_config = ConfigDict(extra="forbid")

    estacion: str = Field(pattern=PATRON_CODIGO_ESTACION, examples=["QRO-CENTRO-01"])
    # AwareDatetime exige zona horaria, ej. 2026-11-19T14:30:00-06:00
    ts: AwareDatetime
    temperatura_dht: float | None = Field(default=None, ge=-10, le=60)
    temperatura_bmp: float | None = Field(default=None, ge=-10, le=60)
    humedad: float | None = Field(default=None, ge=0, le=100)
    presion_hpa: float | None = Field(default=None, ge=700, le=1100)
    iluminancia_lux: float | None = Field(default=None, ge=0, le=200000)

    @model_validator(mode="after")
    def validar_al_menos_una_medicion(self) -> "LecturaEntrada":
        mediciones = [
            self.temperatura_dht,
            self.temperatura_bmp,
            self.humedad,
            self.presion_hpa,
            self.iluminancia_lux,
        ]
        if all(valor is None for valor in mediciones):
            raise ValueError("La lectura debe incluir al menos una medición.")
        return self


class LecturaCreada(BaseModel):
    mensaje: str
    estacion: str
    ts: datetime


class Lectura(BaseModel):
    ts: datetime
    temperatura_dht: float | None
    temperatura_bmp: float | None
    humedad: float | None
    presion_hpa: float | None
    iluminancia_lux: float | None


class Estacion(BaseModel):
    """Datos públicos de una estación (nunca incluye el hash del token)."""

    codigo: str
    nombre: str
    latitud: float
    longitud: float
    altitud_m: float | None
    activa: bool


class Comparacion(BaseModel):
    """Lectura del sensor frente a la climatología (lo 'normal' para ese mes y hora)."""

    ts: datetime
    temperatura_sensor: float | None = Field(
        description="Temperatura de referencia: BMP280 si existe (más precisa), si no DHT11."
    )
    temperatura_normal: float | None
    anomalia_temperatura: float | None = Field(
        description="Sensor menos normal. Positivo = más caliente de lo habitual."
    )
    anomalia_estandarizada: float | None = Field(
        description="Anomalía dividida entre la desviación estándar (|z| > 2 es inusual)."
    )
    humedad_sensor: float | None
    humedad_normal: float | None


class BrechaMinuto(BaseModel):
    """Comparación de cada lectura (una por minuto) con el modelo y el normal interpolados."""

    ts: datetime = Field(description="Instante de la lectura (UTC).")
    temperatura_sensor: float | None
    temperatura_modelo: float | None = Field(
        description="Modelo regional interpolado linealmente entre la hora anterior y la siguiente."
    )
    brecha_termica: float | None = Field(description="Sensor menos modelo (°C).")
    temperatura_normal: float | None = Field(description="Normal histórico interpolado entre horas.")
    anomalia_climatologica: float | None = Field(description="Sensor menos normal histórico (°C).")
    humedad_sensor: float | None
    humedad_modelo: float | None
    diferencia_humedad: float | None


class BrechaHoraria(BaseModel):
    """Comparación hora por hora entre el sensor y el modelo meteorológico (Open-Meteo)."""

    hora: datetime = Field(description="Hora en punto (UTC) a la que corresponde la comparación.")
    lecturas_promediadas: int = Field(description="Lecturas del sensor usadas en el promedio.")

    temperatura_sensor: float | None
    temperatura_modelo: float | None
    brecha_termica: float | None = Field(
        description="Sensor menos modelo (°C). Positivo = la calle está más caliente que la región: "
        "indicador de isla de calor urbana."
    )

    temperatura_normal: float | None = Field(
        description="Promedio histórico (ERA5-Land 2023-2025) para ese mes y hora."
    )
    anomalia_climatologica: float | None = Field(
        description="Sensor menos normal histórico (°C). Positivo = más caliente de lo habitual."
    )

    humedad_sensor: float | None
    humedad_modelo: float | None
    diferencia_humedad: float | None
    humedad_normal: float | None

    presion_estacion_sensor: float | None = Field(description="Presión medida en la estación (hPa).")
    presion_nivel_mar_sensor: float | None = Field(
        description="Presión del sensor reducida al nivel del mar (hPa), comparable con el modelo."
    )
    presion_nivel_mar_modelo: float | None
    diferencia_presion: float | None

    radiacion_estimada_sensor: float | None = Field(
        description="ESTIMACIÓN de radiación solar (W/m²) a partir de lux (÷120). Aproximada."
    )
    radiacion_modelo: float | None = Field(description="Radiación solar del modelo (W/m²).")


# --- Administración y control remoto ---

class CredencialesAdmin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usuario: str = Field(min_length=3, max_length=40)
    contrasena: str = Field(min_length=1, max_length=200)


class SesionAdmin(BaseModel):
    token: str | None = Field(description="Token de sesión: se envía como 'Authorization: Bearer <token>'.")
    usuario: str
    expira_en: datetime


class ComandoEstacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accion: Literal["activar", "detener"]


class RegistroComando(BaseModel):
    accion: str
    enviado_en: datetime
    usuario: str | None


class EstadoEstacion(BaseModel):
    estado: str = Field(description="midiendo, en_espera, desconectado o desconocido")
    ts: str | None = Field(description="Momento en que la estación informó su estado (si lo envió).")
    control_remoto: bool = Field(description="True si el control por MQTT está configurado en la API.")
