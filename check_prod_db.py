import sys
import os
from sqlalchemy import create_engine, text

# Add current folder to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings

def run_check():
    settings = get_settings()
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            # Count AR_Document by year
            print("--- AR_Document Years ---")
            res_ar = conn.execute(text("""
                SELECT YEAR(DocumentDate) as anio, COUNT(*) as cant 
                FROM AR_Document 
                GROUP BY YEAR(DocumentDate) 
                ORDER BY anio DESC
            """)).fetchall()
            for row in res_ar:
                print(f"Year: {row[0]} | Count: {row[1]}")
                
            # Count WH_Transaction by year
            print("\n--- WH_Transaction Years ---")
            res_wh = conn.execute(text("""
                SELECT YEAR(TransactionDate) as anio, COUNT(*) as cant 
                FROM WH_Transaction 
                GROUP BY YEAR(TransactionDate) 
                ORDER BY anio DESC
            """)).fetchall()
            for row in res_wh:
                print(f"Year: {row[0]} | Count: {row[1]}")
                
            # Query the latest 5 guides in 2026
            print("\n--- Latest 5 guides in year 2026 ---")
            res_guides = conn.execute(text("""
                SELECT TOP 5 [Transaction], DocumentNo, DocumentSerie, TransactionDate, FechaTraslado 
                FROM WH_Transaction 
                WHERE TransactionDate >= '2026-01-01' AND TransactionDate < '2027-01-01'
                ORDER BY TransactionDate DESC
            """)).fetchall()
            for row in res_guides:
                print(f"Guia: {row[2]}-{row[1]} | TransactionDate: {row[3]} | FechaTraslado: {row[4]}")
                
    except Exception as e:
        print("Database connection error:", e)

if __name__ == "__main__":
    run_check()
