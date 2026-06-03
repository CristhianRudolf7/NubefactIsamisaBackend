from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import engine, Base
from app.routers import guias_router, retenciones_router, ventas_router, dashboard_router, auth_router, users_router, auditoria_router, config_router
from app.worker import worker

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events de la aplicación"""
    # Startup: Intentar crear tablas si no existen (no fallar si BD no disponible)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: No se pudo conectar a la base de datos: {e}")
        print("El servidor iniciará pero las funciones de BD no estarán disponibles.")
    
    # Iniciar worker automático
    worker.start()
    
    yield
    
    # Shutdown: Cerrar conexiones y detener worker
    worker.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Sistema de Gestión de Documentos Electrónicos - SUNAT/NubeFact
    
    ## Funcionalidades
    
    * **Ventas**: Gestión de facturas, boletas, notas de crédito y débito
    * **Retenciones**: Gestión de comprobantes de retención
    * **Guías**: Gestión de guías de remisión
    * **Dashboard**: Estadísticas y estados de documentos
    
    ## Integración con NubeFact
    
    Este sistema se integra con la API de NubeFact para el envío de documentos
    electrónicos a SUNAT.
    """,
    lifespan=lifespan,
)

# Configurar CORS
import socket

allowed_origins = settings.allowed_origins.split(",")

# Auto-detectar la IP local del servidor para permitir conexiones desde la misma red local
try:
    # Método 1: Socket UDP (muy confiable)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
except Exception:
    try:
        # Método 2: Hostname
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = None

if local_ip:
    local_origins = [
        f"http://{local_ip}",
        f"http://{local_ip}:80",
        f"http://{local_ip}:5173",
        f"http://{local_ip}:3000",
    ]
    for origin in local_origins:
        if origin not in allowed_origins:
            allowed_origins.append(origin)

# IMPORTANTE: Cuando allow_credentials=True, NO se puede usar allow_origins=["*"]
# El navegador rechaza enviar cookies con orígenes wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(guias_router, prefix="/api")
app.include_router(retenciones_router, prefix="/api")
app.include_router(ventas_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(auditoria_router, prefix="/api")
app.include_router(config_router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz"""
    return {
        "message": "Sistema de Gestión de Documentos Electrónicos",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.app_version}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
