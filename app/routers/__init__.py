from .guias import router as guias_router
from .retenciones import router as retenciones_router
from .ventas import router as ventas_router
from .dashboard import router as dashboard_router
from .auth import router as auth_router
from .users import router as users_router
from .tokens import router as tokens_router
from .external import router as external_router

__all__ = [
    "guias_router",
    "retenciones_router",
    "ventas_router",
    "dashboard_router",
    "auth_router",
    "users_router",
    "tokens_router",
    "external_router",
]
