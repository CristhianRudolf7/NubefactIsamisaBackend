from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Annotated
from datetime import datetime

from ..database import get_db
from ..models.retenciones import APRetencion, APRetencionDetail, APRetencionStatus
from ..models.user import User
from ..schemas.common import ResponseBase
from ..schemas.retenciones import RetencionSchema, RetencionFilter
from ..services.document_service import DocumentService
from .auth import require_authenticated, require_admin

router = APIRouter(prefix="/retenciones", tags=["Retenciones"])


@router.get("/", response_model=ResponseBase)
async def listar_retenciones(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated)],
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (dd-mm-YYYY)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (dd-mm-YYYY)"),
    serie: Optional[str] = Query(None, description="Serie del documento"),
    numero: Optional[str] = Query(None, description="Número del documento"),
    estado: Optional[str] = Query(None, description="Estado del documento"),
    ruc_proveedor: Optional[str] = Query(None, description="RUC del proveedor"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Lista retenciones con filtros"""
    query = db.query(APRetencion)
    
    if serie:
        query = query.filter(APRetencion.Serie == serie)
    if numero:
        query = query.filter(APRetencion.Numero == numero)
    if estado:
        query = query.filter(APRetencion.status == estado)
    if ruc_proveedor:
        query = query.filter(APRetencion.VendorRuc == ruc_proveedor)
    
    # Paginación (SQL Server requiere ORDER BY para OFFSET)
    total = query.count()
    offset = (page - 1) * page_size
    retenciones = query.order_by(APRetencion.Id.desc()).offset(offset).limit(page_size).all()
    
    return ResponseBase(
        success=True,
        message=f"Se encontraron {total} retenciones",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "Id": r.Id,
                    "Serie": r.Serie,
                    "Numero": r.Numero,
                    "VendorRuc": r.VendorRuc,
                    "VendorName": r.VendorName,
                    "DocumentDate": r.DocumentDate,
                    "Tasa": r.Tasa,
                    "TotalRetenido": r.TotalRetenido,
                    "TotalPagado": r.TotalPagado,
                    "status": r.status,
                }
                for r in retenciones
            ]
        }
    )


@router.get("/{retencion_id}", response_model=ResponseBase)
async def obtener_retencion(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated)],
    retencion_id: int
):
    """Obtiene detalle de una retención"""
    retencion = db.query(APRetencion).filter(
        APRetencion.Id == retencion_id
    ).first()
    
    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")
    
    # Obtener último estado
    ultimo_estado = db.query(APRetencionStatus).filter(
        APRetencionStatus.Retencion == retencion_id
    ).order_by(APRetencionStatus.id.desc()).first()
    
    return ResponseBase(
        success=True,
        message="Retención encontrada",
        data={
            "cabecera": {
                "Id": retencion.Id,
                "Serie": retencion.Serie,
                "Numero": retencion.Numero,
                "VendorRuc": retencion.VendorRuc,
                "VendorName": retencion.VendorName,
                "VendorAddress": retencion.VendorAddress,
                "DocumentDate": retencion.DocumentDate,
                "Tasa": retencion.Tasa,
                "TotalRetenido": retencion.TotalRetenido,
                "TotalPagado": retencion.TotalPagado,
                "Obs": retencion.Obs,
                "status": retencion.status,
            },
            "detalles": [
                {
                    "ID": d.ID,
                    "DRserie": d.DRserie,
                    "DRnumero": d.DRnumero,
                    "DRfecha": d.DRfecha,
                    "DRmoneda": d.DRmoneda,
                    "DRtotal": d.DRtotal,
                    "DRpagoFecha": d.DRpagoFecha,
                    "Retenido": d.Retenido,
                    "Pagado": d.Pagado,
                }
                for d in retencion.detalles
            ],
            "estado_sunat": {
                "Status": ultimo_estado.Status if ultimo_estado else None,
                "Pdf": ultimo_estado.Pdf if ultimo_estado else None,
                "Xml": ultimo_estado.Xml if ultimo_estado else None,
                "Cdr": ultimo_estado.Cdr if ultimo_estado else None,
                "Descripcion": ultimo_estado.Descripcion if ultimo_estado else None,
            } if ultimo_estado else None
        }
    )


@router.post("/{retencion_id}/enviar", response_model=ResponseBase)
async def enviar_retencion(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    retencion_id: int,
    usuario: str = Query(..., description="Usuario que envía")
):
    """Envía retención a NubeFact"""
    service = DocumentService(db)
    result = await service.enviar_retencion(retencion_id, usuario)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ResponseBase(
        success=True,
        message="Retención enviada correctamente",
        data=result["data"]
    )


@router.put("/{retencion_id}", response_model=ResponseBase)
async def actualizar_retencion(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    retencion_id: int,
    datos: dict,
    usuario: str = Query(..., description="Usuario que actualiza")
):
    """Actualiza una retención (solo si está rechazada/observada)"""
    retencion = db.query(APRetencion).filter(
        APRetencion.Id == retencion_id
    ).first()
    
    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")
    
    # Verificar si puede ser editada
    service = DocumentService(db)
    if not service._puede_editar(retencion.status or ""):
        raise HTTPException(
            status_code=400,
            detail="La retención no puede ser editada en su estado actual"
        )
    
    # Actualizar campos permitidos
    campos_permitidos = [
        "VendorRuc", "VendorName", "VendorAddress",
        "Tasa", "TotalRetenido", "TotalPagado", "Obs"
    ]
    
    for campo, valor in datos.items():
        if campo in campos_permitidos and hasattr(retencion, campo):
            setattr(retencion, campo, valor)
    
    retencion.XlastUser = usuario
    retencion.XlastDate = datetime.now().timestamp()
    
    db.commit()
    
    return ResponseBase(
        success=True,
        message="Retención actualizada correctamente",
        data={"Id": retencion.Id}
    )
