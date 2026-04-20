from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Base de datos
    database_url: str = "mssql+pyodbc://sa:Isamisa2024!@localhost:1433/isamisa_db?driver=ODBC+Driver+17+for+SQL+Server"

    # NubeFact API
    nubefact_url: str = "https://api.nubefact.com/api/v1/1215c9d4-7765-4ac0-b9ea-268a1ee1b6d1"
    nubefact_token: str = "84b1e3cffb89488aab19c0853bc393e23f0f9ff355ef4c44a361a5a702ebedc1"

    # App
    app_name: str = "Sistema de Gestión de Documentos Electrónicos"
    app_version: str = "1.0.0"
    debug: bool = True

    # Timezone
    timezone: str = "America/Lima"

    # Autenticación JWT
    secret_key: str = "tu_clave_secreta_muy_segura_cambiar_en_produccion_2024"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # WhatsApp API para notificaciones
    whatsapp_api_url: str = "https://161.132.110.220/sis/apis/sy_whats.php"
    whatsapp_timeout: float = 10.0

    # Portal URL para links en notificaciones
    portal_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
