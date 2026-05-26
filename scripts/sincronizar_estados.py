#!/usr/bin/env python
"""
Script para sincronizar y corregir la columna 'nube_status_web' en:
- AR_Document (Ventas)
- WH_Transaction (Guías)
- AP_Retencion (Retenciones)

Optimizado para ejecutarse al instante en bases de datos de producción con millones de registros.
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

def sincronizar_ventas(conn, commit):
    print("\n" + "=" * 80)
    print("SINCRONIZACIÓN DE VENTAS (AR_Document)")
    print("=" * 80)
    
    # 1. Contar/actualizar aceptados
    # Caso A1: Por campo 'fe' en la cabecera (sin joins, instantáneo)
    cnt_aceptado_fe = conn.execute(text("""
        SELECT COUNT(*) FROM AR_Document 
        WHERE nube_status_web IN ('pendiente', 'enviado')
          AND (LOWER(fe) LIKE '%aceptad%' OR LOWER(fe) = 'correcto')
    """)).scalar()

    # Caso A2: Por respuestas en ar_fe_nube (join rápido partiendo de n)
    cnt_aceptado_nube = conn.execute(text("""
        SELECT COUNT(*) 
        FROM ar_fe_nube n
        INNER JOIN AR_Document d ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
        WHERE d.nube_status_web IN ('pendiente', 'enviado')
          AND (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1')
          AND NOT (LOWER(d.fe) LIKE '%aceptad%' OR LOWER(d.fe) = 'correcto')
    """)).scalar()

    # 2. Contar/actualizar enviados
    # Caso B1: Por campo 'fe' = 'enviado' (sin joins)
    cnt_enviado_fe = conn.execute(text("""
        SELECT COUNT(*) FROM AR_Document 
        WHERE nube_status_web = 'pendiente' AND fe = 'enviado'
    """)).scalar()

    # Caso B2: Por existencia en ar_fe_nube pero no aceptado (join rápido partiendo de n)
    cnt_enviado_nube = conn.execute(text("""
        SELECT COUNT(*) 
        FROM ar_fe_nube n
        INNER JOIN AR_Document d ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
        WHERE d.nube_status_web = 'pendiente'
          AND NOT (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1')
          AND d.fe <> 'enviado'
    """)).scalar()

    # 3. Contar/actualizar errores
    cnt_error = conn.execute(text("""
        SELECT COUNT(*) FROM AR_Document 
        WHERE nube_status_web = 'pendiente'
          AND (LOWER(fe) LIKE '%error%' OR LEN(fe) > 20)
    """)).scalar()

    total = cnt_aceptado_fe + cnt_aceptado_nube + cnt_enviado_fe + cnt_enviado_nube + cnt_error
    print(f"Registros a actualizar en Ventas:")
    print(f"  - A 'aceptado' (por histórico): {cnt_aceptado_fe}")
    print(f"  - A 'aceptado' (por NubeFact):  {cnt_aceptado_nube}")
    print(f"  - A 'enviado'  (por histórico): {cnt_enviado_fe}")
    print(f"  - A 'enviado'  (por NubeFact):  {cnt_enviado_nube}")
    print(f"  - A 'error':                    {cnt_error}")
    print(f"  Total a modificar en Ventas:    {total}")
    
    if total > 0 and commit:
        print("Aplicando actualizaciones de Ventas...")
        
        # Updates para Aceptados
        r1 = conn.execute(text("""
            UPDATE AR_Document
            SET nube_status_web = 'aceptado'
            WHERE nube_status_web IN ('pendiente', 'enviado')
              AND (LOWER(fe) LIKE '%aceptad%' OR LOWER(fe) = 'correcto')
        """))
        print(f"  -> {r1.rowcount} registros actualizados a 'aceptado' por histórico")

        r2 = conn.execute(text("""
            UPDATE d
            SET d.nube_status_web = 'aceptado'
            FROM ar_fe_nube n
            INNER JOIN AR_Document d ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
            WHERE d.nube_status_web IN ('pendiente', 'enviado')
              AND (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1')
        """))
        print(f"  -> {r2.rowcount} registros actualizados a 'aceptado' por NubeFact")

        # Updates para Enviados
        r3 = conn.execute(text("""
            UPDATE AR_Document
            SET nube_status_web = 'enviado'
            WHERE nube_status_web = 'pendiente' AND fe = 'enviado'
        """))
        print(f"  -> {r3.rowcount} registros actualizados a 'enviado' por histórico")

        r4 = conn.execute(text("""
            UPDATE d
            SET d.nube_status_web = 'enviado'
            FROM ar_fe_nube n
            INNER JOIN AR_Document d ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
            WHERE d.nube_status_web = 'pendiente'
        """))
        print(f"  -> {r4.rowcount} registros actualizados a 'enviado' por NubeFact")

        # Updates para Errores
        r5 = conn.execute(text("""
            UPDATE AR_Document
            SET nube_status_web = 'error'
            WHERE nube_status_web = 'pendiente'
              AND (LOWER(fe) LIKE '%error%' OR LEN(fe) > 20)
        """))
        print(f"  -> {r5.rowcount} registros actualizados a 'error'")


def sincronizar_guias(conn, commit):
    print("\n" + "=" * 80)
    print("SINCRONIZACIÓN DE GUÍAS (WH_Transaction)")
    print("=" * 80)
    
    # 1. Contar/actualizar aceptados
    cnt_aceptado_fe = conn.execute(text("""
        SELECT COUNT(*) FROM WH_Transaction 
        WHERE nube_status_web IN ('pendiente', 'enviado')
          AND LTRIM(RTRIM(envio_nube)) = 'aceptada'
    """)).scalar()

    cnt_aceptado_nube = conn.execute(text("""
        SELECT COUNT(*) 
        FROM wh_transaction_nube n
        INNER JOIN WH_Transaction g ON n.TransactionId = g.[Transaction]
        WHERE g.nube_status_web IN ('pendiente', 'enviado')
          AND (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1')
          AND NOT LTRIM(RTRIM(g.envio_nube)) = 'aceptada'
    """)).scalar()

    # 2. Contar/actualizar enviados
    cnt_enviado_fe = conn.execute(text("""
        SELECT COUNT(*) FROM WH_Transaction 
        WHERE nube_status_web = 'pendiente' AND LTRIM(RTRIM(envio_nube)) = 'enviado'
    """)).scalar()

    cnt_enviado_nube = conn.execute(text("""
        SELECT COUNT(*) 
        FROM wh_transaction_nube n
        INNER JOIN WH_Transaction g ON n.TransactionId = g.[Transaction]
        WHERE g.nube_status_web = 'pendiente'
          AND NOT (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1')
          AND LTRIM(RTRIM(g.envio_nube)) <> 'enviado'
    """)).scalar()

    # 3. Contar/actualizar errores
    cnt_error = conn.execute(text("""
        SELECT COUNT(*) FROM WH_Transaction 
        WHERE nube_status_web = 'pendiente'
          AND (LTRIM(RTRIM(envio_nube)) LIKE '%error%' OR LEN(LTRIM(RTRIM(envio_nube))) > 20)
          AND LTRIM(RTRIM(envio_nube)) NOT IN ('aceptada', 'enviado', 'anulado')
    """)).scalar()

    total = cnt_aceptado_fe + cnt_aceptado_nube + cnt_enviado_fe + cnt_enviado_nube + cnt_error
    print(f"Registros a actualizar en Guías:")
    print(f"  - A 'aceptado' (por histórico): {cnt_aceptado_fe}")
    print(f"  - A 'aceptado' (por NubeFact):  {cnt_aceptado_nube}")
    print(f"  - A 'enviado'  (por histórico): {cnt_enviado_fe}")
    print(f"  - A 'enviado'  (por NubeFact):  {cnt_enviado_nube}")
    print(f"  - A 'error':                    {cnt_error}")
    print(f"  Total a modificar en Guías:     {total}")
    
    if total > 0 and commit:
        print("Aplicando actualizaciones de Guías...")
        
        # Aceptados
        r1 = conn.execute(text("""
            UPDATE WH_Transaction
            SET nube_status_web = 'aceptado'
            WHERE nube_status_web IN ('pendiente', 'enviado')
              AND LTRIM(RTRIM(envio_nube)) = 'aceptada'
        """))
        print(f"  -> {r1.rowcount} registros actualizados a 'aceptado' por histórico")

        r2 = conn.execute(text("""
            UPDATE g
            SET g.nube_status_web = 'aceptado'
            FROM wh_transaction_nube n
            INNER JOIN WH_Transaction g ON n.TransactionId = g.[Transaction]
            WHERE g.nube_status_web IN ('pendiente', 'enviado')
              AND (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1')
        """))
        print(f"  -> {r2.rowcount} registros actualizados a 'aceptado' por NubeFact")

        # Enviados
        r3 = conn.execute(text("""
            UPDATE WH_Transaction
            SET nube_status_web = 'enviado'
            WHERE nube_status_web = 'pendiente' AND LTRIM(RTRIM(envio_nube)) = 'enviado'
        """))
        print(f"  -> {r3.rowcount} registros actualizados a 'enviado' por histórico")

        r4 = conn.execute(text("""
            UPDATE g
            SET g.nube_status_web = 'enviado'
            FROM wh_transaction_nube n
            INNER JOIN WH_Transaction g ON n.TransactionId = g.[Transaction]
            WHERE g.nube_status_web = 'pendiente'
        """))
        print(f"  -> {r4.rowcount} registros actualizados a 'enviado' por NubeFact")

        # Errores
        r5 = conn.execute(text("""
            UPDATE WH_Transaction
            SET nube_status_web = 'error'
            WHERE nube_status_web = 'pendiente'
              AND (LTRIM(RTRIM(envio_nube)) LIKE '%error%' OR LEN(LTRIM(RTRIM(envio_nube))) > 20)
              AND LTRIM(RTRIM(envio_nube)) NOT IN ('aceptada', 'enviado', 'anulado')
        """))
        print(f"  -> {r5.rowcount} registros actualizados a 'error'")


def sincronizar_retenciones(conn, commit):
    print("\n" + "=" * 80)
    print("SINCRONIZACIÓN DE RETENCIONES (AP_Retencion)")
    print("=" * 80)
    
    # 1. Contar/actualizar aceptados
    cnt_aceptado_fe = conn.execute(text("""
        SELECT COUNT(*) FROM AP_Retencion 
        WHERE nube_status_web IN ('pendiente', 'enviado')
          AND (LOWER(status) LIKE '%aceptad%' OR LOWER(status) = 'enviada')
    """)).scalar()

    cnt_aceptado_nube = conn.execute(text("""
        SELECT COUNT(*) 
        FROM AP_Retencion_Status s
        INNER JOIN AP_Retencion r ON s.Retencion = r.Id
        WHERE r.nube_status_web IN ('pendiente', 'enviado')
          AND s.Status = 'aceptada'
          AND NOT (LOWER(r.status) LIKE '%aceptad%' OR LOWER(r.status) = 'enviada')
    """)).scalar()

    # 2. Contar/actualizar enviados
    cnt_enviado_fe = conn.execute(text("""
        SELECT COUNT(*) FROM AP_Retencion 
        WHERE nube_status_web = 'pendiente' AND LOWER(status) = 'enviado'
    """)).scalar()

    cnt_enviado_nube = conn.execute(text("""
        SELECT COUNT(*) 
        FROM AP_Retencion_Status s
        INNER JOIN AP_Retencion r ON s.Retencion = r.Id
        WHERE r.nube_status_web = 'pendiente'
          AND s.Status <> 'aceptada'
          AND LOWER(r.status) <> 'enviado'
    """)).scalar()

    # 3. Contar/actualizar errores y anulados
    cnt_error = conn.execute(text("""
        SELECT COUNT(*) FROM AP_Retencion 
        WHERE nube_status_web = 'pendiente'
          AND (LOWER(status) LIKE '%error%' OR LOWER(status) LIKE '%rechaza%')
    """)).scalar()

    cnt_anulado = conn.execute(text("""
        SELECT COUNT(*) FROM AP_Retencion 
        WHERE nube_status_web = 'pendiente'
          AND (LOWER(status) = 'anulado' OR LOWER(status) = 'anulada')
    """)).scalar()

    total = cnt_aceptado_fe + cnt_aceptado_nube + cnt_enviado_fe + cnt_enviado_nube + cnt_error + cnt_anulado
    print(f"Registros a actualizar en Retenciones:")
    print(f"  - A 'aceptado' (por histórico): {cnt_aceptado_fe}")
    print(f"  - A 'aceptado' (por NubeFact):  {cnt_aceptado_nube}")
    print(f"  - A 'enviado'  (por histórico): {cnt_enviado_fe}")
    print(f"  - A 'enviado'  (por NubeFact):  {cnt_enviado_nube}")
    print(f"  - A 'error':                    {cnt_error}")
    print(f"  - A 'anulado':                  {cnt_anulado}")
    print(f"  Total a modificar en Retenciones:{total}")
    
    if total > 0 and commit:
        print("Aplicando actualizaciones de Retenciones...")
        
        # Aceptados
        r1 = conn.execute(text("""
            UPDATE AP_Retencion
            SET nube_status_web = 'aceptado'
            WHERE nube_status_web IN ('pendiente', 'enviado')
              AND (LOWER(status) LIKE '%aceptad%' OR LOWER(status) = 'enviada')
        """))
        print(f"  -> {r1.rowcount} registros actualizados a 'aceptado' por histórico")

        r2 = conn.execute(text("""
            UPDATE r
            SET r.nube_status_web = 'aceptado'
            FROM AP_Retencion_Status s
            INNER JOIN AP_Retencion r ON s.Retencion = r.Id
            WHERE r.nube_status_web IN ('pendiente', 'enviado')
              AND s.Status = 'aceptada'
        """))
        print(f"  -> {r2.rowcount} registros actualizados a 'aceptado' por NubeFact")

        # Enviados
        r3 = conn.execute(text("""
            UPDATE AP_Retencion
            SET nube_status_web = 'enviado'
            WHERE nube_status_web = 'pendiente' AND LOWER(status) = 'enviado'
        """))
        print(f"  -> {r3.rowcount} registros actualizados a 'enviado' por histórico")

        r4 = conn.execute(text("""
            UPDATE r
            SET r.nube_status_web = 'enviado'
            FROM AP_Retencion_Status s
            INNER JOIN AP_Retencion r ON s.Retencion = r.Id
            WHERE r.nube_status_web = 'pendiente'
        """))
        print(f"  -> {r4.rowcount} registros actualizados a 'enviado' por NubeFact")

        # Errores
        r5 = conn.execute(text("""
            UPDATE AP_Retencion
            SET nube_status_web = 'error'
            WHERE nube_status_web = 'pendiente'
              AND (LOWER(status) LIKE '%error%' OR LOWER(status) LIKE '%rechaza%')
        """))
        print(f"  -> {r5.rowcount} registros actualizados a 'error'")

        # Anulados
        r6 = conn.execute(text("""
            UPDATE AP_Retencion
            SET nube_status_web = 'anulado'
            WHERE nube_status_web = 'pendiente'
              AND (LOWER(status) = 'anulado' OR LOWER(status) = 'anulada')
        """))
        print(f"  -> {r6.rowcount} registros actualizados a 'anulado'")


def main():
    parser = argparse.ArgumentParser(description="Sincroniza la columna nube_status_web con los estados reales de Ventas, Guías y Retenciones.")
    parser.add_argument("--commit", action="store_true", help="Aplica y confirma los cambios en la base de datos.")
    args = parser.parse_args()

    settings = get_settings()
    db_url = settings.database_url
    
    print("=" * 80)
    print("SINCRONIZACIÓN INTEGRAL DE ESTADOS (NUBE_STATUS_WEB) EN PRODUCCIÓN (OPTIMIZADA)")
    print("=" * 80)
    print(f"Base de datos: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    print(f"Modo: {'EJECUCIÓN REAL (COMMIT)' if args.commit else 'SIMULACIÓN (DRY RUN)'}")
    print("-" * 80)
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Comenzar transacción
            trans = conn.begin()
            
            sincronizar_ventas(conn, args.commit)
            sincronizar_guias(conn, args.commit)
            sincronizar_retenciones(conn, args.commit)
            
            if args.commit:
                trans.commit()
                print("\n✅ ¡Sincronización integral guardada exitosamente en producción!")
            else:
                print("\nSIMULACIÓN COMPLETADA (ROLLBACK).")
                print("Para aplicar los cambios físicamente, vuelve a ejecutar el script con la bandera --commit:")
                print("python scripts/sincronizar_estados.py --commit")
                trans.rollback()
                
    except Exception as e:
        print(f"❌ Error durante la sincronización: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
