#!/usr/bin/env python
"""
Script para verificar el estado de los documentos de venta en la base de datos.
Permite identificar discrepancias entre el estado de envío en el sistema (nube_status_web)
y las respuestas registradas en ar_fe_nube o el campo histórico 'fe'.
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

def main():
    settings = get_settings()
    db_url = settings.database_url
    
    print("=" * 80)
    print("VERIFICACIÓN DE ESTADO DE VENTAS EN PRODUCCIÓN")
    print("=" * 80)
    print(f"Base de datos: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print("-" * 80)
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
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

            # 3. Identificar documentos con discrepancia crítica:
            # nube_status_web = 'pendiente' pero fe = 'enviado' o existe en ar_fe_nube
            print("\n3. Buscando discrepancias (Pendientes en Web, pero Enviadas/Aceptadas en BD/NubeFact):")
            print("-" * 80)
            
            discrepancias = conn.execute(text("""
                SELECT 
                    d.Document, 
                    d.DocumentSerie, 
                    d.DocumentNo, 
                    d.DocumentDate, 
                    d.fe, 
                    d.nube_status_web,
                    n.aceptada_por_sunat,
                    n.enlace
                FROM AR_Document d
                LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
                WHERE d.nube_status_web = 'pendiente' 
                  AND (d.fe = 'enviado' OR n.aceptada_por_sunat = 'true' OR n.id IS NOT NULL)
                ORDER BY d.DocumentDate DESC
            """)).fetchall()
            
            total_discrepancias = len(discrepancias)
            print(f"Total de documentos con discrepancia: {total_discrepancias}")
            
            if total_discrepancias > 0:
                print("\nÚltimos 20 documentos con discrepancia:")
                print("-" * 110)
                print(f"{'Documento ID':<25} | {'Serie-Nro':<15} | {'Fecha':<12} | {'fe (Hist)':<10} | {'nube_status':<12} | {'SUNAT Acept.':<12}")
                print("-" * 110)
                for row in discrepancias[:20]:
                    doc_id, serie, numero, fecha, fe_hist, status_web, aceptada, _ = row
                    fecha_str = fecha.strftime("%Y-%m-%d") if fecha else "N/A"
                    print(f"{str(doc_id):<25} | {str(serie)}-{str(numero):<10} | {fecha_str:<12} | {str(fe_hist):<10} | {str(status_web):<12} | {str(aceptada):<12}")
                
                print("\n[RECOMENDACIÓN]")
                print("Para solucionar estas discrepancias, se podría ejecutar un script de sincronización")
                print("que actualice 'nube_status_web' a 'aceptado' o 'enviado' para aquellos documentos")
                print("que ya cuenten con respuesta positiva en la tabla 'ar_fe_nube'.")
            else:
                print("\nNo se encontraron discrepancias de tipo 'pendiente' con registros de envío.")
                
    except Exception as e:
        print(f"❌ Error al conectar o consultar la base de datos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
