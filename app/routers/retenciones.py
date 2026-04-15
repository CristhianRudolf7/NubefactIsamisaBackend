from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List, Annotated
from datetime import datetime
import base64

from ..database import get_db
from ..models.retenciones import APRetencion, APRetencionDetail, APRetencionStatus
from ..models.user import User
from ..schemas.common import ResponseBase
from ..schemas.retenciones import RetencionSchema, RetencionFilter
from ..services.document_service import DocumentService
from .auth import require_retenciones_access, require_admin

router = APIRouter(prefix="/retenciones", tags=["Retenciones"])


@router.get("/", response_model=ResponseBase)
async def listar_retenciones(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_retenciones_access)],
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
    
    # Obtener errores para retenciones con estado error/rechazado
    errores_status = {}
    retencion_ids = [r.Id for r in retenciones if r.status and r.status.lower() in ['error', 'rechazado']]
    if retencion_ids:
        for ret_id in retencion_ids:
            ultimo_estado = db.query(APRetencionStatus).filter(
                APRetencionStatus.Retencion == ret_id
            ).order_by(APRetencionStatus.id.desc()).first()
            if ultimo_estado:
                error_msg = ultimo_estado.error or ultimo_estado.Soap or ultimo_estado.Descripcion or None
                if error_msg:
                    errores_status[ret_id] = error_msg
                else:
                    errores_status[ret_id] = "No hay detalles del error disponibles"
            else:
                errores_status[ret_id] = "No hay detalles del error disponibles"
    
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
                    "error_mensaje": errores_status.get(r.Id),
                }
                for r in retenciones
            ]
        }
    )


@router.get("/{retencion_id}", response_model=ResponseBase)
async def obtener_retencion(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_retenciones_access)],
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
    
    # Obtener mensaje de error si existe
    error_mensaje = None
    if retencion.status and retencion.status.lower() in ['error', 'rechazado']:
        if ultimo_estado:
            error_mensaje = ultimo_estado.error or ultimo_estado.Soap or ultimo_estado.Descripcion or "No hay detalles del error disponibles"
        else:
            error_mensaje = "No hay detalles del error disponibles"
    
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
                "error_mensaje": error_mensaje,
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
        "Tasa", "TotalRetenido", "TotalPagado", "Obs", "DocumentDate"
    ]
    
    for campo, valor in datos.items():
        if campo in campos_permitidos and hasattr(retencion, campo):
            # Convertir fecha de string DD-MM-YYYY a número de Excel
            if campo == "DocumentDate" and valor:
                from datetime import datetime
                try:
                    fecha = datetime.strptime(str(valor), "%d-%m-%Y")
                    # Número de días desde 1899-12-30 (base de Excel)
                    valor = (fecha - datetime(1899, 12, 30)).days
                except ValueError:
                    pass  # Si no se puede parsear, dejar el valor original
            setattr(retencion, campo, valor)
    
    retencion.XlastUser = usuario
    retencion.XlastDate = datetime.now().timestamp()
    
    db.commit()
    
    return ResponseBase(
        success=True,
        message="Retención actualizada correctamente",
        data={"Id": retencion.Id}
    )


@router.get("/{retencion_id}/pdf")
async def descargar_pdf_retencion(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_retenciones_access)],
    retencion_id: int
):
    """Descarga el PDF de la retención"""
    retencion = db.query(APRetencion).filter(APRetencion.Id == retencion_id).first()
    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")
    
    estado = db.query(APRetencionStatus).filter(
        APRetencionStatus.Retencion == retencion_id
    ).order_by(APRetencionStatus.id.desc()).first()
    
    if not estado or not estado.Pdf:
        raise HTTPException(status_code=404, detail="PDF no disponible")
    
    # Si es base64, decodificar; si es URL, redirigir
    if estado.Pdf.startswith('http'):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=estado.Pdf)
    
    pdf_bytes = base64.b64decode(estado.Pdf)
    filename = f"{retencion.Serie}-{retencion.Numero}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{retencion_id}/xml")
async def descargar_xml_retencion(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_retenciones_access)],
    retencion_id: int
):
    """Descarga el XML de la retención"""
    retencion = db.query(APRetencion).filter(APRetencion.Id == retencion_id).first()
    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")
    
    estado = db.query(APRetencionStatus).filter(
        APRetencionStatus.Retencion == retencion_id
    ).order_by(APRetencionStatus.id.desc()).first()
    
    if not estado or not estado.Xml:
        raise HTTPException(status_code=404, detail="XML no disponible")
    
    if estado.Xml.startswith('http'):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=estado.Xml)
    
    xml_bytes = base64.b64decode(estado.Xml)
    filename = f"{retencion.Serie}-{retencion.Numero}.xml"
    
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{retencion_id}/cdr")
async def descargar_cdr_retencion(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_retenciones_access)],
    retencion_id: int
):
    """Descarga el CDR de la retención"""
    retencion = db.query(APRetencion).filter(APRetencion.Id == retencion_id).first()
    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")
    
    estado = db.query(APRetencionStatus).filter(
        APRetencionStatus.Retencion == retencion_id
    ).order_by(APRetencionStatus.id.desc()).first()
    
    if not estado or not estado.Cdr:
        raise HTTPException(status_code=404, detail="CDR no disponible")
    
    if estado.Cdr.startswith('http'):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=estado.Cdr)
    
    cdr_bytes = base64.b64decode(estado.Cdr)
    filename = f"R-{retencion.Serie}-{retencion.Numero}.zip"
    
    return Response(
        content=cdr_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
