# Sistema de Gestión de Documentos Electrónicos - SUNAT/NubeFact

## 1. Objetivos del Sistema

- **Centralización**: Gestionar todos los tipos de documentos desde un solo portal.
- **Estandarización**: Estandarizar la operación.
- **Monitoreo**: Facilitar el monitoreo en tiempo real.
- **Gestión de Errores**: Registrar el error devuelto por SUNAT/NubeFact.
- **Trazabilidad**: Registro de logs y auditoría de acciones de usuario.
- **Despliegue**: Entorno Docker reproducible con scripts de despliegue incluidos.

---

## 2. Documentos

### 2.1 Documentos de Venta (Facturas, Boletas, ND, NC)

- Reenvío de comprobantes electrónicos.
- Corrección de documentos observados.
- Validación de estados (aceptado, rechazado, pendiente).

### 2.2 Documentos de Retención

- Reenvío de documentos.
- Validación de errores.
- Modificación de documentos observados.

### 2.3 Guías de Remisión (Remitente)

- Reenvío de guías.
- Seguimiento del estado.
- Validación y corrección de errores.

---

## 3. Funcionalidades del Sistema

### 3.1 Filtros y Búsqueda

- Filtros de fecha y serie.

### 3.2 Dashboard

#### a) Datos del Documento

| Campo | Descripción |
|-------|-------------|
| Tipo de documento | Factura, Boleta, Retención, Guía, etc. |
| Serie | Serie del documento |
| Número | Número correlativo |
| Fecha de emisión | Fecha de emisión del documento |
| RUC / DNI | Documento de identidad del cliente |
| Razón social / Nombre | Nombre del cliente |

#### b) Estados del Documento

| Estado | Descripción |
|--------|-------------|
| Enviado a NubeFact | Documento enviado al proveedor |
| Aceptado por SUNAT | Documento validado correctamente |
| Aceptado con observaciones | Documento aceptado con observaciones |
| Rechazado | Documento rechazado por SUNAT |
| Pendiente de envío | Documento pendiente de envío |

- Indicador de CDR (Constancia de Recepción).

#### c) Trazabilidad

- Fecha y hora de envío a NubeFact.
- Usuario que realizó el envío.
- Indicador de si fue enviado al cliente.
- Fecha de envío al cliente (si aplica).

#### d) Información de NubeFact

- **Enlaces de descarga**:
  - PDF
  - XML
- Código Hash del documento.
- Respuesta de validación (mensaje SUNAT/NubeFact).

#### e) Funciones por Fila

| Función | Condición |
|---------|-----------|
| Editar documento | Habilitado solo si está observado o rechazado |
| Reenviar documento | Validar datos antes de enviar |
| Anular documento | - |
| Alertar / Notificar incidencia | - |
| Consulta de estado actualizado | - |
| Imprimir PDF | - |

**Requisitos de las acciones**:
- Registrar auditoría (usuario, fecha, acción).
- Mostrar confirmación antes de ejecutar.
- Devolver resultado de la operación.

---

## 5. Arquitectura Tecnológica

| Componente | Tecnología |
|------------|------------|
| Backend | fastapi |
| Frontend | React + Vite |
| Contenedorización | Docker |
| Comunicación | API REST (JSON) |
| Base de datos | SQL Server |

---

## 7. Accesos y Credenciales

- Credenciales de NubeFact:
ruta: https://api.nubefact.com/api/v1/1215c9d4-7765-4ac0-b9ea-268a1ee1b6d1
token: 84b1e3cffb89488aab19c0853bc393e23f0f9ff355ef4c44a361a5a702ebedc1

---

## 8. Criterios de Aceptación

- [ ] Permita enviar correctamente los 3 tipos de documentos.
- [ ] Muestre estados en tiempo real.
- [ ] Permita corregir y reenviar documentos.
- [ ] Mantenga integridad con la base de datos

---

## 9. Consideraciones Técnicas

### 9.1 Procesamiento de Guías de Remisión

```
SUNAT responde después de 3 segundos
    |
    v
Implementar sleep/wait para esperar respuesta
    |
    v
Usar asincronismo para envío múltiple de documentos
```

### 9.2 Restricciones de Edición

- **Regla**: Una vez enviado el documento a SUNAT, no se puede corregir.
- **Excepción**: Documentos observados o rechazados pueden ser editados y reenviados.

---

## 10. Modelo de Estados

```
Pendiente de envío
        |
        v
Enviado a NubeFact
        |
        v
+----------------+----------------+
|                |                |
v                v                v
Aceptado    Aceptado con     Rechazado
por SUNAT   observaciones         |
                |                v
                v         Permitir corrección
         Permitir corrección    y reenvío
         y reenvío
```
