from pydantic import BaseModel
from typing import Optional, List, Any


class NubeFactItem(BaseModel):
    """Item genérico para NubeFact"""
    unidad_de_medida: str
    codigo: str
    descripcion: str
    cantidad: float
    valor_unitario: Optional[float] = None
    precio_unitario: Optional[float] = None
    descuento: Optional[float] = None
    subtotal: Optional[float] = None
    tipo_de_igv: Optional[str] = None
    igv: Optional[float] = None
    total: Optional[float] = None
    codigo_producto_sunat: Optional[str] = None
    impuesto_bolsas: Optional[float] = None
    anticipo_regularizacion: Optional[bool] = None
    anticipo_documento_serie: Optional[str] = None
    anticipo_documento_numero: Optional[str] = None


class NubeFactRequest(BaseModel):
    """Request genérico para NubeFact - Facturas/Boletas"""
    operacion: str = "generar_comprobante"
    tipo_de_comprobante: int
    serie: str
    numero: str
    sunat_transaction: int = 1
    cliente_tipo_de_documento: str
    cliente_numero_de_documento: str
    cliente_denominacion: str
    cliente_direccion: Optional[str] = ""
    cliente_email: str = ""
    cliente_email_1: str = ""
    cliente_email_2: str = ""
    fecha_de_emision: str
    fecha_de_vencimiento: str = ""
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
    items: List[NubeFactItem]
    venta_al_credito: Optional[List[dict]] = None


class NubeFactGuiaRequest(BaseModel):
    """Request para Guías de Remisión"""
    operacion: str = "generar_guia"
    tipo_de_comprobante: int = 7
    serie: str
    numero: str
    cliente_tipo_de_documento: str
    cliente_numero_de_documento: str
    cliente_denominacion: str
    cliente_direccion: Optional[str] = ""
    cliente_email: str = ""
    cliente_email_1: str = ""
    cliente_email_2: str = ""
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
    items: List[NubeFactItem]
    documento_relacionado: Optional[List[dict]] = None


class NubeFactRetencionItem(BaseModel):
    """Item para Retención"""
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


class NubeFactRetencionRequest(BaseModel):
    """Request para Retenciones"""
    operacion: str = "generar_retencion"
    serie: str
    numero: str
    cliente_tipo_de_documento: str = "6"
    cliente_numero_de_documento: str
    cliente_denominacion: str
    cliente_direccion: Optional[str] = ""
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
    items: List[NubeFactRetencionItem]


class NubeFactResponse(BaseModel):
    """Respuesta de NubeFact"""
    success: bool
    message: str
    
    # Datos de respuesta exitosa
    tipo_de_comprobante: Optional[int] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    enlace: Optional[str] = None
    enlace_del_pdf: Optional[str] = None
    enlace_del_xml: Optional[str] = None
    enlace_del_cdr: Optional[str] = None
    aceptada_por_sunat: Optional[bool] = None
    sunat_description: Optional[str] = None
    sunat_note: Optional[str] = None
    sunat_responsecode: Optional[str] = None
    sunat_soap_error: Optional[str] = None
    pdf_zip_base64: Optional[str] = None
    xml_zip_base64: Optional[str] = None
    cdr_zip_base64: Optional[str] = None
    cadena_para_codigo_qr: Optional[str] = None
    codigo_hash: Optional[str] = None
    
    # Errores
    errors: Optional[List[str]] = None


class NubeFactConsultRequest(BaseModel):
    """Request para consultar CPE"""
    operacion: str = "consultar_comprobante"
    tipo_de_comprobante: int
    serie: str
    numero: str


class NubeFactConsultAnulacionRequest(BaseModel):
    """Request para consultar anulación"""
    operacion: str = "consultar_anulacion"
    tipo_de_comprobante: int
    serie: str
    numero: str
