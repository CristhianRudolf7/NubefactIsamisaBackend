
import sys
import os

# Añadir el directorio raíz al path para importar el app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine

def migrate():
    print("Iniciando migración de base de datos...")
    
    commands = [
        # Ventas
        "ALTER TABLE AR_Document ADD necesita_aprobacion BIT DEFAULT 0",
        "ALTER TABLE AR_Document ADD aprobacion_usuario VARCHAR(50)",
        
        # Guías
        "ALTER TABLE WH_Transaction ADD necesita_aprobacion BIT DEFAULT 0",
        "ALTER TABLE WH_Transaction ADD aprobacion_usuario VARCHAR(50)",
        
        # Retenciones
        "ALTER TABLE AP_Retencion ADD necesita_aprobacion BIT DEFAULT 0",
        "ALTER TABLE AP_Retencion ADD aprobacion_usuario VARCHAR(50)"
    ]
    
    with engine.connect() as conn:
        for cmd in commands:
            try:
                print(f"Ejecutando: {cmd}")
                conn.execute(text(cmd))
                conn.commit()
                print("OK")
            except Exception as e:
                if "already" in str(e).lower() or "exist" in str(e).lower():
                    print(f"Aviso: La columna ya existe o hubo un problema menor: {e}")
                else:
                    print(f"ERROR al ejecutar {cmd}: {e}")
    
    print("Migración finalizada.")

if __name__ == "__main__":
    migrate()
