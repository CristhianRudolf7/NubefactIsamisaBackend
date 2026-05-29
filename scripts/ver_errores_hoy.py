#!/usr/bin/env python
"""
Script para ver los errores de envío de hoy a SUNAT / NubeFact.
Permite opcionalmente ver días anteriores o una fecha específica.

Uso:
  python scripts/ver_errores_hoy.py
  python scripts/ver_errores_hoy.py --days 1
  python scripts/ver_errores_hoy.py --date 2026-05-27
"""
import os
import sys
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Agregar el directorio raíz del proyecto al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.config import get_settings
from app.models.nube_response import ARFENube
from app.models.guia_response import WHTransactionNube
from app.models.retenciones import APRetencionStatus, APRetencion


def ver_errores():
    settings = get_settings()
    timezone_str = settings.timezone
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        # Fallback si no está configurada o falla
        tz = ZoneInfo("America/Lima")
    
    parser = argparse.ArgumentParser(description="Ver errores de envío a SUNAT/NubeFact")
    parser.add_argument(
        "--days", 
        type=int, 
        default=0, 
        help="Días adicionales hacia atrás a consultar (0 = solo hoy, 1 = hoy y ayer, etc.)"
    )
    parser.add_argument(
        "--date", 
        type=str, 
        help="Fecha específica a consultar en formato YYYY-MM-DD (ej. 2026-05-27)"
    )
    
    args = parser.parse_args()
    
    # Calcular rango de fechas en hora de Perú
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
            start_dt = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tz)
            end_dt = target_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=tz)
        except ValueError:
            print("Error: Formato de fecha inválido. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        now_local = datetime.now(tz)
        start_dt = now_local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=args.days)
        end_dt = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()
    
    # Para comparación con DateTime naive en la BD
    start_naive = start_dt.replace(tzinfo=None)
    end_naive = end_dt.replace(tzinfo=None)
    
    db: Session = SessionLocal()
    
    try:
        print("=" * 100)
        print(f"CONSULTANDO ERRORES DE ENVÍO A SUNAT/NUBEFACT")
        print(f"Rango de consulta (Hora Perú): {start_dt.strftime('%d/%m/%Y %H:%M:%S')} - {end_dt.strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 100)
        
        # 1. Ventas (ar_fe_nube)
        print("\n[MÓDULO VENTAS (Facturas/Boletas/NC/ND)]")
        ventas_query = db.query(ARFENube).filter(
            ARFENube.fecha_envio >= start_ts,
            ARFENube.fecha_envio <= end_ts,
            (
                (ARFENube.error != None) & (ARFENube.error != '') |
                (ARFENube.sunat_soap_error != None) & (ARFENube.sunat_soap_error != '')
            )
        )
        ventas_errores = ventas_query.order_by(ARFENube.fecha_envio.desc()).all()
        
        if not ventas_errores:
            print("  No se encontraron errores en Ventas.")
        else:
            for v in ventas_errores:
                fecha_env = datetime.fromtimestamp(v.fecha_envio, tz)
                print(f"  * [{fecha_env.strftime('%H:%M:%S')}] Documento: {v.serie}-{v.numero} | Usuario: {v.usuario_envio}")
                if v.error:
                    print(f"    - Error NubeFact: {v.error}")
                if v.sunat_soap_error:
                    print(f"    - Error SOAP SUNAT: {v.sunat_soap_error}")
                if v.sunat_description:
                    print(f"    - Respuesta SUNAT: {v.sunat_description}")
                print("    " + "-" * 60)
                
        # 2. Guías de Remisión (wh_transaction_nube)
        print("\n[MÓDULO GUÍAS DE REMISIÓN]")
        guias_query = db.query(WHTransactionNube).filter(
            WHTransactionNube.fecha_envio >= start_ts,
            WHTransactionNube.fecha_envio <= end_ts,
            (
                (WHTransactionNube.error != None) & (WHTransactionNube.error != '') |
                (WHTransactionNube.sunat_soap_error != None) & (WHTransactionNube.sunat_soap_error != '')
            )
        )
        guias_errores = guias_query.order_by(WHTransactionNube.fecha_envio.desc()).all()
        
        if not guias_errores:
            print("  No se encontraron errores en Guías.")
        else:
            for g in guias_errores:
                fecha_env = datetime.fromtimestamp(g.fecha_envio, tz)
                print(f"  * [{fecha_env.strftime('%H:%M:%S')}] Guía: {g.serie}-{g.numero} (ID Transacción: {g.TransactionId}) | Usuario: {g.usuario_envio}")
                if g.error:
                    print(f"    - Error NubeFact: {g.error}")
                if g.sunat_soap_error:
                    print(f"    - Error SOAP SUNAT: {g.sunat_soap_error}")
                if g.sunat_description:
                    print(f"    - Respuesta SUNAT: {g.sunat_description}")
                print("    " + "-" * 60)
                
        # 3. Retenciones (AP_Retencion_Status)
        print("\n[MÓDULO RETENCIONES]")
        # Hacemos join con cabecera para ver serie/número
        ret_query = db.query(APRetencionStatus).join(
            APRetencion, APRetencionStatus.Retencion == APRetencion.Id
        ).filter(
            APRetencionStatus.XlastDate >= start_naive,
            APRetencionStatus.XlastDate <= end_naive,
            (
                (APRetencionStatus.Status == 'error') |
                (APRetencionStatus.Status == 'rechazada') |
                (APRetencionStatus.error != None) & (APRetencionStatus.error != '') |
                (APRetencionStatus.Soap != None) & (APRetencionStatus.Soap != '')
            )
        )
        ret_errores = ret_query.order_by(APRetencionStatus.XlastDate.desc()).all()
        
        if not ret_errores:
            print("  No se encontraron errores en Retenciones.")
        else:
            for r in ret_errores:
                ret_doc = db.query(APRetencion).filter(APRetencion.Id == r.Retencion).first()
                doc_info = f"{ret_doc.Serie}-{ret_doc.Numero}" if ret_doc else f"ID {r.Retencion}"
                
                # Asegurar de mostrar con hora correcta
                fecha_env = r.XlastDate
                print(f"  * [{fecha_env.strftime('%H:%M:%S')}] Retención: {doc_info} | Usuario: {r.XlastUser}")
                if r.error:
                    print(f"    - Error NubeFact: {r.error}")
                if r.Soap:
                    print(f"    - Error SOAP SUNAT: {r.Soap}")
                if r.Descripcion:
                    print(f"    - Respuesta SUNAT: {r.Descripcion}")
                print("    " + "-" * 60)
                
        print("\n" + "=" * 100)
        print("Búsqueda completada.")
        print("=" * 100)
        
    except Exception as e:
        print(f"Error consultando la base de datos: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    ver_errores()
