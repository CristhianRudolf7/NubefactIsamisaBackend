#!/usr/bin/env python
"""
Script para sincronizar y corregir la columna 'nube_status_web' en:
- AR_Document (Ventas)
- WH_Transaction (Guías)
- AP_Retencion (Retenciones)

Resuelve las discrepancias donde figuran como 'pendiente' o 'enviado' 
pero ya fueron aceptados o enviados en las tablas históricas o de NubeFact.
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
    
    # Caso A: Cambiar a 'aceptado' porque está aceptado en ar_fe_nube o fe dice correcto/aceptado
    cnt_aceptado = conn.execute(text("""
        SELECT COUNT(*) 
        FROM AR_Document d
        LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
        WHERE d.nube_status_web IN ('pendiente', 'enviado')
          AND (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1' OR LOWER(d.fe) LIKE '%aceptad%' OR LOWER(d.fe) = 'correcto')
          -- Evitar redundancia si ya está en aceptado
          AND d.nube_status_web <> 'aceptado'
    """)).scalar()

    # Caso B: Cambiar a 'enviado' porque fe = 'enviado' o hay respuesta en ar_fe_nube (pero no es 'true'/'1' todavía o no está aceptado)
    cnt_enviado = conn.execute(text("""
        SELECT COUNT(*) 
        FROM AR_Document d
        LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
        WHERE d.nube_status_web = 'pendiente'
          AND (d.fe = 'enviado' OR n.id IS NOT NULL)
          AND NOT (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1' OR LOWER(d.fe) LIKE '%aceptad%' OR LOWER(d.fe) = 'correcto')
    """)).scalar()

    # Caso C: Cambiar a 'error' porque fe tiene error
    cnt_error = conn.execute(text("""
        SELECT COUNT(*) 
        FROM AR_Document d
        WHERE d.nube_status_web = 'pendiente'
          AND (LOWER(d.fe) LIKE '%error%' OR LEN(d.fe) > 20)
    """)).scalar()

    total = cnt_aceptado + cnt_enviado + cnt_error
    print(f"Registros a actualizar en Ventas:")
    print(f"  - A 'aceptado': {cnt_aceptado}")
    print(f"  - A 'enviado':  {cnt_enviado}")
    print(f"  - A 'error':    {cnt_error}")
    print(f"  Total:          {total}")
    
    if total > 0 and commit:
        # 1. Update aceptados (inclinando tanto pendientes como enviados que estén aceptados en SUNAT)
        res_act_aceptado = conn.execute(text("""
            UPDATE d
            SET d.nube_status_web = 'aceptado'
            FROM AR_Document d
            LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
            WHERE d.nube_status_web IN ('pendiente', 'enviado')
              AND (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1' OR LOWER(d.fe) LIKE '%aceptad%' OR LOWER(d.fe) = 'correcto')
              AND d.nube_status_web <> 'aceptado'
        """))
        print(f"  -> {res_act_aceptado.rowcount} registros actualizados a 'aceptado'")

        # 2. Update enviados
        res_act_enviado = conn.execute(text("""
            UPDATE d
            SET d.nube_status_web = 'enviado'
            FROM AR_Document d
            LEFT JOIN ar_fe_nube n ON n.serie = d.DocumentSerie AND n.numero = d.DocumentNo
            WHERE d.nube_status_web = 'pendiente'
              AND (d.fe = 'enviado' OR n.id IS NOT NULL)
              AND NOT (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1' OR LOWER(d.fe) LIKE '%aceptad%' OR LOWER(d.fe) = 'correcto')
        """))
        print(f"  -> {res_act_enviado.rowcount} registros actualizados a 'enviado'")

        # 3. Update errores
        res_act_error = conn.execute(text("""
            UPDATE AR_Document
            SET nube_status_web = 'error'
            WHERE nube_status_web = 'pendiente'
              AND (LOWER(fe) LIKE '%error%' OR LEN(fe) > 20)
        """))
        print(f"  -> {res_act_error.rowcount} registros actualizados a 'error'")


def sincronizar_guias(conn, commit):
    print("\n" + "=" * 80)
    print("SINCRONIZACIÓN DE GUÍAS (WH_Transaction)")
    print("=" * 80)
    
    # Caso A: Cambiar a 'aceptado' porque está aceptado en wh_transaction_nube o envio_nube dice aceptada (con trim)
    cnt_aceptado = conn.execute(text("""
        SELECT COUNT(*) 
        FROM WH_Transaction g
        LEFT JOIN wh_transaction_nube n ON n.TransactionId = g.[Transaction]
        WHERE g.nube_status_web IN ('pendiente', 'enviado')
          AND (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1' OR LTRIM(RTRIM(g.envio_nube)) = 'aceptada')
          AND g.nube_status_web <> 'aceptado'
    """)).scalar()

    # Caso B: Cambiar a 'enviado' porque envio_nube = 'enviado' o hay respuesta en wh_transaction_nube (pero no es 'true'/'1' todavía)
    cnt_enviado = conn.execute(text("""
        SELECT COUNT(*) 
        FROM WH_Transaction g
        LEFT JOIN wh_transaction_nube n ON n.TransactionId = g.[Transaction]
        WHERE g.nube_status_web = 'pendiente'
          AND (LTRIM(RTRIM(g.envio_nube)) = 'enviado' OR n.id IS NOT NULL)
          AND NOT (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1' OR LTRIM(RTRIM(g.envio_nube)) = 'aceptada')
    """)).scalar()

    # Caso C: Cambiar a 'error' porque envio_nube tiene un mensaje largo o error
    cnt_error = conn.execute(text("""
        SELECT COUNT(*) 
        FROM WH_Transaction g
        WHERE g.nube_status_web = 'pendiente'
          AND (LTRIM(RTRIM(g.envio_nube)) LIKE '%error%' OR LEN(LTRIM(RTRIM(g.envio_nube))) > 20)
          AND LTRIM(RTRIM(g.envio_nube)) NOT IN ('aceptada', 'enviado', 'anulado')
    """)).scalar()

    total = cnt_aceptado + cnt_enviado + cnt_error
    print(f"Registros a actualizar en Guías:")
    print(f"  - A 'aceptado': {cnt_aceptado}")
    print(f"  - A 'enviado':  {cnt_enviado}")
    print(f"  - A 'error':    {cnt_error}")
    print(f"  Total:          {total}")
    
    if total > 0 and commit:
        # 1. Update aceptados
        res_act_aceptado = conn.execute(text("""
            UPDATE g
            SET g.nube_status_web = 'aceptado'
            FROM WH_Transaction g
            LEFT JOIN wh_transaction_nube n ON n.TransactionId = g.[Transaction]
            WHERE g.nube_status_web IN ('pendiente', 'enviado')
              AND (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1' OR LTRIM(RTRIM(g.envio_nube)) = 'aceptada')
              AND g.nube_status_web <> 'aceptado'
        """))
        print(f"  -> {res_act_aceptado.rowcount} registros actualizados a 'aceptado'")

        # 2. Update enviados
        res_act_enviado = conn.execute(text("""
            UPDATE g
            SET g.nube_status_web = 'enviado'
            FROM WH_Transaction g
            LEFT JOIN wh_transaction_nube n ON n.TransactionId = g.[Transaction]
            WHERE g.nube_status_web = 'pendiente'
              AND (LTRIM(RTRIM(g.envio_nube)) = 'enviado' OR n.id IS NOT NULL)
              AND NOT (n.aceptada_por_sunat = 'true' OR n.aceptada_por_sunat = '1' OR LTRIM(RTRIM(g.envio_nube)) = 'aceptada')
        """))
        print(f"  -> {res_act_enviado.rowcount} registros actualizados a 'enviado'")

        # 3. Update errores
        res_act_error = conn.execute(text("""
            UPDATE WH_Transaction
            SET nube_status_web = 'error'
            WHERE nube_status_web = 'pendiente'
              AND (LTRIM(RTRIM(envio_nube)) LIKE '%error%' OR LEN(LTRIM(RTRIM(envio_nube))) > 20)
              AND LTRIM(RTRIM(envio_nube)) NOT IN ('aceptada', 'enviado', 'anulado')
        """))
        print(f"  -> {res_act_error.rowcount} registros actualizados a 'error'")


def sincronizar_retenciones(conn, commit):
    print("\n" + "=" * 80)
    print("SINCRONIZACIÓN DE RETENCIONES (AP_Retencion)")
    print("=" * 80)
    
    # Caso A: Cambiar a 'aceptado' porque está aceptada en AP_Retencion_Status o status dice aceptada
    cnt_aceptado = conn.execute(text("""
        SELECT COUNT(*) 
        FROM AP_Retencion r
        LEFT JOIN AP_Retencion_Status s ON s.Retencion = r.Id
        WHERE r.nube_status_web IN ('pendiente', 'enviado')
          AND (s.Status = 'aceptada' OR LOWER(r.status) LIKE '%aceptad%' OR LOWER(r.status) = 'enviada')
          AND r.nube_status_web <> 'aceptado'
    """)).scalar()

    # Caso B: Cambiar a 'enviado' porque status = 'enviado' o hay respuesta en AP_Retencion_Status (pero no es 'aceptada' todavía)
    cnt_enviado = conn.execute(text("""
        SELECT COUNT(*) 
        FROM AP_Retencion r
        LEFT JOIN AP_Retencion_Status s ON s.Retencion = r.Id
        WHERE r.nube_status_web = 'pendiente'
          AND (LOWER(r.status) = 'enviado' OR s.Id IS NOT NULL)
          AND NOT (s.Status = 'aceptada' OR LOWER(r.status) LIKE '%aceptad%' OR LOWER(r.status) = 'enviada')
    """)).scalar()

    # Caso C: Cambiar a 'error' porque status tiene error
    cnt_error = conn.execute(text("""
        SELECT COUNT(*) 
        FROM AP_Retencion r
        WHERE r.nube_status_web = 'pendiente'
          AND (LOWER(r.status) LIKE '%error%' OR LOWER(r.status) LIKE '%rechaza%')
    """)).scalar()

    # Caso D: Cambiar a 'anulado' porque status dice anulado
    cnt_anulado = conn.execute(text("""
        SELECT COUNT(*) 
        FROM AP_Retencion r
        WHERE r.nube_status_web = 'pendiente'
          AND (LOWER(r.status) = 'anulado' OR LOWER(r.status) = 'anulada')
    """)).scalar()

    total = cnt_aceptado + cnt_enviado + cnt_error + cnt_anulado
    print(f"Registros a actualizar en Retenciones:")
    print(f"  - A 'aceptado': {cnt_aceptado}")
    print(f"  - A 'enviado':  {cnt_enviado}")
    print(f"  - A 'error':    {cnt_error}")
    print(f"  - A 'anulado':  {cnt_anulado}")
    print(f"  Total:          {total}")
    
    if total > 0 and commit:
        # 1. Update aceptados
        res_act_aceptado = conn.execute(text("""
            UPDATE r
            SET r.nube_status_web = 'aceptado'
            FROM AP_Retencion r
            LEFT JOIN AP_Retencion_Status s ON s.Retencion = r.Id
            WHERE r.nube_status_web IN ('pendiente', 'enviado')
              AND (s.Status = 'aceptada' OR LOWER(r.status) LIKE '%aceptad%' OR LOWER(r.status) = 'enviada')
              AND r.nube_status_web <> 'aceptado'
        """))
        print(f"  -> {res_act_aceptado.rowcount} registros actualizados a 'aceptado'")

        # 2. Update enviados
        res_act_enviado = conn.execute(text("""
            UPDATE r
            SET r.nube_status_web = 'enviado'
            FROM AP_Retencion r
            LEFT JOIN AP_Retencion_Status s ON s.Retencion = r.Id
            WHERE r.nube_status_web = 'pendiente'
              AND (LOWER(r.status) = 'enviado' OR s.Id IS NOT NULL)
              AND NOT (s.Status = 'aceptada' OR LOWER(r.status) LIKE '%aceptad%' OR LOWER(r.status) = 'enviada')
        """))
        print(f"  -> {res_act_enviado.rowcount} registros actualizados a 'enviado'")

        # 3. Update errores
        res_act_error = conn.execute(text("""
            UPDATE AP_Retencion
            SET nube_status_web = 'error'
            WHERE nube_status_web = 'pendiente'
              AND (LOWER(status) LIKE '%error%' OR LOWER(status) LIKE '%rechaza%')
        """))
        print(f"  -> {res_act_error.rowcount} registros actualizados a 'error'")

        # 4. Update anulados
        res_act_anulado = conn.execute(text("""
            UPDATE AP_Retencion
            SET nube_status_web = 'anulado'
            WHERE nube_status_web = 'pendiente'
              AND (LOWER(status) = 'anulado' OR LOWER(status) = 'anulada')
        """))
        print(f"  -> {res_act_anulado.rowcount} registros actualizados a 'anulado'")


def main():
    parser = argparse.ArgumentParser(description="Sincroniza la columna nube_status_web con los estados reales de Ventas, Guías y Retenciones.")
    parser.add_argument("--commit", action="store_true", help="Aplica y confirma los cambios en la base de datos.")
    args = parser.parse_args()

    settings = get_settings()
    db_url = settings.database_url
    
    print("=" * 80)
    print("SINCRONIZACIÓN INTEGRAL DE ESTADOS (NUBE_STATUS_WEB) EN PRODUCCIÓN")
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
