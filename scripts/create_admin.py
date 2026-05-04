"""
Script para crear un usuario administrador inicial.
Uso: python create_admin.py
"""
import os
import sys
from getpass import getpass

# Agregar el directorio raíz del proyecto al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.services.auth_service import hash_password


def create_admin(dni=None, nombre=None, password=None, celular="000000000"):
    """Crea un usuario administrador"""
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    try:
        # Si no se pasan argumentos, intentar obtener de variables de entorno
        dni = dni or os.getenv("ADMIN_DNI")
        password = password or os.getenv("ADMIN_PASSWORD")
        nombre = nombre or os.getenv("ADMIN_NOMBRE", "Administrador Inicial")

        # Si aún no hay datos, entrar en modo interactivo
        if not dni or not password:
            print("=== Crear Usuario Administrador (Modo Interactivo) ===\n")
            dni = input("DNI (8 dígitos): ").strip()
            nombre = input("Nombre completo: ").strip()
            password = input("Contraseña (mínimo 6 caracteres): ")
            password_confirm = input("Confirmar contraseña: ")
            if password != password_confirm:
                print("Error: Las contraseñas no coinciden")
                return
        
        if len(dni) != 8 or not dni.isdigit():
            print(f"Error: El DNI '{dni}' debe tener 8 dígitos numéricos")
            return
        
        if len(password) < 6:
            print("Error: La contraseña debe tener al menos 6 caracteres")
            return

        # Verificar si ya existe
        existing = db.query(User).filter(User.dni == dni).first()
        if existing:
            print(f"Información: Ya existe un usuario con DNI {dni}. Saltando creación.")
            return
        
        # Crear usuario
        user = User(
            dni=dni,
            nombre=nombre,
            celular=celular,
            password_hash=hash_password(password),
            rol=UserRole.ADMIN,
            is_active=True,
            puede_acceder_ventas=True,
            puede_acceder_guias=True,
            puede_acceder_retenciones=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"\n¡Usuario administrador '{user.nombre}' creado exitosamente!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
