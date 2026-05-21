import sys
import os
from sqlalchemy import create_engine, text

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.config import get_settings

def run_check():
    settings = get_settings()
    print("Database URL:", settings.database_url)
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            # Query column types from database metadata
            print("--- SCHEMA INFO ---")
            query_schema = """
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME IN ('AR_Document', 'WH_Transaction', 'AP_Retencion')
            AND COLUMN_NAME IN ('DocumentDate', 'TransactionDate', 'FechaTraslado', 'DRfecha')
            """
            schema_res = conn.execute(text(query_schema)).fetchall()
            for row in schema_res:
                print(f"Table: {row[0]} | Column: {row[1]} | Type in DB: {row[2]}")
            
            # Query sample rows to see raw values and their types in Python
            print("\n--- SAMPLE DATA FROM AR_Document ---")
            try:
                res_ar = conn.execute(text("SELECT TOP 3 Document, DocumentNo, DocumentSerie, DocumentDate FROM AR_Document ORDER BY DocumentDate DESC")).fetchall()
                for row in res_ar:
                    val = row[3]
                    print(f"Doc: {row[2]}-{row[1]} | DocumentDate value: {val} | Python Type: {type(val)}")
            except Exception as e:
                print("Error querying AR_Document:", e)

            print("\n--- SAMPLE DATA FROM WH_Transaction ---")
            try:
                res_wh = conn.execute(text("SELECT TOP 3 [Transaction], DocumentNo, DocumentSerie, TransactionDate, FechaTraslado FROM WH_Transaction ORDER BY TransactionDate DESC")).fetchall()
                for row in res_wh:
                    val_t = row[3]
                    val_f = row[4]
                    print(f"Guia: {row[2]}-{row[1]} | TransactionDate: {val_t} ({type(val_t)}) | FechaTraslado: {val_f} ({type(val_f)})")
            except Exception as e:
                print("Error querying WH_Transaction:", e)
                
    except Exception as e:
        print("Database connection error:", e)

if __name__ == "__main__":
    run_check()
