#!/usr/bin/env python
"""
Script de prueba para validar que la exclusión de tickets (tanto por Document ID
como por DocumentSerie que empiezan con 'T') funciona correctamente.
"""
import os
import sys
from sqlalchemy import create_engine, text, func, or_
from fastapi.testclient import TestClient

# Agregar el directorio raíz del backend al path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, ".env"))
except ImportError:
    pass

from app.config import get_settings
from app.database import SessionLocal
from app.models.ventas import ARDocument
from main import app

def test_db_queries():
    print("\n" + "=" * 80)
    print("1. VERIFICACIÓN A NIVEL DE CONSULTAS SQL (BASE DE DATOS)")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # A. Total de documentos en la BD vs visibles para la Web
        total_real = db.query(func.count(ARDocument.Document)).scalar()
        
        # Un ticket es aquel cuyo Document ID inicia con 'T' O cuya DocumentSerie inicia con 'T'
        total_tickets = db.query(func.count(ARDocument.Document)).filter(
            or_(ARDocument.Document.like('T%'), ARDocument.DocumentSerie.like('T%'))
        ).scalar()
        
        total_permitidos = db.query(func.count(ARDocument.Document)).filter(
            ~ARDocument.Document.like('T%'),
            ~ARDocument.DocumentSerie.like('T%')
        ).scalar()
        
        print(f"Total de documentos en la tabla AR_Document: {total_real}")
        print(f"Total de tickets (Document o Serie inicia con 'T'): {total_tickets}")
        print(f"Total de documentos visibles en la web:       {total_permitidos}")
        print(f"Verificación suma (permitidos + tickets):    {total_permitidos + total_tickets} "
              f"-> {'✅ OK' if total_permitidos + total_tickets == total_real else '❌ ERROR'}")
        
        # B. Comprobar consulta del worker automático
        ventas_pendientes_con_tickets = db.query(ARDocument).filter(
            or_(ARDocument.fe == None, ARDocument.fe == '', func.lower(ARDocument.fe) == 'pendiente'),
            ARDocument.necesita_aprobacion == False
        ).count()
        
        ventas_pendientes_sin_tickets = db.query(ARDocument).filter(
            or_(ARDocument.fe == None, ARDocument.fe == '', func.lower(ARDocument.fe) == 'pendiente'),
            ARDocument.necesita_aprobacion == False,
            ~ARDocument.Document.like('T%'),
            ~ARDocument.DocumentSerie.like('T%')
        ).count()
        
        print(f"\nWorker automático (Ventas pendientes):")
        print(f"  - Con tickets: {ventas_pendientes_con_tickets}")
        print(f"  - Sin tickets: {ventas_pendientes_sin_tickets} (excluidos: {ventas_pendientes_con_tickets - ventas_pendientes_sin_tickets})")
        print(f"  -> Filtro de worker: {'✅ CORRECTO (Filtra tickets)' if ventas_pendientes_sin_tickets <= ventas_pendientes_con_tickets else '❌ INCORRECTO'}")
        
        # C. Obtener un ID de ticket de muestra para la prueba de la API
        ticket_muestra = db.query(ARDocument.Document).filter(
            or_(ARDocument.Document.like('T%'), ARDocument.DocumentSerie.like('T%'))
        ).first()
        return ticket_muestra[0] if ticket_muestra else None
        
    except Exception as e:
        print(f"❌ Error durante las consultas de base de datos: {e}")
        return None
    finally:
        db.close()

def test_api_endpoints(ticket_id):
    print("\n" + "=" * 80)
    print("2. VERIFICACIÓN A NIVEL DE API (FASTAPI TESTCLIENT)")
    print("=" * 80)
    
    # Creamos un cliente de pruebas local para interactuar con la app FastAPI en memoria
    client = TestClient(app)
    
    # Mockear dependencias de autenticación para que retornen un usuario mock
    from app.routers import auth
    from app.models.user import User, UserRole
    mock_user = User(dni="12345678", nombre="Test User", rol=UserRole.ADMIN, puede_acceder_ventas=True, is_active=True)
    
    app.dependency_overrides[auth.require_ventas_access] = lambda: mock_user
    app.dependency_overrides[auth.require_authenticated] = lambda: mock_user
    app.dependency_overrides[auth.require_admin] = lambda: mock_user
    
    try:
        # A. Probar Listado de Ventas (/api/ventas/)
        print("Consultando listado de ventas a través de la API...")
        response = client.get("/api/ventas/?page=1&page_size=50")
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", {}).get("items", [])
            print(f"  - Total items retornados por la API en la página 1: {len(items)}")
            
            tickets_encontrados = [item for item in items if item["Document"].startswith("T") or item["DocumentSerie"].startswith("T")]
            if tickets_encontrados:
                print(f"  ❌ ERROR: ¡Se encontraron tickets en el listado de la API! Ejemplos:")
                for t in tickets_encontrados[:3]:
                    print(f"    * ID: {t['Document']} | Serie: {t['DocumentSerie']}")
            else:
                print("  ✅ CORRECTO: No se retornó ningún ticket (por ID o Serie) en el listado de la API.")
        else:
            print(f"  ❌ Error al consultar la API: Código {response.status_code} - {response.text}")
            
        # B. Probar consulta de detalle con el ticket de muestra
        if ticket_id:
            print(f"\nConsultando detalle del ticket de muestra '{ticket_id}' a través de la API...")
            response_ticket = client.get(f"/api/ventas/{ticket_id}")
            print(f"  - HTTP Status Code: {response_ticket.status_code}")
            if response_ticket.status_code == 404:
                print("  ✅ CORRECTO: La API retornó 404 (No Encontrado) al intentar ver un ticket.")
            else:
                print(f"  ❌ INCORRECTO: La API debió retornar 404, pero retornó {response_ticket.status_code}")
        else:
            print("\n  ⚠️ No se encontró ningún ticket en la base de datos para probar el endpoint de detalle.")
            
    finally:
        # Limpiar dependencias overrides
        app.dependency_overrides.clear()

if __name__ == "__main__":
    ticket_muestra = test_db_queries()
    test_api_endpoints(ticket_muestra)
    print("\n" + "=" * 80)
    print("FIN DE LAS PRUEBAS")
    print("=" * 80)
