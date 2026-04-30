#!/usr/bin/env python3
"""
Script interactivo para generar documentos de prueba (Ventas, Retenciones o Guías)
"""
import sys
import os
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import Integer, desc, func

# Agregar el directorio raíz del proyecto al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.ventas import ARDocument, ARDocumentDetail
from app.models.retenciones import APRetencion, APRetencionDetail
from app.models.guias import WHTransaction, WHTransactionDetail
from app.utils.datetime import now_peru

def excel_date_now():
    """Convierte la fecha actual a formato Excel"""
    excel_epoch = datetime(1899, 12, 30)
    current_date = now_peru()
    current_date_naive = datetime(
        current_date.year, 
        current_date.month, 
        current_date.day,
        current_date.hour,
        current_date.minute,
        current_date.second
    )
    delta = current_date_naive - excel_epoch
    return delta.days + delta.seconds / (24 * 3600)

def get_next_correlative(db: Session, model, serie_field, number_field, type_filter=None, type_field=None, label="documento"):
    """Obtiene la serie y el siguiente número para un modelo dado"""
    query = db.query(model)
    if type_filter and type_field:
        query = query.filter(getattr(model, type_field).contains(type_filter))
    
    last_doc = query.order_by(desc(getattr(model, number_field).cast(Integer))).first()
    
    if last_doc:
        serie = getattr(last_doc, serie_field)
        try:
            last_num = int(getattr(last_doc, number_field))
            next_num = last_num + 1
        except:
            next_num = 1
    else:
        # Defaults si no hay datos - usar valores autorizados en NubeFact
        serie = "0001"
        if type_filter == "01": 
            serie = "FFF1"
            next_num = 21 # Empezar después del último registrado en NubeFact
        elif type_filter == "03": 
            serie = "BBB1"
        elif type_filter == "07": 
            serie = "FFC1"
        elif model == APRetencion: 
            serie = "R001"
        elif model == WHTransaction: 
            serie = "T001"

        if 'next_num' not in locals():
            next_num = 1
        
        print(f"\n[INFO] No hay datos previos para {label} ({type_filter or ''}). Usando serie {serie}, número {str(next_num).zfill(8)}")
    
    return serie, str(next_num).zfill(6 if model == APRetencion else 8)

def create_venta(db: Session, doc_type_name, type_code, ruc, name, suffix=""):
    serie, numero = get_next_correlative(db, ARDocument, "DocumentSerie", "DocumentNo", type_code, "typeDocSun", label=doc_type_name)
    
    # Forzar series autorizadas si se encuentran series antiguas/erróneas
    if type_code == "03" and serie.startswith("B") and serie != "BBB1":
        print(f"[FIX] Cambiando serie antigua {serie} por BBB1 para Boletas")
        serie = "BBB1"
    
    doc_id = f"TEST-{type_code}-{serie}-{numero}{suffix}"
    
    doc = ARDocument(
        Document=doc_id,
        DocumentNo=numero,
        DocumentSerie=serie,
        DocumentType=doc_type_name,
        Company="LIMADSAS",
        VendorName=name,
        VendorRUC=ruc,
        DocumentDate=excel_date_now(),
        RegisterDate=excel_date_now(),
        DueDate=excel_date_now() + 30,
        DocumentCurrency="LO",  # Soles
        ExchangeRate=1.0,  # Tipo de cambio
        AmountNetLo=100.0,  # Subtotal
        AmountTaxLo=18.0,   # IGV
        AmountTotalLo=118.0,  # Total
        fe="", # Pendiente
        typeDocSun=type_code,
        XLastUser="GENERATOR",
        XLastDate=datetime.now().timestamp()
    )
    db.add(doc)
    db.flush()
    
    detail = ARDocumentDetail(
        Document=doc_id,
        Line=1,
        Description=f"Producto de prueba {suffix}",
        Unit="NIU",  # Unidad
        Quantity=1,
        Price=100.0,  # Valor unitario sin IGV
        PriceTax=118.0,  # Precio unitario con IGV
        SubTotal=100.0,  # Subtotal línea
        TotalTaxLo=18.0,   # IGV línea
        Total=118.0,  # Total línea
        XLastUser="GENERATOR",
        XLastDate=datetime.now().timestamp()
    )
    db.add(detail)
    return doc_id

def create_retencion(db: Session, ruc, name, suffix=""):
    serie, numero = get_next_correlative(db, APRetencion, "Serie", "Numero", label="Retención")
    
    ret = APRetencion(
        Serie=serie,
        Numero=numero,
        VendorRuc=ruc,
        VendorName=name,
        DocumentDate=excel_date_now(),
        Tasa=3,
        TotalRetenido=30.0,
        TotalPagado=970.0,
        status="pendiente",
        XlastUser="GENERATOR",
        XlastDate=datetime.now().timestamp()
    )
    db.add(ret)
    db.flush()
    
    detail = APRetencionDetail(
        Retencion=ret.Id,
        DRserie="F001",
        DRnumero="000001",
        DRfecha=excel_date_now() - 5,
        DRmoneda="PEN",
        DRtotal=1000.0,
        DRpagoFecha=excel_date_now(),
        DRpagoNro="OP-12345",
        DRpagoTotal=970.0,
        TipoCambio=1.0,
        TipoCambioFecha=excel_date_now(),
        Retenido=30.0,
        RetenidoFecha=excel_date_now(),
        Pagado=970.0
    )
    db.add(detail)
    return f"{serie}-{numero}"

def create_guia(db: Session, ruc, name, suffix=""):
    serie, numero = get_next_correlative(db, WHTransaction, "DocumentSerie", "DocumentNo", label="Guía de Remisión")
    trans_id = f"TEST-GUIA-{serie}-{numero}{suffix}"
    
    guia = WHTransaction(
        Transaction=trans_id,
        DocumentSerie=serie,
        DocumentNo=numero,
        DocumentType="GUIA REMISION",
        TargetPersonRUC=ruc,
        TargetPersonName=name,
        TransactionDate=excel_date_now(),
        FechaTraslado=excel_date_now() + 1,
        MotivoTraslado="VENTA",
        Status="pendiente",
        XLastUser="GENERATOR",
        XLastDate=datetime.now().timestamp()
    )
    db.add(guia)
    db.flush()
    
    detail = WHTransactionDetail(
        Transaction=trans_id,
        Line=1,
        ItemDescription=f"Item de guía de prueba {suffix}",
        Quantity=10.0,
        Unit="NIU",
        XLastUser="GENERATOR",
        XLastDate=datetime.now().timestamp()
    )
    db.add(detail)
    return f"{serie}-{numero}"

def main():
    print("=== GENERADOR DE DOCUMENTOS DE PRUEBA ===")
    print("1. Ventas (Factura, Boleta, NC)")
    print("2. Retenciones")
    print("3. Guías de Remisión")
    
    choice = input("\nSeleccione una opción (1-3): ")
    db = SessionLocal()
    
    try:
        if choice == '1':
            # Ventas - Uno de cada uno (Bueno y Malo)
            for doc_name, sun_code in [("FACTURA", "01"), ("BOLETA", "03"), ("NOTA CREDITO", "07")]:
                # Mapear a tipos internos que coincidan con la lógica de DocumentService
                if sun_code == "01":
                    doc_type_name = "LIMADSAS FACTURA"
                elif sun_code == "03":
                    doc_type_name = "LIMADSAS BOLETA"
                else:
                    doc_type_name = "LIMADSAS CREDITO"
                print(f"\nGenerando {doc_name}...")
                id_good = create_venta(db, doc_type_name, sun_code, "20600695771", f"CLIENTE {doc_name} OK", " (OK)")
                # Para error: usar DNI con longitud incorrecta (6 caracteres en lugar de 8)
                id_bad = create_venta(db, doc_type_name, sun_code, "123456", f"CLIENTE {doc_name} ERROR", " (ERROR)")
                print(f"  Creado OK: {id_good}")
                print(f"  Creado Error (DNI inválido - 6 caracteres): {id_bad}")
            
        elif choice == '2':
            print("\nGenerando Retención...")
            id_good = create_retencion(db, "20600695771", "PROVEEDOR OK", " (OK)")
            id_bad = create_retencion(db, "123", "PROVEEDOR ERROR", " (ERROR)")
            print(f"  Creado OK: {id_good}")
            print(f"  Creado Error (RUC inválido): {id_bad}")
            
        elif choice == '3':
            print("\nGenerando Guía de Remisión...")
            id_good = create_guia(db, "20600695771", "DESTINATARIO OK", " (OK)")
            id_bad = create_guia(db, "123", "DESTINATARIO ERROR", " (ERROR)")
            print(f"  Creado OK: {id_good}")
            print(f"  Creado Error (RUC inválido): {id_bad}")
        else:
            print("Opción no válida")
            return

        db.commit()
        print("\n¡Documentos generados y guardados exitosamente!")
        
    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
