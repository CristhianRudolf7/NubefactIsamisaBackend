from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from ..models.user import UserRole


class UserBase(BaseModel):
    """Schema base para usuario"""
    dni: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$")
    nombre: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema para crear usuario"""
    password: str = Field(..., min_length=6, max_length=50)
    rol: UserRole = UserRole.TRABAJADOR
    puede_acceder_ventas: bool = False
    puede_acceder_guias: bool = False
    puede_acceder_retenciones: bool = False


class UserUpdate(BaseModel):
    """Schema para actualizar usuario"""
    dni: Optional[str] = Field(None, min_length=8, max_length=8, pattern=r"^\d{8}$")
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=50)
    rol: Optional[UserRole] = None
    is_active: Optional[bool] = None
    puede_acceder_ventas: Optional[bool] = None
    puede_acceder_guias: Optional[bool] = None
    puede_acceder_retenciones: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema para respuesta de usuario"""
    id: int
    dni: str
    nombre: str
    rol: UserRole
    is_active: bool
    puede_acceder_ventas: bool
    puede_acceder_guias: bool
    puede_acceder_retenciones: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema para login"""
    dni: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$")
    password: str = Field(..., min_length=1)
