#!/usr/bin/env python3
import os
import sys

# Agregar el directorio raíz del proyecto al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.retenciones import APRetencion, APRetencionStatus

def ver_retencion():
    db: Session = SessionLocal()
    try:
        print("=" * 100)
        print("DIAGNÓSTICO DE RETENCIÓN R001-4069")
        print("=" * 100)
        
        # Buscar la cabecera
        ret = db.query(APRetencion).filter(
            APRetencion.Serie == 'R001',
            APRetencion.Numero == '4069'
        ).first()
        
        if not ret:
            # Intentar buscar quitando ceros a la izquierda o buscando por entero
            ret = db.query(APRetencion).filter(
                APRetencion.Serie == 'R001',
                APRetencion.Numero.like('%4069')
            ).first()
            
        if not ret:
            print("ERROR: No se encontró ninguna retención con Serie: R001 y Número: 4069 en la base de datos.")
            return
            
        print(f"DATOS DE CABECERA (AP_Retencion):")
        print(f"  - Id: {ret.Id}")
        print(f"  - Serie: {ret.Serie}")
        print(f"  - Numero: {ret.Numero}")
        print(f"  - VendorRuc: {ret.VendorRuc}")
        print(f"  - VendorName: {ret.VendorName}")
        print(f"  - DocumentDate: {ret.DocumentDate}")
        print(f"  - TotalRetenido: {ret.TotalRetenido}")
        print(f"  - TotalPagado: {ret.TotalPagado}")
        print(f"  - status (ERP): {ret.status}")
        print(f"  - nube_status_web: {ret.nube_status_web}")
        print(f"  - necesita_aprobacion: {ret.necesita_aprobacion}")
        print("-" * 100)
        
        # Buscar todos los estados guardados
        estados = db.query(APRetencionStatus).filter(
            APRetencionStatus.Retencion == ret.Id
        ).order_by(APRetencionStatus.id.desc()).all()
        
        print(f"HISTORIAL DE ESTADOS (AP_Retencion_Status) - Encontrados: {len(estados)}")
        for idx, est in enumerate(estados, 1):
            print(f"  {idx}. Registro ID: {est.id}")
            print(f"     - Status: {est.Status}")
            print(f"     - Pdf: {est.Pdf[:100] if est.Pdf else 'None'}... (longitud: {len(est.Pdf) if est.Pdf else 0})")
            print(f"     - Xml: {est.Xml[:100] if est.Xml else 'None'}... (longitud: {len(est.Xml) if est.Xml else 0})")
            print(f"     - Cdr: {est.Cdr[:100] if est.Cdr else 'None'}... (longitud: {len(est.Cdr) if est.Cdr else 0})")
            print(f"     - Aceptacion: {est.Aceptacion}")
            print(f"     - Descripcion (SUNAT): {est.Descripcion}")
            print(f"     - error (NubeFact/SUNAT): {est.error}")
            print(f"     - Soap error: {est.Soap}")
            print(f"     - Usuario: {est.XlastUser} | Fecha: {est.XlastDate}")
            print("     " + "-" * 50)
            
    except Exception as e:
        print(f"Error consultando la base de datos: {e}")
    finally:
        db.close()
    print("=" * 100)

if __name__ == "__main__":
    ver_retencion()
