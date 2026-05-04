
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.config import ConfiguracionEnvio

def test_db():
    print("Conectando a la DB...")
    db = SessionLocal()
    try:
        print("Buscando configuración de guías...")
        config = db.query(ConfiguracionEnvio).filter(ConfiguracionEnvio.tipo_documento == 'guias').first()
        if config:
            print(f"Configuración encontrada. Modo actual: {config.modo}")
            print("Intentando cambiar a automático...")
            config.modo = 'automatico'
            db.commit()
            print("¡Commit exitoso!")
        else:
            print("No se encontró la configuración de guías.")
    except Exception as e:
        print(f"Error durante la prueba: {e}")
    finally:
        db.close()
        print("Sesión cerrada.")

if __name__ == "__main__":
    test_db()
