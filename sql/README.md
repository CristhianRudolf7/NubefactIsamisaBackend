# SQL Server Docker Setup

Configuración de SQL Server 2022 en Docker para desarrollo con Python.

## Requisitos previos

- Docker y Docker Compose instalados
- ODBC Driver 18 for SQL Server (se instala automáticamente en el contenedor)

## Inicio rápido

```bash
# 1. Iniciar SQL Server
sudo docker compose up -d

# 2. Verificar estado
sudo docker ps | grep sqlserver

# 3. Ver logs (esperar a "SQL Server is ready")
sudo docker logs sqlserver_isamisa -f
```

## Credenciales por defecto

| Parámetro | Valor |
|-----------|-------|
| Host | `localhost` |
| Puerto | `1433` |
| Usuario | `sa` |
| Contraseña | `YourStrong@Passw0rd` |
| Base de datos | `isamisa_db` |

> La contraseña debe tener mínimo 8 caracteres, mayúsculas, minúsculas, números y símbolos.

## Comandos útiles

| Acción | Comando |
|--------|---------|
| Iniciar | `sudo docker compose up -d` |
| Detener | `sudo docker compose down` |
| Ver estado | `sudo docker ps -a` |
| Ver logs | `sudo docker logs sqlserver_isamisa` |
| Reiniciar | `sudo docker compose restart` |
| Eliminar todo | `sudo docker compose down -v` |

---

## Conexión desde Python

### Opción 1: pyodbc (conexión directa)

```python
import pyodbc

conn_str = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=localhost,1433;'
    'DATABASE=isamisa_db;'
    'UID=sa;'
    'PWD=YourStrong@Passw0rd;'
    'TrustServerCertificate=yes;'
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Ejecutar consulta
cursor.execute('SELECT * FROM documentos')
for row in cursor:
    print(row)

conn.close()
```

### Opción 2: SQLAlchemy (ORM)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# URL de conexión (codificar contraseña si tiene caracteres especiales)
from urllib.parse import quote_plus
password = quote_plus('YourStrong@Passw0rd')

DATABASE_URL = f"mssql+pyodbc://sa:{password}@localhost,1433/isamisa_db?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# Usar sesión
db = SessionLocal()
# ... operaciones ORM ...
db.close()
```

### Opción 3: Con variables de entorno

Crear archivo `.env` en `backend/`:

```env
DB_HOST=localhost
DB_PORT=1433
DB_NAME=isamisa_db
DB_USER=sa
DB_PASSWORD=YourStrong@Passw0rd
DB_DRIVER=ODBC Driver 18 for SQL Server
```

```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from urllib.parse import quote_plus

load_dotenv()

PASSWORD_ENCODED = quote_plus(os.getenv('DB_PASSWORD'))
DATABASE_URL = f"mssql+pyodbc://{os.getenv('DB_USER')}:{PASSWORD_ENCODED}@{os.getenv('DB_HOST')},{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?driver={os.getenv('DB_DRIVER').replace(' ', '+')}&TrustServerCertificate=yes"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
```

---

## Scripts útiles del backend

```bash
cd backend

# Crear base de datos si no existe
./venv/bin/python create_db.py

# Crear tablas desde modelos SQLAlchemy
./venv/bin/python create_tables.py

# Inicializar con datos de prueba
./venv/bin/python init_db.py
```

---

## Solución de problemas

### Error: Login timeout expired

El contenedor tarda ~30 segundos en estar listo. Espera y reintenta:

```bash
# Verificar que SQL Server está listo
sudo docker logs sqlserver_isamisa 2>&1 | grep "SQL Server is ready"
```

### Error: Contraseña con caracteres especiales

Si la contraseña tiene `@`, `#`, etc., codificarla para URL:

```python
from urllib.parse import quote_plus
password = quote_plus('YourStrong@Passw0rd')  # -> YourStrong%40Passw0rd
```

### Error: Driver no encontrado

En Linux, instalar el driver ODBC 18:

```bash
# Debian 12 (bookworm)
curl https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
curl https://packages.microsoft.com/config/debian/12/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql18 unixodbc-dev

# Ubuntu
curl https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql18 unixodbc-dev
```

### Reiniciar base de datos desde cero

```python
import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=localhost,1433;DATABASE=master;'
    'UID=sa;PWD=YourStrong@Passw0rd;'
    'TrustServerCertificate=yes;',
    autocommit=True
)
cursor = conn.cursor()
cursor.execute("ALTER DATABASE isamisa_db SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
cursor.execute("DROP DATABASE isamisa_db")
cursor.execute("CREATE DATABASE isamisa_db")
conn.close()
```
