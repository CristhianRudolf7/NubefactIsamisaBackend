from .guias import router as guias_router
from .retenciones import router as retenciones_router
from .ventas import router as ventas_router
from .dashboard import router as dashboard_router
from .auth import router as auth_router
from .users import router as users_router
from .auditoria import router as auditoria_router
from .config import router as config_router

__all__ = [
    "guias_router",
    "retenciones_router",
    "ventas_router",
    "dashboard_router",
    "auth_router",
    "users_router",
    "auditoria_router",
    "config_router",
]
