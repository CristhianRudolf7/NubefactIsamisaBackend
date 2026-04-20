#!/usr/bin/env python3
"""
Script para cargar documentos de ventas de prueba
Crea un documento con error y otro correcto, siguiendo las series y números existentes
"""

import sys
import os
from datetime import datetime
from decimal import Decimal

# Agregar el directorio actual al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import Integer, desc, func
from app.database import SessionLocal
from app.models.ventas import ARDocument, ARDocumentDetail
from app.utils.datetime import now_peru

def get_next_serie_numero(db: Session, document_type: str):
    """Obtiene la siguiente serie y número disponible para un tipo de documento"""
    # Buscar la última serie y número para este tipo de documento
    last_doc = db.query(ARDocument).filter(
        ARDocument.DocumentType == document_type
    ).order_by(desc(ARDocument.DocumentNo.cast(Integer))).first()
    
    if last_doc and last_doc.DocumentSerie:
        serie = last_doc.DocumentSerie
        try:
            last_num = int(last_doc.DocumentNo)
            next_num = last_num + 1
        except (ValueError, TypeError):
            next_num = 1
    else:
        # Si no hay documentos, usar valores por defecto
        if "FACTURA" in document_type.upper():
            serie = "F001"
        elif "BOLETA" in document_type.upper():
            serie = "B001"
        else:
            serie = "T001"
        next_num = 1
    
    return serie, str(next_num).zfill(8)

def excel_date_now():
    """Convierte la fecha actual a formato Excel (número de días desde 1899-12-30)"""
    from datetime import datetime
    excel_epoch = datetime(1899, 12, 30)
    current_date = now_peru()
    # Convertir a naive datetime para evitar error de timezone
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

def create_documento_correcto(db: Session):
    """Crea un documento correcto"""
    print("Creando documento CORRECTO...")
    
    serie, numero = get_next_serie_numero(db, "LIMADSAS FACTURA")
    document_id = f"{serie}-{numero}"
    
    # Crear cabecera del documento
    documento = ARDocument(
        Document=document_id,
        DocumentNo=numero,
        DocumentSerie=serie,
        Company="LIMADSAS",
        Vendor="V001",
        VendorName="CLIENTE CORRECTO SAC",
        VendorRUC="20123456789",
        VendorAddress="Av. Principal 123, Lima",
        VendorTelephone="555-1234",
        DocumentType="LIMADSAS FACTURA",
        DocumentDate=excel_date_now(),
        Period="202604",
        FlagSaleType="1",
        FlagDetail="1",
        Situation="1",
        BUResponsible="ADMIN",
        EMResponsible="ADMIN",
        RegisterDate=excel_date_now(),
        RegisterUser="SCRIPT",
        DueDate=excel_date_now() + 30,
        DocumentCurrency="LO",
        ExchangeRate=1.0,
        AmountNetLo=1000.0,
        AmountNetEx=0.0,
        AmountTaxLo=180.0,
        AmountTaxEx=0.0,
        AmountTotalLo=1180.0,
        AmountTotalEx=0.0,
        PaymentStatus="1",
        Status="1",
        FlagCustomerType="1",
        fe="",  # Pendiente de envío
        v_anticipo="NO",
        juntos="NO",
        condition="1",
        d_cod="01",
        d_tasa=18.0,
        tasa_icbper=0.0,
        v_ave="NO",
        typeDocSun="01",
        XLastUser="SCRIPT",
        XLastDate=excel_date_now()
    )
    
    db.add(documento)
    db.flush()  # Para obtener el ID del documento
    
    # Crear detalles del documento
    detalles = [
        ARDocumentDetail(
            Document=document_id,
            Line=1,
            ItemCode="PROD001",
            Description="PRODUCTO DE PRUEBA CORRECTO",
            Unit="NIU",
            Quantity=10.0,
            Price=100.0,
            PriceLo=100.0,
            PriceTax=18.0,
            PriceTaxLo=18.0,
            AmountImponibleLo=1000.0,
            AmountNetLo=1000.0,
            Tax1="IGV",
            Tax1Code="VAT",
            Tax1Rate=18.0,
            Tax1Lo=180.0,
            TotalTaxLo=180.0,
            Total=1180.0,
            TotalLo=1180.0,
            Company="LIMADSAS",
            Period="202604",
            tasa_icbper=0.0,
            inafecto="NO",
            r_chul="NO",
            XLastUser="SCRIPT",
            XLastDate=excel_date_now()
        )
    ]
    
    for detalle in detalles:
        db.add(detalle)
    
    print(f"Documento CORRECTO creado: {document_id}")
    return document_id

def create_documento_error(db: Session):
    """Crea un documento con error (RUC inválido)"""
    print("Creando documento CON ERROR...")
    
    serie, numero = get_next_serie_numero(db, "LIMADSAS FACTURA")
    document_id = f"{serie}-{numero}"
    
    # Crear cabecera del documento con RUC inválido (demasiado corto)
    documento = ARDocument(
        Document=document_id,
        DocumentNo=numero,
        DocumentSerie=serie,
        Company="LIMADSAS",
        Vendor="V002",
        VendorName="CLIENTE CON ERROR SAC",  # Cliente con RUC inválido
        VendorRUC="123456789",  # RUC inválido (solo 9 dígitos)
        VendorAddress="Av. Error 456, Lima",
        VendorTelephone="555-5678",
        DocumentType="LIMADSAS FACTURA",
        DocumentDate=excel_date_now(),
        Period="202604",
        FlagSaleType="1",
        FlagDetail="1",
        Situation="1",
        BUResponsible="ADMIN",
        EMResponsible="ADMIN",
        RegisterDate=excel_date_now(),
        RegisterUser="SCRIPT",
        DueDate=excel_date_now() + 30,
        DocumentCurrency="LO",
        ExchangeRate=1.0,
        AmountNetLo=500.0,
        AmountNetEx=0.0,
        AmountTaxLo=90.0,
        AmountTaxEx=0.0,
        AmountTotalLo=590.0,
        AmountTotalEx=0.0,
        PaymentStatus="1",
        Status="1",
        FlagCustomerType="1",
        fe="",  # Pendiente de envío
        v_anticipo="NO",
        juntos="NO",
        condition="1",
        d_cod="01",
        d_tasa=18.0,
        tasa_icbper=0.0,
        v_ave="NO",
        typeDocSun="01",
        XLastUser="SCRIPT",
        XLastDate=excel_date_now()
    )
    
    db.add(documento)
    db.flush()  # Para obtener el ID del documento
    
    # Crear detalles del documento
    detalles = [
        ARDocumentDetail(
            Document=document_id,
            Line=1,
            ItemCode="PROD002",
            Description="PRODUCTO CON ERROR DE RUC",
            Unit="NIU",
            Quantity=5.0,
            Price=100.0,
            PriceLo=100.0,
            PriceTax=18.0,
            PriceTaxLo=18.0,
            AmountImponibleLo=500.0,
            AmountNetLo=500.0,
            Tax1="IGV",
            Tax1Code="VAT",
            Tax1Rate=18.0,
            Tax1Lo=90.0,
            TotalTaxLo=90.0,
            Total=590.0,
            TotalLo=590.0,
            Company="LIMADSAS",
            Period="202604",
            tasa_icbper=0.0,
            inafecto="NO",
            r_chul="NO",
            XLastUser="SCRIPT",
            XLastDate=excel_date_now()
        )
    ]
    
    for detalle in detalles:
        db.add(detalle)
    
    print(f"Documento CON ERROR creado: {document_id}")
    return document_id

def main():
    """Función principal"""
    print("=== SCRIPT PARA CARGAR DOCUMENTOS DE VENTA DE PRUEBA ===")
    print(f"Fecha y hora actual: {now_peru()}")
    print()
    
    db = SessionLocal()
    try:
        # Mostrar información actual
        print("=== INFORMACIÓN ACTUAL DE LA BASE DE DATOS ===")
        series_info = db.query(
            ARDocument.DocumentSerie,
            func.max(ARDocument.DocumentNo.cast(Integer)).label('max_numero'),
            func.count(ARDocument.Document).label('count')
        ).group_by(ARDocument.DocumentSerie).all()
        
        print("Series existentes:")
        for serie, max_num, count in series_info:
            print(f"  Serie: {serie}, Último número: {max_num}, Total: {count}")
        
        print("\n=== CREANDO DOCUMENTOS DE PRUEBA ===")
        
        # Crear documento correcto
        doc_correcto = create_documento_correcto(db)
        
        # Crear documento con error
        doc_error = create_documento_error(db)
        
        # Confirmar transacción
        db.commit()
        
        print("\n=== RESUMEN ===")
        print(f"✅ Documento CORRECTO creado: {doc_correcto}")
        print(f"❌ Documento con ERROR creado: {doc_error}")
        print("\nAmbos documentos están listos para ser enviados a NubeFact")
        print("El documento con error debería fallar por RUC inválido (123456789)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
    print("\n=== SCRIPT FINALIZADO ===")

if __name__ == "__main__":
    main()
