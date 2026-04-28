"""
Script para crear un usuario administrador inicial.
Uso: python create_admin.py
"""
import sys
from getpass import getpass

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.services.auth_service import hash_password


def create_admin():
    """Crea un usuario administrador"""
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    try:
        print("=== Crear Usuario Administrador ===\n")
        
        # Solicitar datos
        dni = input("DNI (8 dígitos): ").strip()
        if len(dni) != 8 or not dni.isdigit():
            print("Error: El DNI debe tener 8 dígitos numéricos")
            return
        
        # Verificar si ya existe
        existing = db.query(User).filter(User.dni == dni).first()
        if existing:
            print(f"Error: Ya existe un usuario con DNI {dni}")
            return
        
        nombre = input("Nombre completo: ").strip()
        if not nombre:
            print("Error: El nombre es requerido")
            return
        
        password = getpass("Contraseña (mínimo 6 caracteres): ")
        if len(password) < 6:
            print("Error: La contraseña debe tener al menos 6 caracteres")
            return
        
        password_confirm = getpass("Confirmar contraseña: ")
        if password != password_confirm:
            print("Error: Las contraseñas no coinciden")
            return
        
        # Crear usuario
        user = User(
            dni=dni,
            nombre=nombre,
            password_hash=hash_password(password),
            rol=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"\n¡Usuario administrador creado exitosamente!")
        print(f"  ID: {user.id}")
        print(f"  DNI: {user.dni}")
        print(f"  Nombre: {user.nombre}")
        print(f"  Rol: {user.rol.value}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
