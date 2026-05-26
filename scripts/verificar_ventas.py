#!/usr/bin/env python
"""
Script de diagnóstico detallado para investigar las discrepancias y el formato de datos
en las tablas de ventas, guías y retenciones.
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

def diagnosticar_ventas(conn):
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO DETALLADO: VENTAS (AR_Document)")
    print("=" * 80)
    
    # Ver los 923 registros con discrepancia
    print("\nMuestra de las discrepancias en Ventas (d.nube_status_web = 'pendiente' pero con envío):")
    print("-" * 110)
    discrepancias = conn.execute(text("""
        SELECT TOP 10
            d.Document, 
            d.DocumentSerie, 
            d.DocumentNo, 
            d.DocumentDate, 
            d.fe, 
            d.nube_status_web,
            n.aceptada_por_sunat,
            n.id as nube_id
        FROM AR_Document d
        LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
        WHERE d.nube_status_web = 'pendiente' 
          AND (d.fe = 'enviado' OR n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1' OR n.id IS NOT NULL)
        ORDER BY d.DocumentDate DESC
    """)).fetchall()
    
    print(f"{'Documento ID':<25} | {'Serie-Nro':<15} | {'fe (Hist)':<12} | {'nube_status':<12} | {'Acept. SUNAT':<12} | {'ar_fe_nube ID':<10}")
    print("-" * 110)
    for row in discrepancias:
        doc_id, serie, numero, fecha, fe_hist, status_web, aceptada, nube_id = row
        print(f"{str(doc_id):<25} | {str(serie)}-{str(numero):<10} | {str(fe_hist):<12} | {str(status_web):<12} | {str(aceptada):<12} | {str(nube_id):<10}")

def diagnosticar_guias(conn):
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO DETALLADO: GUÍAS (WH_Transaction)")
    print("=" * 80)
    
    # 1. Mostrar discrepancias usando LTRIM/RTRIM/LIKE para tolerar saltos de línea
    print("\nBuscando discrepancias en Guías con filtros limpios (tolerando saltos de línea/espacios):")
    print("-" * 80)
    
    res = conn.execute(text("""
        SELECT COUNT(*)
        FROM WH_Transaction g
        LEFT JOIN wh_transaction_nube n ON n.TransactionId = g.[Transaction]
        WHERE g.nube_status_web = 'pendiente' 
          AND (
            LTRIM(RTRIM(g.envio_nube)) = 'enviado' 
            OR LTRIM(RTRIM(g.envio_nube)) = 'aceptada' 
            OR n.aceptada_por_sunat = 'true' 
            OR n.id IS NOT NULL
          )
    """)).scalar()
    print(f"Total de guías con discrepancia encontradas con filtros limpios: {res}")
    
    if res > 0:
        print("\nMuestra de las discrepancias en Guías:")
        print("-" * 110)
        guias = conn.execute(text("""
            SELECT TOP 10
                g.[Transaction],
                g.DocumentSerie,
                g.DocumentNo,
                g.envio_nube,
                g.nube_status_web,
                n.aceptada_por_sunat,
                n.id as nube_id
            FROM WH_Transaction g
            LEFT JOIN wh_transaction_nube n ON n.TransactionId = g.[Transaction]
            WHERE g.nube_status_web = 'pendiente' 
              AND (
                LTRIM(RTRIM(g.envio_nube)) = 'enviado' 
                OR LTRIM(RTRIM(g.envio_nube)) = 'aceptada' 
                OR n.aceptada_por_sunat = 'true' 
                OR n.id IS NOT NULL
              )
            ORDER BY g.[Transaction] DESC
        """)).fetchall()
        
        print(f"{'Trans. ID':<15} | {'Serie-Nro':<15} | {'envio_nube (Hist)':<30} | {'nube_status':<12} | {'Acept. SUNAT':<12}")
        print("-" * 110)
        for row in guias:
            trans_id, serie, numero, envio_nube, status_web, aceptada, _ = row
            # Limpiar saltos de línea para mostrar en una sola línea
            envio_nube_clean = str(envio_nube).replace('\r', '').replace('\n', ' ').strip()
            if len(envio_nube_clean) > 28:
                envio_nube_clean = envio_nube_clean[:25] + "..."
            print(f"{str(trans_id):<15} | {str(serie)}-{str(numero):<10} | {envio_nube_clean:<30} | {str(status_web):<12} | {str(aceptada):<12}")

def diagnosticar_retenciones(conn):
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO DETALLADO: RETENCIONES (AP_Retencion)")
    print("=" * 80)
    
    # Mostrar las discrepancias en Retenciones
    print("\nMuestra de las discrepancias en Retenciones (r.nube_status_web = 'pendiente' pero con envío):")
    print("-" * 110)
    retenciones = conn.execute(text("""
        SELECT TOP 10
            r.Id,
            r.Serie,
            r.Numero,
            r.status,
            r.nube_status_web,
            s.Status as sunat_status,
            s.Id as status_record_id
        FROM AP_Retencion r
        LEFT JOIN AP_Retencion_Status s ON s.Retencion = r.Id
        WHERE r.nube_status_web = 'pendiente'
          AND (r.status = 'enviado' OR r.status = 'aceptada' OR s.Status = 'aceptada' OR s.Id IS NOT NULL)
        ORDER BY r.Id DESC
    """)).fetchall()
    
    print(f"{'Retención ID':<15} | {'Serie-Nro':<15} | {'status (Hist)':<15} | {'nube_status':<12} | {'Status SUNAT':<15}")
    print("-" * 110)
    for row in retenciones:
        ret_id, serie, numero, status_hist, status_web, sunat_status, _ = row
        print(f"{str(ret_id):<15} | {str(serie)}-{str(numero):<10} | {str(status_hist):<15} | {str(status_web):<12} | {str(sunat_status):<15}")

def main():
    settings = get_settings()
    db_url = settings.database_url
    
    print("=" * 80)
    print("DIAGNÓSTICO PROFUNDO DE DISCREPANCIAS EN PRODUCCIÓN")
    print("=" * 80)
    print(f"Base de datos: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print("-" * 80)
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            diagnosticar_ventas(conn)
            diagnosticar_guias(conn)
            diagnosticar_retenciones(conn)
            
    except Exception as e:
        print(f"❌ Error al conectar o consultar la base de datos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
