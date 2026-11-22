"""Configuración de la API leída desde variables de entorno o del archivo .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Configuracion(BaseSettings):
    """Valores de configuración. Nunca se escriben contraseñas directamente en el código."""

    # Busca el .env en la raíz del repositorio (../.env) o en la carpeta actual
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5433

    # Orígenes web autorizados a consultar la API desde el navegador (dashboard React)
    origenes_cors: list[str] = ["http://localhost:5173"]

    # Tolerancia para lecturas con hora en el futuro (relojes desincronizados)
    tolerancia_futuro_minutos: int = 5

    # Modelo meteorológico de referencia (Open-Meteo: gratuito y sin llave para uso no comercial)
    url_modelo: str = "https://api.open-meteo.com/v1/forecast"
    tiempo_espera_modelo_s: float = 30.0
    intervalo_sincronizacion_minutos: int = 30

    @property
    def url_base_datos(self) -> URL:
        # URL.create escapa caracteres especiales de la contraseña de forma segura
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Devuelve la configuración (se lee una sola vez y se reutiliza)."""
    return Configuracion()
