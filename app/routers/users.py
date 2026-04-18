from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Annotated, List

from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import UserCreate, UserUpdate, UserResponse
from ..services.auth_service import hash_password
from ..services.auditoria_service import AuditoriaService
from ..utils import get_client_ip
from .auth import require_admin, get_current_user_dep

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/", response_model=List[UserResponse])
async def get_users(
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
):
    """
    Obtener lista de usuarios. Solo administradores.
    """
    users = db.query(User).order_by(User.id).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Obtener un usuario por ID. Solo administradores.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return UserResponse.model_validate(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Crear un nuevo usuario. Solo administradores.
    """
    # Verificar si el DNI ya existe
    existing_user = db.query(User).filter(User.dni == user_data.dni).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El DNI ya está registrado"
        )
    
    # Crear usuario con contraseña hasheada
    new_user = User(
        dni=user_data.dni,
        nombre=user_data.nombre,
        celular=user_data.celular,
        password_hash=hash_password(user_data.password),
        rol=user_data.rol,
        is_active=True,
        recibir_notificaciones=user_data.recibir_notificaciones,
        puede_acceder_ventas=user_data.puede_acceder_ventas,
        puede_acceder_guias=user_data.puede_acceder_guias,
        puede_acceder_retenciones=user_data.puede_acceder_retenciones
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Registrar auditoría
    auditoria = AuditoriaService(db)
    auditoria.registrar_creacion(
        tabla="usuarios",
        registro_id=new_user.id,
        datos_nuevos={
            "dni": new_user.dni,
            "nombre": new_user.nombre,
            "rol": new_user.rol,
            "is_active": new_user.is_active,
        },
        usuario=current_user.nombre,
        ip=get_client_ip(request)
    )
    
    return UserResponse.model_validate(new_user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: int,
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Actualizar un usuario. Solo administradores.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar DNI duplicado si se está cambiando
    if user_data.dni and user_data.dni != user.dni:
        existing = db.query(User).filter(User.dni == user_data.dni).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El DNI ya está registrado"
            )
    
    # Guardar datos anteriores para auditoría
    datos_anteriores = {
        "dni": user.dni,
        "nombre": user.nombre,
        "rol": user.rol,
        "is_active": user.is_active,
        "puede_acceder_ventas": user.puede_acceder_ventas,
        "puede_acceder_guias": user.puede_acceder_guias,
        "puede_acceder_retenciones": user.puede_acceder_retenciones,
    }
    
    # Actualizar campos
    update_data = user_data.model_dump(exclude_unset=True)
    
    # Si hay contraseña, hashearla
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    # Registrar auditoría
    datos_nuevos = {
        "dni": user.dni,
        "nombre": user.nombre,
        "rol": user.rol,
        "is_active": user.is_active,
        "puede_acceder_ventas": user.puede_acceder_ventas,
        "puede_acceder_guias": user.puede_acceder_guias,
        "puede_acceder_retenciones": user.puede_acceder_retenciones,
    }
    auditoria = AuditoriaService(db)
    auditoria.registrar_cambio(
        tabla="usuarios",
        registro_id=user.id,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
        usuario=current_user.nombre,
        ip=get_client_ip(request)
    )
    
    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Eliminar un usuario. Solo administradores.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No permitir eliminarse a sí mismo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminarte a ti mismo"
        )
    
    # Guardar datos para auditoría antes de eliminar
    datos_usuario = {
        "dni": user.dni,
        "nombre": user.nombre,
        "rol": user.rol,
    }
    
    db.delete(user)
    db.commit()
    
    # Registrar auditoría
    auditoria = AuditoriaService(db)
    auditoria.registrar_eliminacion(
        tabla="usuarios",
        registro_id=user_id,
        datos_anteriores=datos_usuario,
        usuario=current_user.nombre,
        ip=get_client_ip(request)
    )
    
    return {"message": "Usuario eliminado exitosamente"}
