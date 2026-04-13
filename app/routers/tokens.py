from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated, List

from ..database import get_db
from ..models.user import User
from ..models.api_token import ApiToken
from ..schemas.api_token import ApiTokenCreate, ApiTokenUpdate, ApiTokenResponse, ApiTokenCreated
from ..services.token_service import create_api_token
from .auth import require_admin

router = APIRouter(prefix="/tokens", tags=["Tokens de API"])


@router.get("/", response_model=List[ApiTokenResponse])
async def list_tokens(
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100
):
    """
    Lista todos los tokens de API. Solo administradores.
    No muestra el token completo, solo el prefijo.
    """
    tokens = db.query(ApiToken).order_by(ApiToken.id).offset(skip).limit(limit).all()
    return tokens


@router.post("/", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_token(
    token_data: ApiTokenCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Crea un nuevo token de API. Solo administradores.
    
    IMPORTANTE: El token completo solo se muestra una vez.
    Guárdalo de forma segura, no podrás recuperarlo.
    """
    api_token, token_plain = create_api_token(
        db=db,
        name=token_data.name,
        created_by=current_user.id,
        expires_at=token_data.expires_at
    )
    
    return ApiTokenCreated(
        id=api_token.id,
        name=api_token.name,
        token_prefix=api_token.token_prefix,
        token=token_plain,
        is_active=api_token.is_active,
        last_used_at=api_token.last_used_at,
        expires_at=api_token.expires_at,
        created_at=api_token.created_at,
        created_by=api_token.created_by,
        message="Guarda este token de forma segura. No podrás verlo de nuevo."
    )


@router.get("/{token_id}", response_model=ApiTokenResponse)
async def get_token(
    token_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Obtiene un token por ID. Solo administradores.
    """
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token no encontrado"
        )
    return token


@router.put("/{token_id}", response_model=ApiTokenResponse)
async def update_token(
    token_id: int,
    token_data: ApiTokenUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Actualiza un token de API. Solo administradores.
    Se puede actualizar nombre, estado y fecha de expiración.
    """
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token no encontrado"
        )
    
    if token_data.name is not None:
        token.name = token_data.name
    if token_data.is_active is not None:
        token.is_active = token_data.is_active
    if token_data.expires_at is not None:
        token.expires_at = token_data.expires_at
    
    db.commit()
    db.refresh(token)
    return token


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_token(
    token_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Elimina un token de API. Solo administradores.
    """
    token = db.query(ApiToken).filter(ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token no encontrado"
        )
    
    db.delete(token)
    db.commit()
    return None
