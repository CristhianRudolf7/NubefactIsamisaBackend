from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from ..database import Base


class Auditoria(Base):
    """Modelo para registros de auditoría del sistema"""
    __tablename__ = "auditoria"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tabla = Column(String(100), nullable=False)
    registro_id = Column(String(100), nullable=False)  # String para soportar IDs alfanuméricos
    accion = Column(String(50), nullable=False)  # INSERT, UPDATE, DELETE, SEND, CANCEL
    datos_anteriores = Column(Text)
    datos_nuevos = Column(Text)
    usuario = Column(String(100))
    fecha = Column(DateTime, server_default=func.now(), nullable=False)
    ip = Column(String(50))
