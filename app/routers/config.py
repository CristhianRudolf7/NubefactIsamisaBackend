from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Any, Annotated

from ..database import get_db
from ..models.config import ConfiguracionEnvio
from ..schemas.config import ConfiguracionEnvioSchema, ConfiguracionEnvioUpdate
from ..schemas.common import ResponseBase
from .auth import require_admin

router = APIRouter(prefix="/config", tags=["Configuración"])

@router.get("/envios", response_model=ResponseBase)
async def obtener_configuraciones(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Any, Depends(require_admin)]
):
    """Obtiene todas las configuraciones de envío"""
    configs = db.query(ConfiguracionEnvio).all()
    
    # Si no existen, crearlas por defecto
    if not configs:
        tipos = ['ventas', 'guias', 'retenciones']
        for tipo in tipos:
            db_config = ConfiguracionEnvio(tipo_documento=tipo, modo='manual', activo=False)
            db.add(db_config)
        db.commit()
        configs = db.query(ConfiguracionEnvio).all()
        
    return ResponseBase(
        success=True,
        message="Configuraciones obtenidas",
        data=[ConfiguracionEnvioSchema.from_orm(c) for c in configs]
    )

@router.put("/envios/{tipo}", response_model=ResponseBase)
async def actualizar_configuracion(
    tipo: str,
    datos: ConfiguracionEnvioUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Any, Depends(require_admin)]
):
    """Actualiza la configuración para un tipo de documento"""
    db_config = db.query(ConfiguracionEnvio).filter(
        ConfiguracionEnvio.tipo_documento == tipo
    ).first()
    
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    
    if datos.modo is not None:
        db_config.modo = datos.modo
    if datos.activo is not None:
        db_config.activo = datos.activo
    if datos.intervalo_segundos is not None:
        db_config.intervalo_segundos = datos.intervalo_segundos
        
    db.commit()
    db.refresh(db_config)
    
    return ResponseBase(
        success=True,
        message="Configuración actualizada",
        data=ConfiguracionEnvioSchema.from_orm(db_config)
    )
