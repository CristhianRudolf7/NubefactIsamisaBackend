#!/usr/bin/env python
"""
Script para verificar el estado de los documentos de venta, guías y retenciones en la base de datos.
Permite identificar discrepancias entre el estado de envío en el sistema (nube_status_web)
y las respuestas de facturación electrónica.
"""
import os
import sys
from sqlalchemy import create_engine, text

# Agregar el directorio raíz del backend al path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, ".env"))
except ImportError:
    pass

from app.config import get_settings

def verificar_ventas(conn):
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE ESTADO DE VENTAS (AR_Document)")
    print("=" * 80)
    
    # 1. Resumen de estados en AR_Document
    print("\n1. Resumen de campos de estado en AR_Document:")
    print("-" * 58)
    res_estados = conn.execute(text("""
        SELECT 
            ISNULL(nube_status_web, 'NULL') as nube_status_web, 
            ISNULL(fe, 'NULL') as fe, 
            COUNT(*) as cantidad
        FROM AR_Document
        GROUP BY nube_status_web, fe
        ORDER BY cantidad DESC
    """)).fetchall()
    
    print(f"{'nube_status_web':<20} | {'fe':<20} | {'Cantidad':<10}")
    print("-" * 58)
    for row in res_estados:
        print(f"{str(row[0]):<20} | {str(row[1]):<20} | {row[2]:<10}")
    
    # 2. Resumen de respuestas registradas en ar_fe_nube
    print("\n2. Resumen de respuestas en ar_fe_nube:")
    print("-" * 38)
    res_nube = conn.execute(text("""
        SELECT 
            ISNULL(aceptada_por_sunat, 'NULL') as aceptada,
            COUNT(*) as cantidad
        FROM ar_fe_nube
        GROUP BY aceptada_por_sunat
        ORDER BY cantidad DESC
    """)).fetchall()
    
    print(f"{'aceptada_por_sunat':<25} | {'Cantidad':<10}")
    print("-" * 38)
    for row in res_nube:
        print(f"{str(row[0]):<25} | {row[1]:<10}")

    # 3. Discrepancias
    print("\n3. Discrepancias (Pendientes en Web, pero Enviadas/Aceptadas en BD/NubeFact):")
    print("-" * 80)
    discrepancias = conn.execute(text("""
        SELECT COUNT(*)
        FROM AR_Document d
        LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
        WHERE d.nube_status_web = 'pendiente' 
          AND (d.fe = 'enviado' OR n.aceptada_por_sunat = 'true' OR n.id IS NOT NULL)
    """)).scalar()
    print(f"Total de documentos de venta con discrepancia: {discrepancias}")


def verificar_guias(conn):
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE ESTADO DE GUÍAS (WH_Transaction)")
    print("=" * 80)
    
    # 1. Resumen de estados en WH_Transaction
    print("\n1. Resumen de campos de estado en WH_Transaction:")
    print("-" * 58)
    res_estados = conn.execute(text("""
        SELECT 
            ISNULL(nube_status_web, 'NULL') as nube_status_web, 
            ISNULL(envio_nube, 'NULL') as envio_nube, 
            COUNT(*) as cantidad
        FROM WH_Transaction
        GROUP BY nube_status_web, envio_nube
        ORDER BY cantidad DESC
    """)).fetchall()
    
    print(f"{'nube_status_web':<20} | {'envio_nube':<20} | {'Cantidad':<10}")
    print("-" * 58)
    for row in res_estados:
        print(f"{str(row[0]):<20} | {str(row[1]):<20} | {row[2]:<10}")
    
    # 2. Resumen de respuestas registradas en wh_transaction_nube
    print("\n2. Resumen de respuestas en wh_transaction_nube:")
    print("-" * 38)
    res_nube = conn.execute(text("""
        SELECT 
            ISNULL(aceptada_por_sunat, 'NULL') as aceptada,
            COUNT(*) as cantidad
        FROM wh_transaction_nube
        GROUP BY aceptada_por_sunat
        ORDER BY cantidad DESC
    """)).fetchall()
    
    print(f"{'aceptada_por_sunat':<25} | {'Cantidad':<10}")
    print("-" * 38)
    for row in res_nube:
        print(f"{str(row[0]):<25} | {row[1]:<10}")

    # 3. Discrepancias
    print("\n3. Discrepancias (Pendientes en Web, pero Enviadas/Aceptadas en BD/NubeFact):")
    print("-" * 80)
    discrepancias = conn.execute(text("""
        SELECT COUNT(*)
        FROM WH_Transaction g
        LEFT JOIN wh_transaction_nube n ON n.TransactionId = g.[Transaction]
        WHERE g.nube_status_web = 'pendiente' 
          AND (g.envio_nube = 'enviado' OR g.envio_nube = 'aceptada' OR n.aceptada_por_sunat = 'true' OR n.id IS NOT NULL)
    """)).scalar()
    print(f"Total de guías con discrepancia: {discrepancias}")


def verificar_retenciones(conn):
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE ESTADO DE RETENCIONES (AP_Retencion)")
    print("=" * 80)
    
    # 1. Resumen de estados en AP_Retencion
    print("\n1. Resumen de campos de estado en AP_Retencion:")
    print("-" * 58)
    res_estados = conn.execute(text("""
        SELECT 
            ISNULL(nube_status_web, 'NULL') as nube_status_web, 
            ISNULL(status, 'NULL') as status, 
            COUNT(*) as cantidad
        FROM AP_Retencion
        GROUP BY nube_status_web, status
        ORDER BY cantidad DESC
    """)).fetchall()
    
    print(f"{'nube_status_web':<20} | {'status':<20} | {'Cantidad':<10}")
    print("-" * 58)
    for row in res_estados:
        print(f"{str(row[0]):<20} | {str(row[1]):<20} | {row[2]:<10}")
    
    # 2. Resumen de respuestas registradas en AP_Retencion_Status
    print("\n2. Resumen de respuestas en AP_Retencion_Status:")
    print("-" * 38)
    res_nube = conn.execute(text("""
        SELECT 
            ISNULL(Status, 'NULL') as aceptada,
            COUNT(*) as cantidad
        FROM AP_Retencion_Status
        GROUP BY Status
        ORDER BY cantidad DESC
    """)).fetchall()
    
    print(f"{'Status (sunat)':<25} | {'Cantidad':<10}")
    print("-" * 38)
    for row in res_nube:
        print(f"{str(row[0]):<25} | {row[1]:<10}")

    # 3. Discrepancias
    print("\n3. Discrepancias (Pendientes en Web, pero Enviadas/Aceptadas en BD/NubeFact):")
    print("-" * 80)
    discrepancias = conn.execute(text("""
        SELECT COUNT(*)
        FROM AP_Retencion r
        LEFT JOIN AP_Retencion_Status s ON s.Retencion = r.Id
        WHERE r.nube_status_web = 'pendiente' 
          AND (r.status = 'enviado' OR r.status = 'aceptada' OR s.Status = 'aceptada' OR s.Id IS NOT NULL)
    """)).scalar()
    print(f"Total de retenciones con discrepancia: {discrepancias}")


def main():
    settings = get_settings()
    db_url = settings.database_url
    
    print("=" * 80)
    print("VERIFICACIÓN GENERAL DE ESTADOS EN PRODUCCIÓN")
    print("=" * 80)
    print(f"Base de datos: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print("-" * 80)
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            verificar_ventas(conn)
            verificar_guias(conn)
            verificar_retenciones(conn)
            
    except Exception as e:
        print(f"❌ Error al conectar o consultar la base de datos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
