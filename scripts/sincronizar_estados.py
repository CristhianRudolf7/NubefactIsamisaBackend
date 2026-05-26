#!/usr/bin/env python
"""
Script para sincronizar y corregir la columna 'nube_status_web' en AR_Document,
resolviendo las discrepancias donde figura como 'pendiente' pero ya fue enviado o aceptado.
La única columna modificada es 'nube_status_web'.
"""
import os
import sys
import argparse
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
    parser = argparse.ArgumentParser(description="Sincroniza la columna nube_status_web con los estados de envío reales.")
    parser.add_argument("--commit", action="store_true", help="Aplica y confirma los cambios en la base de datos.")
    args = parser.parse_args()

    settings = get_settings()
    db_url = settings.database_url
    
    print("=" * 80)
    print("SINCRONIZACIÓN DE ESTADOS (NUBE_STATUS_WEB) EN PRODUCCIÓN")
    print("=" * 80)
    print(f"Base de datos: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print(f"Modo: {'EJECUCIÓN REAL (COMMIT)' if args.commit else 'SIMULACIÓN (DRY RUN)'}")
    print("-" * 80)
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Comenzar una transacción explícita
            trans = conn.begin()
            
            # 1. Contar cuántos registros se verían afectados por cada estado
            # Caso A: Cambiar a 'aceptado' porque existe en ar_fe_nube con aceptada_por_sunat = 'true' o fe es correcto/aceptado
            cnt_aceptado = conn.execute(text("""
                SELECT COUNT(*) 
                FROM AR_Document d
                LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
                WHERE d.nube_status_web = 'pendiente'
                  AND (n.aceptada_por_sunat = 'true' OR LOWER(d.fe) LIKE '%aceptad%' OR LOWER(d.fe) = 'correcto')
            """)).scalar()

            # Caso B: Cambiar a 'enviado' porque fe = 'enviado' o hay respuesta en ar_fe_nube (pero no es 'true' todavía o no está aceptado)
            cnt_enviado = conn.execute(text("""
                SELECT COUNT(*) 
                FROM AR_Document d
                LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
                WHERE d.nube_status_web = 'pendiente'
                  AND (d.fe = 'enviado' OR n.id IS NOT NULL)
                  AND NOT (n.aceptada_por_sunat = 'true' OR LOWER(d.fe) LIKE '%aceptad%' OR LOWER(d.fe) = 'correcto')
            """)).scalar()

            # Caso C: Cambiar a 'error' porque fe tiene error
            cnt_error = conn.execute(text("""
                SELECT COUNT(*) 
                FROM AR_Document d
                WHERE d.nube_status_web = 'pendiente'
                  AND (LOWER(d.fe) LIKE '%error%' OR LEN(d.fe) > 20)
            """)).scalar()

            total_a_modificar = cnt_aceptado + cnt_enviado + cnt_error

            print(f"Resumen de registros a actualizar (con nube_status_web = 'pendiente'):")
            print(f"  - Cambiarán a 'aceptado': {cnt_aceptado}")
            print(f"  - Cambiarán a 'enviado':  {cnt_enviado}")
            print(f"  - Cambiarán a 'error':    {cnt_error}")
            print(f"  Total registros a modificar: {total_a_modificar}")
            print("-" * 80)

            if total_a_modificar == 0:
                print("No se encontraron registros que requieran sincronización.")
                trans.rollback()
                return

            if args.commit:
                print("Aplicando actualizaciones...")
                
                # Ejecutar actualización para 'aceptado'
                res_act_aceptado = conn.execute(text("""
                    UPDATE d
                    SET d.nube_status_web = 'aceptado'
                    FROM AR_Document d
                    LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
                    WHERE d.nube_status_web = 'pendiente'
                      AND (n.aceptada_por_sunat = 'true' OR LOWER(d.fe) LIKE '%aceptad%' OR LOWER(d.fe) = 'correcto')
                """))
                print(f"  -> {res_act_aceptado.rowcount} registros actualizados a 'aceptado'")

                # Ejecutar actualización para 'enviado'
                res_act_enviado = conn.execute(text("""
                    UPDATE d
                    SET d.nube_status_web = 'enviado'
                    FROM AR_Document d
                    LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
                    WHERE d.nube_status_web = 'pendiente'
                      AND (d.fe = 'enviado' OR n.id IS NOT NULL)
                      AND NOT (n.aceptada_por_sunat = 'true' OR LOWER(d.fe) LIKE '%aceptad%' OR LOWER(d.fe) = 'correcto')
                """))
                print(f"  -> {res_act_enviado.rowcount} registros actualizados a 'enviado'")

                # Ejecutar actualización para 'error'
                res_act_error = conn.execute(text("""
                    UPDATE AR_Document
                    SET nube_status_web = 'error'
                    WHERE nube_status_web = 'pendiente'
                      AND (LOWER(fe) LIKE '%error%' OR LEN(fe) > 20)
                """))
                print(f"  -> {res_act_error.rowcount} registros actualizados a 'error'")

                trans.commit()
                print("\n✅ ¡Sincronización completada y guardada exitosamente!")
            else:
                print("SIMULACIÓN COMPLETADA.")
                print("Para aplicar los cambios físicamente en la base de datos, ejecuta el script con el parámetro --commit:")
                print("python scripts/sincronizar_estados.py --commit")
                trans.rollback()
                
    except Exception as e:
        print(f"❌ Error durante la sincronización: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
