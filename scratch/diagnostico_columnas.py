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

def check_float_columns(model_class, db_table_name, out_file):
    out_file.write(f"\n--- Columnas FLOAT en {db_table_name} ---\n")
    db_cols = get_db_columns(db_table_name)
    if not db_cols:
        out_file.write(f"Error: No se encontró la tabla {db_table_name}.\n")
        return

    for column in model_class.__table__.columns:
        col_name = column.name
        col_name_lower = col_name.lower()
        python_type = str(column.type)
        
        if "FLOAT" in python_type.upper():
            if col_name_lower in db_cols:
                real_name, db_type, max_len = db_cols[col_name_lower]
                db_type_str = f"{db_type.upper()}({max_len})" if max_len else db_type.upper()
                out_file.write(f"Column '{col_name}': Python={python_type} | DB={db_type_str}\n")
                
                # Si en la BD es de tipo texto, es un candidato fuerte para tener 'N'
                if db_type.lower() in ('varchar', 'char', 'nvarchar', 'nchar', 'text', 'ntext'):
                    try:
                        check_query = f"SELECT COUNT(*) FROM {db_table_name} WHERE [{col_name}] = 'N'"
                        with engine.connect() as connection:
                            res = connection.execute(text(check_query)).scalar()
                            out_file.write(f"  --> ¡CONFIRMADO! Es texto y contiene 'N' en {res} filas.\n")
                    except Exception as e:
                        out_file.write(f"  --> Es texto, pero falló al consultar: {str(e)}\n")
            else:
                out_file.write(f"Column '{col_name}': Python={python_type} | DB=NO EXISTE EN BD\n")

def main():
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultado_diagnostico.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        try:
            check_float_columns(ARDocument, "AR_Document", f)
            check_float_columns(ARDocumentDetail, "AR_DocumentDetail", f)
            f.write("\nAnálisis finalizado correctamente.\n")
            print(f"Resultado guardado exitosamente en: {output_path}")
        except Exception as e:
            f.write(f"Error general: {str(e)}\n")
            print(f"Error durante la ejecución. Ver logs en: {output_path}")

if __name__ == "__main__":
    main()
