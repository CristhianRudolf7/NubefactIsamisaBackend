import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine
from app.models.ventas import ARDocument, ARDocumentDetail

def get_db_columns(table_name):
    query = f"""
    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{table_name}';
    """
    with engine.connect() as connection:
        result = connection.execute(text(query))
        return {row[0].lower(): (row[0], row[1], row[2]) for row in result.fetchall()}

def check_float_columns(model_class, db_table_name):
    print(f"\n--- Columnas FLOAT en {db_table_name} ---")
    db_cols = get_db_columns(db_table_name)
    if not db_cols:
        print(f"Error: No se encontró la tabla {db_table_name}.")
        return

    for column in model_class.__table__.columns:
        col_name = column.name
        col_name_lower = col_name.lower()
        python_type = str(column.type)
        
        if "FLOAT" in python_type.upper():
            if col_name_lower in db_cols:
                real_name, db_type, max_len = db_cols[col_name_lower]
                db_type_str = f"{db_type.upper()}({max_len})" if max_len else db_type.upper()
                print(f"Column '{col_name}': Python={python_type} | DB={db_type_str}")
            else:
                print(f"Column '{col_name}': Python={python_type} | DB=NO EXISTE EN BD")

def main():
    try:
        check_float_columns(ARDocument, "AR_Document")
        check_float_columns(ARDocumentDetail, "AR_DocumentDetail")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
