import sys
import os
from sqlalchemy import create_engine, text
from datetime import datetime

# Add current folder to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings

def run_check():
    settings = get_settings()
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            # Query server time
            time_info = conn.execute(text("SELECT GETDATE() as local_time, GETUTCDATE() as utc_time")).fetchone()
            print("--- SERVER TIME INFO ---")
            print(f"SQL Server Local Time: {time_info[0]}")
            print(f"SQL Server UTC Time:   {time_info[1]}")
            print(f"Python Local Time:     {datetime.now()}")
            print(f"Python UTC Time:       {datetime.utcnow()}")
            
            # Query documents for May 14 00:00:00 to May 16 00:00:00 (the exact API filter range)
            print("\n--- AR_Document (May 14 00:00:00 - May 16 00:00:00) ---")
            res = conn.execute(text("""
                SELECT Document, DocumentSerie, DocumentNo, DocumentDate, RegisterDate 
                FROM AR_Document 
                WHERE DocumentDate >= '2026-05-14 00:00:00' AND DocumentDate <= '2026-05-16 00:00:00'
                ORDER BY DocumentDate DESC, DocumentNo DESC
            """)).fetchall()
            print(f"Total documents found in range (14 00:00 to 16 00:00): {len(res)}")
            
            # Count per day in the matched set
            counts = {}
            for row in res:
                doc_date = row[3]
                day = doc_date.strftime("%Y-%m-%d") if doc_date else "None"
                counts[day] = counts.get(day, 0) + 1
            print("Counts per day in the returned result set:")
            for day, count in sorted(counts.items()):
                print(f"  Date: {day} | Count: {count}")
                
            # If any documents from May 16 matched, show them
            print("\nSample matching documents from May 16:")
            matches_16 = [row for row in res if row[3] and row[3].strftime("%Y-%m-%d") == "2026-05-16"]
            for row in matches_16[:10]:
                print(f"  Doc: {row[1]}-{row[2]} | DocumentDate: {row[3]} | RegisterDate: {row[4]}")
                
    except Exception as e:
        print("Database connection error:", e)

if __name__ == "__main__":
    run_check()

