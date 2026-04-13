from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ApiTokenBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nombre descriptivo del token")
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración opcional")


class ApiTokenCreate(ApiTokenBase):
    pass


class ApiTokenUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class ApiTokenResponse(BaseModel):
    id: int
    name: str
    token_prefix: str = Field(..., description="Primeros 8 caracteres del token")
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    created_by: int
    
    model_config = {"from_attributes": True}


class ApiTokenCreated(ApiTokenResponse):
    token: str = Field(..., description="Token completo (solo se muestra una vez)")
    message: str = "Guarda este token de forma segura. No podrás verlo de nuevo."
