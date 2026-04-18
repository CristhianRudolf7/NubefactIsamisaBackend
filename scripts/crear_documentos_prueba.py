"""
Script para crear documentos de prueba:
- Un documento correcto (pendiente de envío)
- Un documento con RUC inválido (pendiente de envío)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.ventas import ARDocument, ARDocumentDetail
from app.models.retenciones import APRetencion, APRetencionDetail


def crear_ventas_prueba(db: Session):
    """Crea dos documentos de venta de prueba basados en uno enviado"""
    
    # Buscar un documento enviado para usar como plantilla
    documento_aceptado = db.query(ARDocument).filter(
        ARDocument.fe == 'enviado'
    ).first()
    
    if not documento_aceptado:
        print("No se encontró un documento enviado para usar como plantilla")
        return
    
    print(f"Usando como plantilla: {documento_aceptado.DocumentSerie}-{documento_aceptado.DocumentNo}")
    
    # Obtener el último número de serie para crear nuevos documentos
    ultimo_doc = db.query(ARDocument).filter(
        ARDocument.DocumentSerie == documento_aceptado.DocumentSerie
    ).order_by(ARDocument.DocumentNo.desc()).first()
    
    ultimo_numero = int(ultimo_doc.DocumentNo) if ultimo_doc else 0
    
    # Fecha actual en formato Excel (días desde 1899-12-30)
    fecha_excel = (datetime.now() - datetime(1899, 12, 30)).days
    timestamp = datetime.now().timestamp()
    
    # === DOCUMENTO 1: CORRECTO ===
    nuevo_numero_1 = str(ultimo_numero + 1).zfill(len(ultimo_doc.DocumentNo))
    doc_correcto_id = f"{documento_aceptado.DocumentType}_{documento_aceptado.DocumentSerie}_{nuevo_numero_1}"
    
    doc_correcto = ARDocument(
        Document=doc_correcto_id,
        DocumentNo=nuevo_numero_1,
        DocumentSerie=documento_aceptado.DocumentSerie,
        DocumentType=documento_aceptado.DocumentType,
        Company=documento_aceptado.Company,
        Vendor=documento_aceptado.Vendor,
        VendorName="CLIENTE PRUEBA CORRECTO",
        VendorRUC="20123456789",  # RUC válido de prueba
        VendorAddress="Av. Prueba 123, Lima",
        VendorEmail="cliente@test.com",
        DocumentDate=fecha_excel,
        DueDate=fecha_excel + 30,
        DocumentCurrency="PEN",
        ExchangeRate=1.0,
        AmountNetLo=100.00,
        AmountTaxLo=18.00,
        AmountTotalLo=118.00,
        AmountNoImponibleLo=0,
        PlazoDias=30,
        FlagSaleType="1",
        fe="pendiente",  # Pendiente de envío
        Status=None,
        XLastUser="SCRIPT_PRUEBA",
        XLastDate=timestamp,
    )
    db.add(doc_correcto)
    db.flush()  # Para obtener el ID
    
    # Agregar detalle al documento correcto
    detalle_correcto = ARDocumentDetail(
        Document=doc_correcto_id,
        Line=1,
        ItemCode="ITEM001",
        Description="Producto de prueba correcto",
        Unit="NIU",
        Quantity=1,
        Price=100.00,
        PriceTax=118.00,
        SubTotal=100.00,
        TotalTaxLo=18.00,
        Total=118.00,
        XLastUser="SCRIPT_PRUEBA",
        XLastDate=timestamp,
    )
    db.add(detalle_correcto)
    
    # === DOCUMENTO 2: CON RUC INVÁLIDO ===
    nuevo_numero_2 = str(ultimo_numero + 2).zfill(len(ultimo_doc.DocumentNo))
    doc_error_id = f"{documento_aceptado.DocumentType}_{documento_aceptado.DocumentSerie}_{nuevo_numero_2}"
    
    doc_error = ARDocument(
        Document=doc_error_id,
        DocumentNo=nuevo_numero_2,
        DocumentSerie=documento_aceptado.DocumentSerie,
        DocumentType=documento_aceptado.DocumentType,
        Company=documento_aceptado.Company,
        Vendor=documento_aceptado.Vendor,
        VendorName="CLIENTE PRUEBA ERROR RUC",
        VendorRUC="12345678",  # RUC inválido (muy corto)
        VendorAddress="Av. Error 456, Lima",
        VendorEmail="error@test.com",
        DocumentDate=fecha_excel,
        DueDate=fecha_excel + 30,
        DocumentCurrency="PEN",
        ExchangeRate=1.0,
        AmountNetLo=200.00,
        AmountTaxLo=36.00,
        AmountTotalLo=236.00,
        AmountNoImponibleLo=0,
        PlazoDias=30,
        FlagSaleType="1",
        fe="pendiente",  # Pendiente de envío
        Status=None,
        XLastUser="SCRIPT_PRUEBA",
        XLastDate=timestamp,
    )
    db.add(doc_error)
    
    # Agregar detalle al documento con error
    detalle_error = ARDocumentDetail(
        Document=doc_error_id,
        Line=1,
        ItemCode="ITEM002",
        Description="Producto de prueba con error RUC",
        Unit="NIU",
        Quantity=2,
        Price=100.00,
        PriceTax=118.00,
        SubTotal=200.00,
        TotalTaxLo=36.00,
        Total=236.00,
        XLastUser="SCRIPT_PRUEBA",
        XLastDate=timestamp,
    )
    db.add(detalle_error)
    
    db.commit()
    
    print("\n=== DOCUMENTOS CREADOS ===")
    print(f"1. Documento CORRECTO: {documento_aceptado.DocumentSerie}-{nuevo_numero_1}")
    print(f"   RUC: 20123456789 (válido)")
    print(f"   Estado: pendiente")
    print(f"\n2. Documento con ERROR: {documento_aceptado.DocumentSerie}-{nuevo_numero_2}")
    print(f"   RUC: 12345678 (inválido - muy corto)")
    print(f"   Estado: pendiente")


def crear_retenciones_prueba(db: Session):
    """Crea dos retenciones de prueba basadas en una enviada"""
    
    # Buscar cualquier retención para usar como plantilla
    retencion_aceptada = db.query(APRetencion).first()
    
    if not retencion_aceptada:
        print("No se encontró ninguna retención para usar como plantilla")
        return
    
    print(f"\nUsando como plantilla retención: {retencion_aceptada.Serie}-{retencion_aceptada.Numero}")
    
    # Obtener el último número
    ultima_ret = db.query(APRetencion).filter(
        APRetencion.Serie == retencion_aceptada.Serie
    ).order_by(APRetencion.Numero.desc()).first()
    
    ultimo_numero = int(ultima_ret.Numero) if ultima_ret else 0
    
    # Fecha actual en formato Excel
    fecha_excel = (datetime.now() - datetime(1899, 12, 30)).days
    timestamp = datetime.now().timestamp()
    
    # === RETENCIÓN 1: CORRECTA ===
    nuevo_numero_1 = str(ultimo_numero + 1).zfill(len(ultima_ret.Numero))
    
    ret_correcta = APRetencion(
        Serie=retencion_aceptada.Serie,
        Numero=nuevo_numero_1,
        Vendor=retencion_aceptada.Vendor,
        VendorRuc="20123456789",  # RUC válido
        VendorName="PROVEEDOR PRUEBA CORRECTO",
        VendorAddress="Av. Proveedor 123, Lima",
        DocumentDate=fecha_excel,
        Tasa=3,
        TotalRetenido=30.00,
        TotalPagado=970.00,
        Obs="Retención de prueba correcta",
        XlastUser="SCRIPT_PRUEBA",
        XlastDate=timestamp,
        status="pendiente",  # Pendiente de envío
    )
    db.add(ret_correcta)
    db.flush()
    
    # Detalle de retención correcta
    det_correcta = APRetencionDetail(
        Retencion=ret_correcta.Id,
        DRserie="F001",
        DRnumero="00001",
        DRfecha=fecha_excel,
        DRmoneda="PEN",
        DRtotal=1000.00,
        DRpagoFecha=fecha_excel,
        Retenido=30.00,
        Pagado=970.00,
    )
    db.add(det_correcta)
    
    # === RETENCIÓN 2: CON RUC INVÁLIDO ===
    nuevo_numero_2 = str(ultimo_numero + 2).zfill(len(ultima_ret.Numero))
    
    ret_error = APRetencion(
        Serie=retencion_aceptada.Serie,
        Numero=nuevo_numero_2,
        Vendor=retencion_aceptada.Vendor,
        VendorRuc="12345678",  # RUC inválido
        VendorName="PROVEEDOR PRUEBA ERROR RUC",
        VendorAddress="Av. Error 456, Lima",
        DocumentDate=fecha_excel,
        Tasa=3,
        TotalRetenido=60.00,
        TotalPagado=1940.00,
        Obs="Retención de prueba con error RUC",
        XlastUser="SCRIPT_PRUEBA",
        XlastDate=timestamp,
        status="pendiente",  # Pendiente de envío
    )
    db.add(ret_error)
    db.flush()
    
    # Detalle de retención con error
    det_error = APRetencionDetail(
        Retencion=ret_error.Id,
        DRserie="F001",
        DRnumero="00002",
        DRfecha=fecha_excel,
        DRmoneda="PEN",
        DRtotal=2000.00,
        DRpagoFecha=fecha_excel,
        Retenido=60.00,
        Pagado=1940.00,
    )
    db.add(det_error)
    
    db.commit()
    
    print("\n=== RETENCIONES CREADAS ===")
    print(f"1. Retención CORRECTA: {retencion_aceptada.Serie}-{nuevo_numero_1}")
    print(f"   RUC: 20123456789 (válido)")
    print(f"   Estado: pendiente")
    print(f"\n2. Retención con ERROR: {retencion_aceptada.Serie}-{nuevo_numero_2}")
    print(f"   RUC: 12345678 (inválido - muy corto)")
    print(f"   Estado: pendiente")


def main():
    db = SessionLocal()
    try:
        print("=== CREANDO DOCUMENTOS DE PRUEBA ===\n")
        
        # Mostrar documentos existentes
        ventas_enviadas = db.query(ARDocument).filter(ARDocument.fe == 'enviado').count()
        retenciones_total = db.query(APRetencion).count()
        
        print(f"Documentos de venta enviados: {ventas_enviadas}")
        print(f"Retenciones existentes: {retenciones_total}")
        
        if ventas_enviadas > 0:
            crear_ventas_prueba(db)
        
        if retenciones_total > 0:
            crear_retenciones_prueba(db)
        
        print("\n=== PROCESO COMPLETADO ===")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
