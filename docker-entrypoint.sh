#!/bin/bash
set -e

# Intentar crear el usuario administrador inicial
echo "Configurando usuario administrador inicial..."
python scripts/create_admin.py

# Iniciar la aplicación
echo "Iniciando servidor FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
