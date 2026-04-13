from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class ApiToken(Base):
    """Modelo para Tokens de API externa"""
    __tablename__ = "api_tokens"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="Nombre descriptivo del token")
    token_hash = Column(String(255), nullable=False, unique=True, comment="Hash del token (bcrypt)")
    token_prefix = Column(String(8), nullable=False, comment="Prefijo del token para identificación")
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True, comment="Última vez que se usó el token")
    expires_at = Column(DateTime, nullable=True, comment="Fecha de expiración opcional")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relación con usuario creador
    creator = relationship("User", backref="api_tokens")
