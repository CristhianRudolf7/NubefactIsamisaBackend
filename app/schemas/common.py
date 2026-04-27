from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime
from enum import Enum


class EstadoDocumento(str, Enum):
    """Estados posibles de un documento"""
    PENDIENTE = "pendiente"
    ENVIADO_NUBEFACT = "enviado_nubefact"
    ACEPTADO_SUNAT = "aceptado"
    ACEPTADO_OBSERVACIONES = "aceptado_observaciones"
    RECHAZADO = "rechazado"
    ERROR = "error"


class ResponseBase(BaseModel):
    """Respuesta genérica de la API"""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None


class PaginationParams(BaseModel):
    """Parámetros de paginación"""
    page: int = 1
    page_size: int = 20
    total: Optional[int] = None


class FilterParams(BaseModel):
    """Parámetros de filtro para documentos"""
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    estado: Optional[EstadoDocumento] = None
    ruc_cliente: Optional[str] = None


class AuditoriaBase(BaseModel):
    """Base para registro de auditoría"""
    usuario: str
    fecha: datetime
    accion: str
    documento_id: str
    detalles: Optional[str] = None


class BulkEnviarRequest(BaseModel):
    """Request para envío masivo de documentos"""
    ids: List[str]
    usuario: str
