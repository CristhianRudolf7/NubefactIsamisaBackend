from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from ..database import Base


class APRetencion(Base):
    """Modelo para Retenciones - Cabecera"""
    __tablename__ = "AP_Retencion"
    
    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Serie = Column(String(10))
    Numero = Column(String(20))
    Vendor = Column(String(50))
    VendorRuc = Column(String(20))
    VendorName = Column(String(200))
    VendorAddress = Column(String(200))
    DocumentDate = Column(Float)
    Tasa = Column(Integer)
    TotalRetenido = Column(Float)
    TotalPagado = Column(Float)
    Obs = Column(Text)
    XlastUser = Column(String(50))
    XlastDate = Column(Float)
    status = Column(String(20))
    necesita_aprobacion = Column(Boolean, default=False)
    aprobacion_usuario = Column(String(50))
    
    # Relaciones
    detalles = relationship("APRetencionDetail", back_populates="retencion")
    estados = relationship("APRetencionStatus", back_populates="retencion")


class APRetencionDetail(Base):
    """Modelo para Retenciones - Detalle"""
    __tablename__ = "AP_RetencionDetail"
    
    ID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Retencion = Column(Integer, ForeignKey("AP_Retencion.Id"))
    DRserie = Column(String(10))
    DRnumero = Column(String(20))
    DRfecha = Column(Float)
    DRmoneda = Column(String(10))
    DRtotal = Column(Float)
    DRpagoFecha = Column(Float)
    DRpagoNro = Column(String(20))
    DRpagoTotal = Column(Float)
    TipoCambio = Column(Float)
    TipoCambioFecha = Column(Float)
    Retenido = Column(Float)
    RetenidoFecha = Column(Float)
    Pagado = Column(Float)
    
    # Relación con cabecera
    retencion = relationship("APRetencion", back_populates="detalles")


class APRetencionStatus(Base):
    """Modelo para Estado de Retenciones - Respuesta SUNAT"""
    __tablename__ = "AP_Retencion_Status"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Retencion = Column(Integer, ForeignKey("AP_Retencion.Id"))
    Status = Column(String(20))
    Pdf = Column(String(500))
    Xml = Column(String(500))
    Cdr = Column(String(500))
    Aceptacion = Column(String(500))
    Descripcion = Column(Text)
    Nota = Column(Text)
    ResponseCode = Column(String(50))
    Soap = Column(Text)
    error = Column(Text)
    XlastUser = Column(String(50))
    XlastDate = Column(Float)
    
    # Relación con cabecera
    retencion = relationship("APRetencion", back_populates="estados")
