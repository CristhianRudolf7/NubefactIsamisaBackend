from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from typing import Annotated

from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import UserLogin, UserResponse
from ..schemas.auth import CurrentUser
from ..services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    clear_auth_cookies,
    get_current_user,
    decode_token,
    TokenData,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login")
async def login(
    user_login: UserLogin,
    response: Response,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Iniciar sesión con DNI y contraseña.
    Establece cookies HTTP-only con access_token y refresh_token.
    """
    user = authenticate_user(db, user_login.dni, user_login.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="DNI o contraseña incorrectos",
        )
    
    # Crear tokens
    token_data = TokenData(user_id=user.id, dni=user.dni, rol=user.rol)
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Establecer cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    return {
        "message": "Login exitoso",
        "user": UserResponse.model_validate(user)
    }


@router.post("/logout")
async def logout(response: Response):
    """
    Cerrar sesión.
    Elimina las cookies de autenticación.
    """
    clear_auth_cookies(response)
    return {"message": "Sesión cerrada exitosamente"}


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Renovar access token usando el refresh token.
    """
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No hay refresh token",
        )
    
    # Decodificar refresh token
    payload = decode_token(refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )
    
    # Crear nuevos tokens
    token_data = TokenData(user_id=user.id, dni=user.dni, rol=user.rol)
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    # Establecer nuevas cookies
    set_auth_cookies(response, new_access_token, new_refresh_token)
    
    return {
        "message": "Token renovado",
        "user": UserResponse.model_validate(user)
    }


@router.get("/me", response_model=CurrentUser)
async def get_me(
    request: Request,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Obtener información del usuario actual.
    """
    user = get_current_user(request, db)
    return CurrentUser(
        id=user.id,
        dni=user.dni,
        nombre=user.nombre,
        rol=user.rol,
        is_active=user.is_active
    )


# Dependencia para obtener el usuario actual
async def get_current_user_dep(
    request: Request,
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """Dependencia para obtener el usuario actual"""
    return get_current_user(request, db)


# Dependencia para requerir rol admin
async def require_admin(
    current_user: Annotated[User, Depends(get_current_user_dep)]
) -> User:
    """Dependencia que requiere rol admin"""
    if current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador"
        )
    return current_user


# Dependencia para requerir cualquier usuario autenticado
async def require_authenticated(
    current_user: Annotated[User, Depends(get_current_user_dep)]
) -> User:
    """Dependencia que requiere usuario autenticado"""
    return current_user


# Dependencia para requerir acceso a ventas
async def require_ventas_access(
    current_user: Annotated[User, Depends(get_current_user_dep)]
) -> User:
    """Dependencia que requiere acceso al módulo de ventas"""
    if current_user.rol == UserRole.ADMIN:
        return current_user
    if not current_user.puede_acceder_ventas:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso al módulo de ventas"
        )
    return current_user


# Dependencia para requerir acceso a guías
async def require_guias_access(
    current_user: Annotated[User, Depends(get_current_user_dep)]
) -> User:
    """Dependencia que requiere acceso al módulo de guías"""
    if current_user.rol == UserRole.ADMIN:
        return current_user
    if not current_user.puede_acceder_guias:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso al módulo de guías"
        )
    return current_user


# Dependencia para requerir acceso a retenciones
async def require_retenciones_access(
    current_user: Annotated[User, Depends(get_current_user_dep)]
) -> User:
    """Dependencia que requiere acceso al módulo de retenciones"""
    if current_user.rol == UserRole.ADMIN:
        return current_user
    if not current_user.puede_acceder_retenciones:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso al módulo de retenciones"
        )
    return current_user
