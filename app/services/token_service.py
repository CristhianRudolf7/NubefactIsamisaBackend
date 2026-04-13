import secrets
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..database import get_db
from ..models.api_token import ApiToken
from ..services.auth_service import verify_password

# Esquema de autenticación Bearer
security = HTTPBearer()


def generate_token() -> str:
    """Genera un token aleatorio de 32 caracteres (64 hex)"""
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    """Hashea un token usando bcrypt"""
    from ..services.auth_service import hash_password
    return hash_password(token)


def verify_token_hash(token: str, token_hash: str) -> bool:
    """Verifica un token contra su hash"""
    return verify_password(token, token_hash)


def create_api_token(db: Session, name: str, created_by: int, expires_at: datetime = None) -> tuple[ApiToken, str]:
    """
    Crea un nuevo token de API.
    Retorna (ApiToken, token_plano)
    """
    token_plain = generate_token()
    token_hash = hash_token(token_plain)
    token_prefix = token_plain[:8]
    
    api_token = ApiToken(
        name=name,
        token_hash=token_hash,
        token_prefix=token_prefix,
        created_by=created_by,
        expires_at=expires_at,
    )
    
    db.add(api_token)
    db.commit()
    db.refresh(api_token)
    
    return api_token, token_plain


def validate_api_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> ApiToken:
    """
    Dependencia para validar token de API.
    Retorna el objeto ApiToken si es válido.
    """
    token = credentials.credentials
    
    # Buscar token por prefijo para reducir búsquedas
    token_prefix = token[:8]
    
    api_token = db.query(ApiToken).filter(
        ApiToken.token_prefix == token_prefix,
        ApiToken.is_active == True
    ).first()
    
    if not api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o no encontrado"
        )
    
    # Verificar hash
    if not verify_token_hash(token, api_token.token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    # Verificar expiración
    if api_token.expires_at and api_token.expires_at < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    
    # Actualizar última vez usado
    api_token.last_used_at = datetime.now()
    db.commit()
    
    return api_token


def get_optional_api_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> ApiToken:
    """Alias para validate_api_token con nombre más descriptivo"""
    return validate_api_token(credentials, db)
