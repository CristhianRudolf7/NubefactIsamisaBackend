import pyodbc
from app.config import get_settings

settings = get_settings()
conn_str = settings.database_url.replace("mssql+pyodbc://", "DRIVER={ODBC Driver 18 for SQL Server};")
# Fix connection string for pyodbc
# mssql+pyodbc://user:pass@host/db?driver=...
# We need to extract components or use the engine to get a raw connection

from app.database import engine

with engine.connect() as connection:
    result = connection.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'AR_FE_Nube'")
    columns = [row[0] for row in result]
    print("Columnas en AR_FE_Nube:")
    for col in columns:
        print(f" - {col}")
