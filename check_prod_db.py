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
            # Query documents for May 14, 15, 16
            print("--- AR_Document (May 14 - May 16) ---")
            res = conn.execute(text("""
                SELECT Document, DocumentSerie, DocumentNo, DocumentDate, RegisterDate 
                FROM AR_Document 
                WHERE DocumentDate >= '2026-05-14 00:00:00' AND DocumentDate <= '2026-05-16 23:59:59'
                ORDER BY DocumentDate ASC, DocumentNo ASC
            """)).fetchall()
            print(f"Total documents found in range: {len(res)}")
            for row in res[:30]:  # Show first 30
                print(f"Doc: {row[1]}-{row[2]} | DocumentDate: {row[3]} | RegisterDate: {row[4]}")
                
    except Exception as e:
        print("Database connection error:", e)

if __name__ == "__main__":
    run_check()
