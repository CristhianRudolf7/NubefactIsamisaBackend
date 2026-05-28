#!/usr/bin/env python3
"""
Script para ver los últimos 10 errores más actuales de envío a SUNAT / NubeFact.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Agregar el directorio raíz del proyecto al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.config import get_settings
from app.models.nube_response import ARFENube
from app.models.guia_response import WHTransactionNube
from app.models.retenciones import APRetencionStatus, APRetencion

def ver_ultimos_10_errores():
    settings = get_settings()
    timezone_str = settings.timezone
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        tz = ZoneInfo("America/Lima")
    
    db: Session = SessionLocal()
    try:
        print("=" * 100)
        print("CONSULTANDO LOS ÚLTIMOS 10 ERRORES DE ENVÍO MÁS RECIENTES (TODOS LOS MÓDULOS)")
        print("=" * 100)
        
        all_errors = []
        
        # 1. Ventas
        ventas = db.query(ARFENube).filter(
            (ARFENube.error != None) & (ARFENube.error != '') |
            (ARFENube.sunat_soap_error != None) & (ARFENube.sunat_soap_error != '') |
            (ARFENube.aceptada_por_sunat == 'false')
        ).order_by(ARFENube.fecha_envio.desc()).limit(10).all()
        
        for v in ventas:
            fecha_env = datetime.fromtimestamp(v.fecha_envio, tz)
            err_msg = v.error or v.sunat_soap_error or v.sunat_description or "Error desconocido"
            all_errors.append({
                "fecha": fecha_env,
                "modulo": "VENTAS",
                "identificador": f"{v.serie}-{v.numero}",
                "usuario": v.usuario_envio,
                "error": err_msg
            })
            
        # 2. Guías
        guias = db.query(WHTransactionNube).filter(
            (WHTransactionNube.error != None) & (WHTransactionNube.error != '') |
            (WHTransactionNube.sunat_soap_error != None) & (WHTransactionNube.sunat_soap_error != '') |
            (WHTransactionNube.aceptada_por_sunat == 'false')
        ).order_by(WHTransactionNube.fecha_envio.desc()).limit(10).all()
        
        for g in guias:
            fecha_env = datetime.fromtimestamp(g.fecha_envio, tz)
            err_msg = g.error or g.sunat_soap_error or g.sunat_description or "Error desconocido"
            all_errors.append({
                "fecha": fecha_env,
                "modulo": "GUÍAS",
                "identificador": f"{g.serie}-{g.numero} (ID: {g.TransactionId})",
                "usuario": g.usuario_envio,
                "error": err_msg
            })
            
        # 3. Retenciones
        retenciones = db.query(APRetencionStatus).join(
            APRetencion, APRetencionStatus.Retencion == APRetencion.Id
        ).filter(
            (APRetencionStatus.Status == 'error') |
            (APRetencionStatus.Status == 'rechazada') |
            (APRetencionStatus.error != None) & (APRetencionStatus.error != '') |
            (APRetencionStatus.Soap != None) & (APRetencionStatus.Soap != '')
        ).order_by(APRetencionStatus.XlastDate.desc()).limit(10).all()
        
        for r in retenciones:
            ret_doc = db.query(APRetencion).filter(APRetencion.Id == r.Retencion).first()
            doc_info = f"{ret_doc.Serie}-{ret_doc.Numero}" if ret_doc else f"ID {r.Retencion}"
            
            # Convertir XlastDate naive (asumida en Lima) a aware si es necesario
            fecha_env = r.XlastDate.replace(tzinfo=tz) if r.XlastDate.tzinfo is None else r.XlastDate
            err_msg = r.error or r.Soap or r.Descripcion or "Error desconocido"
            all_errors.append({
                "fecha": fecha_env,
                "modulo": "RETENCIONES",
                "identificador": doc_info,
                "usuario": r.XlastUser,
                "error": err_msg
            })
            
        # Ordenar todos los errores combinados por fecha descendente y tomar los primeros 10
        all_errors.sort(key=lambda x: x["fecha"], reverse=True)
        top_10 = all_errors[:10]
        
        if not top_10:
            print("No se encontraron errores en la base de datos.")
        else:
            for idx, err in enumerate(top_10, 1):
                print(f"{idx}. [{err['fecha'].strftime('%Y-%m-%d %H:%M:%S')}] Modulo: {err['modulo']}")
                print(f"   Documento: {err['identificador']} | Usuario: {err['usuario']}")
                print(f"   Detalle del Error: {err['error']}")
                print("-" * 100)
                
    except Exception as e:
        print(f"Error consultando la base de datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    ver_ultimos_10_errores()
