from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from fastapi import HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.user import User, UserRole
from ..schemas.auth import TokenData, CurrentUser

settings = get_settings()


def hash_password(password: str) -> str:
    """Hashea una contraseña con bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: TokenData, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un access token JWT"""
    to_encode = {
        "user_id": data.user_id,
        "dni": data.dni,
        "rol": data.rol.value if data.rol else None,
        "type": "access"
    }
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode["exp"] = expire
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(data: TokenData, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un refresh token JWT"""
    to_encode = {
        "user_id": data.user_id,
        "dni": data.dni,
        "type": "refresh"
    }
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode["exp"] = expire
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decodifica un token JWT"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Establece las cookies de autenticación HTTP-only"""
    # Access token - 15 minutos
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Cambiar a True en producción con HTTPS
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/"
    )
    # Refresh token - 7 días
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # Cambiar a True en producción con HTTPS
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/auth/refresh"  # Solo accesible en el endpoint de refresh
    )


def clear_auth_cookies(response: Response):
    """Elimina las cookies de autenticación"""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/auth/refresh")


def get_current_user(request: Request, db: Session) -> User:
    """Obtiene el usuario actual desde el token en la cookie"""
    access_token = request.cookies.get("access_token")
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(access_token)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    
    return user


def get_current_user_optional(request: Request, db: Session) -> Optional[User]:
    """Obtiene el usuario actual si está autenticado, sino retorna None"""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


def require_role(required_roles: list[UserRole]):
    """Decorator para requerir roles específicos"""
    def role_checker(request: Request, db: Session = None):
        # Esta función se usará como dependencia
        pass
    return role_checker


def authenticate_user(db: Session, dni: str, password: str) -> Optional[User]:
    """Autentica un usuario por DNI y contraseña"""
    user = db.query(User).filter(User.dni == dni).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user
