FROM python:3.11-slim

# Instalar dependencias del sistema para pyodbc y el driver de SQL Server
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unixodbc-dev \
    g++ \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY . .

# Dar permisos de ejecución al script de entrada
RUN chmod +x docker-entrypoint.sh

# Exponer el puerto
EXPOSE 8000

# Usar el script de entrada
ENTRYPOINT ["./docker-entrypoint.sh"]
