#!/usr/bin/env python
import os
import sys
import json
from sqlalchemy import create_engine
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, ".env"))
except ImportError:
    pass

from app.config import get_settings
from app.database import SessionLocal
from app.services.document_service import DocumentService

def main():
    print("=" * 80)
    print("SIMULACIÓN Y VERIFICACIÓN DE PAYLOAD PARA NUBEFACT")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        service = DocumentService(db)
        doc_id = 'DLV1DSAS000000137919'
        
        # 1. Recuperar el documento de la base de datos
        from app.models.ventas import ARDocument
        documento = db.query(ARDocument).filter(ARDocument.Document == doc_id).first()
        
        if not documento:
            print(f"❌ Error: El documento {doc_id} no se encontró en la BD.")
            return

        # 2. Replicar la lógica de construcción de items y cabecera
        is_soles = (documento.DocumentCurrency == "LO")
        
        items = []
        for det in documento.detalles:
            item_subtotal = det.Total or 0
            item_total = det.TotalTaxLo if is_soles else (det.TotalTaxEx or 0)
            item_igv = round(max(0.0, item_total - item_subtotal), 2)
            
            items.append({
                "unidad_de_medida": service._map_unidad(det.Unit),
                "codigo": det.ItemCode or "",
                "descripcion": det.Description or "",
                "cantidad": det.Quantity or 0,
                "valor_unitario": det.Price or 0,
                "precio_unitario": det.PriceTax or 0,
                "subtotal": item_subtotal,
                "tipo_de_igv": "1",
                "igv": item_igv,
                "total": item_total
            })
            
        header_total = documento.AmountTotalLo if is_soles else (documento.AmountTotalEx or 0)
        header_gravada = documento.AmountNetLo if is_soles else (documento.AmountNetEx or 0)
        header_igv = round(max(0.0, header_total - header_gravada), 2)
        
        payload = {
            "serie": documento.DocumentSerie,
            "numero": documento.DocumentNo,
            "moneda": "1" if is_soles else "2",
            "total_gravada": header_gravada,
            "total_igv": header_igv,
            "total": header_total,
            "items": items
        }
        
        print("\n--- JSON GENERADO (SIMULADO) ---")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 80)
        print("VERIFICACIONES MATEMÁTICAS LOCALES")
        print("=" * 80)
        
        # A. Verificar Cabecera
        sum_cabecera = round(payload["total_gravada"] + payload["total_igv"], 2)
        ok_cabecera = sum_cabecera == round(payload["total"], 2)
        print(f"Cabecera: Gravada ({payload['total_gravada']}) + IGV ({payload['total_igv']}) = {sum_cabecera}")
        print(f"          Total declarado en cabecera = {payload['total']}")
        print(f"          ¿Coincide cabecera?: {'✅ SÍ' if ok_cabecera else '❌ NO'}")
        
        # B. Verificar Items
        sum_items_subtotal = round(sum(item["subtotal"] for item in items), 2)
        sum_items_igv = round(sum(item["igv"] for item in items), 2)
        sum_items_total = round(sum(item["total"] for item in items), 2)
        
        ok_line_igv = sum_items_igv == payload["total_igv"]
        ok_line_total = sum_items_total == payload["total"]
        
        print(f"\nItems Sumados: Subtotal ({sum_items_subtotal}) | IGV ({sum_items_igv}) | Total ({sum_items_total})")
        print(f"Comparación con Cabecera:")
        print(f"  - Suma de IGV de líneas ({sum_items_igv}) vs IGV Cabecera ({payload['total_igv']}) "
              f"-> {'✅ COINCIDE' if ok_line_igv else '❌ ERROR'}")
        print(f"  - Suma de Totales de líneas ({sum_items_total}) vs Total Cabecera ({payload['total']}) "
              f"-> {'✅ COINCIDE' if ok_line_total else '❌ ERROR'}")
              
        for i, item in enumerate(items):
            # Validar aritmética por línea: total - subtotal == igv
            dif = round(item["total"] - item["subtotal"], 2)
            ok_linea = dif == item["igv"]
            print(f"  * Línea {i+1}: Total ({item['total']}) - Subtotal ({item['subtotal']}) = {dif} (Declarado: {item['igv']}) -> {'✅ OK' if ok_linea else '❌ ERROR'}")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
