from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DocumentoVentaItem(BaseModel):
    """Item de detalle de documento de venta"""
    unidad_de_medida: str
    codigo: str
    descripcion: str
    cantidad: float
    valor_unitario: float
    precio_unitario: float
    descuento: Optional[float] = None
    subtotal: float
    tipo_de_igv: str = "1"
    igv: float
    impuesto_bolsas: Optional[float] = None
    total: float
    anticipo_regularizacion: bool = False
    anticipo_documento_serie: Optional[str] = None
    anticipo_documento_numero: Optional[str] = None
    codigo_producto_sunat: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentoVentaBase(BaseModel):
    """Base para documento de venta"""
    Document: str
    DocumentSerie: str
    DocumentNo: str
    DocumentType: str
    VendorRUC: str
    VendorName: str
    VendorAddress: str
    DocumentDate: Optional[float] = None
    DueDate: Optional[float] = None
    DocumentCurrency: str = "LO"
    ExchangeRate: Optional[float] = None
    AmountNetLo: float
    AmountTaxLo: float
    AmountTotalLo: float
    fe: Optional[str] = None


class DocumentoVentaSchema(DocumentoVentaBase):
    """Schema completo de documento de venta"""
    VendorEmail: Optional[str] = None
    VendorTelephone: Optional[str] = None
    PlazoDias: Optional[int] = None
    FlagSaleType: Optional[str] = None
    AmountNoImponibleLo: Optional[float] = None
    detraccion: Optional[str] = None
    d_cod: Optional[str] = None
    d_tasa: Optional[float] = None
    montodetrac: Optional[float] = None
    RefGuides: Optional[str] = None
    MotivoNC: Optional[str] = None
    RefDocSerie: Optional[str] = None
    RefDocNo: Optional[str] = None
    detalles: List[DocumentoVentaItem] = []

    class Config:
        from_attributes = True


class DocumentoVentaCreate(BaseModel):
    """Schema para crear/actualizar documento de venta"""
    DocumentSerie: str
    DocumentNo: str
    DocumentType: str
    VendorRUC: str
    VendorName: str
    VendorAddress: str
    VendorEmail: Optional[str] = None
    DocumentDate: str
    DueDate: Optional[str] = None
    DocumentCurrency: str = "LO"
    ExchangeRate: Optional[float] = None
    AmountNetLo: float
    AmountTaxLo: float
    AmountTotalLo: float
    AmountNoImponibleLo: Optional[float] = None
    PlazoDias: Optional[int] = None
    FlagSaleType: Optional[str] = None
    detraccion: Optional[bool] = False
    d_cod: Optional[str] = None
    d_tasa: Optional[float] = None
    montodetrac: Optional[float] = None
    RefGuides: Optional[str] = None
    MotivoNC: Optional[str] = None
    RefDocSerie: Optional[str] = None
    RefDocNo: Optional[str] = None
    detalles: List[DocumentoVentaItem]


class DocumentoVentaFilter(BaseModel):
    """Filtros para búsqueda de documentos de venta"""
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    estado: Optional[str] = None
    ruc_cliente: Optional[str] = None
    tipo_documento: Optional[str] = None


class DocumentoVentaNubeFact(BaseModel):
    """Schema para enviar documento de venta a NubeFact"""
    operacion: str = "generar_comprobante"
    tipo_de_comprobante: int
    serie: str
    numero: str
    sunat_transaction: int = 1
    cliente_tipo_de_documento: str
    cliente_numero_de_documento: str
    cliente_denominacion: str
    cliente_direccion: str
    cliente_email: str = ""
    cliente_email_1: str = ""
    cliente_email_2: str = ""
    fecha_de_emision: str
    fecha_de_vencimiento: Optional[str] = ""
    moneda: str = "1"
    tipo_de_cambio: Optional[float] = None
    porcentaje_de_igv: str = "18.00"
    descuento_global: Optional[float] = None
    total_descuento: Optional[float] = None
    total_anticipo: Optional[float] = None
    total_gravada: float
    total_inafecta: Optional[float] = None
    total_exonerada: Optional[float] = None
    total_igv: float
    total_gratuita: Optional[float] = None
    total_otros_cargos: Optional[float] = None
    total_impuestos_bolsas: Optional[float] = None
    total: float
    percepcion_tipo: Optional[str] = None
    percepcion_base_imponible: Optional[float] = None
    total_percepcion: Optional[float] = None
    total_incluido_percepcion: Optional[float] = None
    detraccion: bool = False
    detraccion_tipo: Optional[str] = None
    detraccion_total: Optional[float] = None
    detraccion_porcentaje: Optional[float] = None
    medio_de_pago_detraccion: Optional[str] = None
    observaciones: str = ""
    documento_que_se_modifica_tipo: Optional[str] = None
    documento_que_se_modifica_serie: Optional[str] = None
    documento_que_se_modifica_numero: Optional[str] = None
    tipo_de_nota_de_credito: Optional[str] = None
    tipo_de_nota_de_debito: Optional[str] = None
    enviar_automaticamente_a_la_sunat: bool = True
    enviar_automaticamente_al_cliente: bool = False
    codigo_unico: str = ""
    condiciones_de_pago: Optional[str] = None
    medio_de_pago: Optional[str] = None
    placa_vehiculo: str = ""
    orden_compra_servicio: str = ""
    tabla_personalizada_codigo: str = ""
    formato_de_pdf: str = ""
    items: List[DocumentoVentaItem]
    venta_al_credito: Optional[List[dict]] = None
