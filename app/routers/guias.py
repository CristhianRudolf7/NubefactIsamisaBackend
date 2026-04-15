from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List, Annotated
from datetime import datetime
import base64

from ..database import get_db
from ..models.guias import WHTransaction, WHTransactionDetail
from ..models.guia_response import WHTransactionNube
from ..models.user import User
from ..schemas.common import ResponseBase
from ..schemas.guias import GuiaRemisionSchema, GuiaRemisionFilter
from ..services.document_service import DocumentService
from .auth import require_guias_access, require_admin

router = APIRouter(prefix="/guias", tags=["Guías de Remisión"])


@router.get("/", response_model=ResponseBase)
async def listar_guias(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_guias_access)],
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (dd-mm-YYYY)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (dd-mm-YYYY)"),
    serie: Optional[str] = Query(None, description="Serie del documento"),
    numero: Optional[str] = Query(None, description="Número del documento"),
    estado: Optional[str] = Query(None, description="Estado del documento"),
    ruc_destinatario: Optional[str] = Query(None, description="RUC del destinatario"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Lista guías de remisión con filtros"""
    query = db.query(WHTransaction)
    
    if serie:
        query = query.filter(WHTransaction.DocumentSerie == serie)
    if numero:
        query = query.filter(WHTransaction.DocumentNo == numero)
    if estado:
        query = query.filter(WHTransaction.envio_nube == estado)
    if ruc_destinatario:
        query = query.filter(WHTransaction.TargetPersonRUC == ruc_destinatario)
    
    # Paginación (SQL Server requiere ORDER BY para OFFSET)
    total = query.count()
    offset = (page - 1) * page_size
    guias = query.order_by(WHTransaction.Transaction.desc()).offset(offset).limit(page_size).all()
    
    return ResponseBase(
        success=True,
        message=f"Se encontraron {total} guías",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "Transaction": g.Transaction,
                    "DocumentSerie": g.DocumentSerie,
                    "DocumentNo": g.DocumentNo,
                    "TargetPersonRUC": g.TargetPersonRUC,
                    "TargetPersonName": g.TargetPersonName,
                    "TargetAddress": g.TargetAddress,
                    "MotivoTraslado": g.MotivoTraslado,
                    "envio_nube": g.envio_nube,
                    "Status": g.Status,
                    "error_mensaje": g.RejectionReason or g.Comments or "No hay detalles del error disponibles" if g.envio_nube and g.envio_nube.lower() in ['error', 'rechazado'] else None,
                }
                for g in guias
            ]
        }
    )


@router.get("/{transaction_id}", response_model=ResponseBase)
async def obtener_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_guias_access)],
    transaction_id: str
):
    """Obtiene detalle de una guía de remisión"""
    guia = db.query(WHTransaction).filter(
        WHTransaction.Transaction == transaction_id
    ).first()
    
    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    
    # Obtener mensaje de error si existe
    error_mensaje = None
    if guia.envio_nube and guia.envio_nube.lower() in ['error', 'rechazado']:
        error_mensaje = guia.RejectionReason or guia.Comments or "No hay detalles del error disponibles"
    
    return ResponseBase(
        success=True,
        message="Guía encontrada",
        data={
            "cabecera": {
                "Transaction": guia.Transaction,
                "DocumentSerie": guia.DocumentSerie,
                "DocumentNo": guia.DocumentNo,
                "TransactionDate": guia.TransactionDate,
                "TargetPersonRUC": guia.TargetPersonRUC,
                "TargetPersonName": guia.TargetPersonName,
                "TargetAddress": guia.TargetAddress,
                "MotivoTraslado": guia.MotivoTraslado,
                "PesoBruto": guia.PesoBruto,
                "RucTransportista": guia.RucTransportista,
                "Transportista": guia.Transportista,
                "VehicleID": guia.VehicleID,
                "Driver": guia.Driver,
                "LicenciaConducir": guia.LicenciaConducir,
                "origenaddress": guia.origenaddress,
                "ubigeo_des": guia.ubigeo_des,
                "envio_nube": guia.envio_nube,
                "Status": guia.Status,
                "Comments": guia.Comments,
                "error_mensaje": error_mensaje,
            },
            "detalles": [
                {
                    "Line": d.Line,
                    "ItemCode": d.ItemCode,
                    "ItemDescription": d.ItemDescription,
                    "Quantity": d.Quantity,
                    "Unit": d.Unit,
                }
                for d in guia.detalles
            ]
        }
    )


@router.post("/{transaction_id}/enviar", response_model=ResponseBase)
async def enviar_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    transaction_id: str,
    usuario: str = Query(..., description="Usuario que envía")
):
    """Envía guía de remisión a NubeFact"""
    service = DocumentService(db)
    result = await service.enviar_guia(transaction_id, usuario)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ResponseBase(
        success=True,
        message="Guía enviada correctamente",
        data=result["data"]
    )


@router.put("/{transaction_id}", response_model=ResponseBase)
async def actualizar_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    transaction_id: str,
    datos: dict,
    usuario: str = Query(..., description="Usuario que actualiza")
):
    """Actualiza una guía de remisión (solo si está rechazada/observada)"""
    guia = db.query(WHTransaction).filter(
        WHTransaction.Transaction == transaction_id
    ).first()
    
    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    
    # Verificar si puede ser editada
    service = DocumentService(db)
    if not service._puede_editar(guia.envio_nube or ""):
        raise HTTPException(
            status_code=400,
            detail="La guía no puede ser editada en su estado actual"
        )
    
    # Actualizar campos permitidos
    campos_permitidos = [
        "TargetPersonRUC", "TargetPersonName", "TargetAddress",
        "MotivoTraslado", "PesoBruto", "RucTransportista",
        "Transportista", "VehicleID", "Driver", "LicenciaConducir",
        "origenaddress", "ubigeo_des", "Comments"
    ]
    
    for campo, valor in datos.items():
        if campo in campos_permitidos and hasattr(guia, campo):
            setattr(guia, campo, valor)
    
    guia.XLastUser = usuario
    guia.XLastDate = datetime.now().timestamp()
    
    db.commit()
    
    return ResponseBase(
        success=True,
        message="Guía actualizada correctamente",
        data={"Transaction": guia.Transaction}
    )


@router.get("/{transaction_id}/pdf")
async def descargar_pdf_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_guias_access)],
    transaction_id: str
):
    """Descarga el PDF de la guía de remisión"""
    guia = db.query(WHTransaction).filter(WHTransaction.Transaction == transaction_id).first()
    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")

    nube_response = db.query(WHTransactionNube).filter(
        WHTransactionNube.TransactionId == transaction_id
    ).order_by(WHTransactionNube.id.desc()).first()

    if not nube_response:
        raise HTTPException(status_code=404, detail="Guía no enviada a NubeFact")

    # Si hay URL de NubeFact, redirigir
    if nube_response.enlace_del_pdf:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=nube_response.enlace_del_pdf)

    # Si hay base64, decodificar
    if nube_response.pdf_zip_base64:
        pdf_bytes = base64.b64decode(nube_response.pdf_zip_base64)
        filename = f"{guia.DocumentSerie}-{guia.DocumentNo}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    raise HTTPException(status_code=404, detail="PDF no disponible")


@router.get("/{transaction_id}/xml")
async def descargar_xml_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_guias_access)],
    transaction_id: str
):
    """Descarga el XML de la guía de remisión"""
    guia = db.query(WHTransaction).filter(WHTransaction.Transaction == transaction_id).first()
    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")

    nube_response = db.query(WHTransactionNube).filter(
        WHTransactionNube.TransactionId == transaction_id
    ).order_by(WHTransactionNube.id.desc()).first()

    if not nube_response:
        raise HTTPException(status_code=404, detail="Guía no enviada a NubeFact")

    # Si hay URL de NubeFact, redirigir
    if nube_response.enlace_del_xml:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=nube_response.enlace_del_xml)

    # Si hay base64, decodificar
    if nube_response.xml_zip_base64:
        xml_bytes = base64.b64decode(nube_response.xml_zip_base64)
        filename = f"{guia.DocumentSerie}-{guia.DocumentNo}.xml"
        return Response(
            content=xml_bytes,
            media_type="application/xml",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    raise HTTPException(status_code=404, detail="XML no disponible")


@router.get("/{transaction_id}/cdr")
async def descargar_cdr_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_guias_access)],
    transaction_id: str
):
    """Descarga el CDR de la guía de remisión"""
    guia = db.query(WHTransaction).filter(WHTransaction.Transaction == transaction_id).first()
    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")

    nube_response = db.query(WHTransactionNube).filter(
        WHTransactionNube.TransactionId == transaction_id
    ).order_by(WHTransactionNube.id.desc()).first()

    if not nube_response:
        raise HTTPException(status_code=404, detail="Guía no enviada a NubeFact")

    # Si hay URL de NubeFact, redirigir
    if nube_response.enlace_del_cdr:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=nube_response.enlace_del_cdr)

    # Si hay base64, decodificar
    if nube_response.cdr_zip_base64:
        cdr_bytes = base64.b64decode(nube_response.cdr_zip_base64)
        filename = f"R-{guia.DocumentSerie}-{guia.DocumentNo}.zip"
        return Response(
            content=cdr_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    raise HTTPException(status_code=404, detail="CDR no disponible")
