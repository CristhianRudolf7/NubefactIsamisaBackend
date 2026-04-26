from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List, Annotated
import base64

from ..database import get_db
from ..models.guias import WHTransaction, WHTransactionDetail
from ..models.guia_response import WHTransactionNube
from ..models.user import User
from ..schemas.common import ResponseBase
from ..schemas.guias import GuiaRemisionSchema, GuiaRemisionFilter
from ..services.document_service import DocumentService
from ..services.auditoria_service import AuditoriaService
from ..utils import get_client_ip
from ..utils.datetime import now_peru
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
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    transaction_id: str,
    usuario: str = Query(..., description="Usuario que envía")
):
    """Envía guía de remisión a NubeFact"""
    # Obtener guía antes de enviar
    guia = db.query(WHTransaction).filter(WHTransaction.Transaction == transaction_id).first()
    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")

    # Obtener detalles de la guía
    detalles = db.query(WHTransactionDetail).filter(WHTransactionDetail.Transaction == transaction_id).all()

    datos_guia = {
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
        },
        "detalles": [
            {
                "Line": d.Line,
                "ItemCode": d.ItemCode,
                "ItemDescription": d.ItemDescription,
                "Quantity": d.Quantity,
                "Unit": d.Unit,
            }
            for d in detalles
        ]
    }
    
    service = DocumentService(db)
    result = await service.enviar_guia(transaction_id, usuario)
    
    # Registrar auditoría
    auditoria = AuditoriaService(db)
    auditoria.registrar_envio(
        tabla="guias",
        registro_id=guia.Transaction,
        datos_documento=datos_guia,
        usuario=usuario,
        respuesta_nubefact=result.get("data"),
        ip=get_client_ip(request)
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ResponseBase(
        success=True,
        message="Guía enviada correctamente",
        data=result["data"]
    )


@router.post("/{transaction_id}/consultar", response_model=ResponseBase)
async def consultar_estado_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    transaction_id: str
):
    """Consulta el estado de la guía en NubeFact/SUNAT"""
    service = DocumentService(db)
    result = await service.consultar_guia(transaction_id)
    
    return ResponseBase(
        success=result["success"],
        message=result["message"],
        data=result.get("data")
    )


@router.put("/{transaction_id}", response_model=ResponseBase)
async def actualizar_guia(
    request: Request,
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
    
    # Guardar datos anteriores para auditoría
    datos_anteriores = {
        "Transaction": guia.Transaction,
        "TargetPersonRUC": guia.TargetPersonRUC,
        "TargetPersonName": guia.TargetPersonName,
        "TargetAddress": guia.TargetAddress,
        "MotivoTraslado": guia.MotivoTraslado,
        "PesoBruto": guia.PesoBruto,
        "RucTransportista": guia.RucTransportista,
        "Transportista": guia.Transportista,
        "VehicleID": guia.VehicleID,
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
    
    # Actualizar campos permitidos
    campos_permitidos = [
        "origenaddress", "ubigeo_des", # Remitente
        "TargetPersonRUC", "TargetPersonName", "TargetAddress", # Destinatario
        "RucTransportista", "Transportista", "VehicleID", "LicenciaConducir", # Transportista
        "SaleDocSerie", "SaleDocNo", # Documento de referencia
        "MotivoTraslado", "PesoBruto" # Otros
    ]
    
    for campo, valor in datos.items():
        if campo in campos_permitidos and hasattr(guia, campo):
            setattr(guia, campo, valor)
            
    # Manejar campos especiales de conductor
    if "DriverDNI" in datos:
        guia.DriverId = datos["DriverDNI"]
    
    if "DriverNombre" in datos or "DriverApellido" in datos:
        # Reconstruir Driver como "Apellido Nombre" (asumiendo que el servicio espera este orden)
        # El servicio actual hace: 
        # conductor_nombre=guia.Driver.split()[2]
        # conductor_apellidos=f"{guia.Driver.split()[0]} {guia.Driver.split()[1]}"
        # Así que esperamos "Apellido1 Apellido2 Nombre"
        nombre = datos.get("DriverNombre", "")
        apellido = datos.get("DriverApellido", "")
        guia.Driver = f"{apellido} {nombre}".strip()
    
    guia.XLastUser = usuario
    guia.XLastDate = now_peru().timestamp()
    
    db.commit()
    
    # Registrar auditoría
    datos_nuevos = {
        "Transaction": guia.Transaction,
        "TargetPersonRUC": guia.TargetPersonRUC,
        "TargetPersonName": guia.TargetPersonName,
        "TargetAddress": guia.TargetAddress,
        "MotivoTraslado": guia.MotivoTraslado,
        "PesoBruto": guia.PesoBruto,
        "RucTransportista": guia.RucTransportista,
        "Transportista": guia.Transportista,
        "VehicleID": guia.VehicleID,
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
    auditoria = AuditoriaService(db)
    auditoria.registrar_cambio(
        tabla="guias",
        registro_id=guia.Transaction,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
        usuario=usuario,
        ip=get_client_ip(request)
    )
    
    return ResponseBase(
        success=True,
        message="Guía actualizada correctamente",
        data={"Transaction": guia.Transaction}
    )


@router.post("/{transaction_id}/anular", response_model=ResponseBase)
async def anular_guia(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    transaction_id: str,
    motivo: str = Query(..., description="Motivo de anulación"),
    usuario: str = Query(..., description="Usuario que anula")
):
    """Genera guía de anulación"""
    guia = db.query(WHTransaction).filter(
        WHTransaction.Transaction == transaction_id
    ).first()

    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")

    if guia.envio_nube != "enviado":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden anular guías enviadas"
        )

    # Obtener detalles de la guía
    detalles = db.query(WHTransactionDetail).filter(WHTransactionDetail.Transaction == transaction_id).all()

    # Guardar datos para auditoría
    datos_guia = {
        "cabecera": {
            "Transaction": guia.Transaction,
            "DocumentSerie": guia.DocumentSerie,
            "DocumentNo": guia.DocumentNo,
            "TargetPersonRUC": guia.TargetPersonRUC,
            "TargetPersonName": guia.TargetPersonName,
            "MotivoTraslado": guia.MotivoTraslado,
        },
        "detalles": [
            {
                "Line": d.Line,
                "ItemCode": d.ItemCode,
                "ItemDescription": d.ItemDescription,
                "Quantity": d.Quantity,
            }
            for d in detalles
        ]
    }
    
    # Enviar anulación a NubeFact (tipo 9 = guía de remisión)
    from ..services.nubefact_client import nubefact_client
    response = await nubefact_client.generar_anulacion(
        tipo_comprobante=9,  # Guía de remisión
        serie=guia.DocumentSerie,
        numero=guia.DocumentNo,
        motivo=motivo
    )
    
    if response.success:
        guia.envio_nube = "anulado"
        guia.XLastUser = usuario
        guia.XLastDate = now_peru().timestamp()
        db.commit()
    
    # Registrar auditoría
    auditoria = AuditoriaService(db)
    auditoria.registrar_anulacion(
        tabla="guias",
        registro_id=guia.Transaction,
        datos_anteriores=datos_guia,
        motivo=motivo,
        usuario=usuario,
        respuesta_nubefact=response.model_dump(exclude_none=True),
        ip=get_client_ip(request)
    )
    
    return ResponseBase(
        success=response.success,
        message="Anulación procesada" if response.success else "Error en anulación",
        data=response.model_dump(exclude_none=True)
    )


@router.get("/{transaction_id}/pdf")
async def descargar_pdf_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_guias_access)],
    transaction_id: str
):
    """Descarga el PDF de la guía de remisión"""
    import httpx
    
    guia = db.query(WHTransaction).filter(WHTransaction.Transaction == transaction_id).first()
    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")

    nube_response = db.query(WHTransactionNube).filter(
        WHTransactionNube.TransactionId == transaction_id
    ).order_by(WHTransactionNube.id.desc()).first()

    if not nube_response:
        raise HTTPException(status_code=404, detail="Guía no enviada a NubeFact")

    # Si hay base64, decodificar y devolver
    if nube_response.pdf_zip_base64:
        pdf_bytes = base64.b64decode(nube_response.pdf_zip_base64)
        filename = f"{guia.DocumentSerie}-{guia.DocumentNo}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    # Si hay URL de NubeFact, descargar el PDF y devolverlo
    if nube_response.enlace_del_pdf:
        try:
            async with httpx.AsyncClient() as client:
                pdf_response = await client.get(nube_response.enlace_del_pdf, timeout=30.0)
                if pdf_response.status_code == 200:
                    filename = f"{guia.DocumentSerie}-{guia.DocumentNo}.pdf"
                    return Response(
                        content=pdf_response.content,
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
                    )
        except Exception as e:
            print(f"Error descargando PDF de NubeFact: {e}")

    # Si no hay PDF, consultar a NubeFact para ver si ya está disponible
    from ..services.document_service import DocumentService
    service = DocumentService(db)
    result = await service.consultar_guia(transaction_id)
    
    # Revisar si ahora hay PDF disponible
    db.refresh(nube_response)
    
    # Intentar descargar de la URL
    if nube_response.enlace_del_pdf:
        try:
            async with httpx.AsyncClient() as client:
                pdf_response = await client.get(nube_response.enlace_del_pdf, timeout=30.0)
                if pdf_response.status_code == 200:
                    filename = f"{guia.DocumentSerie}-{guia.DocumentNo}.pdf"
                    return Response(
                        content=pdf_response.content,
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
                    )
        except Exception as e:
            print(f"Error descargando PDF de NubeFact: {e}")
    
    # Intentar con base64
    if nube_response.pdf_zip_base64:
        pdf_bytes = base64.b64decode(nube_response.pdf_zip_base64)
        filename = f"{guia.DocumentSerie}-{guia.DocumentNo}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    # Mensaje más informativo según el estado
    if guia.envio_nube == "enviado":
        raise HTTPException(
            status_code=404, 
            detail="SUNAT aún no ha aceptado la guía. Intente nuevamente en unos segundos."
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
