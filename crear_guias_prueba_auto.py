#!/usr/bin/env python3
"""
Script para crear guías de remisión de prueba automáticamente
- Detecta automáticamente la siguiente serie y número
- Crea una guía correcta basada en guías enviadas
- Crea una guía con error en RUC del destinatario
- Indica el RUC correcto para corrección manual
"""

import sys
import os
from datetime import datetime

# Agregar el directorio actual al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import Integer, desc, func
from app.database import SessionLocal
from app.models.guias import WHTransaction, WHTransactionDetail
from app.utils.datetime import now_peru

def get_next_serie_numero_guia(db: Session):
    """Detecta automáticamente la siguiente serie y número disponible para guías"""
    # Buscar la serie más usada
    serie_mas_usada = db.query(
        WHTransaction.DocumentSerie,
        func.count(WHTransaction.Transaction).label('count')
    ).filter(
        WHTransaction.DocumentSerie.isnot(None)
    ).group_by(WHTransaction.DocumentSerie).order_by(desc('count')).first()

    if serie_mas_usada:
        serie = serie_mas_usada[0]
    else:
        serie = "T001"

    # Buscar números existentes en la serie
    docs_existentes = db.query(WHTransaction).filter(
        WHTransaction.DocumentSerie == serie,
        WHTransaction.DocumentNo.isnot(None)
    ).all()

    numeros_existentes = set()
    for doc in docs_existentes:
        if doc.DocumentNo and doc.DocumentNo.isdigit():
            numeros_existentes.add(int(doc.DocumentNo))

    # Buscar el siguiente número disponible a partir de 1
    for num in range(1, 1000):
        if num not in numeros_existentes:
            return serie, str(num).zfill(8)

    return serie, "00000001"

def get_guia_template(db: Session):
    """Obtiene una guía enviada como plantilla"""
    # Buscar guía enviada exitosamente
    guia_enviada = db.query(WHTransaction).filter(
        WHTransaction.envio_nube.in_(['enviado', 'aceptado', 'aceptado_observaciones'])
    ).order_by(desc(WHTransaction.TransactionDate)).first()

    return guia_enviada

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

def create_guia_correcta(db: Session, serie: str, numero: str, template: WHTransaction):
    """Crea una guía correcta"""
    print("Creando guía CORRECTA...")

    transaction_id = f"GUIA_AUTO_{now_peru().strftime('%Y%m%d%H%M%S')}_CORRECTA"

    # Crear cabecera de la guía
    guia = WHTransaction(
        Transaction=transaction_id,
        Company=template.Company if template else None,
        WareHouse=template.WareHouse if template else "ALMACEN001",
        Application=template.Application if template else "VENTAS",
        TransactionType=template.TransactionType if template else "GUIA_REMISION",
        DocumentType=template.DocumentType if template else "GUIA",
        DocumentSerie=serie,
        DocumentNo=numero,
        TransactionDate=excel_date_now(),
        TransactionCurrency=template.TransactionCurrency if template else "PEN",
        ServiceType=template.ServiceType if template else None,
        Period=now_peru().strftime('%Y%m'),
        ExchangeRate=template.ExchangeRate if template else 1.0,
        FechaTraslado=excel_date_now(),
        MotivoTraslado=template.MotivoTraslado if template else "VENTA",
        WareHouseTarget=template.WareHouseTarget if template else "ALMACEN002",
        TargetType=template.TargetType if template else "CLIENTE",
        TargetAddress=template.TargetAddress if template else "Av. Destino 456, Lima",
        TargetPerson=template.TargetPerson if template else None,
        TargetPersonRUC=template.TargetPersonRUC if template else "20123456789",  # RUC correcto
        TargetPersonName=template.TargetPersonName if template else "EMPRESA DESTINO S.A.C.",
        Driver=template.Driver if template else "Juan Pérez García",
        LicenciaConducir=template.LicenciaConducir if template else "A12345678",
        VehicleID=template.VehicleID if template else "ABC-123",
        Transportista=template.Transportista if template else "TRANSPORTES RÁPIDOS S.A.C.",
        RucTransportista=template.RucTransportista if template else "20602674488",
        AddressTransportista=template.AddressTransportista if template else "Av. Transporte 789, Lima",
        PesoBruto=template.PesoBruto if template else 150.0,
        origenaddress=template.origenaddress if template else "Almacén Central - Av. Industrial 100, Lima",
        ubigeo_des=template.ubigeo_des if template else "150101",
        envio_nube="",  # Pendiente de envío
        Status="1",
        XLastUser="SCRIPT_AUTO",
        XLastDate=excel_date_now(),
        RegisterUser="SCRIPT_AUTO"
    )

    db.add(guia)
    db.flush()

    # Crear detalles de la guía con números de línea únicos
    # Usar timestamp para garantizar unicidad
    import time
    line_base = int(time.time() * 1000) % 100000  # Número base único

    detalles = [
        WHTransactionDetail(
            Line=line_base,
            Transaction=transaction_id,
            ItemCode="ITEM-001",
            ItemDescription="Producto de prueba A",
            Unit="NIU",
            Quantity=20.0,
            QuantityBultos=20.0,
            Warehouse=template.WareHouse if template else "ALMACEN001",
            Company=template.Company if template else None,
            XLastUser="SCRIPT_AUTO",
            XLastDate=excel_date_now()
        ),
        WHTransactionDetail(
            Line=line_base + 1,
            Transaction=transaction_id,
            ItemCode="ITEM-002",
            ItemDescription="Producto de prueba B",
            Unit="NIU",
            Quantity=30.0,
            QuantityBultos=30.0,
            Warehouse=template.WareHouse if template else "ALMACEN001",
            Company=template.Company if template else None,
            XLastUser="SCRIPT_AUTO",
            XLastDate=excel_date_now()
        )
    ]

    for detalle in detalles:
        db.add(detalle)

    print(f"  Guía creada: {serie}-{numero}")
    print(f"  Transaction ID: {transaction_id}")
    print(f"  RUC Destinatario: {guia.TargetPersonRUC} (válido)")
    print(f"  Destinatario: {guia.TargetPersonName}")
    print(f"  Motivo: {guia.MotivoTraslado}")
    print(f"  Peso Bruto: {guia.PesoBruto} kg")

    return transaction_id, guia.TargetPersonRUC

def create_guia_error_ruc(db: Session, serie: str, numero: str, template: WHTransaction):
    """Crea una guía con error en RUC del destinatario"""
    print("\nCreando guía CON ERROR EN RUC...")

    transaction_id = f"GUIA_AUTO_{now_peru().strftime('%Y%m%d%H%M%S')}_ERROR"

    # RUC con error (cambiar último dígito)
    ruc_correcto = template.TargetPersonRUC if template else "20123456789"
    ruc_error = ruc_correcto[:-1] + "0"  # Cambiar último dígito a 0

    # Crear cabecera de la guía
    guia = WHTransaction(
        Transaction=transaction_id,
        Company=template.Company if template else None,
        WareHouse=template.WareHouse if template else "ALMACEN001",
        Application=template.Application if template else "VENTAS",
        TransactionType=template.TransactionType if template else "GUIA_REMISION",
        DocumentType=template.DocumentType if template else "GUIA",
        DocumentSerie=serie,
        DocumentNo=numero,
        TransactionDate=excel_date_now(),
        TransactionCurrency=template.TransactionCurrency if template else "PEN",
        ServiceType=template.ServiceType if template else None,
        Period=now_peru().strftime('%Y%m'),
        ExchangeRate=template.ExchangeRate if template else 1.0,
        FechaTraslado=excel_date_now(),
        MotivoTraslado=template.MotivoTraslado if template else "VENTA",
        WareHouseTarget=template.WareHouseTarget if template else "ALMACEN002",
        TargetType=template.TargetType if template else "CLIENTE",
        TargetAddress=template.TargetAddress if template else "Av. Destino 456, Lima",
        TargetPerson=template.TargetPerson if template else None,
        TargetPersonRUC=ruc_error,  # RUC con error
        TargetPersonName=template.TargetPersonName if template else "EMPRESA DESTINO S.A.C.",
        Driver=template.Driver if template else "Juan Pérez García",
        LicenciaConducir=template.LicenciaConducir if template else "A12345678",
        VehicleID=template.VehicleID if template else "ABC-123",
        Transportista=template.Transportista if template else "TRANSPORTES RÁPIDOS S.A.C.",
        RucTransportista=template.RucTransportista if template else "20602674488",
        AddressTransportista=template.AddressTransportista if template else "Av. Transporte 789, Lima",
        PesoBruto=template.PesoBruto if template else 100.0,
        origenaddress=template.origenaddress if template else "Almacén Central - Av. Industrial 100, Lima",
        ubigeo_des=template.ubigeo_des if template else "150101",
        envio_nube="",  # Pendiente de envío
        Status="1",
        XLastUser="SCRIPT_AUTO",
        XLastDate=excel_date_now(),
        RegisterUser="SCRIPT_AUTO"
    )

    db.add(guia)
    db.flush()

    # Crear detalles de la guía con número de línea único
    import time
    line_base = int(time.time() * 1000) % 100000  # Número base único

    detalle = WHTransactionDetail(
        Line=line_base + 2,  # +2 para evitar colisión con la guía correcta
        Transaction=transaction_id,
        ItemCode="ITEM-003",
        ItemDescription="Producto con error de RUC",
        Unit="NIU",
        Quantity=10.0,
        QuantityBultos=10.0,
        Warehouse=template.WareHouse if template else "ALMACEN001",
        Company=template.Company if template else None,
        XLastUser="SCRIPT_AUTO",
        XLastDate=excel_date_now()
    )

    db.add(detalle)

    print(f"  Guía creada: {serie}-{numero}")
    print(f"  Transaction ID: {transaction_id}")
    print(f"  RUC INCORRECTO: {ruc_error} (último dígito cambiado)")
    print(f"  Destinatario: {guia.TargetPersonName}")
    print(f"  Motivo: {guia.MotivoTraslado}")
    print(f"  Peso Bruto: {guia.PesoBruto} kg")

    return transaction_id, ruc_error, ruc_correcto

def main():
    """Función principal"""
    print("=" * 70)
    print("SCRIPT AUTOMÁTICO PARA CREAR GUÍAS DE REMISIÓN DE PRUEBA")
    print("=" * 70)
    print(f"Fecha y hora: {now_peru()}")
    print()

    db = SessionLocal()
    try:
        # Obtener plantilla de guía enviada
        print("Buscando guía enviada como plantilla...")
        template = get_guia_template(db)

        if template:
            print(f"  Plantilla encontrada: {template.Transaction}")
            print(f"  Serie: {template.DocumentSerie}, Número: {template.DocumentNo}")
            print(f"  Destinatario: {template.TargetPersonName}")
            print(f"  RUC: {template.TargetPersonRUC}")
        else:
            print("  No se encontraron guías enviadas, usando valores por defecto")

        print()

        # Detectar siguiente serie y número
        print("Detectando siguiente serie y número...")
        serie1, numero1 = get_next_serie_numero_guia(db)
        print(f"  Serie detectada: {serie1}")
        print(f"  Primer número: {numero1}")

        # El segundo número es el siguiente al primero
        numero2 = str(int(numero1) + 1).zfill(8)
        print(f"  Segundo número: {numero2}")
        print()

        # Crear guías
        print("=" * 70)
        print("CREANDO GUÍAS")
        print("=" * 70)

        # Guía correcta
        guia_correcta_id, ruc_correcto = create_guia_correcta(db, serie1, numero1, template)

        # Guía con error
        guia_error_id, ruc_error, ruc_a_corregir = create_guia_error_ruc(db, serie1, numero2, template)

        # Confirmar transacción
        db.commit()

        # Mostrar resumen
        print()
        print("=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print()
        print("GUÍA CORRECTA:")
        print(f"  Transaction ID: {guia_correcta_id}")
        print(f"  Serie-Número: {serie1}-{numero1}")
        print(f"  RUC Destinatario: {ruc_correcto} (válido)")
        print(f"  Estado: Lista para enviar a NubeFact")
        print()
        print("GUÍA CON ERROR:")
        print(f"  Transaction ID: {guia_error_id}")
        print(f"  Serie-Número: {serie1}-{numero2}")
        print(f"  RUC INCORRECTO: {ruc_error}")
        print(f"  RUC CORRECTO A CORREGIR: {ruc_a_corregir}")
        print()
        print("INSTRUCCIONES:")
        print("  1. Envía ambas guías a NubeFact desde la interfaz")
        print("  2. La guía correcta debería enviarse exitosamente")
        print("  3. La guía con error fallará por RUC inválido")
        print(f"  4. Corrige el RUC en la interfaz de {ruc_error} a {ruc_a_corregir}")
        print("  5. Vuelve a enviar la guía corregida")
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
