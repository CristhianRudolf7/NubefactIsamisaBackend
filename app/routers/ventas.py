from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from typing import Optional, List, Annotated
import base64
import asyncio
from datetime import datetime

from ..database import get_db
from ..models.ventas import ARDocument, ARDocumentDetail
from ..models.nube_response import ARFENube
from sqlalchemy.orm import joinedload
from ..models.user import User
from ..schemas.common import ResponseBase, BulkEnviarRequest
from ..schemas.ventas import DocumentoVentaSchema, DocumentoVentaFilter, DocumentoVentaUpdate
from ..services.document_service import DocumentService
from ..services.auditoria_service import AuditoriaService
from ..utils import get_client_ip
from ..utils.datetime import now_peru
from .auth import require_ventas_access, require_admin

router = APIRouter(prefix="/ventas", tags=["Documentos de Venta"])


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
async def listar_documentos(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ventas_access)],
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (dd-mm-YYYY)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (dd-mm-YYYY)"),
    serie: Optional[str] = Query(None, description="Serie del documento"),
    numero: Optional[str] = Query(None, description="Número del documento"),
    estado: Optional[str] = Query(None, description="Estado del documento"),
    ruc_cliente: Optional[str] = Query(None, description="RUC del cliente"),
    tipo_documento: Optional[str] = Query(None, description="Tipo de documento"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    query = db.query(ARDocument)
    
    if fecha_inicio:
        query = query.filter(ARDocument.DocumentDate >= date_to_excel(fecha_inicio))
    if fecha_fin:
        # Si la fecha_fin solo tiene fecha (10 caracteres), sumar el día completo
        # Si tiene hora, usar el valor exacto
        excel_fin = date_to_excel(fecha_fin)
        if len(fecha_fin) <= 10:
            excel_fin += 0.99999
        query = query.filter(ARDocument.DocumentDate <= excel_fin)
    
    if serie:
        query = query.filter(ARDocument.DocumentSerie == serie)
    if numero:
        query = query.filter(ARDocument.DocumentNo == numero)
    if estado:
        estado_lower = estado.lower()
        if estado_lower == 'pendiente':
            query = query.filter(or_(ARDocument.fe == None, ARDocument.fe == '', func.lower(ARDocument.fe) == 'pendiente'))
        elif estado_lower == 'aceptado':
            query = query.filter(func.lower(ARDocument.fe).in_(['aceptado', 'aceptada']))
        elif estado_lower == 'rechazado':
            query = query.filter(func.lower(ARDocument.fe).in_(['rechazado', 'rechazada']))
        else:
            query = query.filter(func.lower(ARDocument.fe) == estado_lower)
    if ruc_cliente:
        query = query.filter(ARDocument.VendorRUC == ruc_cliente)
    if tipo_documento:
        # Limpiar prefijo LIMADSAS para la búsqueda para ser más flexibles
        tipo_busqueda = tipo_documento.lower().replace('limadsas', '')
        query = query.filter(func.lower(ARDocument.DocumentType).contains(tipo_busqueda))
    
    # Paginación (SQL Server requiere ORDER BY para OFFSET)
    total = query.count()
    offset = (page - 1) * page_size
    documentos = query.order_by(ARDocument.Document.desc()).offset(offset).limit(page_size).all()
    
    # Obtener errores de NubeFact y hash para documentos
    errores_nube = {}
    hashes_nube = {}
    series_numeros = [(d.DocumentSerie, d.DocumentNo, d.RejectionReason, d.Comments) for d in documentos if d.fe and d.fe.lower() in ['error', 'rechazado']]
    # Obtener hash para todos los documentos enviados
    for d in documentos:
        if d.fe and d.fe.lower() not in ['pendiente', '', None]:
            nube_resp = db.query(ARFENube).filter(
                ARFENube.serie == d.DocumentSerie,
                ARFENube.numero == d.DocumentNo
            ).order_by(ARFENube.id.desc()).first()
            if nube_resp and nube_resp.codigo_hash:
                hashes_nube[(d.DocumentSerie, d.DocumentNo)] = nube_resp.codigo_hash
    
    if series_numeros:
        for serie, numero, rejection_reason, comments in series_numeros:
            nube_resp = db.query(ARFENube).filter(
                ARFENube.serie == serie,
                ARFENube.numero == numero
            ).order_by(ARFENube.id.desc()).first()
            if nube_resp:
                error_msg = nube_resp.sunat_soap_error or nube_resp.error or nube_resp.sunat_description or None
                if error_msg:
                    errores_nube[(serie, numero)] = error_msg
                else:
                    errores_nube[(serie, numero)] = rejection_reason or comments or "No hay detalles del error disponibles"
            elif rejection_reason or comments:
                # Si no hay respuesta de NubeFact, usar RejectionReason o Comments
                errores_nube[(serie, numero)] = rejection_reason or comments
            else:
                # Si no hay ninguna fuente de error, mostrar mensaje por defecto
                errores_nube[(serie, numero)] = "No hay detalles del error disponibles"
    
    return ResponseBase(
        success=True,
        message=f"Se encontraron {total} documentos",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "Document": d.Document,
                    "DocumentSerie": d.DocumentSerie,
                    "DocumentNo": d.DocumentNo,
                    "DocumentType": d.DocumentType,
                    "VendorRUC": d.VendorRUC,
                    "VendorName": d.VendorName,
                    "DocumentDate": d.DocumentDate,
                    "AmountTotalLo": d.AmountTotalLo,
                    "DocumentCurrency": d.DocumentCurrency,
                    "fe": d.fe,
                    "Status": d.Status,
                    "error_mensaje": errores_nube.get((d.DocumentSerie, d.DocumentNo)),
                    "codigo_hash": hashes_nube.get((d.DocumentSerie, d.DocumentNo)),
                }
                for d in documentos
            ]
        }
    )


@router.get("/{document_id}", response_model=ResponseBase)
async def obtener_documento(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ventas_access)],
    document_id: str
):
    """Obtiene detalle de un documento de venta"""
    documento = db.query(ARDocument).filter(
        ARDocument.Document == document_id
    ).first()
    
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Obtener respuesta de NubeFact
    nube_response = db.query(ARFENube).filter(
        ARFENube.serie == documento.DocumentSerie,
        ARFENube.numero == documento.DocumentNo
    ).order_by(ARFENube.id.desc()).first()
    
    # Obtener mensaje de error si existe
    error_mensaje = None
    if documento.fe and documento.fe.lower() in ['error', 'rechazado']:
        if nube_response:
            error_mensaje = nube_response.sunat_soap_error or nube_response.error or nube_response.sunat_description or None
        if not error_mensaje:
            error_mensaje = documento.RejectionReason or documento.Comments or "No hay detalles del error disponibles"
    
    return ResponseBase(
        success=True,
        message="Documento encontrado",
        data={
            "cabecera": {
                "Document": documento.Document,
                "DocumentSerie": documento.DocumentSerie,
                "DocumentNo": documento.DocumentNo,
                "DocumentType": documento.DocumentType,
                "VendorRUC": documento.VendorRUC,
                "VendorName": documento.VendorName,
                "VendorAddress": documento.VendorAddress,
                "VendorEmail": documento.VendorEmail,
                "DocumentDate": documento.DocumentDate,
                "DueDate": documento.DueDate,
                "DocumentCurrency": documento.DocumentCurrency,
                "ExchangeRate": documento.ExchangeRate,
                "AmountNetLo": documento.AmountNetLo,
                "AmountTaxLo": documento.AmountTaxLo,
                "AmountTotalLo": documento.AmountTotalLo,
                "AmountNoImponibleLo": documento.AmountNoImponibleLo,
                "PlazoDias": documento.PlazoDias,
                "FlagSaleType": documento.FlagSaleType,
                "CondicionPago": documento.CondicionPago,
                "fe": documento.fe,
                "Status": documento.Status,
                "error_mensaje": error_mensaje,
            },
            "detalles": [
                {
                    "Line": d.Line,
                    "ItemCode": d.ItemCode,
                    "Description": d.Description,
                    "Quantity": d.Quantity,
                    "Unit": d.Unit,
                    "Price": d.Price,
                    "PriceTax": d.PriceTax,
                    "SubTotal": d.SubTotal,
                    "Total": d.Total,
                    "TotalTaxLo": d.TotalTaxLo,
                }
                for d in documento.detalles
            ],
            "respuesta_nubefact": {
                "enlace": nube_response.enlace if nube_response else None,
                "aceptada_por_sunat": nube_response.aceptada_por_sunat if nube_response else None,
                "sunat_description": nube_response.sunat_description if nube_response else None,
                "sunat_note": nube_response.sunat_note if nube_response else None,
                "sunat_soap_error": nube_response.sunat_soap_error if nube_response else None,
                "error": nube_response.error if nube_response else None,
                "codigo_hash": nube_response.codigo_hash if nube_response else None,
                "pdf_zip_base64": nube_response.pdf_zip_base64 if nube_response else None,
                "xml_zip_base64": nube_response.xml_zip_base64 if nube_response else None,
                "cdr_zip_base64": nube_response.cdr_zip_base64 if nube_response else None,
            } if nube_response else None
        }
    )


@router.post("/{document_id}/enviar", response_model=ResponseBase)
async def enviar_documento(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    document_id: str,
    usuario: str = Query(..., description="Usuario que envía")
):
    """Envía documento de venta a NubeFact"""
    # Obtener documento antes de enviar
    documento = db.query(ARDocument).filter(ARDocument.Document == document_id).first()
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Obtener detalles del documento
    detalles = db.query(ARDocumentDetail).filter(ARDocumentDetail.Document == document_id).all()

    datos_documento = {
        "cabecera": {
            "Document": documento.Document,
            "DocumentSerie": documento.DocumentSerie,
            "DocumentNo": documento.DocumentNo,
            "DocumentType": documento.DocumentType,
            "DocumentDate": documento.DocumentDate,
            "VendorRUC": documento.VendorRUC,
            "VendorName": documento.VendorName,
            "VendorAddress": documento.VendorAddress,
            "AmountNetLo": documento.AmountNetLo,
            "AmountTaxLo": documento.AmountTaxLo,
            "AmountTotalLo": documento.AmountTotalLo,
            "DocumentCurrency": documento.DocumentCurrency,
        },
        "detalles": [
            {
                "Line": d.Line,
                "ItemCode": d.ItemCode,
                "Description": d.Description,
                "Unit": d.Unit,
                "Quantity": d.Quantity,
                "Price": d.Price,
                "PriceTax": d.PriceTax,
                "SubTotal": d.SubTotal,
                "TotalTaxLo": d.TotalTaxLo,
                "Total": d.Total,
            }
            for d in detalles
        ]
    }
    
    service = DocumentService(db)
    result = await service.enviar_documento_venta(document_id, usuario)
    
    # Registrar auditoría
    auditoria = AuditoriaService(db)
    auditoria.registrar_envio(
        tabla="ventas",
        registro_id=documento.Document,
        datos_documento=datos_documento,
        usuario=usuario,
        respuesta_nubefact=result.get("data"),
        ip=get_client_ip(request)
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ResponseBase(
        success=True,
        message="Documento enviado correctamente",
        data=result["data"]
    )


async def procesar_envio_masivo_ventas(ids: List[str], usuario: str, db: Session):
    """Función de fondo para procesar múltiples documentos"""
    service = DocumentService(db)
    for doc_id in ids:
        try:
            await service.enviar_documento_venta(doc_id, usuario)
            # Esperar 1 segundo entre envíos para no saturar
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error en envío masivo para {doc_id}: {e}")
            # Marcar como error en la base de datos
            try:
                doc = db.query(ARDocument).filter(ARDocument.Document == doc_id).first()
                if doc:
                    doc.fe = "error"
                    db.commit()
            except:
                db.rollback()


@router.post("/bulk-enviar", response_model=ResponseBase)
async def enviar_masivo_ventas(
    request: BulkEnviarRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)]
):
    """Inicia el proceso de envío masivo en segundo plano"""
    background_tasks.add_task(
        procesar_envio_masivo_ventas,
        request.ids,
        request.usuario,
        db
    )
    
    return ResponseBase(
        success=True,
        message=f"Se ha iniciado el proceso de envío para {len(request.ids)} documentos"
    )


@router.put("/{document_id}", response_model=ResponseBase)
async def actualizar_documento(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    document_id: str,
    datos: DocumentoVentaUpdate,
    usuario: str = Query(..., description="Usuario que actualiza")
):
    """Actualiza un documento de venta (solo si está rechazado/observado)"""
    documento = db.query(ARDocument).filter(
        ARDocument.Document == document_id
    ).first()
    
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Verificar si puede ser editado
    service = DocumentService(db)
    if not service._puede_editar(documento.fe or ""):
        raise HTTPException(
            status_code=400,
            detail="El documento no puede ser editado en su estado actual"
        )
    
    # Guardar datos anteriores para auditoría
    datos_anteriores = {
        "Document": documento.Document,
        "VendorRUC": documento.VendorRUC,
        "VendorName": documento.VendorName,
        "VendorAddress": documento.VendorAddress,
        "AmountNetLo": documento.AmountNetLo,
        "AmountTaxLo": documento.AmountTaxLo,
        "AmountTotalLo": documento.AmountTotalLo,
        "detalles": [
            {
                "Line": d.Line,
                "ItemCode": d.ItemCode,
                "Description": d.Description,
                "Quantity": d.Quantity,
                "Unit": d.Unit,
                "Price": d.Price,
                "Total": d.Total,
            }
            for d in documento.detalles
        ]
    }
    
    # Actualizar campos de cabecera
    if datos.VendorRUC is not None:
        documento.VendorRUC = datos.VendorRUC
    if datos.VendorName is not None:
        documento.VendorName = datos.VendorName
    if datos.VendorAddress is not None:
        documento.VendorAddress = datos.VendorAddress
    if datos.VendorEmail is not None:
        documento.VendorEmail = datos.VendorEmail
    if datos.AmountNetLo is not None:
        documento.AmountNetLo = datos.AmountNetLo
    if datos.AmountTaxLo is not None:
        documento.AmountTaxLo = datos.AmountTaxLo
    if datos.AmountTotalLo is not None:
        documento.AmountTotalLo = datos.AmountTotalLo
    if datos.AmountNoImponibleLo is not None:
        documento.AmountNoImponibleLo = datos.AmountNoImponibleLo
    if datos.Comments is not None:
        documento.Comments = datos.Comments
    if datos.CondicionPago is not None:
        documento.CondicionPago = datos.CondicionPago
    
    # Actualizar items si se proporcionan
    if datos.detalles is not None:
        # Eliminar items existentes
        db.query(ARDocumentDetail).filter(
            ARDocumentDetail.Document == document_id
        ).delete()
        
        # Insertar nuevos items
        for i, item in enumerate(datos.detalles, start=1):
            nuevo_detalle = ARDocumentDetail(
                Document=document_id,
                Line=item.Line or i,
                ItemCode=item.ItemCode,
                Description=item.Description,
                Unit=item.Unit,
                Quantity=item.Quantity,
                Price=item.Price,
                PriceTax=item.PriceTax,
                SubTotal=item.SubTotal,
                TotalTaxLo=item.TotalTaxLo,
                Total=item.Total,
            )
            db.add(nuevo_detalle)
    
    
    documento.XLastUser = usuario
    documento.XLastDate = now_peru().timestamp()
    
    db.commit()
    
    # Registrar auditoría
    datos_nuevos = {
        "Document": documento.Document,
        "VendorRUC": documento.VendorRUC,
        "VendorName": documento.VendorName,
        "VendorAddress": documento.VendorAddress,
        "AmountNetLo": documento.AmountNetLo,
        "AmountTaxLo": documento.AmountTaxLo,
        "AmountTotalLo": documento.AmountTotalLo,
        "detalles": [
            {
                "Line": d.Line,
                "ItemCode": d.ItemCode,
                "Description": d.Description,
                "Quantity": d.Quantity,
                "Unit": d.Unit,
                "Price": d.Price,
                "Total": d.Total,
            }
            for d in documento.detalles
        ]
    }
    auditoria = AuditoriaService(db)
    auditoria.registrar_cambio(
        tabla="ventas",
        registro_id=documento.Document,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
        usuario=usuario,
        ip=get_client_ip(request)
    )
    
    return ResponseBase(
        success=True,
        message="Documento actualizado correctamente",
        data={"Document": documento.Document}
    )


@router.post("/{document_id}/anular", response_model=ResponseBase)
async def anular_documento(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    document_id: str,
    motivo: str = Query(..., description="Motivo de anulación"),
    usuario: str = Query(..., description="Usuario que anula")
):
    """Genera documento de anulación"""
    documento = db.query(ARDocument).filter(
        ARDocument.Document == document_id
    ).first()

    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if documento.fe != "enviado":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden anular documentos enviados"
        )

    # Obtener detalles del documento
    detalles = db.query(ARDocumentDetail).filter(ARDocumentDetail.Document == document_id).all()

    # Guardar datos para auditoría
    datos_documento = {
        "cabecera": {
            "Document": documento.Document,
            "DocumentSerie": documento.DocumentSerie,
            "DocumentNo": documento.DocumentNo,
            "DocumentType": documento.DocumentType,
            "VendorRUC": documento.VendorRUC,
            "VendorName": documento.VendorName,
            "AmountTotalLo": documento.AmountTotalLo,
        },
        "detalles": [
            {
                "Line": d.Line,
                "ItemCode": d.ItemCode,
                "Description": d.Description,
                "Quantity": d.Quantity,
                "Total": d.Total,
            }
            for d in detalles
        ]
    }
    
    # Mapear tipo de documento
    tipo_doc_map = {
        "LIMADSASFACTURA": 1,
        "LIMADSASBOLETA": 2,
    }
    tipo_comprobante = tipo_doc_map.get(documento.DocumentType, 1)
    
    # Enviar anulación a NubeFact
    from ..services.nubefact_client import nubefact_client
    response = await nubefact_client.generar_anulacion(
        tipo_comprobante=tipo_comprobante,
        serie=documento.DocumentSerie,
        numero=documento.DocumentNo,
        motivo=motivo
    )
    
    if response.success:
        documento.fe = "anulado"
        documento.XLastUser = usuario
        documento.XLastDate = now_peru().timestamp()
        db.commit()
    
    # Registrar auditoría
    auditoria = AuditoriaService(db)
    auditoria.registrar_anulacion(
        tabla="ventas",
        registro_id=documento.Document,
        datos_anteriores=datos_documento,
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


@router.get("/{document_id}/pdf")
async def descargar_pdf(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ventas_access)],
    document_id: str
):
    """Descarga el PDF del documento"""
    documento = db.query(ARDocument).filter(ARDocument.Document == document_id).first()
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    nube_response = db.query(ARFENube).filter(
        ARFENube.serie == documento.DocumentSerie,
        ARFENube.numero == documento.DocumentNo
    ).order_by(ARFENube.id.desc()).first()

    if not nube_response:
        raise HTTPException(status_code=404, detail="Documento no enviado a NubeFact")

    # Si hay URL de NubeFact, redirigir
    if nube_response.enlace_del_pdf:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=nube_response.enlace_del_pdf)

    # Si hay base64, decodificar
    if nube_response.pdf_zip_base64:
        pdf_bytes = base64.b64decode(nube_response.pdf_zip_base64)
        filename = f"{documento.DocumentSerie}-{documento.DocumentNo}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    raise HTTPException(status_code=404, detail="PDF no disponible")


@router.get("/{document_id}/xml")
async def descargar_xml(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ventas_access)],
    document_id: str
):
    """Descarga el XML firmado del documento"""
    documento = db.query(ARDocument).filter(ARDocument.Document == document_id).first()
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    nube_response = db.query(ARFENube).filter(
        ARFENube.serie == documento.DocumentSerie,
        ARFENube.numero == documento.DocumentNo
    ).order_by(ARFENube.id.desc()).first()

    if not nube_response:
        raise HTTPException(status_code=404, detail="Documento no enviado a NubeFact")

    # Si hay URL de NubeFact, redirigir
    if nube_response.enlace_del_xml:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=nube_response.enlace_del_xml)

    # Si hay base64, decodificar
    if nube_response.xml_zip_base64:
        xml_bytes = base64.b64decode(nube_response.xml_zip_base64)
        filename = f"{documento.DocumentSerie}-{documento.DocumentNo}.xml"
        return Response(
            content=xml_bytes,
            media_type="application/xml",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    raise HTTPException(status_code=404, detail="XML no disponible")


@router.get("/{document_id}/cdr")
async def descargar_cdr(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ventas_access)],
    document_id: str
):
    """Descarga el CDR (Constancia de Recepción) del documento"""
    documento = db.query(ARDocument).filter(ARDocument.Document == document_id).first()
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    nube_response = db.query(ARFENube).filter(
        ARFENube.serie == documento.DocumentSerie,
        ARFENube.numero == documento.DocumentNo
    ).order_by(ARFENube.id.desc()).first()

    if not nube_response:
        raise HTTPException(status_code=404, detail="Documento no enviado a NubeFact")

    # Si hay URL de NubeFact, redirigir
    if nube_response.enlace_del_cdr:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=nube_response.enlace_del_cdr)

    # Si hay base64, decodificar
    if nube_response.cdr_zip_base64:
        cdr_bytes = base64.b64decode(nube_response.cdr_zip_base64)
        filename = f"R-{documento.DocumentSerie}-{documento.DocumentNo}.zip"
        return Response(
            content=cdr_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    raise HTTPException(status_code=404, detail="CDR no disponible")
