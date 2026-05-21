from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, Date
from typing import Optional, Annotated
from datetime import datetime, timedelta
import json

from ..database import get_db
from ..models.auditoria import Auditoria
from ..models.user import User
from ..schemas.auditoria import (
    AuditoriaResponse,
    AuditoriaDetalleResponse,
    AuditoriaEstadisticas,
)
from ..schemas.common import ResponseBase
from .auth import require_admin

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])


@router.get("", response_model=ResponseBase)
async def listar_auditoria(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    tabla: Optional[str] = Query(None),
    accion: Optional[str] = Query(None),
    usuario: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    registro_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
):
    """Lista registros de auditoría con filtros y paginación (solo admin)"""
    
    query = db.query(Auditoria)
    
    # Aplicar filtros
    if tabla:
        query = query.filter(Auditoria.tabla == tabla)
    if accion:
        query = query.filter(Auditoria.accion == accion)
    if registro_id:
        query = query.filter(Auditoria.registro_id == registro_id)
    if usuario:
        query = query.filter(Auditoria.usuario.ilike(f"%{usuario}%"))
    if fecha_inicio:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            query = query.filter(Auditoria.fecha >= fecha_inicio_dt)
        except ValueError:
            pass
    if fecha_fin:
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Auditoria.fecha < fecha_fin_dt)
        except ValueError:
            pass
    
    # Total para paginación
    total = query.count()
    
    # Ordenar y paginar
    registros = query.order_by(desc(Auditoria.fecha)).offset((page - 1) * page_size).limit(page_size).all()
    
    return ResponseBase(
        success=True,
        message="Registros de auditoría obtenidos",
        data={
            "registros": [AuditoriaResponse.model_validate(r) for r in registros],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    )


@router.get("/estadisticas/resumen", response_model=ResponseBase)
async def obtener_estadisticas(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    dias: int = Query(30, ge=1, le=365, description="Días hacia atrás para estadísticas"),
):
    """Obtiene estadísticas de auditoría (solo admin)"""
    
    # Usar fecha del servidor SQL para evitar problemas de zona horaria
    fecha_actual = db.query(func.now()).scalar()
    fecha_limite = fecha_actual - timedelta(days=dias)
    
    # Total de registros
    total_registros = db.query(func.count(Auditoria.id)).filter(
        Auditoria.fecha >= fecha_limite
    ).scalar()
    
    # Acciones por tipo
    acciones_por_tipo = db.query(
        Auditoria.accion,
        func.count(Auditoria.id).label("cantidad")
    ).filter(
        Auditoria.fecha >= fecha_limite
    ).group_by(Auditoria.accion).all()
    
    # Acciones por tabla
    acciones_por_tabla = db.query(
        Auditoria.tabla,
        func.count(Auditoria.id).label("cantidad")
    ).filter(
        Auditoria.fecha >= fecha_limite
    ).group_by(Auditoria.tabla).all()
    
    # Usuarios más activos
    usuarios_activos = db.query(
        Auditoria.usuario,
        func.count(Auditoria.id).label("cantidad")
    ).filter(
        Auditoria.fecha >= fecha_limite,
        Auditoria.usuario.isnot(None)
    ).group_by(Auditoria.usuario).order_by(desc("cantidad")).limit(10).all()
    
    # Acciones por día - usar CAST para compatibilidad con SQL Server
    acciones_por_dia = db.query(
        func.cast(Auditoria.fecha, Date).label("fecha"),
        func.count(Auditoria.id).label("cantidad")
    ).filter(
        Auditoria.fecha >= fecha_limite
    ).group_by(func.cast(Auditoria.fecha, Date)).order_by(func.cast(Auditoria.fecha, Date)).all()
    
    return ResponseBase(
        success=True,
        message="Estadísticas de auditoría obtenidas",
        data=AuditoriaEstadisticas(
            total_registros=total_registros or 0,
            acciones_por_tipo={a.accion: a.cantidad for a in acciones_por_tipo},
            acciones_por_tabla={t.tabla: t.cantidad for t in acciones_por_tabla},
            usuarios_mas_activos=[{"usuario": u.usuario, "cantidad": u.cantidad} for u in usuarios_activos],
            acciones_por_dia=[{"fecha": str(d.fecha), "cantidad": d.cantidad} for d in acciones_por_dia],
        )
    )


@router.get("/tablas")
async def listar_tablas(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Lista las tablas que tienen registros de auditoría (solo admin)"""
    
    tablas = db.query(Auditoria.tabla).distinct().all()
    
    return {
        "success": True,
        "message": "Tablas obtenidas",
        "data": [t[0] for t in tablas]
    }


@router.get("/acciones")
async def listar_acciones(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Lista los tipos de acciones registradas (solo admin)"""
    
    acciones = db.query(Auditoria.accion).distinct().all()
    
    return {
        "success": True,
        "message": "Acciones obtenidas",
        "data": [a[0] for a in acciones]
    }


@router.get("/{id}", response_model=ResponseBase)
async def obtener_detalle_auditoria(
    id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    """Obtiene detalle de un registro de auditoría con datos parseados (solo admin)"""
    
    registro = db.query(Auditoria).filter(Auditoria.id == id).first()
    
    if not registro:
        return ResponseBase(
            success=False,
            message="Registro de auditoría no encontrado",
        )
    
    # Parsear datos JSON
    datos_anteriores = None
    datos_nuevos = None
    
    if registro.datos_anteriores:
        try:
            datos_anteriores = json.loads(registro.datos_anteriores)
        except json.JSONDecodeError:
            datos_anteriores = registro.datos_anteriores
    
    if registro.datos_nuevos:
        try:
            datos_nuevos = json.loads(registro.datos_nuevos)
        except json.JSONDecodeError:
            datos_nuevos = registro.datos_nuevos
    
    return ResponseBase(
        success=True,
        message="Detalle de auditoría obtenido",
        data=AuditoriaDetalleResponse(
            id=registro.id,
            tabla=registro.tabla,
            registro_id=registro.registro_id,
            accion=registro.accion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            usuario=registro.usuario,
            fecha=registro.fecha,
            ip=registro.ip,
        )
    )
