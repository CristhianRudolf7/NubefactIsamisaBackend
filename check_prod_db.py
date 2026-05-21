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
            # Query documents around May 14 to May 16
            print("--- AR_Document Samples (May 12 - May 18) ---")
            res = conn.execute(text("""
                SELECT TOP 15 Document, DocumentSerie, DocumentNo, DocumentDate, RegisterDate 
                FROM AR_Document 
                WHERE DocumentDate >= '2026-05-12 00:00:00' AND DocumentDate <= '2026-05-18 23:59:59'
                ORDER BY DocumentDate ASC
            """)).fetchall()
            for row in res:
                print(f"Doc: {row[1]}-{row[2]} | DocumentDate: {row[3]} | RegisterDate: {row[4]}")
                
    except Exception as e:
        print("Database connection error:", e)

if __name__ == "__main__":
    run_check()
