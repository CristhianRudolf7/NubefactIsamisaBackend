from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..models.user import UserRole


class Token(BaseModel):
    """Schema para respuesta de token"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema para datos del token"""
    user_id: Optional[int] = None
    dni: Optional[str] = None
    rol: Optional[UserRole] = None


class CurrentUser(BaseModel):
    """Schema para usuario actual"""
    id: int
    dni: str
    nombre: str
    rol: UserRole
    is_active: bool
