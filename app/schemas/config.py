from pydantic import BaseModel
from typing import Optional

class ConfiguracionEnvioBase(BaseModel):
    tipo_documento: str
    modo: str
    activo: bool
    intervalo_segundos: int

class ConfiguracionEnvioSchema(ConfiguracionEnvioBase):
    id: int

    class Config:
        from_attributes = True

class ConfiguracionEnvioUpdate(BaseModel):
    modo: Optional[str] = None
    activo: Optional[bool] = None
    intervalo_segundos: Optional[int] = None
