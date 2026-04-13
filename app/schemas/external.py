from pydantic import BaseModel, Field
from typing import Optional, List


# ==================== VENTAS ====================

class ExternalVentaDetalle(BaseModel):
    """Detalle de documento de venta para API externa"""
    Line: int
    ItemCode: Optional[str] = None
    Description: str
    Quantity: float
    Unit: Optional[str] = None
    Price: float
    PriceTax: Optional[float] = None
    SubTotal: Optional[float] = None
    Total: float
    TotalTaxLo: Optional[float] = None


class ExternalVentaCreate(BaseModel):
    """Documento de venta para API externa"""
    Document: str = Field(..., description="ID único del documento")
    DocumentSerie: Optional[str] = None
    DocumentNo: Optional[str] = None
    DocumentType: Optional[str] = None
    VendorRUC: Optional[str] = None
    VendorName: Optional[str] = None
    VendorAddress: Optional[str] = None
    DocumentDate: Optional[float] = None
    DueDate: Optional[float] = None
    DocumentCurrency: Optional[str] = "LO"
    ExchangeRate: Optional[float] = None
    AmountNetLo: Optional[float] = 0
    AmountTaxLo: Optional[float] = 0
    AmountTotalLo: Optional[float] = 0
    AmountNoImponibleLo: Optional[float] = 0
    detalles: Optional[List[ExternalVentaDetalle]] = []


# ==================== GUÍAS ====================

class ExternalGuiaDetalle(BaseModel):
    """Detalle de guía de remisión para API externa"""
    Line: int
    ItemCode: Optional[str] = None
    ItemDescription: str
    Quantity: float
    Unit: Optional[str] = None


class ExternalGuiaCreate(BaseModel):
    """Guía de remisión para API externa"""
    Transaction: str = Field(..., description="ID único de la transacción")
    DocumentSerie: Optional[str] = None
    DocumentNo: Optional[str] = None
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
    origenaddress: Optional[str] = None
    ubigeo_des: Optional[str] = None
    Comments: Optional[str] = None
    detalles: Optional[List[ExternalGuiaDetalle]] = []


# ==================== RETENCIONES ====================

class ExternalRetencionDetalle(BaseModel):
    """Detalle de retención para API externa"""
    DRserie: Optional[str] = None
    DRnumero: Optional[str] = None
    DRfecha: Optional[float] = None
    DRmoneda: Optional[str] = None
    DRtotal: Optional[float] = None
    DRpagoFecha: Optional[float] = None
    Retenido: Optional[float] = None
    Pagado: Optional[float] = None


class ExternalRetencionCreate(BaseModel):
    """Retención para API externa"""
    Serie: Optional[str] = None
    Numero: Optional[str] = None
    VendorRuc: Optional[str] = None
    VendorName: Optional[str] = None
    VendorAddress: Optional[str] = None
    DocumentDate: Optional[float] = None
    Tasa: Optional[int] = 8
    TotalRetenido: Optional[float] = 0
    TotalPagado: Optional[float] = 0
    Obs: Optional[str] = None
    detalles: Optional[List[ExternalRetencionDetalle]] = []


# ==================== RESPUESTA ====================

class ExternalResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
