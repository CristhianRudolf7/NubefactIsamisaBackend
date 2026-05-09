# Documentación Técnica - Isamisa NubeFact

Este documento detalla el stack tecnológico utilizado en el proyecto y la estructura de las APIs del backend.

## 1. Stack Tecnológico

El proyecto está dividido en dos repositorios independientes que se comunican mediante una API REST.

### Backend
- **Lenguaje**: Python 3.11+
- **Framework Web**: [FastAPI](https://fastapi.tiangolo.com/) (Asíncrono, alto rendimiento).
- **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) con `pyodbc`.
- **Base de Datos**: Microsoft SQL Server.
- **Validación de Datos**: [Pydantic 2.0](https://docs.pydantic.dev/).
- **Seguridad**:
  - Autenticación mediante **JWT** (JSON Web Tokens).
  - Encriptación de contraseñas con **Bcrypt**.
- **Tareas en Segundo Plano**: [APScheduler](https://apscheduler.readthedocs.io/) para el procesamiento automático de documentos.
- **Cliente HTTP**: `httpx` y `aiohttp` para integración con la API de NubeFact.
- **Despliegue**: Docker y Docker Compose.

### Frontend
- **Framework**: [React 19](https://react.dev/) (Vite).
- **Lenguaje**: TypeScript (Tipado estático).
- **Estilos**: [Tailwind CSS 4](https://tailwindcss.com/) para diseño responsivo.
- **Componentes UI**: [Ant Design (antd)](https://ant.design/) para una interfaz profesional y [Lucide React](https://lucide.dev/) para iconos.
- **Gestión de Estado y Datos**: 
  - [TanStack React Query v5](https://tanstack.com/query/latest) para fetching y caché.
  - [Axios](https://axios-http.com/) como cliente HTTP.
- **Gráficos**: [Recharts](https://recharts.org/) para el dashboard estadístico.
- **Manejo de Fechas**: [Day.js](https://day.js.org/).

---

## 2. Estructura de APIs (Backend)

Todos los endpoints tienen el prefijo base `/api`. A continuación se detallan los módulos principales:

### Autenticación (`/auth`)
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| POST | `/login` | Inicia sesión y devuelve token JWT. |
| POST | `/logout` | Invalida la sesión actual. |
| GET | `/me` | Obtiene los datos del usuario autenticado. |

### Documentos de Venta (`/ventas`)
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| GET | `/` | Lista documentos con filtros (serie, número, estado, ruc). |
| GET | `/{id}` | Obtiene el detalle completo de un documento. |
| POST | `/{id}/enviar` | Envía un documento individual a NubeFact. |
| POST | `/bulk-enviar` | Envía múltiples documentos en segundo plano. |
| PUT | `/{id}` | Actualiza datos del documento (edición técnica). |
| POST | `/{id}/aprobar` | Aprueba cambios realizados por un trabajador. |
| POST | `/{id}/anular` | Genera una comunicación de baja/anulación en SUNAT. |
| GET | `/{id}/pdf` | Descarga o redirige al PDF oficial del documento. |

### Guías de Remisión (`/guias`)
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| GET | `/` | Lista guías de remisión con filtros de búsqueda. |
| POST | `/{id}/enviar` | Sincroniza la guía con NubeFact/SUNAT. |
| POST | `/{id}/aprobar` | Valida cambios en peso o transportista. |
| GET | `/{id}/xml` | Descarga el XML firmado por SUNAT. |

### Comprobantes de Retención (`/retenciones`)
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| GET | `/` | Listado de retenciones aplicadas. |
| POST | `/{id}/enviar` | Procesa la retención ante SUNAT. |

### Dashboard y Estadísticas (`/dashboard`)
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| GET | `/stats` | Resumen de totales, errores y documentos pendientes. |
| GET | `/charts` | Datos formateados para gráficos de líneas y barras. |

### Usuarios y Permisos (`/users`)
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| GET | `/` | Lista todos los usuarios del sistema. |
| POST | `/` | Crea un nuevo usuario (Admin). |
| PATCH | `/{id}/permisos` | Gestiona accesos granulares por módulo. |

### Auditoría y Configuración (`/auditoria`, `/config`)
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| GET | `/auditoria` | Historial de cambios, envíos y anulaciones. |
| GET | `/config` | Consulta modo de envío (Manual/Automático). |
| PATCH | `/config` | Cambia el comportamiento del worker de envío. |

---

## 3. Estructura de Carpetas (Backend)

La lógica del servidor está organizada siguiendo un patrón de arquitectura limpia. A continuación se detallan los módulos dentro del directorio `app/`:

### Models (`app/models/`)
Define la estructura de la base de datos utilizando SQLAlchemy.
- `ventas.py`: Mapeo de `AR_Document` y `AR_DocumentDetail`.
- `guias.py`: Mapeo de `WH_Transaction` y `WH_TransactionDetail`.
- `retenciones.py`: Mapeo de `AP_Retencion` y sus estados.
- `user.py`: Modelo de usuario y roles.
- `nube_response.py`: Almacena respuestas de la API de NubeFact para ventas.
- `guia_response.py`: Almacena respuestas de NubeFact para guías.

### Routers (`app/routers/`)
Contiene los controladores que definen los endpoints de la API.
- `ventas.py`, `guias.py`, `retenciones.py`: Gestión de documentos.
- `auth.py`: Lógica de inicio de sesión y validación de tokens.
- `dashboard.py`: Endpoints para métricas y gráficos.
- `users.py`: Administración de usuarios y permisos.

### Schemas (`app/schemas/`)
Modelos de Pydantic para validación y tipado de datos.
- `ventas.py`, `guias.py`, `retenciones.py`: Estructuras de datos para solicitudes y respuestas.
- `nubefact.py`: Esquemas específicos para la integración con la API externa.
- `common.py`: Respuestas base y estructuras compartidas.

### Services (`app/services/`)
Contiene la lógica de negocio pura y servicios externos.
- `document_service.py`: Procesamiento principal de documentos y estados.
- `nubefact_client.py`: Cliente especializado para la comunicación con NubeFact.
- `notification_service.py`: Lógica para disparar alertas y avisos.
- `whatsapp_service.py`: Integración con el API de mensajería de WhatsApp.
- `auditoria_service.py`: Registro automático de acciones en la tabla de auditoría.

### Utils y Core (`app/utils/`, `app/`)
- `utils/datetime.py`: Helpers para conversión de formatos de fecha (Excel vs ISO).
- `database.py`: Gestión del `engine` y `SessionLocal` para SQL Server.
- `worker.py`: Implementación del planificador de tareas (Cron) para envíos masivos.
- `main.py`: Inicialización de FastAPI, configuración de CORS y montaje de rutas.

---

## 4. Estructura de Carpetas (Frontend)

El frontend sigue un flujo modular basado en componentes de React y servicios de TypeScript. A continuación se detallan los archivos clave:

### Pages (`src/pages/`)
Componentes que representan las vistas y rutas principales de la aplicación.
- **Ventas (`/Ventas`)**:
  - `VentasList.tsx`: Tabla principal con filtros y acciones masivas.
  - `VentasDetail.tsx`: Visualización de cabecera y detalle de factura/boleta.
  - `VentasEdit.tsx`: Formulario para corregir documentos rechazados o con errores.
- **Guías (`/Guias`)**:
  - `GuiasList.tsx`, `GuiasDetail.tsx`, `GuiasEdit.tsx`: Gestión de Guías de Remisión.
- **Retenciones (`/Retenciones`)**:
  - `RetencionesList.tsx`, `RetencionesDetail.tsx`, `RetencionesEdit.tsx`: Gestión de comprobantes de retención.
- **Dashboard**:
  - `Dashboard.tsx`: Dashboard interactivo con estadísticas de envío y gráficos de Recharts.
- **Administración**:
  - `Login.tsx`: Pantalla de acceso al sistema.
  - `Users/UsersList.tsx`: Gestión de cuentas de usuario y permisos granulares.

### Services (`src/services/`)
Abstracción de la comunicación con el backend (Axios + React Query).
- `api.ts`: Instancia central de Axios, manejo de errores y adjunto de tokens Bearer.
- `ventasService.ts`: Peticiones para listar, enviar, anular y descargar documentos de venta.
- `guiasService.ts`: Servicios para la gestión de guías y sincronización con SUNAT.
- `retencionesService.ts`: Servicios para el módulo de retenciones.
- `authService.ts`: Lógica de autenticación (Login/Logout/Profile).
- `dashboardService.ts`: Consulta de KPIs y datos para gráficos.
- `auditoriaService.ts`: Consulta del registro histórico de acciones.

### Components (`src/components/`)
Elementos de interfaz reutilizables.
- **Layout (`/layout`)**:
  - `MainLayout.tsx`: Contenedor principal que envuelve las páginas protegidas.
  - `Sidebar.tsx`: Menú de navegación lateral con colapsado.
  - `Header.tsx`: Barra superior con perfil de usuario y notificaciones rápidas.
- **Comunes (`/common`)**:
  - `DataTable.tsx`: Componente de tabla genérica con soporte para paginación y selección.
  - `FilterPanel.tsx`: Panel expandible para los filtros de búsqueda.
  - `StatusBadge.tsx`: Visualizador de estados de SUNAT con colores dinámicos.
  - `ChangesModal.tsx`: Visualizador de diferencias (antes/después) para auditoría.
  - `ColumnSelector.tsx`: Herramienta para personalizar las columnas visibles en las tablas.

### Core y Contextos (`src/`)
- **`contexts/`**:
  - `AuthContext.tsx`: Gestión del estado de sesión y verificación de tokens.
  - `AppContext.tsx`: Configuración global de la aplicación y temas.
- **`hooks/`**: Custom hooks para manejo de estados de carga, formularios y navegación.
- **`utils/`**: Funciones para formateo de moneda peruana (PEN), manejo de fechas con Day.js y normalización de textos.
- `App.tsx`: Configuración central de rutas mediante `react-router-dom`.
- `main.tsx`: Punto de entrada que renderiza la aplicación y los proveedores de `QueryClient`.
