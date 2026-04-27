from sqlalchemy import Column, String, Boolean, Integer
from ..database import Base

class ConfiguracionEnvio(Base):
    """Configuración de envío por tipo de documento"""
    __tablename__ = "sy_configuracion_envio"

    id = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String(50), unique=True, index=True) # 'ventas', 'guias', 'retenciones'
    modo = Column(String(20), default="manual") # 'automatico', 'manual'
    activo = Column(Boolean, default=False)
    intervalo_segundos = Column(Integer, default=60)
