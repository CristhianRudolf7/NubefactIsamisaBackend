from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RetencionItem(BaseModel):
    """Item de detalle de retención"""
    documento_relacionado_tipo: str = "01"
    documento_relacionado_serie: str
    documento_relacionado_numero: str
    documento_relacionado_fecha_de_emision: str
    documento_relacionado_moneda: str
    documento_relacionado_total: float
    pago_fecha: str
    pago_numero: str
    pago_total_sin_retencion: float
    tipo_de_cambio: Optional[float] = None
    tipo_de_cambio_fecha: Optional[str] = None
    importe_retenido: float
    importe_retenido_fecha: str
    importe_pagado_con_retencion: float

    class Config:
        from_attributes = True


class RetencionBase(BaseModel):
    """Base para retención"""
    Id: int
    Serie: str
    Numero: str
    VendorRuc: str
    VendorName: str
    VendorAddress: str
    DocumentDate: Optional[float] = None
    Tasa: int
    TotalRetenido: float
    TotalPagado: float
    status: Optional[str] = None


class RetencionSchema(RetencionBase):
    """Schema completo de retención"""
    Obs: Optional[str] = None
    XlastUser: Optional[str] = None
    XlastDate: Optional[float] = None
    detalles: List[RetencionItem] = []

    class Config:
        from_attributes = True


class RetencionCreate(BaseModel):
    """Schema para crear/actualizar retención"""
    Serie: str
    Numero: str
    VendorRuc: str
    VendorName: str
    VendorAddress: str
    Tasa: int
    TotalRetenido: float
    TotalPagado: float
    Obs: Optional[str] = None
    detalles: List[RetencionItem]


class RetencionFilter(BaseModel):
    """Filtros para búsqueda de retenciones"""
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    estado: Optional[str] = None
    ruc_proveedor: Optional[str] = None


class RetencionNubeFact(BaseModel):
    """Schema para enviar retención a NubeFact"""
    operacion: str = "generar_retencion"
    serie: str
    numero: str
    cliente_tipo_de_documento: str = "6"
    cliente_numero_de_documento: str
    cliente_denominacion: str
    cliente_direccion: str
    cliente_email: str = ""
    cliente_email_1: str = ""
    cliente_email_2: str = ""
    fecha_de_emision: str
    moneda: str = "1"
    tipo_de_tasa_de_retencion: str
    total_retenido: float
    total_pagado: float
    observaciones: str = ""
    enviar_automaticamente_a_la_sunat: bool = True
    enviar_automaticamente_al_cliente: bool = False
    codigo_unico: str = ""
    formato_de_pdf: str = ""
    items: List[RetencionItem]
