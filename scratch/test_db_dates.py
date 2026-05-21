import sys
import os
from sqlalchemy import create_engine, text

sys.path.append('/home/Rudy/proyectos/isamisa_nubefact/backend')
from app.config import get_settings

def test():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            # Query all table names
            res = conn.execute(text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")).fetchall()
            print("Tables in database:")
            for row in res:
                print(row)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
