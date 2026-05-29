#!/usr/bin/env python3
"""
Script para ver los errores de los documentos de serie B037 con fecha >= 28/05/2026.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Agregar el directorio raíz del proyecto al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.database import SessionLocal
from app.config import get_settings
from app.models.ventas import ARDocument
from app.models.nube_response import ARFENube

def ver_errores_b037():
    settings = get_settings()
    timezone_str = settings.timezone
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        tz = ZoneInfo("America/Lima")
    
    db: Session = SessionLocal()
    try:
        fecha_limite = datetime(2026, 5, 28)
        
        print("=" * 100)
        print(f"CONSULTANDO ERRORES DE DOCUMENTOS SERIE B037 (FECHA >= 28/05/2026)")
        print("=" * 100)
        
        # 1. Obtener todos los documentos de serie B037 con fecha >= 28/05/2026
        documentos = db.query(ARDocument).filter(
            ARDocument.DocumentSerie == 'B037',
            ARDocument.DocumentDate >= fecha_limite
        ).order_by(ARDocument.DocumentDate.desc()).all()
        
        if not documentos:
            print("No se encontraron documentos de la serie B037 con fecha >= 28/05/2026 en el ERP.")
            return
            
        print(f"Total de documentos encontrados en el ERP: {len(documentos)}")
        print("-" * 100)
        
        # 2. Obtener respuestas de NubeFact en un solo lote para evitar N+1 queries
        document_keys = {(d.DocumentSerie, d.DocumentNo) for d in documentos if d.DocumentSerie and d.DocumentNo}
        nube_resps_map = {}
        if document_keys:
            filters = [and_(ARFENube.serie == s, ARFENube.numero == n) for s, n in document_keys]
            nube_resps = db.query(ARFENube).filter(or_(*filters)).all()
            for r in nube_resps:
                key = (r.serie, r.numero)
                if key not in nube_resps_map or r.id > nube_resps_map[key].id:
                    nube_resps_map[key] = r
                    
        # 3. Filtrar y mostrar los que tienen estado de error o rechazo
        errores_encontrados = 0
        for d in documentos:
            key = (d.DocumentSerie, d.DocumentNo)
            nube_resp = nube_resps_map.get(key)
            
            # Determinar si el documento tiene error
            tiene_error_erp = (d.fe or '').lower() in ['error', 'rechazado'] or (d.nube_status_web or '').lower() in ['error', 'rechazado']
            tiene_error_nube = False
            error_nube_msg = None
            
            if nube_resp:
                error_nube_msg = nube_resp.error or nube_resp.sunat_soap_error
                if error_nube_msg:
                    tiene_error_nube = True
            
            if tiene_error_erp or tiene_error_nube:
                errores_encontrados += 1
                fecha_doc = d.DocumentDate.astimezone(tz) if d.DocumentDate.tzinfo else d.DocumentDate
                print(f"{errores_encontrados}. [{fecha_doc.strftime('%Y-%m-%d %H:%M:%S')}] Documento: {d.DocumentSerie}-{d.DocumentNo}")
                print(f"   Código ERP: {d.Document} | Cliente: {d.VendorName} | RUC: {d.VendorRUC}")
                print(f"   Monto Total: S/. {d.AmountTotalLo:.2f} | Moneda: {d.DocumentCurrency}")
                print(f"   Estado ERP (fe): {d.fe} | Estado Web (nube_status_web): {d.nube_status_web}")
                
                # Obtener el mejor mensaje de error posible
                err_msg = error_nube_msg or d.RejectionReason or d.Comments
                if nube_resp and not err_msg:
                    err_msg = nube_resp.sunat_description
                if not err_msg:
                    err_msg = "Error desconocido o sin descripción registrada."
                    
                print(f"   Detalle del Error: {err_msg}")
                print("-" * 100)
                
        if errores_encontrados == 0:
            print("No se encontraron documentos en estado de ERROR o RECHAZADO para la serie B037 en el rango indicado.")
        else:
            print(f"Búsqueda finalizada. Se encontraron {errores_encontrados} documentos con errores.")
        print("=" * 100)

    except Exception as e:
        print(f"Error consultando la base de datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    ver_errores_b037()
