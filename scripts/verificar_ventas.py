#!/usr/bin/env python
"""
Script de verificación optimizado para evitar búsquedas lentas en tablas grandes.
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

    # 3. Discrepancias optimizadas (evitando full scans con OR cruzados)
    print("\n3. Discrepancias (Pendientes en Web, pero Enviadas/Aceptadas en BD/NubeFact):")
    print("-" * 80)
    
    # Consulta rápida: Cuenta discrepancias usando UNION para optimizar
    discrepancias = conn.execute(text("""
        SELECT COUNT(DISTINCT Document) FROM (
            -- Caso 1: fe = 'enviado'
            SELECT Document FROM AR_Document 
            WHERE nube_status_web = 'pendiente' AND fe = 'enviado'
            
            UNION ALL
            
            -- Caso 2: Tiene registro en ar_fe_nube
            SELECT d.Document 
            FROM ar_fe_nube n
            INNER JOIN AR_Document d ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
            WHERE d.nube_status_web = 'pendiente'
        ) t
    """)).scalar()
    print(f"Total de documentos de venta con discrepancia: {discrepancias}")
    
    if discrepancias > 0:
        print("\nMuestra de las discrepancias en Ventas:")
        print("-" * 110)
        muestras = conn.execute(text("""
            SELECT TOP 10 Document, DocumentSerie, DocumentNo, fe_val, status_web, aceptada, nube_id FROM (
                SELECT 
                    d.Document, 
                    d.DocumentSerie, 
                    d.DocumentNo, 
                    d.fe as fe_val, 
                    d.nube_status_web as status_web,
                    NULL as aceptada,
                    NULL as nube_id,
                    d.DocumentDate
                FROM AR_Document d 
                WHERE d.nube_status_web = 'pendiente' AND d.fe = 'enviado'
                
                UNION ALL
                
                SELECT 
                    d.Document, 
                    d.DocumentSerie, 
                    d.DocumentNo, 
                    d.fe as fe_val, 
                    d.nube_status_web as status_web,
                    n.aceptada_por_sunat as aceptada,
                    n.id as nube_id,
                    d.DocumentDate
                FROM ar_fe_nube n
                INNER JOIN AR_Document d ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
                WHERE d.nube_status_web = 'pendiente'
            ) combined
            ORDER BY DocumentDate DESC
        """)).fetchall()
        
        print(f"{'Documento ID':<25} | {'Serie-Nro':<15} | {'fe (Hist)':<12} | {'nube_status':<12} | {'Acept. SUNAT':<12} | {'ar_fe_nube ID':<10}")
        print("-" * 110)
        for row in muestras:
            doc_id, serie, numero, fe_hist, status_web, aceptada, nube_id = row
            print(f"{str(doc_id):<25} | {str(serie)}-{str(numero):<10} | {str(fe_hist):<12} | {str(status_web):<12} | {str(aceptada):<12} | {str(nube_id):<10}")


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
        # Reemplazar saltos de línea para que imprima en una sola línea compacta
        envio_nube_clean = str(row[1]).replace('\r', '').replace('\n', ' ').strip()
        if len(envio_nube_clean) > 30:
            envio_nube_clean = envio_nube_clean[:27] + "..."
        print(f"{str(row[0]):<20} | {envio_nube_clean:<20} | {row[2]:<10}")
    
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

    # 3. Discrepancias optimizadas (evitando full scans con OR cruzados)
    print("\n3. Discrepancias (Pendientes en Web, pero Enviadas/Aceptadas en BD/NubeFact):")
    print("-" * 80)
    
    discrepancias = conn.execute(text("""
        SELECT COUNT(DISTINCT [Transaction]) FROM (
            SELECT [Transaction] FROM WH_Transaction 
            WHERE nube_status_web = 'pendiente' 
              AND LTRIM(RTRIM(envio_nube)) IN ('enviado', 'aceptada')
            
            UNION ALL
            
            SELECT g.[Transaction]
            FROM wh_transaction_nube n
            INNER JOIN WH_Transaction g ON n.TransactionId = g.[Transaction]
            WHERE g.nube_status_web = 'pendiente'
        ) t
    """)).scalar()
    print(f"Total de guías con discrepancia: {discrepancias}")
    
    if discrepancias > 0:
        print("\nMuestra de las discrepancias en Guías:")
        print("-" * 110)
        guias = conn.execute(text("""
            SELECT TOP 10 [Transaction], DocumentSerie, DocumentNo, envio_nube_val, status_web, aceptada FROM (
                SELECT 
                    g.[Transaction],
                    g.DocumentSerie,
                    g.DocumentNo,
                    g.envio_nube as envio_nube_val,
                    g.nube_status_web as status_web,
                    NULL as aceptada,
                    g.FechaTraslado
                FROM WH_Transaction g
                WHERE g.nube_status_web = 'pendiente' 
                  AND LTRIM(RTRIM(g.envio_nube)) IN ('enviado', 'aceptada')
                
                UNION ALL
                
                SELECT 
                    g.[Transaction],
                    g.DocumentSerie,
                    g.DocumentNo,
                    g.envio_nube as envio_nube_val,
                    g.nube_status_web as status_web,
                    n.aceptada_por_sunat as aceptada,
                    g.FechaTraslado
                FROM wh_transaction_nube n
                INNER JOIN WH_Transaction g ON n.TransactionId = g.[Transaction]
                WHERE g.nube_status_web = 'pendiente'
            ) combined
            ORDER BY [Transaction] DESC
        """)).fetchall()
        
        print(f"{'Trans. ID':<15} | {'Serie-Nro':<15} | {'envio_nube (Hist)':<30} | {'nube_status':<12} | {'Acept. SUNAT':<12}")
        print("-" * 110)
        for row in guias:
            trans_id, serie, numero, envio_nube, status_web, aceptada = row
            envio_nube_clean = str(envio_nube).replace('\r', '').replace('\n', ' ').strip()
            if len(envio_nube_clean) > 28:
                envio_nube_clean = envio_nube_clean[:25] + "..."
            print(f"{str(trans_id):<15} | {str(serie)}-{str(numero):<10} | {envio_nube_clean:<30} | {str(status_web):<12} | {str(aceptada):<12}")


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
        SELECT COUNT(DISTINCT Id) FROM (
            SELECT Id FROM AP_Retencion 
            WHERE nube_status_web = 'pendiente' 
              AND status IN ('enviado', 'aceptada', 'enviada', 'aceptado')
            
            UNION ALL
            
            SELECT r.Id
            FROM AP_Retencion_Status s
            INNER JOIN AP_Retencion r ON s.Retencion = r.Id
            WHERE r.nube_status_web = 'pendiente'
        ) t
    """)).scalar()
    print(f"Total de retenciones con discrepancia: {discrepancias}")
    
    if discrepancias > 0:
        print("\nMuestra de las discrepancias en Retenciones:")
        print("-" * 110)
        retenciones = conn.execute(text("""
            SELECT TOP 10 Id, Serie, Numero, status_val, status_web, sunat_status FROM (
                SELECT 
                    r.Id,
                    r.Serie,
                    r.Numero,
                    r.status as status_val,
                    r.nube_status_web as status_web,
                    NULL as sunat_status
                FROM AP_Retencion r
                WHERE r.nube_status_web = 'pendiente' 
                  AND r.status IN ('enviado', 'aceptada', 'enviada', 'aceptado')
                
                UNION ALL
                
                SELECT 
                    r.Id,
                    r.Serie,
                    r.Numero,
                    r.status as status_val,
                    r.nube_status_web as status_web,
                    s.Status as sunat_status
                FROM AP_Retencion_Status s
                INNER JOIN AP_Retencion r ON s.Retencion = r.Id
                WHERE r.nube_status_web = 'pendiente'
            ) combined
            ORDER BY Id DESC
        """)).fetchall()
        
        print(f"{'Retención ID':<15} | {'Serie-Nro':<15} | {'status (Hist)':<15} | {'nube_status':<12} | {'Status SUNAT':<15}")
        print("-" * 110)
        for row in retenciones:
            ret_id, serie, numero, status_hist, status_web, sunat_status = row
            print(f"{str(ret_id):<15} | {str(serie)}-{str(numero):<10} | {str(status_hist):<15} | {str(status_web):<12} | {str(sunat_status):<15}")

def main():
    settings = get_settings()
    db_url = settings.database_url
    
    print("=" * 80)
    print("VERIFICACIÓN GENERAL DE ESTADOS EN PRODUCCIÓN (OPTIMIZADA)")
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
