#!/usr/bin/env python
import os
import sys
from sqlalchemy import create_engine, text

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT_DIR, ".env"))
except ImportError:
    pass

from app.config import get_settings

def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    doc_id = 'DLV1DSAS000000137919'
    
    print(f"Consultando montos para el documento: {doc_id}\n")
    
    with engine.connect() as conn:
        # Cabecera
        res_doc = conn.execute(text("""
            SELECT 
                Document, DocumentSerie, DocumentNo, DocumentCurrency, ExchangeRate,
                AmountNetLo, AmountNetEx, AmountTaxLo, AmountTaxEx, AmountTotalLo, AmountTotalEx
            FROM AR_Document 
            WHERE Document = :doc_id
        """), {"doc_id": doc_id}).fetchone()
        
        if not res_doc:
            print("❌ Documento no encontrado en cabecera.")
            return
            
        print("--- CABECERA (AR_Document) ---")
        print(f"DocumentCurrency: {res_doc[3]}")
        print(f"ExchangeRate:     {res_doc[4]}")
        print(f"AmountNetLo:      {res_doc[5]}")
        print(f"AmountNetEx:      {res_doc[6]}")
        print(f"AmountTaxLo:      {res_doc[7]}")
        print(f"AmountTaxEx:      {res_doc[8]}")
        print(f"AmountTotalLo:    {res_doc[9]}")
        print(f"AmountTotalEx:    {res_doc[10]}")
        
        # Detalles
        res_det = conn.execute(text("""
            SELECT 
                Line, ItemCode, Quantity, Price, PriceTax, SubTotal, 
                Tax1Rate, Tax1Lo, Tax1Ex, TotalTaxLo, TotalTaxEx, Total, TotalLo, TotalEx
            FROM AR_DocumentDetail 
            WHERE Document = :doc_id
            ORDER BY Line
        """), {"doc_id": doc_id}).fetchall()
        
        print("\n--- DETALLES (AR_DocumentDetail) ---")
        for row in res_det:
            print(f"Línea {row[0]}:")
            print(f"  - ItemCode: {row[1]}")
            print(f"  - Cantidad: {row[2]} | Price (Sin IGV): {row[3]} | PriceTax (Con IGV): {row[4]}")
            print(f"  - SubTotal: {row[5]} | Total (Línea): {row[11]}")
            print(f"  - Tax1Rate: {row[6]}% | Tax1Lo: {row[7]} | Tax1Ex: {row[8]}")
            print(f"  - TotalTaxLo: {row[9]} | TotalTaxEx: {row[10]}")
            print(f"  - TotalLo: {row[12]} | TotalEx: {row[13]}")

if __name__ == "__main__":
    main()
