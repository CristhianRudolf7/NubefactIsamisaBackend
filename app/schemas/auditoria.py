from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class AuditoriaResponse(BaseModel):
    """Schema para respuesta básica de auditoría"""
    id: int
    tabla: str
    registro_id: str  # String para soportar IDs alfanuméricos
    accion: str
    datos_anteriores: Optional[str] = None
    datos_nuevos: Optional[str] = None
    usuario: Optional[str] = None
    fecha: datetime
    ip: Optional[str] = None

    class Config:
        from_attributes = True


class AuditoriaDetalleResponse(BaseModel):
    """Schema para respuesta detallada con datos parseados"""
    id: int
    tabla: str
    registro_id: str  # String para soportar IDs alfanuméricos
    accion: str
    datos_anteriores: Optional[Any] = None
    datos_nuevos: Optional[Any] = None
    usuario: Optional[str] = None
    fecha: datetime
    ip: Optional[str] = None

    class Config:
        from_attributes = True


class AuditoriaEstadisticas(BaseModel):
    """Schema para estadísticas de auditoría"""
    total_registros: int
    acciones_por_tipo: dict[str, int]
    acciones_por_tabla: dict[str, int]
    usuarios_mas_activos: list[dict[str, Any]]
    acciones_por_dia: list[dict[str, Any]]


class AuditoriaFilterParams(BaseModel):
    """Parámetros de filtro para auditoría"""
    tabla: Optional[str] = None
    accion: Optional[str] = None
    usuario: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    page: int = 1
    page_size: int = 20
