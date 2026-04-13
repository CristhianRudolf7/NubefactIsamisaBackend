from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime

from ..database import get_db
from ..models.api_token import ApiToken
from ..models.ventas import ARDocument, ARDocumentDetail
from ..models.guias import WHTransaction, WHTransactionDetail
from ..models.retenciones import APRetencion, APRetencionDetail
from ..schemas.external import (
    ExternalVentaCreate,
    ExternalGuiaCreate,
    ExternalRetencionCreate,
    ExternalResponse
)
from ..services.token_service import validate_api_token

router = APIRouter(prefix="/external", tags=["API Externa"])


@router.get("/status", response_model=ExternalResponse)
async def check_status(
    api_token: Annotated[ApiToken, Depends(validate_api_token)]
):
    """
    Verifica que el token de API está activo y funcionando.
    """
    return ExternalResponse(
        success=True,
        message="Token válido",
        data={
            "token_name": api_token.name,
            "token_prefix": api_token.token_prefix,
            "last_used_at": api_token.last_used_at.isoformat() if api_token.last_used_at else None,
        }
    )


@router.post("/ventas/", response_model=ExternalResponse)
async def notify_venta(
    venta_data: ExternalVentaCreate,
    api_token: Annotated[ApiToken, Depends(validate_api_token)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Notifica un nuevo documento de venta desde un sistema externo.
    
    El documento se guarda en la base de datos con estado 'pendiente'
    para su posterior envío a SUNAT.
    """
    # Verificar si ya existe
    existing = db.query(ARDocument).filter(ARDocument.Document == venta_data.Document).first()
    if existing:
        return ExternalResponse(
            success=False,
            message=f"El documento {venta_data.Document} ya existe",
            data={"Document": venta_data.Document}
        )
    
    # Crear documento
    documento = ARDocument(
        Document=venta_data.Document,
        DocumentSerie=venta_data.DocumentSerie,
        DocumentNo=venta_data.DocumentNo,
        DocumentType=venta_data.DocumentType,
        VendorRUC=venta_data.VendorRUC,
        VendorName=venta_data.VendorName,
        VendorAddress=venta_data.VendorAddress,
        DocumentDate=venta_data.DocumentDate,
        DueDate=venta_data.DueDate,
        DocumentCurrency=venta_data.DocumentCurrency,
        ExchangeRate=venta_data.ExchangeRate,
        AmountNetLo=venta_data.AmountNetLo,
        AmountTaxLo=venta_data.AmountTaxLo,
        AmountTotalLo=venta_data.AmountTotalLo,
        AmountNoImponibleLo=venta_data.AmountNoImponibleLo,
        fe=None,  # Pendiente de envío
    )
    
    db.add(documento)
    db.flush()  # Para obtener el ID si es necesario
    
    # Crear detalles
    if venta_data.detalles:
        for det in venta_data.detalles:
            detalle = ARDocumentDetail(
                Document=venta_data.Document,
                Line=det.Line,
                ItemCode=det.ItemCode,
                Description=det.Description,
                Quantity=det.Quantity,
                Unit=det.Unit,
                Price=det.Price,
                PriceTax=det.PriceTax,
                SubTotal=det.SubTotal,
                Total=det.Total,
                TotalTaxLo=det.TotalTaxLo,
            )
            db.add(detalle)
    
    db.commit()
    
    return ExternalResponse(
        success=True,
        message="Documento de venta registrado correctamente",
        data={
            "Document": venta_data.Document,
            "status": "pendiente"
        }
    )


@router.post("/guias/", response_model=ExternalResponse)
async def notify_guia(
    guia_data: ExternalGuiaCreate,
    api_token: Annotated[ApiToken, Depends(validate_api_token)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Notifica una nueva guía de remisión desde un sistema externo.
    """
    # Verificar si ya existe
    existing = db.query(WHTransaction).filter(WHTransaction.Transaction == guia_data.Transaction).first()
    if existing:
        return ExternalResponse(
            success=False,
            message=f"La guía {guia_data.Transaction} ya existe",
            data={"Transaction": guia_data.Transaction}
        )
    
    # Crear guía
    guia = WHTransaction(
        Transaction=guia_data.Transaction,
        DocumentSerie=guia_data.DocumentSerie,
        DocumentNo=guia_data.DocumentNo,
        TransactionDate=guia_data.TransactionDate,
        TargetPersonRUC=guia_data.TargetPersonRUC,
        TargetPersonName=guia_data.TargetPersonName,
        TargetAddress=guia_data.TargetAddress,
        MotivoTraslado=guia_data.MotivoTraslado,
        PesoBruto=guia_data.PesoBruto,
        RucTransportista=guia_data.RucTransportista,
        Transportista=guia_data.Transportista,
        VehicleID=guia_data.VehicleID,
        Driver=guia_data.Driver,
        LicenciaConducir=guia_data.LicenciaConducir,
        origenaddress=guia_data.origenaddress,
        ubigeo_des=guia_data.ubigeo_des,
        Comments=guia_data.Comments,
        envio_nube=None,  # Pendiente de envío
    )
    
    db.add(guia)
    db.flush()
    
    # Crear detalles
    if guia_data.detalles:
        for det in guia_data.detalles:
            detalle = WHTransactionDetail(
                Transaction=guia_data.Transaction,
                Line=det.Line,
                ItemCode=det.ItemCode,
                ItemDescription=det.ItemDescription,
                Quantity=det.Quantity,
                Unit=det.Unit,
            )
            db.add(detalle)
    
    db.commit()
    
    return ExternalResponse(
        success=True,
        message="Guía de remisión registrada correctamente",
        data={
            "Transaction": guia_data.Transaction,
            "status": "pendiente"
        }
    )


@router.post("/retenciones/", response_model=ExternalResponse)
async def notify_retencion(
    retencion_data: ExternalRetencionCreate,
    api_token: Annotated[ApiToken, Depends(validate_api_token)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Notifica una nueva retención desde un sistema externo.
    """
    # Crear retención (no hay ID único, se crea nueva)
    retencion = APRetencion(
        Serie=retencion_data.Serie,
        Numero=retencion_data.Numero,
        VendorRuc=retencion_data.VendorRuc,
        VendorName=retencion_data.VendorName,
        VendorAddress=retencion_data.VendorAddress,
        DocumentDate=retencion_data.DocumentDate,
        Tasa=retencion_data.Tasa,
        TotalRetenido=retencion_data.TotalRetenido,
        TotalPagado=retencion_data.TotalPagado,
        Obs=retencion_data.Obs,
        status=None,  # Pendiente de envío
    )
    
    db.add(retencion)
    db.flush()
    
    # Crear detalles
    if retencion_data.detalles:
        for det in retencion_data.detalles:
            detalle = APRetencionDetail(
                Retencion=retencion.Id,
                DRserie=det.DRserie,
                DRnumero=det.DRnumero,
                DRfecha=det.DRfecha,
                DRmoneda=det.DRmoneda,
                DRtotal=det.DRtotal,
                DRpagoFecha=det.DRpagoFecha,
                Retenido=det.Retenido,
                Pagado=det.Pagado,
            )
            db.add(detalle)
    
    db.commit()
    
    return ExternalResponse(
        success=True,
        message="Retención registrada correctamente",
        data={
            "Id": retencion.Id,
            "Serie": retencion.Serie,
            "Numero": retencion.Numero,
            "status": "pendiente"
        }
    )
