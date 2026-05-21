import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.database import SessionLocal
from backend.app.models.ventas import ARDocument
from datetime import datetime

db = SessionLocal()
try:
    print("--- Analizando documentos de venta cerca del 16-05-2026 ---")
    docs = db.query(ARDocument).filter(
        ARDocument.DocumentDate >= datetime(2026, 5, 14),
        ARDocument.DocumentDate <= datetime(2026, 5, 17)
    ).order_by(ARDocument.DocumentDate.desc()).all()
    
    print(f"Total encontrados: {len(docs)}")
    for d in docs[:20]:
        print(f"ID: {d.Document} | Serie-Nro: {d.DocumentSerie}-{d.DocumentNo} | Fecha DB: {d.DocumentDate} (type: {type(d.DocumentDate)}) | FE Status: {d.nube_status_web} | Necesita Aprobación: {d.necesita_aprobacion}")

finally:
    db.close()
