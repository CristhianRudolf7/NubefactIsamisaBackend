import sys
import os
from datetime import datetime

# Añadir el directorio raíz al path para poder importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.ventas import ARDocument, ARDocumentDetail
from app.models.nube_response import ARFENube

def create_samples():
    db = SessionLocal()
    try:
        now = datetime.now().timestamp()
        
        # Tipos de documentos
        # 01: Factura, 03: Boleta, 07: Nota de Crédito, 08: Nota de Débito
        docs_to_create = [
            # Facturas
            {"type": "01", "serie": "F999", "num": "000001", "fe": "aceptado", "msg": "Aceptado por SUNAT"},
            {"type": "01", "serie": "F999", "num": "000002", "fe": "error", "msg": "Error en RUC del cliente", "err": "El RUC proporcionado no es válido"},
            
            # Boletas
            {"type": "03", "serie": "B999", "num": "000001", "fe": "aceptado", "msg": "Aceptado por SUNAT"},
            {"type": "03", "serie": "B999", "num": "000002", "fe": "error", "msg": "Error de validación", "err": "Monto total no coincide con la suma de items"},
            
            # Notas de Crédito
            {"type": "07", "serie": "FC99", "num": "000001", "fe": "aceptado", "msg": "Aceptado por SUNAT"},
            {"type": "07", "serie": "FC99", "num": "000002", "fe": "error", "msg": "Documento de referencia no existe", "err": "No se encontró la factura F001-123 en los registros"},
            
            # Notas de Débito
            {"type": "08", "serie": "FD99", "num": "000001", "fe": "aceptado", "msg": "Aceptado por SUNAT"},
            {"type": "08", "serie": "FD99", "num": "000002", "fe": "error", "msg": "Error interno", "err": "Error al procesar la firma digital"},
        ]

        for d in docs_to_create:
            doc_id = f"{d['serie']}-{d['num']}"
            
            # Eliminar si ya existe para evitar errores de duplicidad
            db.query(ARDocumentDetail).filter(ARDocumentDetail.Document == doc_id).delete()
            db.query(ARFENube).filter(ARFENube.serie == d['serie'], ARFENube.numero == d['num']).delete()
            db.query(ARDocument).filter(ARDocument.Document == doc_id).delete()
            
            # Mapeo de nombre legible
            nombres = {
                "01": "FACTURA",
                "03": "BOLETA",
                "07": "NOTA DE CREDITO",
                "08": "NOTA DE DEBITO"
            }
            
            # Crear cabecera
            new_doc = ARDocument(
                Document=doc_id,
                DocumentSerie=d['serie'],
                DocumentNo=d['num'],
                DocumentType=nombres.get(d['type'], d['type']),
                typeDocSun=d['type'],
                Company="ISAMISA",
                Vendor="12345678",
                VendorName="CLIENTE DE PRUEBA SAC",
                VendorRUC="20123456789",
                VendorAddress="AV. LAS PRUEBAS 123",
                DocumentDate=now,
                DocumentCurrency="LO",
                AmountNetLo=100.0,
                AmountTaxLo=18.0,
                AmountTotalLo=118.0,
                Status="1", # Activo
                fe=d['fe'],
                XLastUser="ADMIN",
                XLastDate=now
            )
            db.add(new_doc)
            
            # Crear detalle
            new_detail = ARDocumentDetail(
                Document=doc_id,
                Line=1,
                ItemCode="P001",
                Description="PRODUCTO DE PRUEBA 001",
                Unit="NIU",
                Quantity=10.0,
                Price=10.0,
                PriceTax=11.8,
                Total=118.0,
                TotalLo=118.0,
                AmountNetLo=100.0,
                TotalTaxLo=18.0
            )
            db.add(new_detail)
            
            # Crear respuesta de NubeFact
            new_nube = ARFENube(
                serie=d['serie'],
                numero=d['num'],
                aceptada_por_sunat="S" if d['fe'] == "aceptado" else "N",
                sunat_description=d['msg'],
                error=d.get('err'),
                fecha_envio=now,
                usuario_envio="ADMIN",
                enlace=f"https://api.nubefact.com/temp/{doc_id}"
            )
            db.add(new_nube)
            
        db.commit()
        print(f"Creados {len(docs_to_create)} documentos de prueba correctamente.")
        
    except Exception as e:
        db.rollback()
        print(f"Error al crear documentos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_samples()
