# API de Integración - Documentos Electrónicos

Esta API permite notificar documentos electrónicos (ventas, guías, retenciones) desde sistemas externos como ERPs.

## Autenticación

Todas las peticiones deben incluir el token de acceso en el header:

```
Authorization: Bearer <tu_token>
```

> **Nota**: El token te será proporcionado por el administrador del sistema. Guárdalo de forma segura.

---

## Endpoints Disponibles

### Verificar Conexión

Verifica que tu token está activo y funcionando.

```http
GET /external/status
```

**Ejemplo:**
```bash
curl -X GET "https://tu-servidor.com/external/status" \
  -H "Authorization: Bearer tu_token_aqui"
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Token válido",
  "data": {
    "token_name": "Mi ERP",
    "last_used_at": "2026-04-13T21:30:00"
  }
}
```

---

## Notificar Documento de Venta

Registra una factura, boleta, nota de crédito o nota de débito.

```http
POST /external/ventas/
```

### Campos Requeridos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `Document` | string | ID único del documento (obligatorio) |
| `DocumentSerie` | string | Serie del documento (ej: FFF1) |
| `DocumentNo` | string | Número del documento |
| `DocumentType` | string | Tipo: FACTURA, BOLETA, NC, ND |
| `VendorRUC` | string | RUC del cliente |
| `VendorName` | string | Nombre del cliente |
| `DocumentDate` | float | Fecha en formato Excel (número serie) |
| `DocumentCurrency` | string | Moneda: LO (Soles) o EX (Dólares) |
| `AmountNetLo` | float | Monto neto |
| `AmountTaxLo` | float | IGV |
| `AmountTotalLo` | float | Total |
| `detalles` | array | Lista de items del documento |

### Campos del Detalle

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `Line` | int | Número de línea |
| `ItemCode` | string | Código del producto |
| `Description` | string | Descripción del producto/servicio |
| `Quantity` | float | Cantidad |
| `Unit` | string | Unidad de medida (UN, KG, etc.) |
| `Price` | float | Precio unitario |
| `Total` | float | Total de la línea |

### Ejemplo Completo

```bash
curl -X POST "https://tu-servidor.com/external/ventas/" \
  -H "Authorization: Bearer tu_token_aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "Document": "FFF1-00123",
    "DocumentSerie": "FFF1",
    "DocumentNo": "00123",
    "DocumentType": "FACTURA",
    "VendorRUC": "20123456789",
    "VendorName": "Cliente S.A.C.",
    "VendorAddress": "Av. Principal 123",
    "DocumentDate": 45234.0,
    "DocumentCurrency": "LO",
    "AmountNetLo": 1000.0,
    "AmountTaxLo": 180.0,
    "AmountTotalLo": 1180.0,
    "detalles": [
      {
        "Line": 1,
        "ItemCode": "PROD001",
        "Description": "Producto 1",
        "Quantity": 10,
        "Unit": "UN",
        "Price": 100.0,
        "Total": 1000.0
      }
    ]
  }'
```

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Documento de venta registrado correctamente",
  "data": {
    "Document": "FFF1-00123",
    "status": "pendiente"
  }
}
```

---

## Notificar Guía de Remisión

Registra una guía de remisión para transporte de mercancía.

```http
POST /external/guias/
```

### Campos Requeridos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `Transaction` | string | ID único de la transacción (obligatorio) |
| `DocumentSerie` | string | Serie de la guía |
| `DocumentNo` | string | Número de la guía |
| `TransactionDate` | float | Fecha en formato Excel |
| `TargetPersonRUC` | string | RUC del destinatario |
| `TargetPersonName` | string | Nombre del destinatario |
| `TargetAddress` | string | Dirección de destino |
| `MotivoTraslado` | string | Código de motivo (01-09) |
| `PesoBruto` | float | Peso total en kg |
| `VehicleID` | string | Placa del vehículo |
| `Driver` | string | Nombre del conductor |
| `LicenciaConducir` | string | Licencia del conductor |
| `detalles` | array | Lista de items a transportar |

### Ejemplo

```bash
curl -X POST "https://tu-servidor.com/external/guias/" \
  -H "Authorization: Bearer tu_token_aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "Transaction": "WH001",
    "DocumentSerie": "T001",
    "DocumentNo": "00123",
    "TransactionDate": 45234.0,
    "TargetPersonRUC": "20123456789",
    "TargetPersonName": "Destinatario S.A.C.",
    "TargetAddress": "Av. Destino 456",
    "MotivoTraslado": "01",
    "PesoBruto": 100.0,
    "VehicleID": "ABC-123",
    "Driver": "Juan Pérez",
    "LicenciaConducir": "12345678",
    "detalles": [
      {
        "Line": 1,
        "ItemCode": "PROD001",
        "ItemDescription": "Producto 1",
        "Quantity": 10,
        "Unit": "UN"
      }
    ]
  }'
```

---

## Notificar Retención

Registra un comprobante de retención.

```http
POST /external/retenciones/
```

### Campos Requeridos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `Serie` | string | Serie de la retención |
| `Numero` | string | Número de la retención |
| `VendorRuc` | string | RUC del proveedor |
| `VendorName` | string | Nombre del proveedor |
| `DocumentDate` | float | Fecha en formato Excel |
| `Tasa` | int | Tasa de retención (ej: 8) |
| `TotalRetenido` | float | Monto retenido |
| `TotalPagado` | float | Monto pagado |
| `detalles` | array | Detalles de la retención |

### Ejemplo

```bash
curl -X POST "https://tu-servidor.com/external/retenciones/" \
  -H "Authorization: Bearer tu_token_aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "Serie": "R001",
    "Numero": "00123",
    "VendorRuc": "20123456789",
    "VendorName": "Proveedor S.A.C.",
    "DocumentDate": 45234.0,
    "Tasa": 8,
    "TotalRetenido": 80.0,
    "TotalPagado": 920.0,
    "detalles": [
      {
        "DRserie": "FFF1",
        "DRnumero": "00100",
        "DRfecha": 45230.0,
        "DRmoneda": "LO",
        "DRtotal": 1000.0,
        "Retenido": 80.0,
        "Pagado": 920.0
      }
    ]
  }'
```

---

## Códigos de Error

| Código | Descripción | Solución |
|--------|-------------|----------|
| 401 | Token inválido o expirado | Verifica que el token sea correcto o solicita uno nuevo |
| 400 | Documento ya existe | El documento ya fue registrado previamente |
| 400 | Datos inválidos | Revisa los campos enviados |
| 500 | Error del servidor | Contacta al administrador |

---

## Flujo de Integración

1. **Al crear un documento en tu ERP**, envía los datos a esta API
2. **El documento queda en estado "pendiente"** para su posterior envío a SUNAT
3. **El sistema notificará a SUNAT** automáticamente
4. **Consulta el estado** del documento en la web del sistema

---

## Recomendaciones

- Guarda el token en una variable de entorno segura
- Implementa reintentos con backoff exponencial si el servicio no está disponible
- Registra los errores para debugging
- Valida que los campos obligatorios estén presentes antes de enviar
