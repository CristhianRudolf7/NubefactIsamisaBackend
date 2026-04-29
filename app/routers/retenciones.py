from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from typing import Optional, List, Annotated
import base64
import asyncio
from datetime import datetime

from ..database import get_db
from ..models.retenciones import APRetencion, APRetencionDetail, APRetencionStatus
import json
from ..models.auditoria import Auditoria
from ..models.user import User, UserRole
from ..schemas.common import ResponseBase, BulkEnviarRequest
from ..schemas.retenciones import RetencionSchema, RetencionFilter
from ..services.document_service import DocumentService
from ..services.auditoria_service import AuditoriaService
from ..services.notification_service import NotificationService
from ..utils import get_client_ip
from ..utils.datetime import now_peru
from .auth import require_retenciones_access, require_admin

router = APIRouter(prefix="/retenciones", tags=["Retenciones"])


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
    query = db.query(APRetencion)
    
    if fecha_inicio:
        query = query.filter(APRetencion.DocumentDate >= date_to_excel(fecha_inicio))
    if fecha_fin:
        # Si la fecha_fin solo tiene fecha (10 caracteres), sumar el día completo
        # Si tiene hora, usar el valor exacto
        excel_fin = date_to_excel(fecha_fin)
        if len(fecha_fin) <= 10:
            excel_fin += 0.99999
        query = query.filter(APRetencion.DocumentDate <= excel_fin)
    
    if serie:
        query = query.filter(APRetencion.Serie == serie)
    if numero:
        query = query.filter(APRetencion.Numero == numero)
    if estado:
        estado_lower = estado.lower()
        if estado_lower == 'pendiente':
            query = query.filter(or_(APRetencion.status == None, APRetencion.status == '', func.lower(APRetencion.status) == 'pendiente'))
        elif estado_lower == 'aceptado':
            query = query.filter(func.lower(APRetencion.status).in_(['aceptado', 'aceptada']))
        elif estado_lower == 'rechazado':
            query = query.filter(func.lower(APRetencion.status).in_(['rechazado', 'rechazada']))
        else:
            query = query.filter(func.lower(APRetencion.status) == estado_lower)
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
                    "necesita_aprobacion": r.necesita_aprobacion,
                    "aprobacion_usuario": r.aprobacion_usuario,
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
                    "DRpagoNro": d.DRpagoNro,
                    "DRpagoTotal": d.DRpagoTotal,
                    "TipoCambio": d.TipoCambio,
                    "TipoCambioFecha": d.TipoCambioFecha,
                    "Retenido": d.Retenido,
                    "RetenidoFecha": d.RetenidoFecha,
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
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    retencion_id: int,
    usuario: str = Query(..., description="Usuario que envía")
):
    """Envía retención a NubeFact"""
    # Obtener retención antes de enviar
    retencion = db.query(APRetencion).filter(APRetencion.Id == retencion_id).first()
    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")

    # Obtener detalles de la retención
    detalles = db.query(APRetencionDetail).filter(APRetencionDetail.Retencion == retencion_id).all()

    datos_retencion = {
        "cabecera": {
            "Id": retencion.Id,
            "Serie": retencion.Serie,
            "Numero": retencion.Numero,
            "DocumentDate": retencion.DocumentDate,
            "VendorRuc": retencion.VendorRuc,
            "VendorName": retencion.VendorName,
            "VendorAddress": retencion.VendorAddress,
            "Tasa": retencion.Tasa,
            "TotalRetenido": retencion.TotalRetenido,
            "TotalPagado": retencion.TotalPagado,
        },
        "detalles": [
            {
                "Line": d.ID,
                "DRserie": d.DRserie,
                "DRnumero": d.DRnumero,
                "DRfecha": d.DRfecha,
                "DRtotal": d.DRtotal,
                "Retenido": d.Retenido,
                "Pagado": d.Pagado,
            }
            for d in detalles
        ]
    }
    
    service = DocumentService(db)
    result = await service.enviar_retencion(retencion_id, usuario)
    
    # Registrar auditoría
    auditoria = AuditoriaService(db)
    auditoria.registrar_envio(
        tabla="retenciones",
        registro_id=retencion.Id,
        datos_documento=datos_retencion,
        usuario=usuario,
        respuesta_nubefact=result.get("data"),
        ip=get_client_ip(request)
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ResponseBase(
        success=True,
        message="Retención enviada correctamente",
        data=result["data"]
    )


async def procesar_envio_masivo_retenciones(ids: List[str], usuario: str, db: Session):
    """Función de fondo para procesar múltiples retenciones"""
    service = DocumentService(db)
    for ret_id in ids:
        try:
            result = await service.enviar_retencion(int(ret_id), usuario)
            if not result.get("success", False):
                print(f"Error devuelto por servicio para retención {ret_id}: {result.get('message')}")
                ret = db.query(APRetencion).filter(APRetencion.Id == int(ret_id)).first()
                if ret and ret.status in ["pendiente", "error"] and not ret.necesita_aprobacion:
                    ret.status = "error"
                    
                    status_record = APRetencionStatus(
                        RetencionId=int(ret_id),
                        Status="error",
                        Message=result.get("message", "Error al enviar"),
                        RawResponse="",
                        CreatedBy=usuario,
                        CreatedAt=now_peru()
                    )
                    db.add(status_record)
                    db.commit()
            await asyncio.sleep(1)
        except Exception as e:
            error_msg = str(e)
            print(f"Excepción en envío masivo para retención {ret_id}: {error_msg}")
            # Marcar como error en la base de datos para que el usuario lo vea
            try:
                ret = db.query(APRetencion).filter(APRetencion.Id == int(ret_id)).first()
                if ret and ret.status in ["pendiente", "error"] and not ret.necesita_aprobacion:
                    ret.status = "error"
                    
                    # Registrar el error en APRetencionStatus
                    status_record = APRetencionStatus(
                        Retencion=ret.Id,
                        Status="error",
                        error=error_msg,
                        XlastUser=usuario,
                        XlastDate=now_peru().timestamp(),
                    )
                    db.add(status_record)
                    db.commit()
            except Exception as db_e:
                print(f"Error al guardar estado de error en DB: {db_e}")
                db.rollback()


@router.post("/bulk-enviar", response_model=ResponseBase)
async def enviar_masivo_retenciones(
    request: BulkEnviarRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)]
):
    """Inicia el proceso de envío masivo de retenciones"""
    background_tasks.add_task(
        procesar_envio_masivo_retenciones,
        request.ids,
        request.usuario,
        db
    )
    
    return ResponseBase(
        success=True,
        message=f"Se ha iniciado el proceso de envío para {len(request.ids)} retenciones"
    )


@router.put("/{retencion_id}", response_model=ResponseBase)
async def actualizar_retencion(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_retenciones_access)],
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
    
    # Guardar datos anteriores para auditoría
    datos_anteriores = {
        "Id": retencion.Id,
        "Serie": retencion.Serie,
        "Numero": retencion.Numero,
        "VendorRuc": retencion.VendorRuc,
        "VendorName": retencion.VendorName,
        "VendorAddress": retencion.VendorAddress,
        "Tasa": retencion.Tasa,
        "TotalRetenido": retencion.TotalRetenido,
        "TotalPagado": retencion.TotalPagado,
        "detalles": [
            {
                "ID": d.ID,
                "DRserie": d.DRserie,
                "DRnumero": d.DRnumero,
                "DRfecha": d.DRfecha,
                "Retenido": d.Retenido,
                "Pagado": d.Pagado,
            }
            for d in retencion.detalles
        ]
    }
    
    # Actualizar campos permitidos (Monto retenido y Monto Pagado)
    campos_permitidos = ["TotalRetenido", "TotalPagado"]
    
    for campo, valor in datos.items():
        if campo in campos_permitidos and hasattr(retencion, campo):
            setattr(retencion, campo, valor)
    
    # Actualizar detalles si se proporcionan (Monto retenido, Monto Pagado, Nro de pago)
    if "detalles" in datos and isinstance(datos["detalles"], list):
        for det_data in datos["detalles"]:
            if "ID" in det_data:
                detalle = db.query(APRetencionDetail).filter(
                    APRetencionDetail.ID == det_data["ID"]
                ).first()
                if detalle:
                    # Actualizar campos permitidos del detalle
                    if "DRpagoNro" in det_data:
                        detalle.DRpagoNro = det_data["DRpagoNro"]
                    if "Retenido" in det_data:
                        detalle.Retenido = det_data["Retenido"]
                    if "Pagado" in det_data:
                        detalle.Pagado = det_data["Pagado"]
    
    retencion.XlastUser = usuario
    retencion.XlastDate = now_peru().timestamp()
    
    # Lógica de aprobación: Trabajadores requieren aprobación, Admins no.
    if current_user.rol == UserRole.TRABAJADOR:
        retencion.necesita_aprobacion = True
    else:
        retencion.necesita_aprobacion = False
        retencion.aprobacion_usuario = usuario
    
    db.commit()
    
    # Registrar auditoría
    datos_nuevos = {
        "Id": retencion.Id,
        "Serie": retencion.Serie,
        "Numero": retencion.Numero,
        "VendorRuc": retencion.VendorRuc,
        "VendorName": retencion.VendorName,
        "VendorAddress": retencion.VendorAddress,
        "Tasa": retencion.Tasa,
        "TotalRetenido": retencion.TotalRetenido,
        "TotalPagado": retencion.TotalPagado,
        "detalles": [
            {
                "ID": d.ID,
                "DRserie": d.DRserie,
                "DRnumero": d.DRnumero,
                "DRfecha": d.DRfecha,
                "Retenido": d.Retenido,
                "Pagado": d.Pagado,
            }
            for d in retencion.detalles
        ]
    }
    auditoria = AuditoriaService(db)
    auditoria.registrar_cambio(
        tabla="AP_Retencion",
        registro_id=retencion.Id,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
        usuario=usuario,
        ip=get_client_ip(request)
    )
    
    # Notificar edición por WhatsApp
    notification_service = NotificationService(db)
    await notification_service.notificar_edicion_documento(
        tipo_modulo="retenciones",
        tipo_documento="retencion",
        serie=retencion.Serie,
        numero=retencion.Numero,
        usuario=usuario,
        documento_id=str(retencion.Id)
    )
    
    return ResponseBase(
        success=True,
        message="Retención actualizada correctamente",
        data={"Id": retencion.Id}
    )


@router.post("/{retencion_id}/aprobar", response_model=ResponseBase)
async def aprobar_retencion(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    retencion_id: int,
    usuario: str = Query(..., description="Usuario que aprueba")
):
    """Aprueba una edición realizada por un trabajador"""
    retencion = db.query(APRetencion).filter(APRetencion.Id == retencion_id).first()
    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")
    
    retencion.necesita_aprobacion = False
    retencion.aprobacion_usuario = usuario
    db.commit()
    
    return ResponseBase(success=True, message="Retención aprobada correctamente")


@router.post("/{retencion_id}/rechazar", response_model=ResponseBase)
async def rechazar_retencion(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    retencion_id: int
):
    """Rechaza los cambios y restaura la versión anterior"""
    retencion = db.query(APRetencion).filter(APRetencion.Id == retencion_id).first()
    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")
    
    # Buscar el último registro de auditoría de tipo UPDATE para este documento
    ultimo_cambio = db.query(Auditoria).filter(
        Auditoria.tabla == "AP_Retencion",
        Auditoria.registro_id == str(retencion_id),
        Auditoria.accion == "UPDATE"
    ).order_by(Auditoria.fecha.desc()).first()
    
    if not ultimo_cambio or not ultimo_cambio.datos_anteriores:
        retencion.necesita_aprobacion = False
        db.commit()
        return ResponseBase(success=True, message="Flag de aprobación removido (sin historial para restaurar)")

    try:
        anteriores = json.loads(ultimo_cambio.datos_anteriores)
        
        # Restaurar cabecera
        for key, value in anteriores.items():
            if key == "detalles": continue
            if hasattr(retencion, key):
                setattr(retencion, key, value)
        
        # Restaurar detalles
        if "detalles" in anteriores:
            db.query(APRetencionDetail).filter(APRetencionDetail.Retencion == retencion_id).delete()
            for det in anteriores["detalles"]:
                campos_modelo = APRetencionDetail.__table__.columns.keys()
                det_filtrado = {k: v for k, v in det.items() if k in campos_modelo}
                nuevo_det = APRetencionDetail(**det_filtrado)
                db.add(nuevo_det)
                
        retencion.necesita_aprobacion = False
        db.commit()
        return ResponseBase(success=True, message="Cambios rechazados y versión anterior restaurada")
    except Exception as e:
        db.rollback()
        return ResponseBase(success=False, message=f"Error al restaurar versión: {str(e)}")


@router.post("/{retencion_id}/anular", response_model=ResponseBase)
async def anular_retencion(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    retencion_id: int,
    motivo: str = Query(..., description="Motivo de anulación"),
    usuario: str = Query(..., description="Usuario que anula")
):
    """Genera retención de anulación"""
    retencion = db.query(APRetencion).filter(
        APRetencion.Id == retencion_id
    ).first()

    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")

    if retencion.status != "enviado":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden anular retenciones enviadas"
        )

    # Obtener detalles de la retención
    detalles = db.query(APRetencionDetail).filter(APRetencionDetail.Retencion == retencion_id).all()

    # Guardar datos para auditoría
    datos_retencion = {
        "cabecera": {
            "Id": retencion.Id,
            "Serie": retencion.Serie,
            "Numero": retencion.Numero,
            "VendorRuc": retencion.VendorRuc,
            "VendorName": retencion.VendorName,
            "Tasa": retencion.Tasa,
            "TotalRetenido": retencion.TotalRetenido,
        },
        "detalles": [
            {
                "ID": d.ID,
                "DRserie": d.DRserie,
                "DRnumero": d.DRnumero,
                "Retenido": d.Retenido,
            }
            for d in detalles
        ]
    }
    
    # Enviar anulación a NubeFact (tipo 7 = retención)
    from ..services.nubefact_client import nubefact_client
    response = await nubefact_client.generar_anulacion(
        tipo_comprobante=7,  # Retención
        serie=retencion.Serie,
        numero=retencion.Numero,
        motivo=motivo
    )
    
    if response.success:
        retencion.status = "anulado"
        retencion.XlastUser = usuario
        retencion.XlastDate = now_peru().timestamp()
        db.commit()
    
    # Registrar auditoría
    auditoria = AuditoriaService(db)
    auditoria.registrar_anulacion(
        tabla="retenciones",
        registro_id=retencion.Id,
        datos_anteriores=datos_retencion,
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
