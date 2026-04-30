# ISAMISA - Sistema de Gestión de Documentos Electrónicos

Sistema para gestionar documentos electrónicos (Facturas, Boletas, Guías de Remisión, NC, ND) con integración a NubeFact/SUNAT.

## Estructura del Proyecto

```
sunat_isamisa/
  sql/           # Configuración Docker de SQL Server
  backend/       # API FastAPI (Python)
  frontend/      # Interfaz React + Vite
  api/           # Ejemplos JSON de NubeFact
```

## Requisitos

- Docker
- Python 3.11+
- Node.js 20+

## Inicio Rápido

### 1. Iniciar SQL Server

```bash
cd sql
sudo docker compose up -d
```

### 2. Iniciar Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Iniciar Frontend

```bash
cd frontend
npm run dev
```

## URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Funcionalidades

- **Documentos de Venta**: Facturas, Boletas, Notas de Crédito, Notas de Débito
- **Guías de Remisión**: Remitente con datos de transporte
- **Retenciones**: Documentos con retención
- **Estados**: Pendiente, Enviado, Aceptado, Rechazado, Anulado
- **Integración NubeFact**: Envío automático a SUNAT
- **Filtros avanzados**: Por fecha, serie, número, cliente, estado
- **Descargas**: PDF y XML de documentos

## API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/documentos | Lista documentos |
| GET | /api/documentos/{id} | Obtiene documento |
| POST | /api/documentos | Crea documento |
| PUT | /api/documentos/{id} | Actualiza documento |
| POST | /api/documentos/{id}/enviar | Envía a NubeFact |
| POST | /api/documentos/{id}/anular | Anula documento |
| GET | /api/documentos/{id}/consultar | Consulta estado |

## Tipos de Documento

| Código | Tipo |
|--------|------|
| 1 | Factura |
| 2 | Boleta |
| 3 | Nota de Crédito |
| 4 | Nota de Débito |
| 7 | Guía de Remisión |

## Estados

| Estado | Descripción |
|--------|-------------|
| pendiente | Pendiente de envío |
| enviado_nubefact | Enviado a NubeFact |
| aceptado | Aceptado por SUNAT |
| aceptado_observaciones | Aceptado con observaciones |
| rechazado | Rechazado por SUNAT |
| anulado | Documento anulado |

## Configuración

Las credenciales de NubeFact están en `backend/.env`:

```
NUBEFACT_RUTA=https://api.nubefact.com/api/v1/...
NUBEFACT_TOKEN=...
```

## Base de Datos

Tablas principales:
- `documentos` - Cabecera de documentos
- `documentos_items` - Detalle de items
- `guias_remision` - Datos específicos de guías
- `retenciones` - Datos de retención
- `auditoria` - Registro de acciones
- `configuracion` - Parámetros del sistema
