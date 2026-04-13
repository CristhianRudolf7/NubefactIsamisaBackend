from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Annotated
from datetime import datetime

from ..database import get_db
from ..models.guias import WHTransaction
from ..models.retenciones import APRetencion, APRetencionStatus
from ..models.ventas import ARDocument
from ..models.nube_response import ARFENube
from ..models.user import User
from ..schemas.common import ResponseBase, EstadoDocumento
from .auth import require_authenticated

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/estadisticas", response_model=ResponseBase)
async def obtener_estadisticas(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated)],
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    """Obtiene estadísticas generales del dashboard"""
    
    # Estadísticas de Ventas
    ventas_total = db.query(func.count(ARDocument.Document)).scalar()
    ventas_enviadas = db.query(func.count(ARDocument.Document)).filter(
        ARDocument.fe == "enviado"
    ).scalar()
    ventas_pendientes = db.query(func.count(ARDocument.Document)).filter(
        ARDocument.fe == None
    ).scalar()
    ventas_error = db.query(func.count(ARDocument.Document)).filter(
        ARDocument.fe == "Error"
    ).scalar()
    
    # Estadísticas de Retenciones
    retenciones_total = db.query(func.count(APRetencion.Id)).scalar()
    retenciones_enviadas = db.query(func.count(APRetencion.Id)).filter(
        APRetencion.status == "enviado"
    ).scalar()
    retenciones_pendientes = db.query(func.count(APRetencion.Id)).filter(
        APRetencion.status == None
    ).scalar()
    
    # Estadísticas de Guías
    guias_total = db.query(func.count(WHTransaction.Transaction)).scalar()
    guias_aceptadas = db.query(func.count(WHTransaction.Transaction)).filter(
        WHTransaction.envio_nube == "aceptada"
    ).scalar()
    guias_pendientes = db.query(func.count(WHTransaction.Transaction)).filter(
        WHTransaction.envio_nube == None
    ).scalar()
    
    return ResponseBase(
        success=True,
        message="Estadísticas obtenidas",
        data={
            "ventas": {
                "total": ventas_total,
                "enviadas": ventas_enviadas,
                "pendientes": ventas_pendientes,
                "error": ventas_error,
            },
            "retenciones": {
                "total": retenciones_total,
                "enviadas": retenciones_enviadas,
                "pendientes": retenciones_pendientes,
            },
            "guias": {
                "total": guias_total,
                "aceptadas": guias_aceptadas,
                "pendientes": guias_pendientes,
            }
        }
    )


@router.get("/estados", response_model=ResponseBase)
async def listar_estados(
    current_user: Annotated[User, Depends(require_authenticated)]
):
    """Lista los estados posibles de los documentos"""
    estados = [
        {
            "codigo": EstadoDocumento.PENDIENTE.value,
            "descripcion": "Pendiente de envío",
            "color": "#FFA500",
            "puede_editar": True,
        },
        {
            "codigo": EstadoDocumento.ENVIADO_NUBEFACT.value,
            "descripcion": "Enviado a NubeFact",
            "color": "#007BFF",
            "puede_editar": False,
        },
        {
            "codigo": EstadoDocumento.ACEPTADO_SUNAT.value,
            "descripcion": "Aceptado por SUNAT",
            "color": "#28A745",
            "puede_editar": False,
        },
        {
            "codigo": EstadoDocumento.ACEPTADO_OBSERVACIONES.value,
            "descripcion": "Aceptado con observaciones",
            "color": "#FFC107",
            "puede_editar": True,
        },
        {
            "codigo": EstadoDocumento.RECHAZADO.value,
            "descripcion": "Rechazado por SUNAT",
            "color": "#DC3545",
            "puede_editar": True,
        },
        {
            "codigo": EstadoDocumento.ERROR.value,
            "descripcion": "Error en el envío",
            "color": "#6C757D",
            "puede_editar": True,
        },
    ]
    
    return ResponseBase(
        success=True,
        message="Estados obtenidos",
        data=estados
    )


@router.get("/tipos-documento", response_model=ResponseBase)
async def listar_tipos_documento(
    current_user: Annotated[User, Depends(require_authenticated)]
):
    """Lista los tipos de documento"""
    tipos = [
        {"codigo": "LIMADSASFACTURA", "descripcion": "Factura", "tipo_sunat": 1},
        {"codigo": "LIMADSASBOLETA", "descripcion": "Boleta", "tipo_sunat": 2},
        {"codigo": "LIMADSASCREDITO", "descripcion": "Nota de Crédito", "tipo_sunat": 3},
        {"codigo": "LIMADSASDEBITO", "descripcion": "Nota de Débito", "tipo_sunat": 4},
        {"codigo": "GUIA_REMISION", "descripcion": "Guía de Remisión", "tipo_sunat": 7},
        {"codigo": "RETENCION", "descripcion": "Retención", "tipo_sunat": "R"},
    ]
    
    return ResponseBase(
        success=True,
        message="Tipos de documento obtenidos",
        data=tipos
    )


@router.get("/motivos-traslado", response_model=ResponseBase)
async def listar_motivos_traslado(
    current_user: Annotated[User, Depends(require_authenticated)]
):
    """Lista los motivos de traslado para guías"""
    motivos = [
        {"codigo": "01", "descripcion": "Venta"},
        {"codigo": "02", "descripcion": "Compra"},
        {"codigo": "04", "descripcion": "Traslado entre establecimientos de la empresa"},
        {"codigo": "05", "descripcion": "Consignación"},
        {"codigo": "13", "descripcion": "Otros"},
    ]
    
    return ResponseBase(
        success=True,
        message="Motivos de traslado obtenidos",
        data=motivos
    )


@router.get("/resumen-por-estado", response_model=ResponseBase)
async def resumen_por_estado(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated)],
    tipo: str = Query(..., description="Tipo: ventas, retenciones, guias")
):
    """Obtiene resumen de documentos por estado"""
    
    if tipo == "ventas":
        resultados = db.query(
            ARDocument.fe.label("estado"),
            func.count(ARDocument.Document).label("cantidad")
        ).group_by(ARDocument.fe).all()
        
        resumen = [
            {"estado": r.estado or "pendiente", "cantidad": r.cantidad}
            for r in resultados
        ]
        
    elif tipo == "retenciones":
        resultados = db.query(
            APRetencion.status.label("estado"),
            func.count(APRetencion.Id).label("cantidad")
        ).group_by(APRetencion.status).all()
        
        resumen = [
            {"estado": r.estado or "pendiente", "cantidad": r.cantidad}
            for r in resultados
        ]
        
    elif tipo == "guias":
        resultados = db.query(
            WHTransaction.envio_nube.label("estado"),
            func.count(WHTransaction.Transaction).label("cantidad")
        ).group_by(WHTransaction.envio_nube).all()
        
        resumen = [
            {"estado": r.estado or "pendiente", "cantidad": r.cantidad}
            for r in resultados
        ]
        
    else:
        return ResponseBase(
            success=False,
            message="Tipo no válido. Use: ventas, retenciones, guias"
        )
    
    return ResponseBase(
        success=True,
        message=f"Resumen de {tipo} obtenido",
        data=resumen
    )
