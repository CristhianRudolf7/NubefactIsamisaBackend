# Backend - Isamisa NubeFact Integration

Este repositorio contiene el backend para la integración entre el ERP de Isamisa y la API de NubeFact. Gestiona la facturación electrónica, guías de remisión y retenciones.

> [!IMPORTANT]
> Este proyecto está dividido en dos repositorios independientes:
> - **Backend**: API construida con FastAPI (Este repo).
> - **Frontend**: Interfaz de usuario construida con React/Vite.

## Requisitos Previos

- Python 3.11+
- SQL Server (con acceso para el usuario configurado)
- Docker y Docker Compose (opcional para despliegue)

## Instalación y Configuración

### 1. Variables de Entorno
Cree un archivo `.env` en la raíz del backend. A continuación se detallan todas las variables necesarias para el funcionamiento del sistema:

| Variable | Descripción | Ejemplo / Valor |
| :--- | :--- | :--- |
| **Base de Datos** | | |
| `DATABASE_URL` | Cadena de conexión SQL Server (SQLAlchemy + pyodbc). | `mssql+pyodbc://user:pass@host:1433/db?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes` |
| **NubeFact (API)** | | |
| `NUBEFACT_URL_VENTAS` | Endpoint de la API de NubeFact para Facturas y Boletas. | `https://api.nubefact.com/api/v1/TU_ID_COMERCIAL` |
| `NUBEFACT_TOKEN_VENTAS` | Token de seguridad para el módulo de Ventas. | `84b1e3cffb89488aab19c...` |
| `NUBEFACT_URL_GUIAS` | Endpoint de la API de NubeFact para Guías de Remisión. | `https://api.nubefact.com/api/v1/TU_ID_COMERCIAL` |
| `NUBEFACT_TOKEN_GUIAS` | Token de seguridad para el módulo de Guías. | `84b1e3cffb89488aab19c...` |
| `NUBEFACT_URL_RETENCIONES` | Endpoint de la API de NubeFact para Retenciones. | `https://api.nubefact.com/api/v1/TU_ID_COMERCIAL` |
| `NUBEFACT_TOKEN_RETENCIONES` | Token de seguridad para el módulo de Retenciones. | `2575c21c7f054518af91e...` |
| **Configuración App** | | |
| `APP_NAME` | Nombre descriptivo de la aplicación (usado en metadatos). | `Sistema de Gestión de Documentos Electrónicos` |
| `APP_VERSION` | Versión actual del backend. | `1.0.0` |
| `DEBUG` | Modo depuración. Muestra errores detallados si es `True`. | `True` (Desarrollo) / `False` (Producción) |
| **Seguridad (JWT)** | | |
| `SECRET_KEY` | Clave secreta para firmar tokens de sesión. **CAMBIAR EN PRODUCCIÓN**. | `tu_clave_secreta_muy_segura_2024` |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| Tiempo de expiración del token de acceso inicial. | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Tiempo de vida de la sesión antes de pedir login (en días). | `1` o `7` |
| **Integraciones** | | |
| `PORTAL_URL` | URL base del frontend para generar enlaces en notificaciones. | `http://localhost:5173` |
| `WHATSAPP_API_URL` | URL del servicio externo de notificaciones de WhatsApp. | `https://servidor.com/sy_whats.php` |

### 2. Sincronización de Base de Datos
Antes de iniciar, es necesario sincronizar la base de datos de producción ejecutando el script SQL que se encuentra al final de este archivo.

### 3. Ejecución Local (Desarrollo)
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 4. Ejecución con Docker (Producción)
```bash
# Construir y levantar todo con docker-compose (desde la raíz del proyecto)
docker-compose up --build -d
```

## Auditoría de Tablas (ERP vs Implementation)

| Tabla | Estado | Cambios / Observaciones |
| :--- | :--- | :--- |
| `AR_Document` | **Editada** | Se añadieron: `fe`, `error_mensaje`, `necesita_aprobacion`, `aprobacion_usuario`. |
| `AR_FE_Nube` | **Editada** | Respuestas NubeFact. Se añadieron enlaces PDF/XML/CDR y metadatos de envío. |
| `AP_Retencion` | **Editada** | Se añadieron: `status`, `necesita_aprobacion`, `aprobacion_usuario`. |
| `WH_Transaction` | **Editada** | Se añadieron: `envio_nube`, `necesita_aprobacion`, `aprobacion_usuario`. |

## Tablas Nuevas (Exclusivas de la Web)

- **`wh_transaction_nube`**: Respuestas de NubeFact para Guías.
- **`users`**: Gestión de usuarios y roles.
- **`sy_configuracion_envio`**: Configuración de modos Manual/Automático.
- **`auditoria`**: Historial detallado de cambios y reversiones.

## Script de Sincronización para Producción (SQL Server)

Ejecute el siguiente script en la base de datos de producción:

```sql
-- 1. ACTUALIZACIÓN DE TABLAS ERP EXISTENTES
ALTER TABLE AR_Document ADD fe NVARCHAR(20) NULL;
ALTER TABLE AR_Document ADD error_mensaje NVARCHAR(MAX) NULL;
ALTER TABLE AR_Document ADD necesita_aprobacion BIT DEFAULT 0;
ALTER TABLE AR_Document ADD aprobacion_usuario NVARCHAR(50) NULL;

ALTER TABLE AP_Retencion ADD status NVARCHAR(20) NULL;
ALTER TABLE AP_Retencion ADD necesita_aprobacion BIT DEFAULT 0;
ALTER TABLE AP_Retencion ADD aprobacion_usuario NVARCHAR(50) NULL;

ALTER TABLE WH_Transaction ADD envio_nube NVARCHAR(20) NULL;
ALTER TABLE WH_Transaction ADD necesita_aprobacion BIT DEFAULT 0;
ALTER TABLE WH_Transaction ADD aprobacion_usuario NVARCHAR(50) NULL;

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ar_fe_nube') AND name = 'web')
    ALTER TABLE ar_fe_nube ADD web NVARCHAR(10) DEFAULT 'N';

ALTER TABLE ar_fe_nube ADD enlace_del_pdf NVARCHAR(500) NULL;
ALTER TABLE ar_fe_nube ADD enlace_del_xml NVARCHAR(500) NULL;
ALTER TABLE ar_fe_nube ADD enlace_del_cdr NVARCHAR(500) NULL;
ALTER TABLE ar_fe_nube ADD fecha_envio FLOAT NULL;
ALTER TABLE ar_fe_nube ADD usuario_envio NVARCHAR(50) NULL;

-- 2. CREACIÓN DE TABLAS NUEVAS
IF OBJECT_ID('users', 'U') IS NULL
CREATE TABLE users (
    id INT PRIMARY KEY IDENTITY(1,1),
    dni NVARCHAR(8) UNIQUE NOT NULL,
    nombre NVARCHAR(100) NOT NULL,
    celular NVARCHAR(9) NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    rol NVARCHAR(20) DEFAULT 'trabajador' NOT NULL,
    is_active BIT DEFAULT 1 NOT NULL,
    recibir_notificaciones BIT DEFAULT 1 NOT NULL,
    puede_acceder_ventas BIT DEFAULT 0 NOT NULL,
    puede_acceder_guias BIT DEFAULT 0 NOT NULL,
    puede_acceder_retenciones BIT DEFAULT 0 NOT NULL,
    created_at DATETIME DEFAULT GETDATE() NOT NULL,
    updated_at DATETIME DEFAULT GETDATE() NOT NULL
);

IF OBJECT_ID('auditoria', 'U') IS NULL
CREATE TABLE auditoria (
    id INT PRIMARY KEY IDENTITY(1,1),
    tabla NVARCHAR(100) NOT NULL,
    registro_id NVARCHAR(100) NOT NULL,
    accion NVARCHAR(50) NOT NULL,
    datos_anteriores NVARCHAR(MAX),
    datos_nuevos NVARCHAR(MAX),
    usuario NVARCHAR(100),
    fecha DATETIME DEFAULT GETDATE() NOT NULL,
    ip NVARCHAR(50)
);

IF OBJECT_ID('sy_configuracion_envio', 'U') IS NULL
CREATE TABLE sy_configuracion_envio (
    id INT PRIMARY KEY IDENTITY(1,1),
    tipo_documento NVARCHAR(50) UNIQUE NOT NULL,
    modo NVARCHAR(20) DEFAULT 'manual',
    activo BIT DEFAULT 0,
    intervalo_segundos INT DEFAULT 60
);

IF OBJECT_ID('wh_transaction_nube', 'U') IS NULL
CREATE TABLE wh_transaction_nube (
    id INT PRIMARY KEY IDENTITY(1,1),
    TransactionId NVARCHAR(50) NOT NULL,
    serie NVARCHAR(10),
    numero NVARCHAR(20),
    enlace NVARCHAR(500),
    enlace_del_pdf NVARCHAR(500),
    enlace_del_xml NVARCHAR(500),
    enlace_del_cdr NVARCHAR(500),
    aceptada_por_sunat NVARCHAR(20),
    sunat_description NVARCHAR(MAX),
    sunat_note NVARCHAR(MAX),
    sunat_responsecode NVARCHAR(50),
    sunat_soap_error NVARCHAR(MAX),
    pdf_zip_base64 NVARCHAR(MAX),
    xml_zip_base64 NVARCHAR(MAX),
    cdr_zip_base64 NVARCHAR(MAX),
    codigo_hash_qr NVARCHAR(200),
    codigo_hash NVARCHAR(200),
    error NVARCHAR(MAX),
    fecha_envio FLOAT,
    usuario_envio NVARCHAR(50)
);
```
