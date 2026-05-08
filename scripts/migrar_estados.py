import os
import sys
from sqlalchemy import create_engine, text
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Obtener URL de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ Error: DATABASE_URL no definida.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

def execute(sql, description):
    print(f"🚀 {description}...", end=" ", flush=True)
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
            print("✅ OK")
    except Exception as e:
        print(f"❌ ERROR: {e}")

print("--- INICIANDO MIGRACIÓN A NUBE_STATUS_WEB ---")

# 1. Crear columnas físicamente en la BD si no existen
for table in ["AR_Document", "WH_Transaction", "AP_Retencion"]:
    sql = f"IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{table}') AND name = 'nube_status_web') " \
          f"ALTER TABLE {table} ADD nube_status_web NVARCHAR(20) DEFAULT 'pendiente';"
    execute(sql, f"Creando columna en {table}")

# 2. Sincronizar datos históricos
print("\n--- SINCRONIZANDO DATOS EXISTENTES ---")

# VENTAS
sql_ventas = """
UPDATE AR_Document SET nube_status_web = 
CASE 
    WHEN EXISTS (SELECT 1 FROM ar_fe_nube n WHERE n.serie = AR_Document.DocumentSerie AND n.numero = AR_Document.DocumentNo AND n.aceptada_por_sunat = 'true') THEN 'aceptado'
    WHEN LOWER(fe) LIKE '%aceptad%' OR LOWER(fe) = 'correcto' THEN 'aceptado'
    WHEN LOWER(fe) = 'enviado' THEN 'enviado'
    WHEN LOWER(fe) LIKE '%error%' OR LEN(fe) > 20 THEN 'error'
    ELSE 'pendiente'
END
"""
execute(sql_ventas, "Procesando VENTAS")

# GUÍAS
sql_guias = """
UPDATE WH_Transaction SET nube_status_web = 
CASE 
    WHEN EXISTS (SELECT 1 FROM wh_transaction_nube n WHERE n.TransactionId = WH_Transaction.[Transaction] AND n.aceptada_por_sunat = 'true') THEN 'aceptado'
    WHEN LOWER(envio_nube) LIKE '%aceptad%' THEN 'aceptado'
    WHEN LOWER(envio_nube) LIKE '%anula%' THEN 'anulado'
    WHEN LOWER(envio_nube) = 'enviado' THEN 'enviado'
    WHEN LOWER(envio_nube) LIKE '%error%' OR LEN(envio_nube) > 20 THEN 'error'
    ELSE 'pendiente'
END
"""
execute(sql_guias, "Procesando GUÍAS")

# RETENCIONES
sql_retenciones = """
UPDATE AP_Retencion SET nube_status_web = 
CASE 
    WHEN EXISTS (SELECT 1 FROM AP_Retencion_Status s WHERE s.Retencion = AP_Retencion.Id AND s.Status = 'aceptada') THEN 'aceptado'
    WHEN LOWER(status) LIKE '%aceptad%' THEN 'aceptado'
    WHEN LOWER(status) LIKE '%anula%' THEN 'anulado'
    WHEN LOWER(status) LIKE '%enviad%' THEN 'enviado'
    WHEN LOWER(status) LIKE '%error%' THEN 'error'
    ELSE 'pendiente'
END
"""
execute(sql_retenciones, "Procesando RETENCIONES")

print("\n\033[1m✅ Migración completada.\033[0m")
