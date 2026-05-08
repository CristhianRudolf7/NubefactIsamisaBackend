from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from typing import Optional, List, Annotated
import base64
import asyncio
from datetime import datetime

from ..database import get_db
from ..models.guias import WHTransaction, WHTransactionDetail
from ..models.guia_response import WHTransactionNube
import json
from ..models.auditoria import Auditoria
from ..models.user import User, UserRole
from ..schemas.common import ResponseBase, BulkEnviarRequest
from ..schemas.guias import GuiaRemisionSchema, GuiaRemisionFilter
from ..services.document_service import DocumentService
from ..services.auditoria_service import AuditoriaService
from ..services.notification_service import NotificationService
from ..utils import get_client_ip
from ..utils.datetime import now_peru
from .auth import require_guias_access, require_admin

router = APIRouter(prefix="/guias", tags=["Guías de Remisión"])


def date_to_excel(date_str: str) -> float:
    """Convierte string dd-mm-YYYY [HH:mm] a float de Excel"""
    try:
        # Intentar con fecha y hora
        try:
            dt = datetime.strptime(date_str, "%d-%m-%Y %H:%M")
        except ValueError:
            # Fallback a solo fecha
            dt = datetime.strptime(date_str, "%d-%m-%Y")
            
        # Ajustamos a 1899-12-31 como base para coincidir con el almacenamiento de la BD
        excel_epoch = datetime(1899, 12, 31)
        delta = dt - excel_epoch
        # delta.total_seconds() / (24 * 3600) da la fracción exacta de días
        return float(delta.total_seconds() / (24 * 3600))
    except:
        return 0.0


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
    query = db.query(WHTransaction)
    
    if fecha_inicio:
        query = query.filter(WHTransaction.TransactionDate >= date_to_excel(fecha_inicio))
    if fecha_fin:
        # Si la fecha_fin solo tiene fecha (10 caracteres), sumar el día completo
        # Si tiene hora, usar el valor exacto
        excel_fin = date_to_excel(fecha_fin)
        if len(fecha_fin) <= 10:
            excel_fin += 0.99999
        query = query.filter(WHTransaction.TransactionDate <= excel_fin)
    
    if serie:
        query = query.filter(WHTransaction.DocumentSerie == serie)
    if numero:
        query = query.filter(WHTransaction.DocumentNo == numero)
    if estado:
        estado_lower = estado.lower()
        if estado_lower == 'pendiente':
            query = query.filter(or_(WHTransaction.envio_nube == None, WHTransaction.envio_nube == '', func.lower(WHTransaction.envio_nube) == 'pendiente'))
        elif estado_lower == 'aceptado':
            query = query.filter(func.lower(WHTransaction.envio_nube).in_(['aceptado', 'aceptada']))
        elif estado_lower == 'rechazado':
            query = query.filter(func.lower(WHTransaction.envio_nube).in_(['rechazado', 'rechazada']))
        else:
            query = query.filter(func.lower(WHTransaction.envio_nube) == estado_lower)
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
                    "necesita_aprobacion": g.necesita_aprobacion,
                    "aprobacion_usuario": g.aprobacion_usuario,
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


async def procesar_envio_masivo_guias(ids: List[str], usuario: str, db: Session):
    """Función de fondo para procesar múltiples guías"""
    service = DocumentService(db)
    for trans_id in ids:
        try:
            result = await service.enviar_guia(trans_id, usuario)
            if not result.get("success", False):
                print(f"Error devuelto por servicio para {trans_id}: {result.get('message')}")
                guia = db.query(WHTransaction).filter(WHTransaction.Transaction == trans_id).first()
                if guia and guia.Status in ["pendiente", "error"] and not guia.necesita_aprobacion:
                    guia.Status = "error"
                    db.commit()
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Excepción en envío masivo para guía {trans_id}: {e}")
            try:
                guia = db.query(WHTransaction).filter(WHTransaction.Transaction == trans_id).first()
                if guia and guia.Status in ["pendiente", "error"] and not guia.necesita_aprobacion:
                    guia.Status = "error"
                    db.commit()
            except:
                db.rollback()


@router.post("/bulk-enviar", response_model=ResponseBase)
async def enviar_masivo_guias(
    request: BulkEnviarRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)]
):
    """Inicia el proceso de envío masivo de guías"""
    background_tasks.add_task(
        procesar_envio_masivo_guias,
        request.ids,
        request.usuario,
        db
    )
    
    return ResponseBase(
        success=True,
        message=f"Se ha iniciado el proceso de envío para {len(request.ids)} guías"
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
    current_user: Annotated[User, Depends(require_guias_access)],
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
    
    # Lógica de aprobación: Trabajadores requieren aprobación, Admins no.
    if current_user.rol == UserRole.TRABAJADOR:
        guia.necesita_aprobacion = True
    else:
        guia.necesita_aprobacion = False
        guia.aprobacion_usuario = usuario
    
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
        tabla="WH_Transaction",
        registro_id=guia.Transaction,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
        usuario=usuario,
        ip=get_client_ip(request)
    )
    
    # Notificar edición por WhatsApp
    notification_service = NotificationService(db)
    await notification_service.notificar_edicion_documento(
        tipo_modulo="guias",
        tipo_documento="guia",
        serie=guia.DocumentSerie,
        numero=guia.DocumentNo,
        usuario=usuario,
        documento_id=guia.Transaction
    )
    
    return ResponseBase(
        success=True,
        message="Guía actualizada correctamente",
        data={"Transaction": guia.Transaction}
    )


@router.post("/{transaction_id}/aprobar", response_model=ResponseBase)
async def aprobar_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    transaction_id: str,
    usuario: str = Query(..., description="Usuario que aprueba")
):
    """Aprueba una edición realizada por un trabajador"""
    guia = db.query(WHTransaction).filter(WHTransaction.Transaction == transaction_id).first()
    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    
    guia.necesita_aprobacion = False
    guia.aprobacion_usuario = usuario
    db.commit()
    
    return ResponseBase(success=True, message="Guía aprobada correctamente")


@router.post("/{transaction_id}/rechazar", response_model=ResponseBase)
async def rechazar_guia(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    transaction_id: str
):
    """Rechaza los cambios y restaura la versión anterior"""
    guia = db.query(WHTransaction).filter(WHTransaction.Transaction == transaction_id).first()
    if not guia:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    
    # Buscar el último registro de auditoría de tipo UPDATE para este documento
    ultimo_cambio = db.query(Auditoria).filter(
        Auditoria.tabla == "WH_Transaction",
        Auditoria.registro_id == transaction_id,
        Auditoria.accion == "UPDATE"
    ).order_by(Auditoria.fecha.desc()).first()
    
    if not ultimo_cambio or not ultimo_cambio.datos_anteriores:
        guia.necesita_aprobacion = False
        db.commit()
        return ResponseBase(success=True, message="Flag de aprobación removido (sin historial para restaurar)")

    try:
        anteriores = json.loads(ultimo_cambio.datos_anteriores)
        
        # Restaurar cabecera
        for key, value in anteriores.items():
            if key == "detalles": continue
            if hasattr(guia, key):
                setattr(guia, key, value)
        
        # Restaurar detalles
        if "detalles" in anteriores:
            db.query(WHTransactionDetail).filter(WHTransactionDetail.Transaction == transaction_id).delete()
            for det in anteriores["detalles"]:
                campos_modelo = WHTransactionDetail.__table__.columns.keys()
                det_filtrado = {k: v for k, v in det.items() if k in campos_modelo}
                nuevo_det = WHTransactionDetail(**det_filtrado)
                db.add(nuevo_det)
                
        guia.necesita_aprobacion = False
        db.commit()
        return ResponseBase(success=True, message="Cambios rechazados y versión anterior restaurada")
    except Exception as e:
        db.rollback()
        return ResponseBase(success=False, message=f"Error al restaurar versión: {str(e)}")


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
        guia.nube_status_web = "anulado"
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
