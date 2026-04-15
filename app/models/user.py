from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from ..database import Base
import enum


class UserRole(str, enum.Enum):
    """Roles de usuario"""
    ADMIN = "admin"
    TRABAJADOR = "trabajador"


class User(Base):
    """Modelo para Usuarios del sistema"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dni = Column(String(8), unique=True, index=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(UserRole), default=UserRole.TRABAJADOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # Permisos granulares para trabajadores
    puede_acceder_ventas = Column(Boolean, default=False, nullable=False)
    puede_acceder_guias = Column(Boolean, default=False, nullable=False)
    puede_acceder_retenciones = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
