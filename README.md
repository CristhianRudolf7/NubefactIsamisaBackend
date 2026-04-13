# Backend FastAPI - Sistema de Gestión de Documentos Electrónicos

Sistema de gestión de documentos electrónicos integrado con SUNAT a través de NubeFact.

## Requisitos

- Python 3.11+
- SQL Server
- Driver ODBC para SQL Server

## Instalación

### 1. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copiar `.env.example` a `.env` y configurar:

```env
DATABASE_URL=mssql+pyodbc://usuario:password@host:1433/base_datos?driver=ODBC+Driver+17+for+SQL+Server
NUBEFACT_URL=https://api.nubefact.com/api/v1/TU_ID
NUBEFACT_TOKEN=TU_TOKEN
```

## Ejecución

### Desarrollo

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Producción

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Estructura del Proyecto

```
backend/
  app/
    __init__.py
    config.py              # Configuración
    database.py            # Conexión SQL Server
    models/                # Modelos SQLAlchemy
      __init__.py
      guias.py             # WH_Transaction, WH_TransactionDetail
      retenciones.py       # AP_Retencion, AP_RetencionDetail, AP_Retencion_Status
      ventas.py            # AR_Document, AR_DocumentDetail
      nube_response.py     # AR_FE_Nube
    schemas/               # Modelos Pydantic
      __init__.py
      common.py
      guias.py
      retenciones.py
      ventas.py
      nubefact.py
    routers/               # Endpoints API
      __init__.py
      guias.py
      retenciones.py
      ventas.py
      dashboard.py
    services/              # Lógica de negocio
      __init__.py
      nubefact_client.py   # Cliente HTTP NubeFact
      document_service.py  # Servicios de documentos
  main.py
  requirements.txt
  .env
  .env.example
```

## Endpoints

### Guías de Remisión

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/guias/` | Listar guías con filtros |
| GET | `/api/guias/{id}` | Obtener detalle de guía |
| POST | `/api/guias/{id}/enviar` | Enviar guía a NubeFact |
| PUT | `/api/guias/{id}` | Actualizar guía |

### Retenciones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/retenciones/` | Listar retenciones con filtros |
| GET | `/api/retenciones/{id}` | Obtener detalle de retención |
| POST | `/api/retenciones/{id}/enviar` | Enviar retención a NubeFact |
| PUT | `/api/retenciones/{id}` | Actualizar retención |

### Documentos de Venta

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/ventas/` | Listar documentos con filtros |
| GET | `/api/ventas/{id}` | Obtener detalle de documento |
| POST | `/api/ventas/{id}/enviar` | Enviar documento a NubeFact |
| PUT | `/api/ventas/{id}` | Actualizar documento |
| POST | `/api/ventas/{id}/anular` | Anular documento |

### Dashboard

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/dashboard/estadisticas` | Estadísticas generales |
| GET | `/api/dashboard/estados` | Lista de estados posibles |
| GET | `/api/dashboard/tipos-documento` | Tipos de documento |
| GET | `/api/dashboard/motivos-traslado` | Motivos de traslado |
| GET | `/api/dashboard/resumen-por-estado` | Resumen por estado |

## Documentación

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Estados de Documentos

| Estado | Descripción | Puede Editar |
|--------|-------------|--------------|
| pendiente | Pendiente de envío | Sí |
| enviado_nubefact | Enviado a NubeFact | No |
| aceptado | Aceptado por SUNAT | No |
| aceptado_observaciones | Aceptado con observaciones | Sí |
| rechazado | Rechazado por SUNAT | Sí |
| error | Error en el envío | Sí |

## Integración con NubeFact

El sistema utiliza la API de NubeFact para:

1. **Generar comprobantes**: Facturas, boletas, notas de crédito/débito
2. **Generar guías**: Guías de remisión remitente
3. **Generar retenciones**: Comprobantes de retención
4. **Consultar CPE**: Estado de comprobantes
5. **Anular documentos**: Generar documentos de anulación

### Credenciales

Las credenciales de NubeFact se configuran en el archivo `.env`:

```env
NUBEFACT_URL=https://api.nubefact.com/api/v1/TU_ID
NUBEFACT_TOKEN=TU_TOKEN
```

## Docker (Opcional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t sunat-backend .
docker run -p 8000:8000 sunat-backend
```

## Licencia

Privado - ISAMISA
