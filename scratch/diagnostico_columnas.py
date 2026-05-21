import sys
from sqlalchemy import text, inspect
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

def check_table_mismatches(model_class, db_table_name):
    print(f"\n--- Analizando tabla: {db_table_name} ---")
    db_cols = get_db_columns(db_table_name)
    if not db_cols:
        print(f"Error: No se encontró la tabla {db_table_name} en la base de datos.")
        return

    inspector = inspect(engine)
    
    # Obtener columnas del modelo de SQLAlchemy
    mismatches = []
    for column in model_class.__table__.columns:
        col_name = column.name
        col_name_lower = col_name.lower()
        
        # Verificar si la columna existe en la BD
        if col_name_lower not in db_cols:
            continue
            
        real_name, db_type, max_len = db_cols[col_name_lower]
        python_type = column.type
        
        # Si en Python es Float o Integer, pero en la BD es de tipo string/texto
        is_python_numeric = "Float" in str(python_type) or "Integer" in str(python_type) or "Numeric" in str(python_type)
        is_db_string = db_type.lower() in ('varchar', 'char', 'nvarchar', 'nchar', 'text', 'ntext')
        
        if is_python_numeric and is_db_string:
            print(f"⚠️ CONFLICTO DETECTADO en columna '{col_name}':")
            print(f"   - En Python (modelo): {python_type}")
            print(f"   - En Base de Datos (real): {db_type.upper()}({max_len if max_len else ''})")
            
            # Intentar verificar si contiene el valor 'N'
            try:
                check_query = f"SELECT COUNT(*) FROM {db_table_name} WHERE [{col_name}] = 'N'"
                with engine.connect() as connection:
                    res = connection.execute(text(check_query)).scalar()
                    print(f"   - Filas que contienen 'N' en esta columna: {res}")
            except Exception as e:
                print(f"   - No se pudo consultar valores: {str(e)}")
            
            mismatches.append(col_name)
            
    if not mismatches:
        print("✅ No se detectaron discrepancias de tipo numérico a string.")
    else:
        print(f"Total de conflictos en {db_table_name}: {len(mismatches)}")

def main():
    try:
        check_table_mismatches(ARDocument, "AR_Document")
        check_table_mismatches(ARDocumentDetail, "AR_DocumentDetail")
    except Exception as e:
        print(f"Error de conexión o ejecución: {str(e)}")

if __name__ == "__main__":
    main()
