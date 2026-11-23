"""Configuración de la API leída desde variables de entorno o del archivo .env."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL
from sqlalchemy.engine import make_url


class Configuracion(BaseSettings):
    """Valores de configuración. Nunca se escriben contraseñas directamente en el código."""

    # Busca el .env en la raíz del repositorio (../.env) o en la carpeta actual
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    # Opción 1 (nube, ej. Neon): una sola URL de conexión
    #   DATABASE_URL=postgresql://usuario:contraseña@servidor/base?sslmode=require
    database_url: str | None = None

    # Opción 2 (local con Docker): datos por separado
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5433

    # Orígenes web autorizados a consultar la API desde el navegador (dashboard React).
    # En la nube se define como JSON, ej.: ORIGENES_CORS=["https://mi-dashboard.onrender.com"]
    origenes_cors: list[str] = ["http://localhost:5173"]

    # Tolerancia para lecturas con hora en el futuro (relojes desincronizados)
    tolerancia_futuro_minutos: int = 5

    # Modelo meteorológico de referencia (Open-Meteo: gratuito y sin llave para uso no comercial)
    url_modelo: str = "https://api.open-meteo.com/v1/forecast"
    tiempo_espera_modelo_s: float = 30.0
    intervalo_sincronizacion_minutos: int = 30
    # true = la propia API descarga el modelo en segundo plano (útil en la nube, donde el
    # plan gratuito permite un solo servicio). En local lo hace el servicio "sincronizador".
    sincronizar_en_api: bool = False

    @model_validator(mode="after")
    def validar_conexion(self) -> "Configuracion":
        if self.database_url is None and not (
            self.postgres_user and self.postgres_password and self.postgres_db
        ):
            raise ValueError(
                "Configure DATABASE_URL o POSTGRES_USER, POSTGRES_PASSWORD y POSTGRES_DB."
            )
        return self

    @property
    def url_base_datos(self) -> URL:
        if self.database_url:
            url = make_url(self.database_url)
            # Los proveedores entregan "postgresql://"; se indica el driver psycopg (versión 3)
            return url.set(drivername="postgresql+psycopg")
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
