#!/usr/bin/env python3
"""
Script para crear documentos de prueba automáticamente
- Detecta automáticamente la siguiente serie y número
- Crea un documento correcto basado en documentos aprobados
- Crea un documento con error en RUC
- Indica el RUC correcto para corrección manual
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

def get_next_serie_numero(db: Session):
    """Detecta automáticamente la siguiente serie y número disponible"""
    # Buscar la serie más usada recientemente
    serie_mas_usada = db.query(
        ARDocument.DocumentSerie,
        func.count(ARDocument.Document).label('count')
    ).filter(
        ARDocument.DocumentSerie.isnot(None)
    ).group_by(ARDocument.DocumentSerie).order_by(desc('count')).first()

    if serie_mas_usada:
        serie = serie_mas_usada[0]
    else:
        serie = "FFF1"

    # IMPORTANTE: NubeFact tiene su propio correlativo
    # El último número en NubeFact es 13, así que usar números a partir de 14
    # Buscar números existentes en la base de datos local
    docs_existentes = db.query(ARDocument).filter(
        ARDocument.DocumentSerie == serie,
        ARDocument.DocumentNo.cast(Integer) <= 250  # Rango permitido por NubeFact (13 + 200 = 213)
    ).all()

    numeros_existentes = set()
    for doc in docs_existentes:
        if doc.DocumentNo and doc.DocumentNo.isdigit():
            numeros_existentes.add(int(doc.DocumentNo))

    # Buscar el siguiente número disponible a partir de 14
    # NubeFact dice que el último es 13, así que empezamos desde 14
    for num in range(14, 214):  # 14 al 213 (rango permitido)
        if num not in numeros_existentes:
            return serie, str(num)

    # Si no hay números disponibles en el rango, usar el siguiente al máximo
    return serie, "14"

def get_documento_correcto_template(db: Session):
    """Obtiene un documento aprobado como plantilla"""
    # Buscar documento aprobado con más detalles
    doc_aprobado = db.query(ARDocument).filter(
        ARDocument.fe.in_(['aceptado', 'enviado', 'aceptado_observaciones'])
    ).order_by(desc(ARDocument.RegisterDate)).first()
    
    return doc_aprobado

def excel_date_now():
    """Convierte la fecha actual a formato Excel"""
    from datetime import datetime as dt
    excel_epoch = dt(1899, 12, 30)
    current_date = now_peru()
    current_date_naive = dt(
        current_date.year, 
        current_date.month, 
        current_date.day,
        current_date.hour,
        current_date.minute,
        current_date.second
    )
    delta = current_date_naive - excel_epoch
    return delta.days + delta.seconds / (24 * 3600)

def create_documento_correcto(db: Session, serie: str, numero: str, template: ARDocument):
    """Crea un documento correcto basado en documentos aprobados"""
    print("Creando documento CORRECTO...")
    
    document_id = f"{serie}-{numero}"
    
    # Usar datos del documento aprobado
    documento = ARDocument(
        Document=document_id,
        DocumentNo=numero,
        DocumentSerie=serie,
        Company=template.Company if template else "LIMADSAS",
        Vendor=template.Vendor if template else "V001",
        VendorName=template.VendorName if template else "CLIENTE REAL DE PRUEBA SAC",
        VendorRUC=template.VendorRUC if template else "20600695771",  # RUC correcto
        VendorAddress=template.VendorAddress if template else "Av. Principal 123, Lima",
        VendorTelephone=template.VendorTelephone if template else "555-1234",
        DocumentType=template.DocumentType if template else "LIMADSASFACTURA",
        DocumentDate=excel_date_now(),
        Period="202604",
        FlagSaleType=template.FlagSaleType if template else "1",
        FlagDetail=template.FlagDetail if template else "1",
        Situation=template.Situation if template else 1,
        BUResponsible=template.BUResponsible if template else "ADMIN",
        EMResponsible=template.EMResponsible if template else "ADMIN",
        RegisterDate=excel_date_now(),
        RegisterUser="SCRIPT_AUTO",
        DueDate=excel_date_now() + 30,
        DocumentCurrency=template.DocumentCurrency if template else "LO",
        ExchangeRate=template.ExchangeRate if template else 1.0,
        AmountNetLo=500.0,
        AmountNetEx=0.0,
        AmountTaxLo=90.0,
        AmountTaxEx=0.0,
        AmountTotalLo=590.0,
        AmountTotalEx=0.0,
        PaymentStatus=template.PaymentStatus if template else "1",
        Status=template.Status if template else "1",
        FlagCustomerType=template.FlagCustomerType if template else "1",
        fe="",  # Pendiente de envío
        v_anticipo=template.v_anticipo if template else "NO",
        juntos=template.juntos if template else "NO",
        condition=template.condition if template else "1",
        d_cod=template.d_cod if template else "01",
        d_tasa=template.d_tasa if template else 18.0,
        tasa_icbper=template.tasa_icbper if template else 0.0,
        v_ave=template.v_ave if template else "NO",
        typeDocSun=template.typeDocSun if template else "01",
        XLastUser="SCRIPT_AUTO",
        XLastDate=excel_date_now()
    )
    
    db.add(documento)
    db.flush()
    
    # Crear detalle con cálculos correctos
    cantidad = 5.0
    precio_sin_igv = 100.0
    precio_con_igv = precio_sin_igv * 1.18  # 118.0
    subtotal_sin_igv = cantidad * precio_sin_igv  # 500.0
    total_con_igv = cantidad * precio_con_igv  # 590.0
    igv = subtotal_sin_igv * 0.18  # 90.0
    
    detalle = ARDocumentDetail(
        Document=document_id,
        Line=1,
        ItemCode="SERV001",
        Description="Servicio de consultoría",
        Unit="ZZ",
        Quantity=cantidad,
        Price=precio_sin_igv,  # 100.0
        PriceLo=precio_sin_igv,  # 100.0
        PriceTax=precio_con_igv,  # 118.0
        PriceTaxLo=precio_con_igv,  # 118.0
        SubTotal=subtotal_sin_igv,  # 500.0
        AmountImponibleLo=subtotal_sin_igv,  # 500.0
        AmountNetLo=subtotal_sin_igv,  # 500.0
        Tax1="IGV",
        Tax1Code="VAT",
        Tax1Rate=18.0,
        Tax1Lo=igv,  # 90.0
        TotalTaxLo=igv,  # 90.0
        Total=total_con_igv,  # 590.0
        TotalLo=total_con_igv,  # 590.0
        Company=template.Company if template else "LIMADSAS",
        Period="202604",
        tasa_icbper=0.0,
        inafecto="NO",
        r_chul="NO",
        XLastUser="SCRIPT_AUTO",
        XLastDate=excel_date_now()
    )
    
    db.add(detalle)
    
    print(f"  Documento creado: {document_id}")
    print(f"  RUC: {documento.VendorRUC} (válido)")
    print(f"  Cliente: {documento.VendorName}")
    print(f"  Monto: S/ {documento.AmountTotalLo}")
    
    return document_id, documento.VendorRUC

def create_documento_error_ruc(db: Session, serie: str, numero: str, template: ARDocument):
    """Crea un documento con error en RUC"""
    print("\nCreando documento CON ERROR EN RUC...")
    
    document_id = f"{serie}-{numero}"
    
    # RUC con error (cambiar último dígito)
    ruc_correcto = template.VendorRUC if template else "20600695771"
    ruc_error = ruc_correcto[:-1] + "0"  # Cambiar último dígito a 0
    
    documento = ARDocument(
        Document=document_id,
        DocumentNo=numero,
        DocumentSerie=serie,
        Company=template.Company if template else "LIMADSAS",
        Vendor=template.Vendor if template else "V001",
        VendorName=template.VendorName if template else "CLIENTE REAL DE PRUEBA SAC",
        VendorRUC=ruc_error,  # RUC con error
        VendorAddress=template.VendorAddress if template else "Av. Principal 123, Lima",
        VendorTelephone=template.VendorTelephone if template else "555-1234",
        DocumentType=template.DocumentType if template else "LIMADSASFACTURA",
        DocumentDate=excel_date_now(),
        Period="202604",
        FlagSaleType=template.FlagSaleType if template else "1",
        FlagDetail=template.FlagDetail if template else "1",
        Situation=template.Situation if template else 1,
        BUResponsible=template.BUResponsible if template else "ADMIN",
        EMResponsible=template.EMResponsible if template else "ADMIN",
        RegisterDate=excel_date_now(),
        RegisterUser="SCRIPT_AUTO",
        DueDate=excel_date_now() + 30,
        DocumentCurrency=template.DocumentCurrency if template else "LO",
        ExchangeRate=template.ExchangeRate if template else 1.0,
        AmountNetLo=300.0,
        AmountNetEx=0.0,
        AmountTaxLo=54.0,
        AmountTaxEx=0.0,
        AmountTotalLo=354.0,
        AmountTotalEx=0.0,
        PaymentStatus=template.PaymentStatus if template else "1",
        Status=template.Status if template else "1",
        FlagCustomerType=template.FlagCustomerType if template else "1",
        fe="",  # Pendiente de envío
        v_anticipo=template.v_anticipo if template else "NO",
        juntos=template.juntos if template else "NO",
        condition=template.condition if template else "1",
        d_cod=template.d_cod if template else "01",
        d_tasa=template.d_tasa if template else 18.0,
        tasa_icbper=template.tasa_icbper if template else 0.0,
        v_ave=template.v_ave if template else "NO",
        typeDocSun=template.typeDocSun if template else "01",
        XLastUser="SCRIPT_AUTO",
        XLastDate=excel_date_now()
    )
    
    db.add(documento)
    db.flush()
    
    # Crear detalle con cálculos correctos
    cantidad = 3.0
    precio_sin_igv = 100.0
    precio_con_igv = precio_sin_igv * 1.18  # 118.0
    subtotal_sin_igv = cantidad * precio_sin_igv  # 300.0
    total_con_igv = cantidad * precio_con_igv  # 354.0
    igv = subtotal_sin_igv * 0.18  # 54.0
    
    detalle = ARDocumentDetail(
        Document=document_id,
        Line=1,
        ItemCode="SERV002",
        Description="Servicio de soporte técnico",
        Unit="ZZ",
        Quantity=cantidad,
        Price=precio_sin_igv,  # 100.0
        PriceLo=precio_sin_igv,  # 100.0
        PriceTax=precio_con_igv,  # 118.0
        PriceTaxLo=precio_con_igv,  # 118.0
        SubTotal=subtotal_sin_igv,  # 300.0
        AmountImponibleLo=subtotal_sin_igv,  # 300.0
        AmountNetLo=subtotal_sin_igv,  # 300.0
        Tax1="IGV",
        Tax1Code="VAT",
        Tax1Rate=18.0,
        Tax1Lo=igv,  # 54.0
        TotalTaxLo=igv,  # 54.0
        Total=total_con_igv,  # 354.0
        TotalLo=total_con_igv,  # 354.0
        Company=template.Company if template else "LIMADSAS",
        Period="202604",
        tasa_icbper=0.0,
        inafecto="NO",
        r_chul="NO",
        XLastUser="SCRIPT_AUTO",
        XLastDate=excel_date_now()
    )
    
    db.add(detalle)
    
    print(f"  Documento creado: {document_id}")
    print(f"  RUC INCORRECTO: {ruc_error} (último dígito cambiado)")
    print(f"  Cliente: {documento.VendorName}")
    print(f"  Monto: S/ {documento.AmountTotalLo}")
    
    return document_id, ruc_error, ruc_correcto

def main():
    """Función principal"""
    print("=" * 70)
    print("SCRIPT AUTOMÁTICO PARA CREAR DOCUMENTOS DE PRUEBA")
    print("=" * 70)
    print(f"Fecha y hora: {now_peru()}")
    print()
    
    db = SessionLocal()
    try:
        # Obtener plantilla de documento aprobado
        print("Buscando documento aprobado como plantilla...")
        template = get_documento_correcto_template(db)
        
        if template:
            print(f"  Plantilla encontrada: {template.Document}")
            print(f"  Cliente: {template.VendorName}")
            print(f"  RUC: {template.VendorRUC}")
        else:
            print("  No se encontraron documentos aprobados, usando valores por defecto")
        
        print()
        
        # Detectar siguiente serie y número
        print("Detectando siguiente serie y número...")
        serie1, numero1 = get_next_serie_numero(db)
        print(f"  Serie detectada: {serie1}")
        print(f"  Primer número: {numero1}")
        
        # El segundo número es el siguiente al primero
        numero2 = str(int(numero1) + 1)
        print(f"  Segundo número: {numero2}")
        print()
        
        # Crear documentos
        print("=" * 70)
        print("CREANDO DOCUMENTOS")
        print("=" * 70)
        
        # Documento correcto
        doc_correcto_id, ruc_correcto = create_documento_correcto(db, serie1, numero1, template)
        
        # Documento con error
        doc_error_id, ruc_error, ruc_a_corregir = create_documento_error_ruc(db, serie1, numero2, template)
        
        # Confirmar transacción
        db.commit()
        
        # Mostrar resumen
        print()
        print("=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print()
        print("DOCUMENTO CORRECTO:")
        print(f"  ID: {doc_correcto_id}")
        print(f"  RUC: {ruc_correcto} (válido)")
        print(f"  Estado: Listo para enviar a NubeFact")
        print()
        print("DOCUMENTO CON ERROR:")
        print(f"  ID: {doc_error_id}")
        print(f"  RUC INCORRECTO: {ruc_error}")
        print(f"  RUC CORRECTO A CORREGIR: {ruc_a_corregir}")
        print()
        print("INSTRUCCIONES:")
        print("  1. Envía ambos documentos a NubeFact desde la interfaz")
        print("  2. El documento correcto debería enviarse exitosamente")
        print("  3. El documento con error fallará por RUC inválido")
        print(f"  4. Corrige el RUC en la interfaz de {ruc_error} a {ruc_a_corregir}")
        print("  5. Vuelve a enviar el documento corregido")
        print()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()
    
    print("=" * 70)
    print("SCRIPT FINALIZADO")
    print("=" * 70)

if __name__ == "__main__":
    main()
