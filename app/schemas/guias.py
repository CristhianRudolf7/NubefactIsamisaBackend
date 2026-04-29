from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class GuiaRemisionItem(BaseModel):
    """Item de detalle de guía de remisión"""
    unidad_de_medida: str
    codigo: str
    descripcion: str
    cantidad: float

    class Config:
        from_attributes = True


class GuiaRemisionBase(BaseModel):
    """Base para guía de remisión"""
    Transaction: str
    DocumentSerie: str
    DocumentNo: str
    TransactionDate: Optional[float] = None
    TargetPersonRUC: Optional[str] = None
    TargetPersonName: Optional[str] = None
    TargetAddress: Optional[str] = None
    MotivoTraslado: Optional[str] = None
    PesoBruto: Optional[float] = None
    RucTransportista: Optional[str] = None
    Transportista: Optional[str] = None
    VehicleID: Optional[str] = None
    Driver: Optional[str] = None
    LicenciaConducir: Optional[str] = None
    envio_nube: Optional[str] = None
    Status: Optional[str] = None
    necesita_aprobacion: Optional[bool] = False
    aprobacion_usuario: Optional[str] = None


class GuiaRemisionSchema(GuiaRemisionBase):
    """Schema completo de guía de remisión"""
    detalles: List[GuiaRemisionItem] = []
    origenaddress: Optional[str] = None
    ubigeo_des: Optional[str] = None
    Comments: Optional[str] = None
    SaleDocAbbrev: Optional[str] = None
    SaleDocSerie: Optional[str] = None
    SaleDocNo: Optional[str] = None

    class Config:
        from_attributes = True


class GuiaRemisionCreate(BaseModel):
    """Schema para crear/actualizar guía de remisión"""
    DocumentSerie: str
    DocumentNo: str
    TargetPersonRUC: str
    TargetPersonName: str
    TargetAddress: str
    MotivoTraslado: str
    PesoBruto: float
    RucTransportista: str
    Transportista: str
    VehicleID: str
    Driver: str
    LicenciaConducir: str
    origenaddress: str
    ubigeo_des: str
    Comments: Optional[str] = None
    detalles: List[GuiaRemisionItem]


class GuiaRemisionFilter(BaseModel):
    """Filtros para búsqueda de guías"""
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    estado: Optional[str] = None
    ruc_destinatario: Optional[str] = None


class GuiaRemisionNubeFact(BaseModel):
    """Schema para enviar guía a NubeFact"""
    operacion: str = "generar_guia"
    tipo_de_comprobante: int = 7
    serie: str
    numero: str
    cliente_tipo_de_documento: str
    cliente_numero_de_documento: str
    cliente_denominacion: str
    cliente_direccion: str
    cliente_email: str = ""
    fecha_de_emision: str
    observaciones: str = ""
    motivo_de_traslado: str
    peso_bruto_total: float
    peso_bruto_unidad_de_medida: str = "KGM"
    numero_de_bultos: int
    tipo_de_transporte: str
    fecha_de_inicio_de_traslado: str
    transportista_documento_tipo: str = "6"
    transportista_documento_numero: str
    transportista_denominacion: str
    transportista_placa_numero: str
    conductor_documento_tipo: str = "1"
    conductor_documento_numero: str
    conductor_nombre: str
    conductor_apellidos: str
    conductor_numero_licencia: str
    punto_de_partida_ubigeo: str
    punto_de_partida_direccion: str
    punto_de_partida_codigo_establecimiento_sunat: str = ""
    punto_de_llegada_ubigeo: str
    punto_de_llegada_direccion: str
    punto_de_llegada_codigo_establecimiento_sunat: str = ""
    enviar_automaticamente_a_la_sunat: bool = True
    enviar_automaticamente_al_cliente: bool = False
    formato_de_pdf: str = ""
    items: List[GuiaRemisionItem]
    documento_relacionado: Optional[List[dict]] = None
