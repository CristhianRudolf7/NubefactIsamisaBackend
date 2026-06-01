from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import or_, func, text
from sqlalchemy.orm import Session
from typing import Optional, List, Annotated
import base64
import asyncio
from datetime import datetime

from ..database import get_db, SessionLocal
from ..models.retenciones import APRetencion, APRetencionDetail, APRetencionStatus
import json
from ..models.auditoria import Auditoria
from ..models.user import User, UserRole
from ..schemas.common import ResponseBase, BulkEnviarRequest, BulkEnviarFiltrosRequest
from ..schemas.retenciones import RetencionSchema, RetencionFilter
from ..services.document_service import DocumentService
from ..services.auditoria_service import AuditoriaService
from ..services.notification_service import NotificationService
from ..utils import get_client_ip
from ..utils.datetime import now_peru
from .auth import require_retenciones_access, require_admin

router = APIRouter(prefix="/retenciones", tags=["Retenciones"])


def parse_date_filter(date_str: str, is_end_date: bool = False) -> datetime:
    """Convierte string dd-mm-YYYY [HH:mm] a datetime"""
    try:
        date_str = date_str.replace('+', ' ').strip()
        try:
            dt = datetime.strptime(date_str, "%d-%m-%Y %H:%M")
        except ValueError:
            dt = datetime.strptime(date_str, "%d-%m-%Y")
            if is_end_date:
                # Si es fecha fin y no tiene hora, llevar al final del día (sin microsegundos para evitar redondeo en SQL Server)
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=0)
        return dt
    except:
        return datetime.min if not is_end_date else datetime.max


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
    page_size: int = Query(20, ge=1, le=10000)
):
    query = db.query(APRetencion)
    
    if fecha_inicio:
        query = query.filter(APRetencion.DocumentDate >= parse_date_filter(fecha_inicio, is_end_date=False))
    if fecha_fin:
        query = query.filter(APRetencion.DocumentDate <= parse_date_filter(fecha_fin, is_end_date=True))
    
    if serie:
        query = query.filter(APRetencion.Serie == serie)
    if numero:
        query = query.filter(APRetencion.Numero == numero)
    if estado:
        estado_lower = estado.lower()
        query = query.filter(APRetencion.nube_status_web == estado)
    if ruc_proveedor:
        query = query.filter(APRetencion.VendorRuc == ruc_proveedor)
    
    # Paginación (SQL Server requiere ORDER BY para OFFSET)
    total = query.count()
    offset = (page - 1) * page_size
    retenciones = query.order_by(
        text("CASE WHEN DocumentDate >= '2000-01-01' AND DocumentDate <= '2100-12-31' THEN 0 ELSE 1 END"),
        APRetencion.DocumentDate.desc(),
        APRetencion.Id.desc()
    ).offset(offset).limit(page_size).all()
    
    # Obtener errores para retenciones con estado error/rechazado
    errores_status = {}
    retencion_ids = [r.Id for r in retenciones if r.status and r.status.lower() in ['error', 'rechazado']]
    if retencion_ids:
        # Traer todos los estados de retención correspondientes de una sola vez
        estados = db.query(APRetencionStatus).filter(
            APRetencionStatus.Retencion.in_(retencion_ids)
        ).all()
        
        # Agrupar por retención y quedarnos con el último estado (mayor id) en Python
        estados_map = {}
        for est in estados:
            if est.Retencion not in estados_map or est.id > estados_map[est.Retencion].id:
                estados_map[est.Retencion] = est
                
        # Construir el diccionario de errores en memoria
        for ret_id in retencion_ids:
            ultimo_estado = estados_map.get(ret_id)
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
                    "nube_status_web": r.nube_status_web,
                    "status": r.nube_status_web,
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
    if retencion.nube_status_web and retencion.nube_status_web.lower() in ['error', 'rechazado']:
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
                "status": retencion.nube_status_web,
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


async def procesar_envio_masivo_retenciones(ids: List[str], usuario: str):
    """Función de fondo para procesar múltiples retenciones"""
    db: Session = SessionLocal()
    try:
        service = DocumentService(db)
        print(f"\n{'='*60}")
        print(f"[BULK RETENCIONES] Iniciando envío masivo de {len(ids)} retenciones")
        print(f"[BULK RETENCIONES] IDs recibidos (primeros 5): {ids[:5]}")
        print(f"{'='*60}")
        for idx, ret_id in enumerate(ids, 1):
            try:
                # Verificar estado actual antes de enviar
                ret_check = db.query(APRetencion).filter(APRetencion.Id == int(ret_id)).first()
                estado_actual = ret_check.nube_status_web if ret_check else 'NO ENCONTRADO'
                print(f"[BULK RETENCIONES] [{idx}/{len(ids)}] Procesando ID={ret_id} | Estado actual: {estado_actual}")
                
                result = await service.enviar_retencion(int(ret_id), usuario)
                if not result.get("success", False):
                    print(f"[BULK RETENCIONES] [{idx}/{len(ids)}] ERROR para ID={ret_id}: {result.get('message')}")
                    ret = db.query(APRetencion).filter(APRetencion.Id == int(ret_id)).first()
                    if ret and (ret.status in ["pendiente", "error", "", None] or ret.nube_status_web in ["pendiente", "error", "", None]) and not ret.necesita_aprobacion:
                        ret.status = "error"
                        ret.nube_status_web = "error"
                        
                        status_record = APRetencionStatus(
                            Retencion=int(ret_id),
                            Status="error",
                            Descripcion=result.get("message", "Error al enviar"),
                            XlastUser=usuario,
                            XlastDate=now_peru(),
                        )
                        db.add(status_record)
                        db.commit()
                print(f"[BULK RETENCIONES] [{idx}/{len(ids)}] OK para ID={ret_id}: {result.get('message', 'enviado')}")
                await asyncio.sleep(1)
            except Exception as e:
                error_msg = str(e)
                print(f"[BULK RETENCIONES] [{idx}/{len(ids)}] EXCEPCION para ID={ret_id}: {error_msg}")
                # Marcar como error en la base de datos para que el usuario lo vea
                try:
                    ret = db.query(APRetencion).filter(APRetencion.Id == int(ret_id)).first()
                    if ret and (ret.status in ["pendiente", "error", "", None] or ret.nube_status_web in ["pendiente", "error", "", None]) and not ret.necesita_aprobacion:
                        ret.status = "error"
                        ret.nube_status_web = "error"
                        
                        # Registrar el error en APRetencionStatus
                        status_record = APRetencionStatus(
                            Retencion=ret.Id,
                            Status="error",
                            error=error_msg,
                            XlastUser=usuario,
                            XlastDate=now_peru(),
                        )
                        db.add(status_record)
                        db.commit()
                except Exception as db_e:
                    print(f"Error al guardar estado de error en DB: {db_e}")
                    db.rollback()
    finally:
        db.close()


@router.post("/bulk-enviar", response_model=ResponseBase)
async def enviar_masivo_retenciones(
    request: BulkEnviarFiltrosRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)]
):
    """Inicia el proceso de envío masivo de retenciones en segundo plano usando filtros"""
    query = db.query(APRetencion.Id).filter(
        or_(APRetencion.status == None, APRetencion.status == '', APRetencion.status == 'pendiente'),
        APRetencion.necesita_aprobacion == False
    )
    if request.fecha_inicio:
        query = query.filter(APRetencion.DocumentDate >= parse_date_filter(request.fecha_inicio, is_end_date=False))
    if request.fecha_fin:
        query = query.filter(APRetencion.DocumentDate <= parse_date_filter(request.fecha_fin, is_end_date=True))
    if request.serie:
        query = query.filter(APRetencion.Serie == request.serie)
        
    ids = [str(r[0]) for r in query.all()]
    
    if not ids:
        return ResponseBase(
            success=True,
            message="No hay retenciones pendientes para enviar en este rango/serie",
            data={"count": 0}
        )
        
    background_tasks.add_task(
        procesar_envio_masivo_retenciones,
        ids,
        request.usuario
    )
    
    return ResponseBase(
        success=True,
        message=f"Se ha iniciado el proceso de envío para {len(ids)} retenciones",
        data={"count": len(ids)}
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
    retencion.XlastDate = now_peru()
    
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
        retencion.nube_status_web = "anulado"
        retencion.XlastUser = usuario
        retencion.XlastDate = now_peru()
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
    import httpx
    
    retencion = db.query(APRetencion).filter(APRetencion.Id == retencion_id).first()
    if not retencion:
        raise HTTPException(status_code=404, detail="Retención no encontrada")
    
    estado = db.query(APRetencionStatus).filter(
        APRetencionStatus.Retencion == retencion_id
    ).order_by(APRetencionStatus.id.desc()).first()
    
    if not estado or not estado.Pdf:
        raise HTTPException(status_code=404, detail="PDF no disponible")
    
    # Si es URL, descargarla en el servidor y transmitir los bytes
    if estado.Pdf.startswith('http'):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(estado.Pdf, timeout=15.0)
                if resp.status_code == 200:
                    filename = f"{retencion.Serie}-{retencion.Numero}.pdf"
                    return Response(
                        content=resp.content,
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
                    )
                else:
                    raise HTTPException(status_code=502, detail="Error al descargar el PDF desde el servidor de facturación")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Error de conexión al obtener PDF: {str(e)}")
    
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
