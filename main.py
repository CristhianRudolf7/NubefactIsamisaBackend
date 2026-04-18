from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import engine, Base
from app.routers import guias_router, retenciones_router, ventas_router, dashboard_router, auth_router, users_router, auditoria_router

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
    yield
    # Shutdown: Cerrar conexiones
    pass


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
# IMPORTANTE: Cuando allow_credentials=True, NO se puede usar allow_origins=["*"]
# El navegador rechaza enviar cookies con orígenes wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Puerto alternativo
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
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
