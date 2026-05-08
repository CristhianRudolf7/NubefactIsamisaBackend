from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Integer
from typing import Optional, Annotated
from datetime import datetime, timedelta, date
import logging

from ..database import get_db
from ..models.guias import WHTransaction
from ..models.retenciones import APRetencion
from ..models.ventas import ARDocument
from ..models.user import User
from ..schemas.common import ResponseBase, EstadoDocumento
from .auth import require_authenticated

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

logger = logging.getLogger(__name__)

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
        ARDocument.nube_status_web == "enviado"
    ).scalar()
    ventas_pendientes = db.query(func.count(ARDocument.Document)).filter(
        ARDocument.nube_status_web == "pendiente"
    ).scalar()
    ventas_error = db.query(func.count(ARDocument.Document)).filter(
        ARDocument.nube_status_web == "error"
    ).scalar()
    ventas_por_aprobar = db.query(func.count(ARDocument.Document)).filter(
        ARDocument.necesita_aprobacion == True
    ).scalar()
    
    # Estadísticas de Retenciones
    retenciones_total = db.query(func.count(APRetencion.Id)).scalar()
    retenciones_enviadas = db.query(func.count(APRetencion.Id)).filter(
        APRetencion.nube_status_web == "enviado"
    ).scalar()
    retenciones_pendientes = db.query(func.count(APRetencion.Id)).filter(
        APRetencion.nube_status_web == "pendiente"
    ).scalar()
    retenciones_por_aprobar = db.query(func.count(APRetencion.Id)).filter(
        APRetencion.necesita_aprobacion == True
    ).scalar()
    
    # Estadísticas de Guías
    guias_total = db.query(func.count(WHTransaction.Transaction)).scalar()
    guias_aceptadas = db.query(func.count(WHTransaction.Transaction)).filter(
        WHTransaction.nube_status_web == "aceptado"
    ).scalar()
    guias_pendientes = db.query(func.count(WHTransaction.Transaction)).filter(
        WHTransaction.nube_status_web == "pendiente"
    ).scalar()
    guias_por_aprobar = db.query(func.count(WHTransaction.Transaction)).filter(
        WHTransaction.necesita_aprobacion == True
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
                "por_aprobar": ventas_por_aprobar,
            },
            "retenciones": {
                "total": retenciones_total,
                "enviadas": retenciones_enviadas,
                "pendientes": retenciones_pendientes,
                "por_aprobar": retenciones_por_aprobar,
            },
            "guias": {
                "total": guias_total,
                "aceptadas": guias_aceptadas,
                "pendientes": guias_pendientes,
                "por_aprobar": guias_por_aprobar,
            },
            "por_aprobar_total": ventas_por_aprobar + retenciones_por_aprobar + guias_por_aprobar
        }
    )


@router.get("/actividad-semanal", response_model=ResponseBase)
async def actividad_semanal(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authenticated)]
):
    """Obtiene la cantidad real de documentos procesados en los últimos 7 días"""
    try:
        base_excel = date(1899, 12, 30)
        hoy = date.today()
        dias = [hoy - timedelta(days=i) for i in range(6, -1, -1)]
        
        # Diccionario base para consolidar resultados
        conteo_por_dia = {d.strftime("%Y-%m-%d"): 0 for d in dias}
        
        # Rango en formato Excel (Integer) para consultas eficientes
        excel_inicio = (dias[0] - base_excel).days
        excel_fin = (dias[-1] - base_excel).days

        # 1. Ventas
        try:
            ventas_raw = db.query(
                cast(ARDocument.DocumentDate, Date).label("fecha"),
                func.count(ARDocument.Document).label("cantidad")
            ).filter(
                ARDocument.DocumentDate >= dias[0],
                ARDocument.DocumentDate < (hoy + timedelta(days=1))
            ).group_by(cast(ARDocument.DocumentDate, Date)).all()
            
            for res in ventas_raw:
                if res.fecha:
                    ds = res.fecha.strftime("%Y-%m-%d")
                    if ds in conteo_por_dia:
                        conteo_por_dia[ds] += res.cantidad
        except Exception as e:
            logger.error(f"Error consultando actividad de ventas: {e}")

        # 2. Guías
        try:
            guias_raw = db.query(
                cast(WHTransaction.TransactionDate, Date).label("fecha"),
                func.count(WHTransaction.Transaction).label("cantidad")
            ).filter(
                WHTransaction.TransactionDate >= dias[0],
                WHTransaction.TransactionDate < (hoy + timedelta(days=1))
            ).group_by(cast(WHTransaction.TransactionDate, Date)).all()
            
            for res in guias_raw:
                if res.fecha:
                    ds = res.fecha.strftime("%Y-%m-%d")
                    if ds in conteo_por_dia:
                        conteo_por_dia[ds] += res.cantidad
        except Exception as e:
            logger.error(f"Error consultando actividad de guías: {e}")

        # 3. Retenciones
        try:
            retenciones_raw = db.query(
                cast(APRetencion.DocumentDate, Date).label("fecha"),
                func.count(APRetencion.Id).label("cantidad")
            ).filter(
                APRetencion.DocumentDate >= dias[0],
                APRetencion.DocumentDate < (hoy + timedelta(days=1))
            ).group_by(cast(APRetencion.DocumentDate, Date)).all()
            
            for res in retenciones_raw:
                if res.fecha:
                    ds = res.fecha.strftime("%Y-%m-%d")
                    if ds in conteo_por_dia:
                        conteo_por_dia[ds] += res.cantidad
        except Exception as e:
            logger.error(f"Error consultando actividad de retenciones: {e}")

        # Formatear para el frontend
        resultados = []
        for d in dias:
            ds = d.strftime("%Y-%m-%d")
            resultados.append({
                "fecha": d.strftime("%d/%m"),
                "cantidad": conteo_por_dia.get(ds, 0)
            })
            
        return ResponseBase(
            success=True,
            message="Actividad semanal obtenida",
            data=resultados
        )
    except Exception as e:
        logger.error(f"Error general en actividad-semanal: {e}")
        # En caso de error crítico, devolver lista vacía en lugar de romper el server
        return ResponseBase(
            success=False,
            message=f"Error al obtener actividad: {str(e)}",
            data=[]
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
    
    def normalizar_estado(estado_raw: Optional[str]) -> str:
        # Ahora que usamos nube_status_web, los datos ya vienen normalizados
        if not estado_raw:
            return "pendiente"
        return estado_raw.lower().strip()

    resumen_map = {}
    
    if tipo == "ventas":
        resultados = db.query(
            ARDocument.nube_status_web.label("estado"),
            func.count(ARDocument.Document).label("cantidad")
        ).group_by(ARDocument.nube_status_web).all()
        
    elif tipo == "retenciones":
        resultados = db.query(
            APRetencion.nube_status_web.label("estado"),
            func.count(APRetencion.Id).label("cantidad")
        ).group_by(APRetencion.nube_status_web).all()
        
    elif tipo == "guias":
        resultados = db.query(
            WHTransaction.nube_status_web.label("estado"),
            func.count(WHTransaction.Transaction).label("cantidad")
        ).group_by(WHTransaction.nube_status_web).all()
        
    else:
        return ResponseBase(
            success=False,
            message="Tipo no válido. Use: ventas, retenciones, guias"
        )

    for r in resultados:
        est = normalizar_estado(r.estado)
        resumen_map[est] = resumen_map.get(est, 0) + r.cantidad
        
    resumen = [
        {"estado": est, "cantidad": cant}
        for est, cant in resumen_map.items()
    ]
    
    return ResponseBase(
        success=True,
        message=f"Resumen de {tipo} obtenido",
        data=resumen
    )

