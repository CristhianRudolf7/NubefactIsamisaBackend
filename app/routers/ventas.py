from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Annotated
from datetime import datetime

from ..database import get_db
from ..models.ventas import ARDocument, ARDocumentDetail
from ..models.nube_response import ARFENube
from ..models.user import User
from ..schemas.common import ResponseBase
from ..schemas.ventas import DocumentoVentaSchema, DocumentoVentaFilter
from ..services.document_service import DocumentService
from .auth import require_authenticated, require_admin

router = APIRouter(prefix="/ventas", tags=["Documentos de Venta"])


@router.get("/", response_model=ResponseBase)
async def listar_documentos(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated)],
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
    """Lista documentos de venta con filtros"""
    query = db.query(ARDocument)
    
    if serie:
        query = query.filter(ARDocument.DocumentSerie == serie)
    if numero:
        query = query.filter(ARDocument.DocumentNo == numero)
    if estado:
        query = query.filter(ARDocument.fe == estado)
    if ruc_cliente:
        query = query.filter(ARDocument.VendorRUC == ruc_cliente)
    if tipo_documento:
        query = query.filter(ARDocument.DocumentType == tipo_documento)
    
    # Paginación (SQL Server requiere ORDER BY para OFFSET)
    total = query.count()
    offset = (page - 1) * page_size
    documentos = query.order_by(ARDocument.Document.desc()).offset(offset).limit(page_size).all()
    
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
                }
                for d in documentos
            ]
        }
    )


@router.get("/{document_id}", response_model=ResponseBase)
async def obtener_documento(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated)],
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
                "fe": documento.fe,
                "Status": documento.Status,
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
                "codigo_hash": nube_response.codigo_hash if nube_response else None,
                "pdf_zip_base64": nube_response.pdf_zip_base64 if nube_response else None,
                "xml_zip_base64": nube_response.xml_zip_base64 if nube_response else None,
                "cdr_zip_base64": nube_response.cdr_zip_base64 if nube_response else None,
            } if nube_response else None
        }
    )


@router.post("/{document_id}/enviar", response_model=ResponseBase)
async def enviar_documento(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    document_id: str,
    usuario: str = Query(..., description="Usuario que envía")
):
    """Envía documento de venta a NubeFact"""
    service = DocumentService(db)
    result = await service.enviar_documento_venta(document_id, usuario)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return ResponseBase(
        success=True,
        message="Documento enviado correctamente",
        data=result["data"]
    )


@router.put("/{document_id}", response_model=ResponseBase)
async def actualizar_documento(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    document_id: str,
    datos: dict,
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
    
    # Actualizar campos permitidos
    campos_permitidos = [
        "VendorRUC", "VendorName", "VendorAddress", "VendorEmail",
        "AmountNetLo", "AmountTaxLo", "AmountTotalLo",
        "AmountNoImponibleLo", "PlazoDias", "Comments"
    ]
    
    for campo, valor in datos.items():
        if campo in campos_permitidos and hasattr(documento, campo):
            setattr(documento, campo, valor)
    
    documento.XLastUser = usuario
    documento.XLastDate = datetime.now().timestamp()
    
    db.commit()
    
    return ResponseBase(
        success=True,
        message="Documento actualizado correctamente",
        data={"Document": documento.Document}
    )


@router.post("/{document_id}/anular", response_model=ResponseBase)
async def anular_documento(
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
        documento.XLastDate = datetime.now().timestamp()
        db.commit()
    
    return ResponseBase(
        success=response.success,
        message="Anulación procesada" if response.success else "Error en anulación",
        data=response.model_dump(exclude_none=True)
    )
