#!/usr/bin/env python
import os
import sys
import traceback
from sqlalchemy import create_engine, text, or_
from fastapi.testclient import TestClient

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

def main():
    print("=" * 80)
    print("DIAGNÓSTICO DEL TICKET T037-11662 Y DE LA API")
    print("=" * 80)
    
    # 1. Búsqueda en la Base de Datos
    print("\n1. BUSCANDO EN BASE DE DATOS...")
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    target_serie = 'T037'
    target_no = '11662'
    
    with engine.connect() as conn:
        # A. Buscar en AR_Document (Ventas)
        try:
            res_venta = conn.execute(text("""
                SELECT Document, DocumentSerie, DocumentNo, DocumentType, nube_status_web, fe 
                FROM AR_Document 
                WHERE (DocumentSerie = :serie AND DocumentNo = :numero) 
                   OR Document = :id
            """), {"serie": target_serie, "numero": target_no, "id": f"{target_serie}-{target_no}"}).fetchall()
            
            print(f"\nResultados en AR_Document (Ventas) [{len(res_venta)} encontrados]:")
            for row in res_venta:
                print(f"  - Document: {row[0]}")
                print(f"  - DocumentSerie: {row[1]}")
                print(f"  - DocumentNo: {row[2]}")
                print(f"  - DocumentType: {row[3]}")
                print(f"  - nube_status_web: {row[4]}")
                print(f"  - fe (Histórico): {row[5]}")
        except Exception as e:
            print(f"  ❌ Error al buscar en AR_Document: {e}")
            
        # B. Buscar en WH_Transaction (Guías)
        try:
            res_guia = conn.execute(text("""
                SELECT [Transaction], DocumentSerie, DocumentNo, Type, nube_status_web, envio_nube 
                FROM WH_Transaction 
                WHERE (DocumentSerie = :serie AND DocumentNo = :numero)
                   OR [Transaction] = :id
            """), {"serie": target_serie, "numero": target_no, "id": f"{target_serie}-{target_no}"}).fetchall()
            
            print(f"\nResultados en WH_Transaction (Guías) [{len(res_guia)} encontrados]:")
            for row in res_guia:
                print(f"  - Transaction: {row[0]}")
                print(f"  - DocumentSerie: {row[1]}")
                print(f"  - DocumentNo: {row[2]}")
                print(f"  - Type: {row[3]}")
                print(f"  - nube_status_web: {row[4]}")
                print(f"  - envio_nube: {row[5]}")
        except Exception as e:
            print(f"  ❌ Error al buscar en WH_Transaction: {e}")
            
        # C. Buscar en AP_Retencion (Retenciones)
        try:
            res_ret = conn.execute(text("""
                SELECT id, serie, numero, nube_status_web, estado 
                FROM AP_Retencion 
                WHERE (serie = :serie AND numero = :numero)
                   OR id = :id
            """), {"serie": target_serie, "numero": target_no, "id": f"{target_serie}-{target_no}"}).fetchall()
            
            print(f"\nResultados en AP_Retencion (Retenciones) [{len(res_ret)} encontrados]:")
            for row in res_ret:
                print(f"  - ID: {row[0]}")
                print(f"  - Serie: {row[1]}")
                print(f"  - Numero: {row[2]}")
                print(f"  - nube_status_web: {row[3]}")
                print(f"  - estado: {row[4]}")
        except Exception as e:
            print(f"  ❌ Error al buscar en AP_Retencion: {e}")

    # 2. Diagnóstico de la API
    print("\n" + "=" * 80)
    print("2. DIAGNÓSTICO DE LA API (TEST CLIENT)")
    print("=" * 80)
    
    client = TestClient(app)
    from app.routers import auth
    from app.models.user import User, UserRole
    mock_user = User(dni="12345678", nombre="Test User", rol=UserRole.ADMIN, puede_acceder_ventas=True, is_active=True)
    
    app.dependency_overrides[auth.require_ventas_access] = lambda: mock_user
    app.dependency_overrides[auth.require_authenticated] = lambda: mock_user
    app.dependency_overrides[auth.require_admin] = lambda: mock_user
    
    # Probando con trailing slash
    url_with_slash = "/api/ventas/?page=1&page_size=5"
    print(f"\nProbando GET {url_with_slash}...")
    try:
        response = client.get(url_with_slash)
        print(f"  - Status Code: {response.status_code}")
        print(f"  - Headers: {response.headers}")
        print(f"  - Body: {response.text[:500]}")
    except Exception as e:
        print("  ❌ Exception raised during GET request:")
        traceback.print_exc()
        
    # Probando sin trailing slash
    url_no_slash = "/api/ventas?page=1&page_size=5"
    print(f"\nProbando GET {url_no_slash}...")
    try:
        response = client.get(url_no_slash)
        print(f"  - Status Code: {response.status_code}")
        print(f"  - Body: {response.text[:500]}")
    except Exception as e:
        print("  ❌ Exception raised during GET request:")
        traceback.print_exc()

    # Probando health check
    print(f"\nProbando GET /health...")
    try:
        response = client.get("/health")
        print(f"  - Status Code: {response.status_code}")
        print(f"  - Body: {response.text}")
    except Exception as e:
        print("  ❌ Exception raised during GET /health request:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
